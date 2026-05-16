"""
============================================
PERSONALIZED EMAIL WRITER MODULE
============================================
Uses Mistral AI to generate unique, personalized
outreach emails for each company based on
research data, job role, and user profile.
"""

import time
import random
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage
import config


def _create_writer_llm():
    """Create a Mistral AI instance for email writing."""
    return ChatMistralAI(
        model=config.MISTRAL_MODEL,
        mistral_api_key=config.MISTRAL_API_KEY,
        temperature=config.MISTRAL_TEMPERATURE,
        max_tokens=config.MISTRAL_MAX_TOKENS,
    )


def _generate_email(
    llm: ChatMistralAI,
    company_name: str,
    job_role: str,
    research: str,
    sender_email: str,
) -> dict:
    """
    Generate a personalized outreach email for a specific company.

    Returns:
        dict with 'subject' and 'body' keys
    """
    try:
        messages = [
            SystemMessage(content=(
                "You are an expert job application email writer. Write a professional, "
                "concise, and personalized cold outreach email for a job application. "
                "\n\nRULES:\n"
                "1. Keep it SHORT - maximum 150 words for the body\n"
                "2. Start with a specific reference to the company (use the research provided)\n"
                "3. Clearly state the target role\n"
                "4. Highlight 2-3 relevant value propositions\n"
                "5. Mention that a resume is attached\n"
                "6. End with a clear call to action\n"
                "7. Be professional but warm, not robotic\n"
                "8. AVOID spam trigger words: 'free', 'guaranteed', 'act now', 'limited time'\n"
                "9. Do NOT use excessive exclamation marks\n"
                "10. Make each email feel genuinely personalized\n"
                "\nOutput EXACTLY in this format:\n"
                "SUBJECT: [your subject line here]\n"
                "BODY:\n[your email body here]"
            )),
            HumanMessage(content=(
                f"Company: {company_name}\n"
                f"Target Role: {job_role}\n"
                f"Company Research: {research}\n"
                f"Sender Email: {sender_email}\n\n"
                f"Write a personalized job application outreach email for this company. "
                f"Remember to mention that a resume is attached."
            )),
        ]

        response = llm.invoke(messages)
        content = response.content.strip()

        # Parse subject and body from response
        subject = ""
        body = ""

        if "SUBJECT:" in content and "BODY:" in content:
            parts = content.split("BODY:")
            subject_part = parts[0]
            body = parts[1].strip() if len(parts) > 1 else ""

            # Extract subject
            subject = subject_part.replace("SUBJECT:", "").strip()
            # Clean up any extra newlines
            subject = subject.split("\n")[0].strip()
        else:
            # Fallback parsing
            lines = content.split("\n")
            subject = f"Application for {job_role} Position - {company_name}"
            body = content

        # Clean up the body
        body = body.strip()
        if not body:
            body = (
                f"Dear Hiring Team,\n\n"
                f"I am writing to express my interest in the {job_role} position "
                f"at {company_name}. I believe my skills and experience align well "
                f"with your team's needs.\n\n"
                f"I have attached my resume for your review. I would welcome the "
                f"opportunity to discuss how I can contribute to {company_name}.\n\n"
                f"Thank you for your time and consideration.\n\n"
                f"Best regards"
            )

        if not subject:
            subject = f"Application for {job_role} Position - {company_name}"

        return {"subject": subject, "body": body}

    except Exception as e:
        # Fallback email
        return {
            "subject": f"Application for {job_role} Position - {company_name}",
            "body": (
                f"Dear Hiring Team,\n\n"
                f"I am writing to express my strong interest in the {job_role} "
                f"position at {company_name}. Based on my research, I am confident "
                f"that my skills would be a great fit for your team.\n\n"
                f"I have attached my resume for your review. I would appreciate "
                f"the opportunity to discuss how I can contribute to {company_name}'s "
                f"continued success.\n\n"
                f"Thank you for your time and consideration.\n\n"
                f"Best regards"
            ),
        }


def personalized_email_writer(state: dict) -> dict:
    """
    LANGGRAPH NODE: Generate personalized emails for every company.

    Uses Mistral AI to create unique, company-specific outreach emails
    based on the research data collected in the previous step.

    Args:
        state: LangGraph state with researched 'companies' list

    Returns:
        Updated state with 'email_subject' and 'email_body' per company
    """
    companies = state["companies"]
    job_role = state["job_role"]
    sender_email = config.GMAIL_EMAIL

    print(f"\n✍️  PERSONALIZED EMAIL WRITER")
    print(f"   Generating emails for {len(companies)} companies with Mistral AI...")
    print("=" * 50)

    llm = _create_writer_llm()
    generated = 0
    fallback_count = 0

    for i, company in enumerate(companies):
        company_name = company.get("company_name", "Unknown")
        research = company.get("research", "")

        print(f"   [{i+1}/{len(companies)}] Writing email for {company_name}...", end=" ")

        email_data = _generate_email(llm, company_name, job_role, research, sender_email)

        company["email_subject"] = email_data["subject"]
        company["email_body"] = email_data["body"]

        # Check if it's a real generated email or fallback
        if "I am writing to express" not in email_data["body"][:50]:
            generated += 1
            print("✅")
        else:
            fallback_count += 1
            print("📝 (template)")

        # Rate limiting for Mistral API
        if (i + 1) % 5 == 0:
            time.sleep(random.uniform(2.0, 4.0))
        else:
            time.sleep(random.uniform(0.5, 1.0))

    print(f"\n   📊 EMAIL GENERATION COMPLETE:")
    print(f"      AI-personalized: {generated}")
    print(f"      Template fallback: {fallback_count}")

    state["companies"] = companies
    state["emails_generated"] = len(companies)
    return state
