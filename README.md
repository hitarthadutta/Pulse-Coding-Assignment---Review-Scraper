PulseAI - Review Scraper
========================

Overview
--------
This project provides a CLI script to scrape product reviews for a given company from G2, Capterra, and TrustRadius (third source). The script accepts a company name, start date, end date, and source (g2, capterra, trustradius, or all), and writes a JSON file with the matching reviews.

Notes
-----
- Public review sites often use dynamic rendering and bot-protection. The script tries `requests` + `BeautifulSoup` first and can fall back to Selenium when needed (`--use-selenium`).
- Parsers are heuristic and may need adjustments if the target site structure changes.

Quickstart
----------
1. Create a virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

2. Run the scraper (example):

```bash
python main.py --company "Slack" --start 2023-01-01 --end 2024-12-31 --source all --output slack_reviews.json
```

3. If `requests` fails to extract content, try Selenium (requires Chrome installed):

```bash
python main.py --company "Slack" --start 2023-01-01 --end 2024-12-31 --source all --use-selenium
```

Files
-----
- `main.py` - main scraper CLI implementation
- `requirements.txt` - Python dependencies
- `sample_output.json` - example output structure

Limitations & Next Steps
------------------------
- Exact HTML selectors may need tuning per site; this script aims to be a robust starting point.
- For production scraping consider respectful rate-limiting, retries, and complying with site terms of service.

If you want, I can run a quick test scrape (demo mode) or refine selectors for a specific company now.
