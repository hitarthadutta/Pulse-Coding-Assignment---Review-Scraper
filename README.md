Pulse-Coding-Assignment: Review-Scraper
========================

Overview
--------
PulseAI is a Python-based command-line tool designed to scrape SaaS product reviews from popular platforms such as G2, Capterra, and TrustRadius.

The script allows users to provide key inputs including the company name, start date, end date, and review source, making the scraping process flexible and configurable.

Based on the selected inputs, the tool automatically collects all relevant reviews within the specified time range while handling pagination efficiently.

Each review is parsed and converted into a structured JSON format, containing the review title, description, date, rating, reviewer details, and other available metadata.

To handle dynamically loaded web pages and bot-protected content, the project supports both Requests + BeautifulSoup scraping and an optional Selenium fallback mode.

The codebase follows a modular design where each review source has its own scraper module, allowing easy maintenance and future extension to additional platforms.

Input validation and error handling are implemented to manage invalid company names, incorrect date ranges, or unavailable pages gracefully.

The final output can be directly used for downstream tasks such as sentiment analysis, market research, or product comparison studies.

The project emphasizes clean code structure, scalability, and practical applicability, making it suitable for academic assignments as well as real-world data collection use cases.

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
