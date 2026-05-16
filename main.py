"""
============================================
BULK AI JOB OUTREACH BOT
============================================
Main entry point. One command, full automation.

Usage:
    python main.py

The bot will:
    1. Analyze your resume (extract skills, education, experience)
    2. Ask for target role, location, and preferences
    3. Cross-check your input with resume data
    4. Search 100-300 companies matched to your level
    5. Find HR/careers emails
    6. Validate and deduplicate emails
    7. Research each company with AI
    8. Write realistic personalized emails using YOUR resume
    9. Send in batches with resume attached
    10. Log everything to CSV
"""

import sys
import time
from datetime import datetime

# Validate config before anything else
from config import validate_config
from graph import build_outreach_graph
from csv_logger import log_activity
from resume_handler import analyze_resume, classify_experience, build_rich_candidate_summary


def print_banner():
    """Print the startup banner."""
    print("\n" + "=" * 60)
    print("   🤖 BULK AI JOB OUTREACH BOT")
    print("   Powered by LangChain + LangGraph + Mistral AI")
    print("=" * 60)
    print("   One run. 100-300 companies. Full automation.")
    print("=" * 60)


def get_user_input(resume_profile: dict) -> dict:
    """
    Collect candidate preferences, cross-checked with resume data.
    Resume-extracted fields are shown as defaults — user can override.
    """
    print("\n📋 CANDIDATE PROFILE")
    print("-" * 50)

    # Pre-fill from resume where possible
    resume_skills = resume_profile.get("skills", [])
    resume_domain = resume_profile.get("preferred_domain", "")
    resume_years = resume_profile.get("total_years_experience", 0)
    resume_level = resume_profile.get("experience_level", "fresher")

    # 1. Job role — suggest from resume domain
    if resume_domain:
        print(f"   (Resume suggests: {resume_domain})")
    job_role = input("   1. Target job role (e.g., Data Analyst): ").strip()
    if not job_role:
        if resume_domain:
            job_role = resume_domain
            print(f"      Using resume domain: {job_role}")
        else:
            print("   ❌ Job role is required!")
            sys.exit(1)

    # 2. Location (optional)
    location = input("   2. Preferred location (press Enter for any): ").strip()

    # 3. Experience level — show resume-detected level
    if resume_level == "fresher":
        print(f"\n   3. Experience level (resume detected: Fresher):")
    else:
        print(f"\n   3. Experience level (resume detected: {resume_years} yrs):")
    print("      [1] Fresher / Entry-level")
    print("      [2] Experienced")
    exp_choice = input("      Select (1 or 2, Enter to use resume): ").strip()

    if exp_choice == "2":
        user_level = "experienced"
        while True:
            default_years = resume_years if resume_years > 0 else ""
            prompt = f"   4. Years of experience"
            if default_years:
                prompt += f" (resume: {default_years})"
            prompt += ": "
            years_input = input(prompt).strip()
            if not years_input and default_years:
                user_years = int(default_years)
                break
            try:
                user_years = int(years_input)
                if user_years < 1:
                    print("      ⚠ Enter at least 1 year.")
                    continue
                break
            except ValueError:
                print("      ⚠ Enter a valid number.")
    elif exp_choice == "1":
        user_level = "fresher"
        user_years = 0
    else:
        # Default to resume
        user_level = resume_level if resume_level != "fresher" else "fresher"
        user_years = resume_years

    # Cross-check experience with resume
    experience_level, years_of_experience, seniority = classify_experience(
        resume_profile, user_years, user_level
    )

    # 5. Key skills — show resume-extracted skills
    if resume_skills:
        print(f"\n   5. Resume skills: {', '.join(resume_skills[:10])}")
        skills_input = input("      Add/override skills (Enter to use resume skills): ").strip()
        if skills_input:
            skills = [s.strip() for s in skills_input.split(",") if s.strip()]
        else:
            skills = resume_skills
    else:
        skills_input = input("   5. Key skills (comma-separated): ").strip()
        if not skills_input:
            print("   ❌ At least one skill is required!")
            sys.exit(1)
        skills = [s.strip() for s in skills_input.split(",") if s.strip()]

    # 6. Preferred industry (optional)
    industry = input("   6. Preferred industry (press Enter to skip): ").strip()

    # Merge resume skills with user skills (deduplicated)
    if resume_skills and skills != resume_skills:
        seen = set(s.lower() for s in skills)
        for rs in resume_skills:
            if rs.lower() not in seen:
                skills.append(rs)
                seen.add(rs.lower())

    # Confirmation — show merged profile
    print("\n" + "-" * 50)
    print("   📝 FINAL PROFILE (resume + your input):")
    print(f"      Name:        {resume_profile.get('full_name') or 'N/A'}")
    print(f"      Role:        {job_role}")
    print(f"      Location:    {location or 'Any / Remote'}")
    print(f"      Level:       {seniority}")
    print(f"      Education:   {resume_profile.get('education', 'N/A')} — {resume_profile.get('degree_field', 'N/A')}")
    print(f"      Skills:      {', '.join(skills[:8])}")
    print(f"      Industry:    {industry or 'Any'}")
    print("-" * 50)

    confirm = input("\n   🚀 Start bulk outreach? (y/n): ").strip().lower()
    if confirm != "y":
        print("   Cancelled. Exiting.")
        sys.exit(0)

    return {
        "job_role": job_role,
        "location": location,
        "experience_level": experience_level,
        "years_of_experience": years_of_experience,
        "skills": skills,
        "industry": industry,
        "seniority": seniority,
    }


def main():
    """Main execution function."""
    print_banner()

    # Step 1: Validate configuration
    print("\n⚙️  CONFIGURATION CHECK")
    print("-" * 40)
    validate_config()

    # Step 2: Analyze resume FIRST
    resume_profile = analyze_resume()

    # Step 3: Get user profile (cross-checked with resume)
    profile = get_user_input(resume_profile)

    # Step 4: Build rich candidate summary from resume
    candidate_summary = build_rich_candidate_summary(resume_profile, profile["job_role"])
    print(f"\n   📝 Candidate summary for emails:")
    print(f"      \"{candidate_summary}\"")

    # Step 5: Build the LangGraph pipeline
    print("\n🔧 Building outreach pipeline...")
    app = build_outreach_graph()
    print("   ✅ Pipeline ready!\n")

    # Log the start
    log_activity("=" * 50)
    log_activity("NEW OUTREACH SESSION STARTED")
    log_activity(f"Name: {resume_profile.get('full_name', 'N/A')}")
    log_activity(f"Role: {profile['job_role']}")
    log_activity(f"Location: {profile['location'] or 'Any'}")
    log_activity(f"Level: {profile['seniority']}")
    log_activity(f"Skills: {', '.join(profile['skills'][:10])}")
    log_activity(f"Industry: {profile['industry'] or 'Any'}")
    log_activity(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 6: Run the pipeline
    start_time = time.time()

    print("🚀 STARTING BULK OUTREACH PIPELINE")
    print("=" * 60)

    # Initial state — includes full candidate profile + resume data
    initial_state = {
        "job_role": profile["job_role"],
        "location": profile["location"],
        "experience_level": profile["experience_level"],
        "years_of_experience": profile["years_of_experience"],
        "skills": profile["skills"],
        "industry": profile["industry"],
        "seniority": profile["seniority"],
        "resume_profile": resume_profile,
        "candidate_summary": candidate_summary,
        "companies": [],
        "total_found": 0,
        "validated_count": 0,
        "emails_generated": 0,
        "total_sent": 0,
        "total_failed": 0,
        "sent_companies": [],
        "failed_companies": [],
        "logging_complete": False,
    }

    # Execute the full pipeline
    try:
        final_state = app.invoke(initial_state)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Partial results may be saved.")
        log_activity("SESSION INTERRUPTED BY USER")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline error: {e}")
        log_activity(f"PIPELINE ERROR: {e}")
        raise

    # Step 7: Print final summary
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60

    print("\n" + "=" * 60)
    print("   🎉 BULK OUTREACH COMPLETE!")
    print("=" * 60)
    print(f"   📊 FINAL RESULTS:")
    print(f"      Candidate:         {resume_profile.get('full_name', 'N/A')}")
    print(f"      Job Role:          {profile['job_role']}")
    print(f"      Level:             {profile['seniority']}")
    print(f"      Location:          {profile['location'] or 'Any'}")
    print(f"      Companies Found:   {final_state.get('total_found', 0)}")
    print(f"      Emails Validated:  {final_state.get('validated_count', 0)}")
    print(f"      Emails Generated:  {final_state.get('emails_generated', 0)}")
    print(f"      Emails Sent:       {final_state.get('total_sent', 0)}")
    print(f"      Emails Failed:     {final_state.get('total_failed', 0)}")
    print(f"      Total Time:        {elapsed_min:.1f} minutes")
    print()
    print(f"   📁 OUTPUT FILES:")
    print(f"      output/sent_log.csv")
    print(f"      output/failed_log.csv")
    print(f"      output/companies_found.csv")
    print(f"      output/activity_log.txt")
    print("=" * 60)

    log_activity(f"SESSION COMPLETED in {elapsed_min:.1f} minutes")


if __name__ == "__main__":
    main()
