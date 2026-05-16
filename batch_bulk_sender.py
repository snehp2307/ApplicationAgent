"""
============================================
BATCH BULK SENDER MODULE
============================================
Sends personalized emails in configurable batches
via Gmail SMTP with resume attachment, retries,
and Gmail-safe sending rates.
"""

import smtplib
import time
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import config
from resume_handler import load_resume, get_resume_bytes
from csv_logger import log_sent, log_failed, log_activity


def _create_email_message(sender, recipient, subject, body, resume_info, resume_bytes):
    """Create a MIME email message with resume attachment."""
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if resume_bytes and resume_info.get("exists"):
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(resume_bytes)
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="{resume_info["filename"]}"',
        )
        msg.attach(attachment)
    return msg


def _send_single_email(smtp_server, sender, recipient, msg):
    """Send a single email via an existing SMTP connection."""
    try:
        smtp_server.sendmail(sender, recipient, msg.as_string())
        return True
    except smtplib.SMTPRecipientsRefused:
        return False
    except smtplib.SMTPDataError as e:
        if "Daily user sending quota exceeded" in str(e):
            raise
        return False
    except Exception:
        return False


def _create_smtp_connection():
    """Create and authenticate a Gmail SMTP connection."""
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(config.GMAIL_EMAIL, config.GMAIL_APP_PASSWORD)
    return server


def batch_bulk_sender(state):
    """
    LANGGRAPH NODE: Send all generated emails in batches via Gmail SMTP.
    Features: configurable batch sizes, randomized delays, retry logic,
    Gmail quota monitoring, error handling, and activity logging.
    """
    companies = state["companies"]
    batch_size = config.BATCH_SIZE
    sender = config.GMAIL_EMAIL

    print(f"\n📬 BATCH BULK SENDER")
    print(f"   Total: {len(companies)} | Batch: {batch_size} | Delay: {config.MIN_DELAY_BETWEEN_EMAILS}-{config.MAX_DELAY_BETWEEN_EMAILS}s")
    print("=" * 50)

    resume_info = load_resume()
    resume_bytes = get_resume_bytes(resume_info)
    if not resume_info.get("exists"):
        print("   ⚠ WARNING: Resume not found. Emails sent without attachment.")
        log_activity("WARNING: Sending without resume attachment")

    batches = [companies[i:i + batch_size] for i in range(0, len(companies), batch_size)]
    total_sent = 0
    total_failed = 0
    sent_companies = []
    failed_companies = []

    for batch_num, batch in enumerate(batches, 1):
        print(f"\n   📦 BATCH {batch_num}/{len(batches)} ({len(batch)} companies)")

        try:
            smtp_server = _create_smtp_connection()
        except Exception as e:
            print(f"   ❌ SMTP failed: {e}")
            for company in batch:
                company["send_status"] = "FAILED"
                company["send_error"] = str(e)
                log_failed(company)
                failed_companies.append(company)
                total_failed += 1
            continue

        for i, company in enumerate(batch):
            name = company.get("company_name", "Unknown")
            recipient = company.get("primary_email", "")
            subject = company.get("email_subject", "")
            body = company.get("email_body", "")

            if not recipient:
                company["send_status"] = "SKIPPED"
                log_failed(company)
                failed_companies.append(company)
                total_failed += 1
                continue

            print(f"      [{i+1}/{len(batch)}] {name} → {recipient}...", end=" ")
            msg = _create_email_message(sender, recipient, subject, body, resume_info, resume_bytes)

            sent = False
            for attempt in range(config.MAX_RETRIES):
                try:
                    if _send_single_email(smtp_server, sender, recipient, msg):
                        sent = True
                        break
                    time.sleep(5)
                except smtplib.SMTPDataError as e:
                    if "quota" in str(e).lower():
                        print("\n   🚫 GMAIL QUOTA EXCEEDED! Stopping.")
                        log_activity("QUOTA EXCEEDED")
                        try: smtp_server.quit()
                        except: pass
                        state["total_sent"] = total_sent
                        state["total_failed"] = total_failed
                        state["sent_companies"] = sent_companies
                        state["failed_companies"] = failed_companies
                        return state
                    break
                except Exception:
                    time.sleep(5)
                    try: smtp_server.quit()
                    except: pass
                    try: smtp_server = _create_smtp_connection()
                    except: break

            if sent:
                print("✅")
                company["send_status"] = "SENT"
                log_sent(company)
                sent_companies.append(company)
                total_sent += 1
            else:
                print("❌")
                company["send_status"] = "FAILED"
                log_failed(company)
                failed_companies.append(company)
                total_failed += 1

            if i < len(batch) - 1:
                delay = random.uniform(config.MIN_DELAY_BETWEEN_EMAILS, config.MAX_DELAY_BETWEEN_EMAILS)
                print(f"         ⏱ Waiting {delay:.0f}s...")
                time.sleep(delay)

        try: smtp_server.quit()
        except: pass

        if batch_num < len(batches):
            wait = config.BATCH_DELAY_MINUTES * 60 + random.uniform(-60, 60)
            wait = max(60, wait)
            print(f"\n   ⏳ Batch done. Waiting {wait/60:.1f} min...")
            log_activity(f"Batch {batch_num} done. Sent: {total_sent}")
            time.sleep(wait)

    print(f"\n   📊 COMPLETE: Sent={total_sent}, Failed={total_failed}")
    log_activity(f"DONE - Sent: {total_sent}, Failed: {total_failed}")

    state["total_sent"] = total_sent
    state["total_failed"] = total_failed
    state["sent_companies"] = sent_companies
    state["failed_companies"] = failed_companies
    return state
