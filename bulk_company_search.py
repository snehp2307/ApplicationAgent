"""
============================================
BULK COMPANY SEARCH MODULE
============================================
Searches the web for 100-300 companies hiring
for the target job role using Tavily Search API.

Now experience-aware: generates different search
queries for freshers vs experienced candidates
to find level-appropriate companies.
"""

import time
import random
from tavily import TavilyClient
import config


# ============================================
# EXPERIENCE-LEVEL SEARCH KEYWORDS
# ============================================

FRESHER_KEYWORDS = [
    "internship", "entry level", "fresher", "trainee",
    "junior", "associate", "graduate", "campus hiring",
    "entry-level", "new graduate",
]

JUNIOR_KEYWORDS = [
    "junior", "associate", "early career", "1-2 years",
    "entry level", "analyst", "coordinator",
]

MID_KEYWORDS = [
    "mid level", "mid-level", "3-5 years experience",
    "specialist", "experienced", "professional",
]

SENIOR_KEYWORDS = [
    "senior", "lead", "principal", "manager",
    "head of", "director", "5+ years", "expert",
]


def _get_level_keywords(experience_level: str, years: int) -> list[str]:
    """Return search keyword modifiers based on candidate experience level."""
    if experience_level == "fresher":
        return FRESHER_KEYWORDS
    elif years <= 2:
        return JUNIOR_KEYWORDS
    elif years <= 5:
        return MID_KEYWORDS
    else:
        return SENIOR_KEYWORDS


def _generate_search_queries(
    job_role: str,
    location: str,
    experience_level: str,
    years_of_experience: int,
    industry: str,
) -> list[str]:
    """
    Generate diverse, experience-aware search queries.
    Freshers get internship/entry-level queries.
    Experienced candidates get seniority-matched queries.
    """
    location_str = f" in {location}" if location else ""
    industry_str = f" {industry}" if industry else ""
    level_keywords = _get_level_keywords(experience_level, years_of_experience)

    queries = []

    # --- Level-specific queries (highest priority) ---
    for kw in level_keywords[:6]:
        queries.append(f"{kw} {job_role} jobs{location_str} 2025 2026")
        queries.append(f"companies hiring {kw} {job_role}{location_str}")

    # --- Industry-filtered queries ---
    if industry:
        queries.extend([
            f"{industry} companies hiring {job_role}{location_str}",
            f"{job_role} jobs {industry} sector{location_str}",
            f"top {industry} companies {job_role} openings{location_str}",
            f"{industry} {job_role} careers{location_str}",
        ])

    # --- General company discovery ---
    queries.extend([
        f"companies hiring {job_role}{location_str} careers email",
        f"top companies recruiting {job_role}{location_str}",
        f"{job_role} open positions apply{location_str}",
        f"best companies for {job_role}{location_str}",
        f"startups hiring {job_role}{location_str}",
        f"enterprise companies hiring {job_role}{location_str}",
        f"mid-size companies hiring {job_role}{location_str}",
        f"who is hiring {job_role}{location_str} this month",
        f"growing companies {job_role} roles{location_str}",
        f"{job_role} jobs{location_str} company names list",
        f"top employers {job_role}{location_str} 2025",
        f"companies looking for {job_role}{location_str}",
        f"hiring {job_role} professionals{location_str}",
        f"{job_role} vacancies{location_str} employer",
        f"new {job_role} positions{location_str} companies",
    ])

    # --- Fresher-specific extras ---
    if experience_level == "fresher":
        queries.extend([
            f"campus hiring {job_role}{location_str}",
            f"fresher {job_role} walk in{location_str}",
            f"graduate {job_role} program{location_str}",
            f"{job_role} internship companies{location_str}",
            f"companies offering {job_role} training{location_str}",
        ])

    # --- Experienced-specific extras ---
    if experience_level == "experienced" and years_of_experience >= 3:
        queries.extend([
            f"{job_role} team lead opportunities{location_str}",
            f"experienced {job_role} hiring{location_str}",
            f"{job_role} specialist roles{location_str}",
        ])

    # Industry + level combo queries
    if industry:
        for kw in level_keywords[:3]:
            queries.append(f"{industry} {kw} {job_role}{location_str}")

    # Deduplicate and shuffle
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)
    random.shuffle(unique)
    return unique


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

    Now experience-aware — freshers get internship/entry-level results,
    experienced candidates get seniority-matched companies.

    Args:
        state: LangGraph state containing candidate profile fields

    Returns:
        Updated state with 'companies' list
    """
    job_role = state["job_role"]
    location = state.get("location", "")
    experience_level = state.get("experience_level", "fresher")
    years_of_experience = state.get("years_of_experience", 0)
    industry = state.get("industry", "")
    seniority = state.get("seniority", "")
    target_count = config.TARGET_COMPANY_COUNT

    print(f"\n🔍 BULK COMPANY SEARCH")
    print(f"   Role: {job_role}")
    print(f"   Level: {seniority}")
    print(f"   Location: {location or 'Any'}")
    print(f"   Industry: {industry or 'Any'}")
    print(f"   Target: {target_count} companies")
    print("=" * 50)

    # Initialize Tavily client
    client = TavilyClient(api_key=config.TAVILY_API_KEY)

    # Generate experience-aware search queries
    queries = _generate_search_queries(
        job_role, location, experience_level, years_of_experience, industry
    )
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
