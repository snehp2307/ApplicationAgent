"""
============================================
BULK COMPANY SEARCH MODULE — LINKEDIN-FIRST
============================================
Discovers companies with relevant job openings
by searching LinkedIn via Tavily Search API.

Strategy:
  1. PRIMARY: LinkedIn job listings (via Tavily)
  2. FALLBACK: General web search (only if needed)

Extracts per company:
  - Company name
  - LinkedIn job title
  - LinkedIn job URL
  - Seniority fit
  - Location
  - Match confidence score
"""

import re
import time
import random
from urllib.parse import urlparse
from tavily import TavilyClient
import config


# ============================================
# SENIORITY KEYWORDS PER LEVEL
# ============================================

LEVEL_SEARCH_TERMS = {
    "fresher": [
        "intern", "internship", "entry level", "entry-level",
        "fresher", "trainee", "graduate", "associate", "junior",
    ],
    "junior": [
        "junior", "associate", "entry level", "early career",
        "analyst", "coordinator", "1-2 years",
    ],
    "mid": [
        "mid level", "mid-level", "specialist", "experienced",
        "3-5 years", "professional", "senior analyst",
    ],
    "senior": [
        "senior", "lead", "principal", "manager", "director",
        "head", "5+ years", "expert", "staff",
    ],
}

SENIORITY_MATCH_KEYWORDS = {
    "fresher": ["intern", "entry", "fresher", "trainee", "graduate", "junior", "associate"],
    "junior": ["junior", "associate", "entry", "early career", "analyst", "coordinator"],
    "mid": ["mid", "specialist", "experienced", "professional", "senior analyst"],
    "senior": ["senior", "lead", "principal", "manager", "director", "head", "staff", "vp"],
}


def _get_seniority_bucket(experience_level: str, years: int) -> str:
    """Map experience to seniority bucket."""
    if experience_level == "fresher":
        return "fresher"
    elif years <= 2:
        return "junior"
    elif years <= 5:
        return "mid"
    else:
        return "senior"


# ============================================
# LINKEDIN-SPECIFIC SEARCH QUERIES
# ============================================

def _generate_linkedin_queries(
    job_role: str,
    location: str,
    seniority_bucket: str,
    industry: str,
) -> list[str]:
    """
    Generate search queries optimized for LinkedIn job results.
    Uses site:linkedin.com/jobs and LinkedIn-specific patterns.
    """
    loc = f" {location}" if location else ""
    ind = f" {industry}" if industry else ""
    level_terms = LEVEL_SEARCH_TERMS.get(seniority_bucket, LEVEL_SEARCH_TERMS["fresher"])

    queries = []

    # --- Core LinkedIn job search queries ---
    queries.extend([
        f"site:linkedin.com/jobs {job_role}{loc}",
        f"linkedin.com jobs {job_role}{loc} hiring",
        f"site:linkedin.com/jobs {job_role}{loc} 2025",
        f"linkedin {job_role} jobs{loc} apply",
    ])

    # --- Level-specific LinkedIn queries ---
    for term in level_terms[:5]:
        queries.append(f"site:linkedin.com/jobs {term} {job_role}{loc}")
        queries.append(f"linkedin {term} {job_role} jobs{loc}")

    # --- Industry-filtered LinkedIn queries ---
    if industry:
        queries.extend([
            f"site:linkedin.com/jobs {job_role} {industry}{loc}",
            f"linkedin {industry} {job_role} hiring{loc}",
            f"site:linkedin.com/jobs {job_role}{ind}{loc}",
        ])

    # --- LinkedIn company pages with hiring signals ---
    queries.extend([
        f"site:linkedin.com/company {job_role} hiring{loc}",
        f"linkedin.com company {job_role} openings{loc}",
    ])

    # --- Fresher-specific LinkedIn queries ---
    if seniority_bucket == "fresher":
        queries.extend([
            f"site:linkedin.com/jobs internship {job_role}{loc}",
            f"linkedin entry level {job_role} freshers{loc}",
            f"site:linkedin.com/jobs graduate {job_role}{loc}",
            f"linkedin campus hiring {job_role}{loc}",
        ])

    # --- Senior-specific LinkedIn queries ---
    if seniority_bucket == "senior":
        queries.extend([
            f"site:linkedin.com/jobs senior {job_role}{loc}",
            f"linkedin lead {job_role} director{loc}",
            f"site:linkedin.com/jobs manager {job_role}{loc}",
        ])

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


def _generate_fallback_queries(
    job_role: str,
    location: str,
    seniority_bucket: str,
    industry: str,
) -> list[str]:
    """
    General web search queries — used ONLY as fallback
    when LinkedIn queries don't yield enough results.
    """
    loc = f" in {location}" if location else ""
    ind = f" {industry}" if industry else ""
    level_terms = LEVEL_SEARCH_TERMS.get(seniority_bucket, LEVEL_SEARCH_TERMS["fresher"])

    queries = []
    for term in level_terms[:3]:
        queries.append(f"companies hiring {term} {job_role}{loc} careers email")
    queries.extend([
        f"top companies recruiting {job_role}{loc}",
        f"{job_role} open positions{loc} company",
        f"startups hiring {job_role}{loc}",
        f"best companies for {job_role}{loc} 2025",
    ])
    if industry:
        queries.append(f"{industry} companies hiring {job_role}{loc}")

    random.shuffle(queries)
    return queries


# ============================================
# LINKEDIN RESULT PARSING
# ============================================

def _parse_linkedin_result(result: dict, seniority_bucket: str) -> dict | None:
    """
    Parse a single Tavily search result from LinkedIn
    and extract structured job/company data.

    Returns a company dict or None if unparseable.
    """
    url = result.get("url", "")
    title = result.get("title", "")
    content = result.get("content", "")

    if not url or not title:
        return None

    parsed_url = urlparse(url)
    hostname = parsed_url.netloc.replace("www.", "")

    # Determine if this is a LinkedIn job page or company page
    is_linkedin_job = "linkedin.com" in hostname and "/jobs/" in url
    is_linkedin_company = "linkedin.com" in hostname and "/company/" in url

    if not is_linkedin_job and not is_linkedin_company:
        return None

    # --- Extract company name from LinkedIn title ---
    # LinkedIn titles are typically:
    #   "Company Name hiring Job Title in Location | LinkedIn"
    #   "Job Title - Company Name | LinkedIn"
    #   "Company Name | LinkedIn"
    company_name = ""
    job_title = ""
    job_location = ""

    # Clean the title
    clean_title = title.replace(" | LinkedIn", "").replace(" - LinkedIn", "").strip()

    if " hiring " in clean_title:
        # "Company hiring Title in Location"
        parts = clean_title.split(" hiring ", 1)
        company_name = parts[0].strip()
        remainder = parts[1] if len(parts) > 1 else ""
        if " in " in remainder:
            jt_parts = remainder.split(" in ", 1)
            job_title = jt_parts[0].strip()
            job_location = jt_parts[1].strip()
        else:
            job_title = remainder.strip()
    elif " - " in clean_title:
        # "Job Title - Company Name"
        parts = clean_title.rsplit(" - ", 1)
        if len(parts) == 2:
            job_title = parts[0].strip()
            company_name = parts[1].strip()
    elif is_linkedin_company:
        company_name = clean_title.strip()

    if not company_name or len(company_name) < 2:
        return None

    # Skip very generic or too-long names
    if len(company_name) > 80:
        company_name = company_name[:80]

    # --- Seniority match scoring ---
    match_score = _calculate_match_score(
        job_title, content, seniority_bucket
    )

    # Skip very low matches (irrelevant seniority)
    if match_score < config.LINKEDIN_MIN_MATCH_SCORE:
        return None

    return {
        "company_name": company_name,
        "domain": "",                           # resolved later
        "website": "",                          # resolved later
        "linkedin_job_url": url if is_linkedin_job else "",
        "linkedin_company_url": url if is_linkedin_company else "",
        "linkedin_job_title": job_title,
        "linkedin_location": job_location,
        "seniority_fit": seniority_bucket,
        "match_score": match_score,
        "source": "linkedin",
        "snippet": content[:300] if content else "",
    }


def _calculate_match_score(job_title: str, content: str, seniority_bucket: str) -> int:
    """
    Score how well a LinkedIn listing matches the candidate's level.
    0-100 scale. Higher = better fit.
    """
    text = f"{job_title} {content}".lower()
    score = 50  # base score for being on LinkedIn

    match_keywords = SENIORITY_MATCH_KEYWORDS.get(seniority_bucket, [])
    for kw in match_keywords:
        if kw in text:
            score += 10

    # Cap at 100
    return min(score, 100)


def _parse_general_result(result: dict) -> dict | None:
    """
    Parse a general web search result (fallback).
    Extracts company domain directly from the URL.
    """
    url = result.get("url", "")
    title = result.get("title", "")
    content = result.get("content", "")

    if not url:
        return None

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")

    skip_domains = [
        "linkedin.com", "indeed.com", "glassdoor.com", "monster.com",
        "ziprecruiter.com", "naukri.com", "google.com", "youtube.com",
        "twitter.com", "facebook.com", "reddit.com", "quora.com",
        "wikipedia.org", "medium.com", "github.com", "stackoverflow.com",
        "wellfound.com", "angellist.com", "lever.co", "greenhouse.io",
        "workday.com", "simplyhired.com", "careerbuilder.com",
    ]

    if domain in skip_domains or not domain:
        return None

    # Clean company name from domain/title
    company_name = _clean_company_name(domain, title)

    return {
        "company_name": company_name,
        "domain": domain,
        "website": f"https://{domain}",
        "linkedin_job_url": "",
        "linkedin_company_url": "",
        "linkedin_job_title": "",
        "linkedin_location": "",
        "seniority_fit": "",
        "match_score": 30,                      # lower confidence (not from LinkedIn)
        "source": "web_fallback",
        "snippet": content[:200] if content else "",
    }


def _clean_company_name(domain: str, title: str) -> str:
    """Generate a readable company name from a domain or title."""
    if title:
        for sep in [" - ", " | ", " – ", " — ", " · "]:
            parts = title.split(sep)
            if len(parts) >= 2:
                candidate = parts[0].strip()
                if 2 < len(candidate) < 50:
                    return candidate

    name = domain.split(".")[0]
    name = name.replace("-", " ").replace("_", " ").title()
    return name


# ============================================
# DOMAIN RESOLVER FOR LINKEDIN COMPANIES
# ============================================

def _resolve_company_domains(
    companies: list[dict],
    client: TavilyClient,
) -> list[dict]:
    """
    For companies found via LinkedIn (no domain yet),
    do a quick web search to find their actual website domain.
    This is needed so the HR email scraper can find contact emails.
    """
    needs_domain = [c for c in companies if not c.get("domain")]
    if not needs_domain:
        return companies

    print(f"\n   🌐 Resolving domains for {len(needs_domain)} LinkedIn-found companies...")

    for i, company in enumerate(needs_domain):
        name = company["company_name"]
        try:
            results = client.search(
                query=f"{name} official website",
                max_results=3,
                search_depth="basic",
                exclude_domains=[
                    "linkedin.com", "indeed.com", "glassdoor.com",
                    "youtube.com", "wikipedia.org", "facebook.com",
                ],
            )

            for r in results.get("results", []):
                r_url = r.get("url", "")
                if r_url:
                    parsed = urlparse(r_url)
                    domain = parsed.netloc.replace("www.", "")
                    if domain and "." in domain and len(domain) > 3:
                        company["domain"] = domain
                        company["website"] = f"https://{domain}"
                        break

            if company.get("domain"):
                print(f"      [{i+1}/{len(needs_domain)}] {name} → {company['domain']} ✅")
            else:
                # Generate domain guess from company name
                domain_guess = re.sub(r"[^a-z0-9]", "", name.lower()) + ".com"
                company["domain"] = domain_guess
                company["website"] = f"https://{domain_guess}"
                print(f"      [{i+1}/{len(needs_domain)}] {name} → {domain_guess} (guessed)")

            time.sleep(random.uniform(0.5, 1.5))

        except Exception:
            domain_guess = re.sub(r"[^a-z0-9]", "", name.lower()) + ".com"
            company["domain"] = domain_guess
            company["website"] = f"https://{domain_guess}"

    return companies


# ============================================
# MAIN NODE
# ============================================

def bulk_company_search(state: dict) -> dict:
    """
    LANGGRAPH NODE: LinkedIn-first company discovery.

    Phase 1: Search LinkedIn via Tavily (primary source)
    Phase 2: General web fallback (only if LinkedIn < target)
    Phase 3: Resolve company domains for LinkedIn-found companies

    Args:
        state: LangGraph state with candidate profile

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

    seniority_bucket = _get_seniority_bucket(experience_level, years_of_experience)

    print(f"\n🔍 LINKEDIN-FIRST COMPANY SEARCH")
    print(f"   Role: {job_role}")
    print(f"   Level: {seniority} (bucket: {seniority_bucket})")
    print(f"   Location: {location or 'Any'}")
    print(f"   Industry: {industry or 'Any'}")
    print(f"   Target: {target_count} companies")
    print("=" * 50)

    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    all_companies = []
    seen_names = set()  # use company name (not domain) since LinkedIn results lack domains

    # =========================
    # PHASE 1: LINKEDIN SEARCH
    # =========================
    print(f"\n   📌 PHASE 1: LinkedIn Job Search")
    print(f"   " + "-" * 45)

    linkedin_queries = _generate_linkedin_queries(
        job_role, location, seniority_bucket, industry
    )

    for i, query in enumerate(linkedin_queries):
        if len(all_companies) >= target_count:
            print(f"\n   ✅ Reached target of {target_count} companies!")
            break

        print(f"   [{i+1}/{len(linkedin_queries)}] {query[:65]}...")

        try:
            results = client.search(
                query=query,
                max_results=config.LINKEDIN_RESULTS_PER_QUERY,
                search_depth="advanced",
                include_domains=["linkedin.com"],
            )

            search_results = results.get("results", [])
            added = 0
            for result in search_results:
                company = _parse_linkedin_result(result, seniority_bucket)
                if company:
                    name_key = company["company_name"].lower().strip()
                    if name_key not in seen_names and len(name_key) > 1:
                        seen_names.add(name_key)
                        all_companies.append(company)
                        added += 1

            print(f"         +{added} companies (Total: {len(all_companies)})")
            time.sleep(random.uniform(1, 3))

        except Exception as e:
            print(f"         ⚠ {str(e)[:70]}")
            time.sleep(2)

    linkedin_count = len(all_companies)
    print(f"\n   📊 LinkedIn phase: {linkedin_count} companies found")

    # =========================
    # PHASE 2: WEB FALLBACK
    # =========================
    if linkedin_count < target_count:
        shortfall = target_count - linkedin_count
        print(f"\n   📌 PHASE 2: Web Fallback (need {shortfall} more)")
        print(f"   " + "-" * 45)

        fallback_queries = _generate_fallback_queries(
            job_role, location, seniority_bucket, industry
        )

        for i, query in enumerate(fallback_queries):
            if len(all_companies) >= target_count:
                break

            print(f"   [F{i+1}/{len(fallback_queries)}] {query[:65]}...")

            try:
                results = client.search(
                    query=query,
                    max_results=15,
                    search_depth="advanced",
                    exclude_domains=[
                        "linkedin.com", "indeed.com", "glassdoor.com",
                        "youtube.com", "wikipedia.org", "reddit.com",
                    ],
                )

                added = 0
                for result in results.get("results", []):
                    company = _parse_general_result(result)
                    if company:
                        name_key = company["company_name"].lower().strip()
                        if name_key not in seen_names and company["domain"] not in seen_names:
                            seen_names.add(name_key)
                            seen_names.add(company["domain"])
                            all_companies.append(company)
                            added += 1

                print(f"         +{added} companies (Total: {len(all_companies)})")
                time.sleep(random.uniform(1, 2))

            except Exception as e:
                print(f"         ⚠ {str(e)[:70]}")
                time.sleep(2)

        fallback_count = len(all_companies) - linkedin_count
        print(f"   📊 Fallback phase: {fallback_count} additional companies")
    else:
        print(f"\n   ⏩ Skipping fallback — LinkedIn yielded enough results")

    # =========================
    # PHASE 3: RESOLVE DOMAINS
    # =========================
    all_companies = _resolve_company_domains(all_companies, client)

    # Deduplicate by domain (now that domains are resolved)
    final = []
    seen_domains = set()
    for c in all_companies:
        d = c.get("domain", "")
        if d and d not in seen_domains:
            seen_domains.add(d)
            final.append(c)

    # Trim and sort by match score
    final.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    if len(final) > target_count:
        final = final[:target_count]

    # Stats
    from_linkedin = sum(1 for c in final if c.get("source") == "linkedin")
    from_fallback = sum(1 for c in final if c.get("source") == "web_fallback")

    print(f"\n   📊 SEARCH COMPLETE:")
    print(f"      Total companies:    {len(final)}")
    print(f"      From LinkedIn:      {from_linkedin}")
    print(f"      From web fallback:  {from_fallback}")
    print(f"      Avg match score:    {sum(c.get('match_score', 0) for c in final) / max(len(final), 1):.0f}/100")

    state["companies"] = final
    state["total_found"] = len(final)
    return state
