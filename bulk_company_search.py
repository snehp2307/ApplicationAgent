"""
============================================
BULK COMPANY SEARCH MODULE
============================================
Searches the web for 100-300 companies hiring
for the target job role using Tavily Search API.
Generates diverse search queries to maximize
company discovery across multiple sources.
"""

import time
import random
from tavily import TavilyClient
import config


def _generate_search_queries(job_role: str, location: str) -> list[str]:
    """
    Generate diverse search queries to find many companies.
    Uses different angles to maximize unique company discovery.
    """
    location_str = f" in {location}" if location else ""
    location_str_alt = f" {location}" if location else ""

    queries = [
        # Direct hiring searches
        f"companies hiring {job_role}{location_str} 2025 2026",
        f"{job_role} job openings{location_str} careers email",
        f"top companies recruiting {job_role}{location_str}",
        f"{job_role} positions available{location_str}",

        # Careers page focused
        f"{job_role} careers page apply now{location_str}",
        f"site:careers hiring {job_role}{location_str_alt}",
        f"{job_role} open positions apply{location_str}",

        # LinkedIn & job board style
        f"{job_role} hiring now{location_str} company list",
        f"best companies for {job_role}{location_str}",
        f"{job_role} employer{location_str} job listing",

        # Industry specific
        f"startups hiring {job_role}{location_str}",
        f"tech companies {job_role} jobs{location_str}",
        f"enterprise companies hiring {job_role}{location_str}",
        f"fortune 500 {job_role} positions{location_str}",

        # HR / recruiting focused
        f"{job_role} recruiter contact{location_str}",
        f"HR department hiring {job_role}{location_str}",
        f"talent acquisition {job_role}{location_str}",

        # Domain specific
        f"{job_role} remote jobs companies hiring",
        f"mid-size companies hiring {job_role}{location_str}",
        f"{job_role} job fair companies{location_str}",

        # Additional variety
        f"who is hiring {job_role}{location_str} this month",
        f"new {job_role} positions{location_str} companies",
        f"{job_role} team openings{location_str}",
        f"growing companies {job_role} roles{location_str}",

        # Job board aggregation
        f"{job_role} jobs{location_str} company names list",
        f"top employers {job_role}{location_str} 2025",
        f"{job_role} opportunities{location_str} apply",
        f"companies looking for {job_role}{location_str}",
        f"{job_role} vacancies{location_str} employer",
        f"hiring {job_role} professionals{location_str}",
    ]

    # Shuffle to vary the search pattern
    random.shuffle(queries)
    return queries


def _extract_companies_from_results(results: list[dict]) -> list[dict]:
    """
    Extract company names and domains from Tavily search results.
    Parses titles and URLs to identify unique companies.
    """
    companies = []
    seen_domains = set()

    for result in results:
        url = result.get("url", "")
        title = result.get("title", "")
        content = result.get("content", "")

        # Extract domain from URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")

            # Skip common non-company domains
            skip_domains = [
                "linkedin.com", "indeed.com", "glassdoor.com", "monster.com",
                "ziprecruiter.com", "naukri.com", "google.com", "youtube.com",
                "twitter.com", "facebook.com", "reddit.com", "quora.com",
                "wikipedia.org", "medium.com", "github.com", "stackoverflow.com",
                "wellfound.com", "angellist.com", "lever.co", "greenhouse.io",
                "workday.com", "careers-page.com", "simplyhired.com",
                "careerbuilder.com", "dice.com", "flexjobs.com",
            ]

            if domain in skip_domains or not domain:
                # Still try to extract company names from the content
                _extract_company_names_from_text(title, content, companies, seen_domains)
                continue

            if domain not in seen_domains:
                seen_domains.add(domain)
                # Clean company name from domain
                company_name = _clean_company_name(domain, title)
                companies.append({
                    "company_name": company_name,
                    "domain": domain,
                    "website": f"https://{domain}",
                    "source_url": url,
                    "snippet": content[:200] if content else "",
                })
        except Exception:
            continue

    return companies


def _extract_company_names_from_text(title: str, content: str, companies: list, seen: set):
    """
    Try to extract company names from job listing text when the URL
    is a job board (not the company's own site).
    """
    # Common patterns in job board titles: "Company Name - Job Title" or "Job Title at Company Name"
    import re

    text = f"{title} {content}"

    # Pattern: "at CompanyName" or "@ CompanyName"
    patterns = [
        r"(?:at|@)\s+([A-Z][A-Za-z0-9\s&.,-]+?)(?:\s*[-–|]|\s*$)",
        r"([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,3})\s+is\s+hiring",
        r"([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,3})\s+careers",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            name = match.strip()
            if len(name) > 2 and name.lower() not in seen:
                # Generate a plausible domain
                domain_guess = name.lower().replace(" ", "").replace("&", "and")
                domain_guess = re.sub(r"[^a-z0-9]", "", domain_guess) + ".com"
                if domain_guess not in seen:
                    seen.add(domain_guess)
                    companies.append({
                        "company_name": name,
                        "domain": domain_guess,
                        "website": f"https://{domain_guess}",
                        "source_url": "",
                        "snippet": text[:200],
                    })


def _clean_company_name(domain: str, title: str) -> str:
    """Generate a readable company name from a domain or title."""
    # Try to get name from title first
    if title:
        # Remove common suffixes from titles
        for sep in [" - ", " | ", " – ", " — ", " · "]:
            parts = title.split(sep)
            if len(parts) >= 2:
                # Usually company name is first or last part
                candidate = parts[0].strip()
                if len(candidate) > 2 and len(candidate) < 50:
                    return candidate

    # Fall back to domain-based name
    name = domain.split(".")[0]
    # Capitalize
    name = name.replace("-", " ").replace("_", " ").title()
    return name


def bulk_company_search(state: dict) -> dict:
    """
    LANGGRAPH NODE: Search for 100-300 companies hiring for the target role.

    Uses Tavily Search API with multiple diverse queries to discover
    as many unique companies as possible in a single execution.

    Args:
        state: LangGraph state containing 'job_role' and 'location'

    Returns:
        Updated state with 'companies' list
    """
    job_role = state["job_role"]
    location = state.get("location", "")
    target_count = config.TARGET_COMPANY_COUNT

    print(f"\n🔍 BULK COMPANY SEARCH")
    print(f"   Role: {job_role}")
    print(f"   Location: {location or 'Any'}")
    print(f"   Target: {target_count} companies")
    print("=" * 50)

    # Initialize Tavily client
    client = TavilyClient(api_key=config.TAVILY_API_KEY)

    # Generate search queries
    queries = _generate_search_queries(job_role, location)
    all_companies = []
    seen_domains = set()

    for i, query in enumerate(queries):
        # Stop if we have enough companies
        if len(all_companies) >= target_count:
            print(f"\n   ✅ Reached target of {target_count} companies!")
            break

        print(f"   [{i+1}/{len(queries)}] Searching: {query[:60]}...")

        try:
            # Run search
            results = client.search(
                query=query,
                max_results=20,
                search_depth="advanced",
                include_domains=[],
                exclude_domains=[
                    "linkedin.com", "indeed.com", "glassdoor.com",
                    "youtube.com", "wikipedia.org", "reddit.com",
                ],
            )

            search_results = results.get("results", [])
            new_companies = _extract_companies_from_results(search_results)

            # Add only new unique companies
            added = 0
            for company in new_companies:
                if company["domain"] not in seen_domains:
                    seen_domains.add(company["domain"])
                    all_companies.append(company)
                    added += 1

            print(f"         Found {added} new companies (Total: {len(all_companies)})")

            # Small delay between searches to be polite
            time.sleep(random.uniform(1, 3))

        except Exception as e:
            print(f"         ⚠ Search error: {str(e)[:80]}")
            time.sleep(2)
            continue

    # Trim to target count
    if len(all_companies) > target_count:
        all_companies = all_companies[:target_count]

    print(f"\n   📊 SEARCH COMPLETE: Found {len(all_companies)} unique companies")

    state["companies"] = all_companies
    state["total_found"] = len(all_companies)
    return state
