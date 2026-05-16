"""
============================================
BULK COMPANY SEARCH MODULE — LINKEDIN ONLY
============================================
Discovers companies with relevant job openings
EXCLUSIVELY from LinkedIn via Tavily Search API.

Source: LinkedIn ONLY. Zero exceptions.
No Google, no Indeed, no Glassdoor, no web fallback.

If a company is not found on LinkedIn → it is skipped.

Extracts per company:
  - Company name
  - LinkedIn job title
  - LinkedIn job URL
  - LinkedIn company URL
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
# LINKEDIN SEARCH QUERIES
# ============================================

def _generate_linkedin_queries(
    job_role: str,
    location: str,
    seniority_bucket: str,
    industry: str,
) -> list[str]:
    """
    Generate search queries targeting ONLY LinkedIn job listings
    and LinkedIn company pages. No other sources.
    """
    loc = f" {location}" if location else ""
    level_terms = LEVEL_SEARCH_TERMS.get(seniority_bucket, LEVEL_SEARCH_TERMS["fresher"])

    queries = []

    # --- Core LinkedIn job searches ---
    queries.extend([
        f"site:linkedin.com/jobs {job_role}{loc}",
        f"linkedin.com jobs {job_role}{loc} hiring",
        f"site:linkedin.com/jobs {job_role}{loc} 2025",
        f"site:linkedin.com/jobs {job_role}{loc} 2026",
        f"linkedin {job_role} jobs{loc} apply",
        f"site:linkedin.com/jobs {job_role}{loc} open",
    ])

    # --- Level-specific LinkedIn queries ---
    for term in level_terms[:6]:
        queries.append(f"site:linkedin.com/jobs {term} {job_role}{loc}")
        queries.append(f"linkedin {term} {job_role} jobs{loc}")

    # --- Industry-filtered LinkedIn queries ---
    if industry:
        queries.extend([
            f"site:linkedin.com/jobs {job_role} {industry}{loc}",
            f"linkedin {industry} {job_role} hiring{loc}",
            f"site:linkedin.com/jobs {industry} {job_role}{loc}",
            f"linkedin {job_role} {industry} jobs{loc}",
        ])

    # --- LinkedIn company pages with hiring signals ---
    queries.extend([
        f"site:linkedin.com/company {job_role} hiring{loc}",
        f"site:linkedin.com/company {job_role} openings{loc}",
        f"linkedin.com company {job_role} jobs{loc}",
    ])

    # --- Fresher-specific LinkedIn queries ---
    if seniority_bucket == "fresher":
        queries.extend([
            f"site:linkedin.com/jobs internship {job_role}{loc}",
            f"linkedin entry level {job_role} freshers{loc}",
            f"site:linkedin.com/jobs graduate {job_role}{loc}",
            f"site:linkedin.com/jobs trainee {job_role}{loc}",
            f"linkedin campus hiring {job_role}{loc}",
            f"site:linkedin.com/jobs associate {job_role}{loc}",
        ])

    # --- Mid-level specific ---
    if seniority_bucket == "mid":
        queries.extend([
            f"site:linkedin.com/jobs experienced {job_role}{loc}",
            f"site:linkedin.com/jobs specialist {job_role}{loc}",
            f"linkedin mid level {job_role}{loc}",
        ])

    # --- Senior-specific LinkedIn queries ---
    if seniority_bucket == "senior":
        queries.extend([
            f"site:linkedin.com/jobs senior {job_role}{loc}",
            f"site:linkedin.com/jobs lead {job_role}{loc}",
            f"site:linkedin.com/jobs manager {job_role}{loc}",
            f"linkedin director {job_role}{loc}",
            f"site:linkedin.com/jobs principal {job_role}{loc}",
        ])

    # --- Broad LinkedIn catch-all (still LinkedIn only) ---
    queries.extend([
        f"linkedin.com/jobs {job_role}{loc} company",
        f"site:linkedin.com {job_role} hiring{loc} 2025",
        f"linkedin jobs {job_role}{loc} remote",
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


# ============================================
# LINKEDIN RESULT PARSING
# ============================================

def _parse_linkedin_result(result: dict, seniority_bucket: str) -> dict | None:
    """
    Parse a single Tavily search result from LinkedIn
    and extract structured job/company data.

    Returns a company dict or None if:
      - Not a LinkedIn URL
      - Company name unparseable
      - Seniority match below threshold
    """
    url = result.get("url", "")
    title = result.get("title", "")
    content = result.get("content", "")

    if not url or not title:
        return None

    parsed_url = urlparse(url)
    hostname = parsed_url.netloc.replace("www.", "")

    # === STRICT LINKEDIN CHECK ===
    if "linkedin.com" not in hostname:
        return None  # Not LinkedIn → reject completely

    # Determine page type
    is_linkedin_job = "/jobs/" in url
    is_linkedin_company = "/company/" in url

    if not is_linkedin_job and not is_linkedin_company:
        return None

    # --- Extract company name from LinkedIn title ---
    # LinkedIn title patterns:
    #   "Company Name hiring Job Title in Location | LinkedIn"
    #   "Job Title - Company Name | LinkedIn"
    #   "Company Name | LinkedIn"
    company_name = ""
    job_title = ""
    job_location = ""

    clean_title = title.replace(" | LinkedIn", "").replace(" - LinkedIn", "").strip()

    if " hiring " in clean_title:
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
        parts = clean_title.rsplit(" - ", 1)
        if len(parts) == 2:
            job_title = parts[0].strip()
            company_name = parts[1].strip()
    elif is_linkedin_company:
        company_name = clean_title.strip()

    if not company_name or len(company_name) < 2:
        return None

    if len(company_name) > 80:
        company_name = company_name[:80]

    # --- Seniority match scoring ---
    match_score = _calculate_match_score(job_title, content, seniority_bucket)

    if match_score < config.LINKEDIN_MIN_MATCH_SCORE:
        return None

    return {
        "company_name": company_name,
        "domain": "",
        "website": "",
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

    return min(score, 100)


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

    NOTE: This is NOT a company discovery step — only domain lookup
    for companies already qualified via LinkedIn.
    """
    needs_domain = [c for c in companies if not c.get("domain")]
    if not needs_domain:
        return companies

    print(f"\n   🌐 Resolving domains for {len(needs_domain)} LinkedIn-qualified companies...")

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
    LANGGRAPH NODE: LinkedIn-ONLY company discovery.

    Source: LinkedIn exclusively. No fallback. No exceptions.
    If not found on LinkedIn → skipped.

    Phase 1: Search LinkedIn via Tavily (ONLY source)
    Phase 2: Resolve company domains for email scraping

    Args:
        state: LangGraph state with candidate profile

    Returns:
        Updated state with LinkedIn-qualified 'companies' list
    """
    job_role = state["job_role"]
    location = state.get("location", "")
    experience_level = state.get("experience_level", "fresher")
    years_of_experience = state.get("years_of_experience", 0)
    industry = state.get("industry", "")
    seniority = state.get("seniority", "")
    target_count = config.TARGET_COMPANY_COUNT

    seniority_bucket = _get_seniority_bucket(experience_level, years_of_experience)

    print(f"\n🔍 LINKEDIN-ONLY COMPANY SEARCH")
    print(f"   Source: {config.JOB_SOURCE}")
    print(f"   Role: {job_role}")
    print(f"   Level: {seniority} (bucket: {seniority_bucket})")
    print(f"   Location: {location or 'Any'}")
    print(f"   Industry: {industry or 'Any'}")
    print(f"   Target: {target_count} companies")
    print("=" * 50)

    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    all_companies = []
    seen_names = set()

    # ================================
    # LINKEDIN SEARCH (ONLY SOURCE)
    # ================================
    linkedin_queries = _generate_linkedin_queries(
        job_role, location, seniority_bucket, industry
    )

    print(f"\n   📌 Searching LinkedIn ({len(linkedin_queries)} queries)")
    print(f"   " + "-" * 45)

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
            skipped_non_linkedin = 0

            for result in search_results:
                # Strict LinkedIn check — reject anything not from LinkedIn
                result_url = result.get("url", "")
                if "linkedin.com" not in result_url:
                    skipped_non_linkedin += 1
                    continue

                company = _parse_linkedin_result(result, seniority_bucket)
                if company:
                    name_key = company["company_name"].lower().strip()
                    if name_key not in seen_names and len(name_key) > 1:
                        seen_names.add(name_key)
                        all_companies.append(company)
                        added += 1

            status = f"+{added} companies (Total: {len(all_companies)})"
            if skipped_non_linkedin > 0:
                status += f" [skipped {skipped_non_linkedin} non-LinkedIn]"
            print(f"         {status}")

            time.sleep(random.uniform(1, 3))

        except Exception as e:
            print(f"         ⚠ {str(e)[:70]}")
            time.sleep(2)

    # ================================
    # RESOLVE DOMAINS
    # ================================
    all_companies = _resolve_company_domains(all_companies, client)

    # Deduplicate by domain
    final = []
    seen_domains = set()
    for c in all_companies:
        d = c.get("domain", "")
        if d and d not in seen_domains:
            seen_domains.add(d)
            final.append(c)

    # Sort by match score (best matches first)
    final.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    if len(final) > target_count:
        final = final[:target_count]

    # === SOURCE VALIDATION ===
    # Hard enforcement: every company must be LinkedIn-sourced
    validated = [c for c in final if c.get("source") == "linkedin"]
    rejected = len(final) - len(validated)

    print(f"\n   📊 SEARCH COMPLETE (LINKEDIN ONLY):")
    print(f"      LinkedIn companies:  {len(validated)}")
    if rejected > 0:
        print(f"      Rejected (non-LI):   {rejected}")
    print(f"      Avg match score:     {sum(c.get('match_score', 0) for c in validated) / max(len(validated), 1):.0f}/100")

    if len(validated) == 0:
        print(f"\n   ⚠ No companies found on LinkedIn for this search.")
        print(f"      Try broadening the role or location.")

    state["companies"] = validated
    state["total_found"] = len(validated)
    return state
