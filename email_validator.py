"""
============================================
EMAIL VALIDATOR MODULE
============================================
Validates discovered email addresses using:
1. Format validation (regex)
2. DNS MX record lookup
3. Duplicate removal across all companies
"""

import re
import dns.resolver


def _check_email_format(email: str) -> bool:
    """Validate email format with regex."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _check_mx_record(domain: str, cache: dict) -> bool:
    """
    Check if the email domain has valid MX (mail exchange) records.
    Uses a cache to avoid repeated DNS lookups for the same domain.
    """
    if domain in cache:
        return cache[domain]

    try:
        mx_records = dns.resolver.resolve(domain, "MX", lifetime=5)
        has_mx = len(mx_records) > 0
        cache[domain] = has_mx
        return has_mx
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout):
        cache[domain] = False
        return False
    except Exception:
        # If DNS check fails, give benefit of the doubt for generated patterns
        cache[domain] = True
        return True


def email_validator(state: dict) -> dict:
    """
    LANGGRAPH NODE: Validate all collected emails and remove duplicates.

    Performs:
    1. Format validation
    2. DNS MX record verification
    3. Cross-company duplicate removal
    4. Removes companies with no valid emails

    Args:
        state: LangGraph state with companies having 'emails' field

    Returns:
        Updated state with validated emails and cleaned company list
    """
    companies = state["companies"]
    print(f"\n✅ EMAIL VALIDATOR & DUPLICATE CLEANER")
    print(f"   Validating emails for {len(companies)} companies...")
    print("=" * 50)

    mx_cache = {}
    all_used_emails = set()
    valid_companies = []
    removed_count = 0
    invalid_email_count = 0

    for company in companies:
        emails = company.get("emails", [])
        valid_emails = []

        for email in emails:
            email = email.lower().strip()

            # Skip if already used by another company
            if email in all_used_emails:
                continue

            # Check format
            if not _check_email_format(email):
                invalid_email_count += 1
                continue

            # Check MX record
            domain = email.split("@")[1]
            if not _check_mx_record(domain, mx_cache):
                invalid_email_count += 1
                continue

            valid_emails.append(email)
            all_used_emails.add(email)

        if valid_emails:
            company["emails"] = valid_emails
            company["primary_email"] = valid_emails[0]
            valid_companies.append(company)
        else:
            removed_count += 1

    print(f"   📊 VALIDATION COMPLETE:")
    print(f"      Valid companies: {len(valid_companies)}")
    print(f"      Removed (no valid email): {removed_count}")
    print(f"      Invalid emails filtered: {invalid_email_count}")
    print(f"      Unique emails: {len(all_used_emails)}")

    state["companies"] = valid_companies
    state["validated_count"] = len(valid_companies)
    return state
