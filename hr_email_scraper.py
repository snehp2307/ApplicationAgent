"""
============================================
HR EMAIL SCRAPER MODULE
============================================
Finds HR / careers / recruiting email addresses
for each company discovered via LinkedIn-first search.

Companies arrive with resolved domains from the
bulk search module. This scraper uses:
  1. Website scraping for contact/careers pages
  2. Tavily search for public email addresses
  3. Common email pattern generation (fallback)
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import config


def _generate_email_patterns(domain: str) -> list[str]:
    """Generate common HR/careers email addresses for a domain."""
    patterns = []
    for pattern in config.EMAIL_PATTERNS:
        email = pattern.format(domain=domain)
        patterns.append(email)
    return patterns


def _scrape_emails_from_url(url: str, timeout: int = 10) -> list[str]:
    """
    Scrape email addresses from a webpage.
    Looks for mailto: links and email patterns in page text.
    """
    emails = set()
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Find mailto: links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "mailto:" in href:
                email = href.replace("mailto:", "").split("?")[0].strip()
                if _is_valid_email_format(email):
                    emails.add(email.lower())

        # Find emails in page text using regex
        text = soup.get_text()
        found = re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            text
        )
        for email in found:
            if _is_valid_email_format(email):
                emails.add(email.lower())

    except Exception:
        pass

    return list(emails)


def _is_valid_email_format(email: str) -> bool:
    """Basic email format validation."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False

    # Filter out common non-HR emails
    skip_prefixes = [
        "noreply", "no-reply", "donotreply", "mailer-daemon",
        "postmaster", "webmaster", "admin@", "support@",
        "sales@", "marketing@", "billing@", "abuse@",
    ]
    email_lower = email.lower()
    for prefix in skip_prefixes:
        if email_lower.startswith(prefix):
            return False

    # Filter out image/file extensions mistakenly captured
    skip_extensions = [".png", ".jpg", ".gif", ".svg", ".css", ".js"]
    for ext in skip_extensions:
        if ext in email_lower:
            return False

    return True


def _search_for_emails(company_name: str, domain: str) -> list[str]:
    """Use Tavily to search for company HR/careers emails."""
    emails = set()
    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)

        queries = [
            f"{company_name} HR email contact careers",
            f"{company_name} recruitment email {domain}",
        ]

        for query in queries:
            try:
                results = client.search(query=query, max_results=5)
                for result in results.get("results", []):
                    content = f"{result.get('title', '')} {result.get('content', '')}"
                    found = re.findall(
                        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                        content
                    )
                    for email in found:
                        if _is_valid_email_format(email):
                            emails.add(email.lower())
                time.sleep(random.uniform(0.5, 1.5))
            except Exception:
                continue

    except Exception:
        pass

    return list(emails)


def _prioritize_emails(emails: list[str], domain: str) -> list[str]:
    """
    Sort emails by relevance priority.
    HR/careers emails from the company domain rank highest.
    """
    priority_prefixes = [
        "careers", "hr", "jobs", "recruiting", "talent",
        "hiring", "recruitment", "apply", "resume", "people",
    ]

    def score(email: str) -> int:
        s = 0
        local = email.split("@")[0].lower()
        email_domain = email.split("@")[1].lower()

        # Prefer emails from the company's own domain
        if domain.lower() in email_domain:
            s += 100

        # Score by prefix relevance
        for i, prefix in enumerate(priority_prefixes):
            if prefix in local:
                s += (len(priority_prefixes) - i) * 10
                break

        return s

    return sorted(emails, key=score, reverse=True)


def hr_email_scraper(state: dict) -> dict:
    """
    LANGGRAPH NODE: Find HR/careers emails for each company.

    For each company, tries multiple strategies:
    1. Scrape company website contact/careers pages
    2. Search for public email addresses
    3. Generate common email patterns as fallback

    Args:
        state: LangGraph state with 'companies' list

    Returns:
        Updated state with emails added to each company
    """
    companies = state["companies"]
    print(f"\n📧 HR EMAIL SCRAPER")
    print(f"   Processing {len(companies)} companies...")
    print("=" * 50)

    for i, company in enumerate(companies):
        domain = company.get("domain", "")
        company_name = company.get("company_name", "")
        website = company.get("website", "")

        print(f"   [{i+1}/{len(companies)}] {company_name} ({domain})...", end=" ")

        all_emails = set()

        # Strategy 1: Scrape company website
        if website:
            pages_to_try = [
                website,
                f"{website}/contact",
                f"{website}/about",
                f"{website}/careers",
                f"{website}/jobs",
                f"{website}/about-us",
                f"{website}/contact-us",
            ]

            for page_url in pages_to_try:
                scraped = _scrape_emails_from_url(page_url, timeout=8)
                all_emails.update(scraped)

                # Don't hammer the server
                if scraped:
                    break
                time.sleep(random.uniform(0.3, 0.8))

        # Strategy 2: Web search for emails (every 5th company to save API quota)
        if len(all_emails) == 0 and i % 5 == 0:
            searched = _search_for_emails(company_name, domain)
            all_emails.update(searched)

        # Strategy 3: Generate common patterns as fallback
        if len(all_emails) == 0:
            patterns = _generate_email_patterns(domain)
            # Add the top 3 most likely patterns
            all_emails.update(patterns[:3])

        # Prioritize and store
        email_list = _prioritize_emails(list(all_emails), domain)
        company["emails"] = email_list
        # Use the best email as primary
        company["primary_email"] = email_list[0] if email_list else ""

        status = f"✅ {len(email_list)} emails" if email_list else "⚠ No emails"
        print(status)

        # Rate limiting
        if i % 10 == 0 and i > 0:
            time.sleep(random.uniform(1, 3))

    # Count stats
    with_emails = sum(1 for c in companies if c.get("primary_email"))
    print(f"\n   📊 EMAIL SCRAPING COMPLETE:")
    print(f"      Companies with emails: {with_emails}/{len(companies)}")

    state["companies"] = companies
    return state
