"""
============================================
CSV LOGGER MODULE
============================================
Logs all outreach activity to CSV files and
a text activity log for full traceability.
"""

import os
import csv
from datetime import datetime
import config


def _ensure_output_dir():
    """Make sure the output directory exists."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)


def _write_csv_row(filepath, row_dict, fieldnames):
    """Append a single row to a CSV file, creating headers if needed."""
    _ensure_output_dir()
    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row_dict)


# Standard CSV field names
SENT_FIELDS = [
    "timestamp", "company_name", "domain", "email",
    "subject", "status",
]

FAILED_FIELDS = [
    "timestamp", "company_name", "domain", "email",
    "status", "error",
]

COMPANY_FIELDS = [
    "company_name", "domain", "website", "primary_email",
    "all_emails", "research_snippet",
]


def log_sent(company):
    """Log a successfully sent email to sent_log.csv."""
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company_name": company.get("company_name", ""),
        "domain": company.get("domain", ""),
        "email": company.get("primary_email", ""),
        "subject": company.get("email_subject", ""),
        "status": "SENT",
    }
    _write_csv_row(config.SENT_LOG_FILE, row, SENT_FIELDS)


def log_failed(company):
    """Log a failed email send to failed_log.csv."""
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company_name": company.get("company_name", ""),
        "domain": company.get("domain", ""),
        "email": company.get("primary_email", ""),
        "status": company.get("send_status", "FAILED"),
        "error": company.get("send_error", "Unknown error"),
    }
    _write_csv_row(config.FAILED_LOG_FILE, row, FAILED_FIELDS)


def log_companies(companies):
    """Save all discovered companies to companies_found.csv."""
    _ensure_output_dir()
    filepath = config.COMPANIES_FILE

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMPANY_FIELDS)
        writer.writeheader()
        for company in companies:
            emails = company.get("emails", [])
            row = {
                "company_name": company.get("company_name", ""),
                "domain": company.get("domain", ""),
                "website": company.get("website", ""),
                "primary_email": company.get("primary_email", ""),
                "all_emails": "; ".join(emails) if emails else "",
                "research_snippet": company.get("research", "")[:200],
            }
            writer.writerow(row)


def log_activity(message):
    """Append a timestamped message to the activity log."""
    _ensure_output_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"

    with open(config.FULL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def csv_logger(state):
    """
    LANGGRAPH NODE: Final logging step - saves all data to CSV.
    """
    companies = state.get("companies", [])

    print(f"\n📝 CSV LOGGER")
    print("=" * 50)

    # Save all companies found
    log_companies(companies)
    print(f"   ✅ Saved {len(companies)} companies → {config.COMPANIES_FILE}")

    # Log final summary
    total_sent = state.get("total_sent", 0)
    total_failed = state.get("total_failed", 0)

    log_activity("=" * 50)
    log_activity(f"JOB: {state.get('job_role', 'N/A')}")
    log_activity(f"LOCATION: {state.get('location', 'Any')}")
    log_activity(f"COMPANIES FOUND: {state.get('total_found', 0)}")
    log_activity(f"EMAILS VALIDATED: {state.get('validated_count', 0)}")
    log_activity(f"EMAILS GENERATED: {state.get('emails_generated', 0)}")
    log_activity(f"EMAILS SENT: {total_sent}")
    log_activity(f"EMAILS FAILED: {total_failed}")
    log_activity("=" * 50)

    print(f"   ✅ Sent log → {config.SENT_LOG_FILE}")
    print(f"   ✅ Failed log → {config.FAILED_LOG_FILE}")
    print(f"   ✅ Activity log → {config.FULL_LOG_FILE}")

    state["logging_complete"] = True
    return state
