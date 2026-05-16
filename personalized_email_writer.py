"""
============================================
PERSONALIZED EMAIL WRITER MODULE
============================================
Uses Mistral AI to generate realistic, professional
job application emails. Each email uses the candidate's
RESUME-EXTRACTED profile — real skills, real education,
real experience — no placeholders, no fake praise.
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
        temperature=0.6,
        max_tokens=config.MISTRAL_MAX_TOKENS,
    )


def _build_candidate_summary_fallback(
    experience_level: str,
    years_of_experience: int,
    skills: list[str],
    job_role: str,
) -> str:
    """
    Fallback candidate summary when resume analysis is unavailable.
    Uses only the basic user input fields.
    """
    skills_str = ", ".join(skills) if skills else "relevant technical skills"

    if experience_level == "fresher":
        return (
            f"a recent graduate seeking entry-level {job_role} opportunities. "
            f"Core skills include {skills_str}."
        )
    elif years_of_experience <= 2:
        return (
            f"a professional with {years_of_experience} year{'s' if years_of_experience > 1 else ''} "
            f"of experience in {job_role} roles. "
            f"Key skills include {skills_str}."
        )
    elif years_of_experience <= 5:
        return (
            f"a professional with {years_of_experience} years of experience "
            f"in {job_role} and related domains. "
            f"Areas of expertise include {skills_str}."
        )
    else:
        return (
            f"a seasoned professional with {years_of_experience} years of experience "
            f"in {job_role} and related functions. "
            f"Specializations include {skills_str}."
        )


def _build_system_prompt() -> str:
    """
    The core system prompt that enforces realistic, human-sounding emails.
    This is the single most important piece of prompt engineering in the app.
    """
    return """You are writing a real job application email on behalf of a candidate.
Your output must read like a genuine email a real person would send to a company's HR department.

STRICT RULES — FOLLOW EVERY ONE:

FORMAT:
- Output EXACTLY in this format, nothing else:
  SUBJECT: <subject line>
  BODY:
  <email body>

TONE:
- Professional, formal, and respectful
- Write like a real human candidate, not a marketing bot
- Short sentences, clear language
- No filler, no fluff

ABSOLUTELY FORBIDDEN — never include any of these:
- Square brackets like [Name], [X years], [skills], [Company Mission]
- The word "admire" or "inspired" about the company
- "I came across your company" or "I stumbled upon"
- "Quick call next week?" or any aggressive call to action
- "I would love to" (overused AI phrase)
- Fake flattery about company mission, values, or culture
- Buzzwords: "synergy", "leverage", "passionate", "thrilled", "excited to"
- Exclamation marks
- Placeholder text of any kind
- The phrase "I believe my skills align"
- The phrase "drive meaningful impact"

MUST INCLUDE:
- "Dear Hiring Team," as the greeting (always)
- The candidate's actual experience level and years (provided to you)
- The candidate's actual skills (provided to you)
- A mention that a resume is attached
- "Thank you for your time and consideration." near the end
- "Best regards" as the sign-off (no name after it)

STRUCTURE (4-5 sentences max for the body):
1. State interest in the role at the company (one sentence)
2. State experience level and years with 1-2 actual skills (one sentence)
3. One sentence on what you can contribute (keep it simple and realistic)
4. Mention resume is attached
5. Thank them

SUBJECT LINE:
- Keep it simple and factual
- Good: "Application for Data Analyst Position"
- Good: "Data Analyst | Resume Attached"
- Bad: "Excited to Join Your Amazing Team!"

LENGTH: Maximum 100 words for the body. Shorter is better."""


def _generate_email(
    llm: ChatMistralAI,
    company_name: str,
    job_role: str,
    research: str,
    candidate_summary: str,
    experience_level: str,
) -> dict:
    """
    Generate a realistic outreach email for a specific company.

    Args:
        llm: Mistral AI instance
        company_name: Name of the target company
        job_role: Target position
        research: Brief company research summary
        candidate_summary: Pre-built candidate description with real data
        experience_level: "fresher" or "experienced"

    Returns:
        dict with 'subject' and 'body' keys
    """
    try:
        messages = [
            SystemMessage(content=_build_system_prompt()),
            HumanMessage(content=(
                f"Write a job application email with these EXACT details:\n\n"
                f"Company name: {company_name}\n"
                f"Position: {job_role}\n"
                f"Candidate: {candidate_summary}\n"
                f"Company context: {research}\n\n"
                f"Write the email now. Use the candidate details AS-IS — "
                f"do not add brackets, do not add placeholders, do not invent skills "
                f"or experience the candidate did not provide."
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
            subject = subject.split("\n")[0].strip()
        else:
            # Fallback parsing
            subject = f"Application for {job_role} Position"
            body = content

        # Clean up the body
        body = body.strip()

        # Post-processing: catch any remaining bracket placeholders
        if "[" in body and "]" in body:
            body = _generate_fallback_body(company_name, job_role, candidate_summary, experience_level)

        if not body:
            body = _generate_fallback_body(company_name, job_role, candidate_summary, experience_level)

        if not subject or "[" in subject:
            subject = f"Application for {job_role} Position"

        return {"subject": subject, "body": body}

    except Exception as e:
        return {
            "subject": f"Application for {job_role} Position",
            "body": _generate_fallback_body(company_name, job_role, candidate_summary, experience_level),
        }


def _generate_fallback_body(
    company_name: str,
    job_role: str,
    candidate_summary: str,
    experience_level: str,
) -> str:
    """
    Generate a clean fallback email body using the candidate's real data.
    No AI needed — just a solid, professional template with actual details.
    """
    if experience_level == "fresher":
        return (
            f"Dear Hiring Team,\n\n"
            f"I am writing to express my interest in {job_role} opportunities "
            f"at {company_name}. I am {candidate_summary}\n\n"
            f"I have attached my resume for your review and would appreciate "
            f"the opportunity to be considered for any suitable openings.\n\n"
            f"Thank you for your time and consideration.\n\n"
            f"Best regards"
        )
    else:
        return (
            f"Dear Hiring Team,\n\n"
            f"I am writing to inquire about {job_role} opportunities "
            f"at {company_name}. I am {candidate_summary}\n\n"
            f"I have attached my resume for your review and would welcome "
            f"the chance to discuss how my experience may be relevant to your team.\n\n"
            f"Thank you for your time and consideration.\n\n"
            f"Best regards"
        )


def personalized_email_writer(state: dict) -> dict:
    """
    LANGGRAPH NODE: Generate realistic, professional emails for every company.

    Uses the RESUME-DERIVED candidate summary as the source of truth.
    Falls back to basic user-input summary if resume was not parsed.

    Args:
        state: LangGraph state with researched companies + candidate profile

    Returns:
        Updated state with 'email_subject' and 'email_body' per company
    """
    companies = state["companies"]
    job_role = state["job_role"]
    experience_level = state.get("experience_level", "fresher")
    years_of_experience = state.get("years_of_experience", 0)
    skills = state.get("skills", [])

    # Use resume-derived summary (built in main.py from actual resume).
    # Falls back to basic summary if resume analysis wasn't available.
    candidate_summary = state.get("candidate_summary", "")
    if not candidate_summary:
        candidate_summary = _build_candidate_summary_fallback(
            experience_level, years_of_experience, skills, job_role
        )

    print(f"\n✍️  PERSONALIZED EMAIL WRITER")
    print(f"   Source: {'Resume-analyzed profile' if state.get('resume_profile') else 'User input'}")
    print(f"   Candidate: {candidate_summary[:120]}...")
    print(f"   Generating emails for {len(companies)} companies with Mistral AI...")
    print("=" * 50)

    llm = _create_writer_llm()
    generated = 0
    fallback_count = 0

    for i, company in enumerate(companies):
        company_name = company.get("company_name", "Unknown")
        research = company.get("research", "")

        print(f"   [{i+1}/{len(companies)}] Writing email for {company_name}...", end=" ")

        email_data = _generate_email(
            llm, company_name, job_role, research,
            candidate_summary, experience_level
        )

        company["email_subject"] = email_data["subject"]
        company["email_body"] = email_data["body"]

        # Check quality — no brackets should remain
        has_brackets = "[" in email_data["body"]
        has_forbidden = any(w in email_data["body"].lower() for w in ["admire", "inspired", "thrilled"])

        if not has_brackets and not has_forbidden:
            generated += 1
            print("✅")
        else:
            # Replace with clean fallback
            company["email_body"] = _generate_fallback_body(
                company_name, job_role, candidate_summary, experience_level
            )
            company["email_subject"] = f"Application for {job_role} Position"
            fallback_count += 1
            print("📝 (cleaned)")

        # Rate limiting for Mistral API
        if (i + 1) % 5 == 0:
            time.sleep(random.uniform(2.0, 4.0))
        else:
            time.sleep(random.uniform(0.5, 1.0))

    print(f"\n   📊 EMAIL GENERATION COMPLETE:")
    print(f"      AI-generated (clean): {generated}")
    print(f"      Fallback / cleaned:   {fallback_count}")

    state["companies"] = companies
    state["emails_generated"] = len(companies)
    return state
