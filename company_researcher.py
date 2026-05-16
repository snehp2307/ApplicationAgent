"""
============================================
COMPANY RESEARCHER MODULE
============================================
Does brief research on each company using
Mistral AI to create context for personalized
email generation.
"""

import time
import random
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage
import config


def _create_research_llm():
    """Create a Mistral AI instance for company research."""
    return ChatMistralAI(
        model=config.MISTRAL_MODEL,
        mistral_api_key=config.MISTRAL_API_KEY,
        temperature=0.3,
        max_tokens=300,
    )


def _research_single_company(
    llm: ChatMistralAI,
    company_name: str,
    domain: str,
    snippet: str,
    job_role: str,
) -> str:
    """
    Use Mistral AI to generate a brief company research summary.
    This summary will be used to personalize the outreach email.
    """
    try:
        messages = [
            SystemMessage(content=(
                "You are a job market research assistant. Given a company name and any "
                "available information, provide a brief 2-3 sentence summary about "
                "the company that would be useful for a job applicant. Focus on: "
                "what the company does, their industry, and why they might need "
                "the specified role. Be concise and factual. If you don't know much "
                "about the company, make reasonable inferences from the domain name "
                "and any provided context. Do NOT make up specific revenue numbers "
                "or employee counts."
            )),
            HumanMessage(content=(
                f"Company: {company_name}\n"
                f"Domain: {domain}\n"
                f"Context: {snippet}\n"
                f"Target Role: {job_role}\n\n"
                f"Provide a brief research summary for personalizing a job application email."
            )),
        ]

        response = llm.invoke(messages)
        return response.content.strip()

    except Exception as e:
        return f"Technology company operating at {domain}."


def company_researcher(state: dict) -> dict:
    """
    LANGGRAPH NODE: Research each company briefly using Mistral AI.

    Generates a short research summary for each company to enable
    personalized email content. Processes in mini-batches to
    respect API rate limits.

    Args:
        state: LangGraph state with validated 'companies' list

    Returns:
        Updated state with 'research' field added to each company
    """
    companies = state["companies"]
    job_role = state["job_role"]

    print(f"\n🔬 COMPANY RESEARCHER")
    print(f"   Researching {len(companies)} companies with Mistral AI...")
    print("=" * 50)

    llm = _create_research_llm()
    researched = 0
    errors = 0

    for i, company in enumerate(companies):
        company_name = company.get("company_name", "Unknown")
        domain = company.get("domain", "")
        snippet = company.get("snippet", "")

        print(f"   [{i+1}/{len(companies)}] Researching {company_name}...", end=" ")

        research = _research_single_company(llm, company_name, domain, snippet, job_role)
        company["research"] = research

        if "error" not in research.lower() and len(research) > 20:
            researched += 1
            print("✅")
        else:
            errors += 1
            print("⚠ (using fallback)")

        # Rate limiting for Mistral API (respect limits)
        # Process in groups of 5 with a pause
        if (i + 1) % 5 == 0:
            time.sleep(random.uniform(1.5, 3.0))
        else:
            time.sleep(random.uniform(0.3, 0.8))

    print(f"\n   📊 RESEARCH COMPLETE:")
    print(f"      Successfully researched: {researched}")
    print(f"      Fallback used: {errors}")

    state["companies"] = companies
    return state
