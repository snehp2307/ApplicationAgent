"""
============================================
LANGGRAPH WORKFLOW - BULK OUTREACH PIPELINE
============================================
Defines the complete LangGraph state machine that
orchestrates the entire bulk outreach process:

user_input → bulk_company_search → hr_email_scraper
→ email_validator → company_researcher
→ personalized_email_writer → batch_bulk_sender
→ csv_logger
"""

from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

# Import all node functions
from bulk_company_search import bulk_company_search
from hr_email_scraper import hr_email_scraper
from email_validator import email_validator
from company_researcher import company_researcher
from personalized_email_writer import personalized_email_writer
from batch_bulk_sender import batch_bulk_sender
from csv_logger import csv_logger


# ============================================
# STATE DEFINITION
# ============================================

class OutreachState(TypedDict, total=False):
    """Complete state for the bulk outreach pipeline."""
    # User inputs
    job_role: str
    location: str

    # Candidate profile (from user input + resume)
    experience_level: str           # "fresher" or "experienced"
    years_of_experience: int        # 0 for fresher, 1+ for experienced
    skills: list[str]               # e.g. ["Python", "SQL", "Excel"]
    industry: str                   # preferred industry or ""
    seniority: str                  # display label e.g. "Fresher / Entry-Level"

    # Resume-derived data
    resume_profile: dict[str, Any]  # full parsed profile from resume
    candidate_summary: str          # pre-built summary for email generation

    # Pipeline data
    companies: list[dict[str, Any]]
    total_found: int
    validated_count: int
    emails_generated: int

    # Send results
    total_sent: int
    total_failed: int
    sent_companies: list[dict[str, Any]]
    failed_companies: list[dict[str, Any]]

    # Final
    logging_complete: bool


# ============================================
# BUILD THE GRAPH
# ============================================

def build_outreach_graph():
    """
    Build and compile the LangGraph workflow for bulk outreach.

    Flow:
        start → bulk_search → email_scrape → validate
        → research → write_emails → send_bulk → log → end
    """
    # Create the graph with our state type
    workflow = StateGraph(OutreachState)

    # Add all nodes
    workflow.add_node("bulk_company_search", bulk_company_search)
    workflow.add_node("hr_email_scraper", hr_email_scraper)
    workflow.add_node("email_validator", email_validator)
    workflow.add_node("company_researcher", company_researcher)
    workflow.add_node("personalized_email_writer", personalized_email_writer)
    workflow.add_node("batch_bulk_sender", batch_bulk_sender)
    workflow.add_node("csv_logger", csv_logger)

    # Set the entry point
    workflow.set_entry_point("bulk_company_search")

    # Define the linear flow
    workflow.add_edge("bulk_company_search", "hr_email_scraper")
    workflow.add_edge("hr_email_scraper", "email_validator")
    workflow.add_edge("email_validator", "company_researcher")
    workflow.add_edge("company_researcher", "personalized_email_writer")
    workflow.add_edge("personalized_email_writer", "batch_bulk_sender")
    workflow.add_edge("batch_bulk_sender", "csv_logger")
    workflow.add_edge("csv_logger", END)

    # Compile the graph
    app = workflow.compile()
    return app
