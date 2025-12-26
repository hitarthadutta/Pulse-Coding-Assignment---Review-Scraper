import argparse
import json
import sys
from datetime import datetime
from dateutil import parser as dateparser
from time import sleep
from urllib.parse import quote_plus, urljoin

import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def parse_args():
    p = argparse.ArgumentParser(description="Scrape reviews from G2, Capterra, and TrustRadius")
    p.add_argument("--company", required=True, help="Company name to search for")
    p.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    p.add_argument("--source", default="all", choices=["g2", "capterra", "trustradius", "all"], help="Source to scrape")
    p.add_argument("--output", default="reviews.json", help="Output JSON file")
    p.add_argument("--use-selenium", action="store_true", help="Use Selenium browser when necessary")
    p.add_argument("--proxy", default=None, help="Optional proxy URL (e.g. http://host:port)")
    return p.parse_args()


def parse_date(dstr):
    try:
        return dateparser.parse(dstr).date()
    except Exception:
        raise ValueError(f"Invalid date: {dstr}")


def create_session(retries=3, backoff=0.5, status_forcelist=(429, 500, 502, 503, 504), proxies=None):
    s = requests.Session()
    retries_obj = Retry(total=retries, backoff_factor=backoff, status_forcelist=status_forcelist, allowed_methods=["GET", "POST"])
    s.mount("https://", HTTPAdapter(max_retries=retries_obj))
    s.mount("http://", HTTPAdapter(max_retries=retries_obj))
    s.headers.update(HEADERS)
    if proxies:
        s.proxies.update(proxies)
    return s


def fetch(url, use_selenium=False, session=None, proxies=None):
    if session is None:
        session = create_session()

    # Try requests first
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 403 and SELENIUM_AVAILABLE:
            # Let Selenium try to render when blocked
            use_selenium = True
        else:
            r.raise_for_status()
            return r.text
    except requests.HTTPError as e:
        # If blocked, fall back to selenium if available
        if getattr(e.response, "status_code", None) == 403 and SELENIUM_AVAILABLE:
            use_selenium = True
        else:
            raise

    if use_selenium and SELENIUM_AVAILABLE:
        opts = Options()
        opts.headless = True
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
            try:
                driver.get(url)
                sleep(2)
                html = driver.page_source
            finally:
                driver.quit()
            return html
        except Exception as e:
            # If Selenium fails for any reason, surface a clear error
            raise RuntimeError(f"Selenium fetch failed: {e}")
    # If no selenium or still failed, raise
    raise RuntimeError(f"Unable to fetch URL: {url}")


def g2_search_company_link(company, use_selenium=False, session=None, proxies=None):
    q = quote_plus(company)
    url = f"https://www.g2.com/search?q={q}"
    html = fetch(url, use_selenium=use_selenium, session=session, proxies=proxies)
    soup = BeautifulSoup(html, "html.parser")
    # Heuristic: look for product/company link
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/products/") or "/products/" in href or "/product/" in href:
            return urljoin("https://www.g2.com", href)
    return None


def capterra_search_company_link(company, use_selenium=False, session=None, proxies=None):
    q = quote_plus(company)
    # Try several search endpoints and fallback to slugified direct product path
    candidates = [
        f"https://www.capterra.com/search?search={q}",
        f"https://www.capterra.com/search?query={q}",
    ]

    # slugify company -> try /p/<slug> and /software/<slug>
    def slugify(name: str) -> str:
        s = name.lower()
        s = ''.join(c for c in s if c.isalnum() or c.isspace() or c == '-')
        s = '-'.join(s.split())
        return s

    slug = slugify(company)
    candidates.extend([
        f"https://www.capterra.com/p/{slug}",
        f"https://www.capterra.com/software/{slug}",
    ])

    for url in candidates:
        try:
            html = fetch(url, use_selenium=use_selenium, session=session, proxies=proxies)
        except Exception:
            continue
        soup = BeautifulSoup(html, "html.parser")
        # Look for product/result links - patterns vary
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/p") or "/product/" in href or "/software/" in href or href.startswith("/vendor/"):
                return urljoin("https://www.capterra.com", href)
        # check for canonical/meta as fallback
        can = soup.find("link", rel="canonical")
        if can and can.get("href"):
            return can.get("href")
    return None


def trustradius_search_company_link(company, use_selenium=False, session=None, proxies=None):
    q = quote_plus(company)
    url = f"https://www.trustradius.com/search?query={q}"
    html = fetch(url, use_selenium=use_selenium, session=session, proxies=proxies)
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/products/") or "/products/" in href or "/product/" in href:
            return urljoin("https://www.trustradius.com", href)
    return None


def parse_reviews_from_soup(soup, source):
    reviews = []
    # More targeted heuristics: look for known review containers
    candidates = []
    candidates.extend(soup.find_all(attrs={"data-review-id": True}))
    candidates.extend(soup.find_all(class_=lambda c: c and "review" in c.lower()))
    candidates.extend(soup.select("div.g2-review, div.c-review, div.review-card, article"))

    seen = set()
    for el in candidates:
        try:
            html_text = str(el)
        except Exception:
            continue
        if html_text in seen:
            continue
        seen.add(html_text)
        text = el.get_text(separator=" ", strip=True)
        if not text or len(text) < 40:
            continue
        # title heuristics
        title = None
        for h in ("h3", "h4", "h2"):
            hh = el.find(h)
            if hh:
                title = hh.get_text(strip=True)
                break
        # date heuristics
        date = None
        for time_el in el.find_all(["time", "span", "p"]):
            st = time_el.get_text(strip=True)
            try:
                dt = dateparser.parse(st, fuzzy=True)
                date = dt.date()
                break
            except Exception:
                continue
        # rating / reviewer
        rating = None
        reviewer = None
        text_tokens = [t.strip() for t in el.get_text(separator=" | ").split("|")]
        for token in text_tokens:
            if token.endswith("/5") or token.endswith(" out of 5") or token.lower().startswith("rating"):
                rating = token
                break

        review = {
            "title": title or (text[:120] + "...") if text else "",
            "description": text,
            "date": date.isoformat() if date else None,
            "source": source,
            "additional": {
                "rating": rating,
                "reviewer": reviewer,
            },
        }
        reviews.append(review)

    # dedupe
    unique = []
    seen_desc = set()
    for r in reviews:
        desc = r.get("description")
        if not desc or desc in seen_desc:
            continue
        seen_desc.add(desc)
        unique.append(r)
    return unique


def _scrape_with_pagination(start_url, source, start_date, end_date, use_selenium=False, session=None, proxies=None):
    reviews = []
    next_url = start_url
    visited = set()
    while next_url and next_url not in visited:
        visited.add(next_url)
        try:
            html = fetch(next_url, use_selenium=use_selenium, session=session, proxies=proxies)
        except Exception as e:
            print(f"Error fetching page {next_url}: {e}")
            break
        soup = BeautifulSoup(html, "html.parser")
        reviews.extend(parse_reviews_from_soup(soup, source))
        # find next link
        next_link = None
        # common patterns
        a = soup.find("a", string=lambda s: s and "next" in s.lower())
        if a and a.get("href"):
            next_link = urljoin(next_url, a.get("href"))
        elif soup.find("link", rel="next"):
            nl = soup.find("link", rel="next").get("href")
            next_link = urljoin(next_url, nl)
        else:
            # try pagination class
            nxt = soup.select_one("a.pagination-next, a.next")
            if nxt and nxt.get("href"):
                next_link = urljoin(next_url, nxt.get("href"))

        next_url = next_link
        # polite pause
        sleep(0.8)

    # filter by date
    filtered = []
    for r in reviews:
        try:
            if not r.get("date"):
                filtered.append(r)
            else:
                d = dateparser.parse(r["date"]).date()
                if start_date <= d <= end_date:
                    filtered.append(r)
        except Exception:
            filtered.append(r)
    return filtered


def scrape_g2(company, start_date, end_date, use_selenium=False, session=None, proxies=None):
    print(f"[G2] searching for company page: {company}")
    link = g2_search_company_link(company, use_selenium=use_selenium, session=session, proxies=proxies)
    if not link:
        print("[G2] Company page not found")
        return []
    print(f"[G2] found: {link}")
    return _scrape_with_pagination(link, "g2", start_date, end_date, use_selenium=use_selenium, session=session, proxies=proxies)


def scrape_capterra(company, start_date, end_date, use_selenium=False, session=None, proxies=None):
    print(f"[Capterra] searching for company page: {company}")
    link = capterra_search_company_link(company, use_selenium=use_selenium, session=session, proxies=proxies)
    if not link:
        print("[Capterra] Company page not found")
        return []
    print(f"[Capterra] found: {link}")
    return _scrape_with_pagination(link, "capterra", start_date, end_date, use_selenium=use_selenium, session=session, proxies=proxies)


def scrape_trustradius(company, start_date, end_date, use_selenium=False, session=None, proxies=None):
    print(f"[TrustRadius] searching for company page: {company}")
    link = trustradius_search_company_link(company, use_selenium=use_selenium, session=session, proxies=proxies)
    if not link:
        print("[TrustRadius] Company page not found")
        return []
    print(f"[TrustRadius] found: {link}")
    return _scrape_with_pagination(link, "trustradius", start_date, end_date, use_selenium=use_selenium, session=session, proxies=proxies)


def main():
    args = parse_args()
    try:
        start_date = parse_date(args.start)
        end_date = parse_date(args.end)
    except ValueError as e:
        print(e)
        sys.exit(1)

    use_selenium = args.use_selenium
    if use_selenium and not SELENIUM_AVAILABLE:
        print("Selenium or webdriver-manager not available; install requirements and retry with --use-selenium")
        use_selenium = False

    proxies = None
    if getattr(args, "proxy", None):
        proxies = {"http": args.proxy, "https": args.proxy}

    session = create_session(proxies=proxies)

    results = []
    srcs = [args.source] if args.source != "all" else ["g2", "capterra", "trustradius"]
    for s in srcs:
        try:
            if s == "g2":
                results.extend(scrape_g2(args.company, start_date, end_date, use_selenium=use_selenium, session=session, proxies=proxies))
            elif s == "capterra":
                results.extend(scrape_capterra(args.company, start_date, end_date, use_selenium=use_selenium, session=session, proxies=proxies))
            elif s == "trustradius":
                results.extend(scrape_trustradius(args.company, start_date, end_date, use_selenium=use_selenium, session=session, proxies=proxies))
        except Exception as e:
            print(f"Error scraping {s}: {e}")

    out = {
        "company": args.company,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "source": args.source,
        "reviews": results,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(results)} reviews to {args.output}")


if __name__ == "__main__":
    main()
