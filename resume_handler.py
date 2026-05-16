"""
============================================
RESUME HANDLER MODULE
============================================
Handles resume PDF/DOCX parsing, AI-powered
information extraction, and email attachment.

Extracts a structured candidate profile:
- Name, education, degree
- Skills, certifications, tools
- Work experience, internships, projects
- Estimated years of experience
- Experience level classification
============================================
"""

import os
import re
import json
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage
import config


# ============================================
# TEXT EXTRACTION (PDF / DOCX)
# ============================================

def _extract_text_from_pdf(filepath: str) -> str:
    """Extract all text from a PDF file."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        print(f"   ⚠ PDF parsing error: {e}")
        return ""


def _extract_text_from_docx(filepath: str) -> str:
    """Extract all text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(filepath)
        text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(text_parts)
    except Exception as e:
        print(f"   ⚠ DOCX parsing error: {e}")
        return ""


def extract_resume_text(filepath: str) -> str:
    """
    Extract raw text from a resume file (PDF or DOCX).
    Returns the full text content of the resume.
    """
    filepath_lower = filepath.lower()
    if filepath_lower.endswith(".pdf"):
        return _extract_text_from_pdf(filepath)
    elif filepath_lower.endswith(".docx"):
        return _extract_text_from_docx(filepath)
    elif filepath_lower.endswith(".doc"):
        print("   ⚠ .doc format not supported. Please convert to .pdf or .docx")
        return ""
    else:
        print(f"   ⚠ Unsupported file format: {os.path.splitext(filepath)[1]}")
        return ""


# ============================================
# AI-POWERED PROFILE EXTRACTION
# ============================================

def _create_extraction_llm():
    """Create a Mistral AI instance for resume parsing."""
    return ChatMistralAI(
        model=config.MISTRAL_MODEL,
        mistral_api_key=config.MISTRAL_API_KEY,
        temperature=0.1,
        max_tokens=2048,
    )


def extract_candidate_profile(resume_text: str) -> dict:
    """
    Use Mistral AI to extract a structured candidate profile
    from raw resume text. Returns a dict with all parsed fields.
    """
    if not resume_text or len(resume_text.strip()) < 50:
        print("   ⚠ Resume text too short for analysis.")
        return _empty_profile()

    llm = _create_extraction_llm()

    prompt = """Analyze this resume text and extract candidate information.
Return ONLY valid JSON with these exact keys (use empty string "" if not found, empty list [] if no items):

{
  "full_name": "candidate's full name",
  "email": "email address from resume",
  "phone": "phone number from resume",
  "education": "highest education (e.g. B.Com, B.Tech, MBA, M.Sc)",
  "degree_field": "field of study (e.g. Computer Science, Commerce, Logistics)",
  "university": "university or college name",
  "skills": ["skill1", "skill2", "skill3"],
  "tools_technologies": ["tool1", "tool2"],
  "certifications": ["cert1", "cert2"],
  "projects": ["brief project description 1", "brief project description 2"],
  "internships": ["company - role - duration"],
  "work_experience": ["company - role - duration"],
  "total_years_experience": 0,
  "experience_level": "fresher",
  "preferred_domain": "best-fit job domain based on resume content"
}

RULES for experience_level:
- "fresher" if no work experience or only internships
- "junior" if 1-2 years of work experience
- "mid" if 3-5 years of work experience
- "senior" if 5+ years of work experience

RULES for total_years_experience:
- Count ONLY paid full-time work experience, not internships
- If only internships exist, set to 0
- If unclear, estimate conservatively

RULES for skills:
- Extract ACTUAL skills mentioned in the resume
- Include both technical skills (Python, SQL) and soft skills (communication)
- Do NOT invent skills that are not in the resume

RULES for preferred_domain:
- Infer from the combination of education, skills, and experience
- Examples: "Data Analytics", "Supply Chain", "Software Development", "Marketing"

Return ONLY the JSON object, no explanation."""

    try:
        messages = [
            SystemMessage(content="You are a resume parser. Extract information accurately. Return only valid JSON."),
            HumanMessage(content=f"{prompt}\n\nRESUME TEXT:\n{resume_text[:4000]}"),
        ]
        response = llm.invoke(messages)
        raw = response.content.strip()

        # Clean up: extract JSON from response
        # Handle cases where LLM wraps JSON in markdown code blocks
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        profile = json.loads(raw)
        return _validate_profile(profile)

    except json.JSONDecodeError as e:
        print(f"   ⚠ Could not parse AI response as JSON: {e}")
        return _fallback_extraction(resume_text)
    except Exception as e:
        print(f"   ⚠ AI extraction error: {e}")
        return _fallback_extraction(resume_text)


def _validate_profile(profile: dict) -> dict:
    """Ensure all expected keys exist and have correct types."""
    defaults = _empty_profile()
    for key, default_val in defaults.items():
        if key not in profile:
            profile[key] = default_val
        elif isinstance(default_val, list) and not isinstance(profile[key], list):
            profile[key] = [profile[key]] if profile[key] else []
        elif isinstance(default_val, int) and not isinstance(profile[key], int):
            try:
                profile[key] = int(profile[key])
            except (ValueError, TypeError):
                profile[key] = default_val
    return profile


def _empty_profile() -> dict:
    """Return an empty candidate profile with all keys."""
    return {
        "full_name": "",
        "email": "",
        "phone": "",
        "education": "",
        "degree_field": "",
        "university": "",
        "skills": [],
        "tools_technologies": [],
        "certifications": [],
        "projects": [],
        "internships": [],
        "work_experience": [],
        "total_years_experience": 0,
        "experience_level": "fresher",
        "preferred_domain": "",
    }


# ============================================
# FALLBACK: REGEX-BASED EXTRACTION
# ============================================

def _fallback_extraction(resume_text: str) -> dict:
    """
    Basic regex-based extraction when AI parsing fails.
    Catches common patterns for emails, skills, etc.
    """
    profile = _empty_profile()
    text = resume_text

    # Extract email
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if emails:
        profile["email"] = emails[0]

    # Extract phone
    phones = re.findall(r"[\+]?[\d\s\-\(\)]{10,15}", text)
    if phones:
        profile["phone"] = phones[0].strip()

    # Extract common skills by keyword matching
    common_skills = [
        "Python", "SQL", "Excel", "Power BI", "Tableau", "Java", "JavaScript",
        "R", "C++", "C#", "HTML", "CSS", "React", "Node.js", "Django", "Flask",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "Linux",
        "Machine Learning", "Data Analysis", "Data Science", "Statistics",
        "Communication", "Leadership", "Project Management", "Agile", "Scrum",
        "SAP", "Salesforce", "MongoDB", "PostgreSQL", "MySQL", "TensorFlow",
        "PyTorch", "Pandas", "NumPy", "Spark", "Hadoop", "ETL", "API",
        "Supply Chain", "Logistics", "Operations", "Marketing", "Finance",
        "Accounting", "MS Office", "Word", "PowerPoint", "SPSS", "MATLAB",
    ]
    found_skills = []
    text_lower = text.lower()
    for skill in common_skills:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    profile["skills"] = found_skills[:15]

    # Detect education
    edu_patterns = [
        r"(B\.?Tech|B\.?E|B\.?Sc|B\.?Com|B\.?A|B\.?BA|BCA|BCS)",
        r"(M\.?Tech|M\.?E|M\.?Sc|M\.?Com|M\.?A|MBA|MCA)",
        r"(Ph\.?D|Doctorate)",
        r"(Diploma|Certificate)",
    ]
    for pattern in edu_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            profile["education"] = match.group(0)
            break

    # Estimate experience level from keywords
    exp_matches = re.findall(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", text_lower)
    if exp_matches:
        years = max(int(y) for y in exp_matches)
        profile["total_years_experience"] = years
        if years == 0:
            profile["experience_level"] = "fresher"
        elif years <= 2:
            profile["experience_level"] = "junior"
        elif years <= 5:
            profile["experience_level"] = "mid"
        else:
            profile["experience_level"] = "senior"
    else:
        # Check for fresher indicators
        fresher_words = ["fresher", "fresh graduate", "entry level", "entry-level", "intern", "trainee"]
        if any(w in text_lower for w in fresher_words):
            profile["experience_level"] = "fresher"

    return profile


# ============================================
# EXPERIENCE LEVEL CLASSIFICATION
# ============================================

def classify_experience(profile: dict, user_years: int, user_level: str) -> tuple[str, int, str]:
    """
    Cross-check resume-derived experience with user input.
    Prefers resume data when there's a mismatch. Returns
    (experience_level, years, seniority_label).
    """
    resume_years = profile.get("total_years_experience", 0)
    resume_level = profile.get("experience_level", "fresher")

    # If resume has clear data, prefer it
    if resume_years > 0:
        final_years = resume_years
    elif user_years > 0:
        final_years = user_years
    else:
        final_years = 0

    # Classify based on final years
    if final_years == 0:
        level = "fresher"
        seniority = "Fresher / Entry-Level"
    elif final_years <= 2:
        level = "experienced"
        seniority = f"Junior ({final_years} yr{'s' if final_years > 1 else ''})"
    elif final_years <= 5:
        level = "experienced"
        seniority = f"Mid-Level ({final_years} yrs)"
    else:
        level = "experienced"
        seniority = f"Senior ({final_years} yrs)"

    return level, final_years, seniority


# ============================================
# CANDIDATE SUMMARY BUILDER
# ============================================

def build_rich_candidate_summary(profile: dict, job_role: str) -> str:
    """
    Build a detailed, plain-English candidate summary from the
    parsed resume profile. This is the source of truth for all
    email generation — every fact comes from the actual resume.
    """
    parts = []

    # Experience sentence
    years = profile.get("total_years_experience", 0)
    level = profile.get("experience_level", "fresher")

    if level == "fresher":
        if profile.get("education") and profile.get("degree_field"):
            parts.append(
                f"a recent {profile['education']} graduate in {profile['degree_field']}"
                f" seeking entry-level {job_role} opportunities"
            )
        elif profile.get("education"):
            parts.append(
                f"a recent {profile['education']} graduate seeking entry-level "
                f"{job_role} opportunities"
            )
        else:
            parts.append(f"a recent graduate seeking entry-level {job_role} opportunities")
    else:
        parts.append(
            f"a professional with {years} year{'s' if years != 1 else ''} "
            f"of experience in {job_role} and related domains"
        )

    # Skills sentence
    skills = profile.get("skills", [])
    if skills:
        top_skills = skills[:5]
        parts.append(f"Key skills include {', '.join(top_skills)}")

    # Education (if experienced, add as background)
    if level != "fresher" and profile.get("education") and profile.get("degree_field"):
        parts.append(
            f"Academic background in {profile['degree_field']} "
            f"({profile['education']})"
        )

    # Certifications
    certs = profile.get("certifications", [])
    if certs:
        parts.append(f"Certified in {', '.join(certs[:3])}")

    # Projects (mention count, not details)
    projects = profile.get("projects", [])
    if projects and level == "fresher":
        parts.append(f"Completed {len(projects)} relevant project{'s' if len(projects) > 1 else ''}")

    # Internships (for freshers)
    internships = profile.get("internships", [])
    if internships and level == "fresher":
        parts.append(f"Completed {len(internships)} internship{'s' if len(internships) > 1 else ''}")

    return ". ".join(parts) + "."


# ============================================
# FILE LOADING (for email attachment)
# ============================================

def load_resume() -> dict:
    """
    Load the resume file and prepare it for email attachment.
    Returns file metadata (path, filename, exists, size).
    """
    resume_path = config.RESUME_PATH

    if not resume_path:
        return {"path": "", "filename": "", "exists": False, "size_kb": 0}

    # Normalize path
    resume_path = os.path.abspath(resume_path)

    if not os.path.exists(resume_path):
        print(f"   ⚠ Resume file not found: {resume_path}")
        return {"path": resume_path, "filename": "", "exists": False, "size_kb": 0}

    filename = os.path.basename(resume_path)
    size_bytes = os.path.getsize(resume_path)
    size_kb = round(size_bytes / 1024, 1)

    # Validate file size (Gmail max attachment: 25MB)
    if size_bytes > 25 * 1024 * 1024:
        print(f"   ⚠ Resume file too large ({size_kb}KB). Gmail limit is 25MB.")
        return {"path": resume_path, "filename": filename, "exists": False, "size_kb": size_kb}

    print(f"   📎 Resume loaded: {filename} ({size_kb} KB)")
    return {
        "path": resume_path,
        "filename": filename,
        "exists": True,
        "size_kb": size_kb,
    }


def get_resume_bytes(resume_info: dict) -> bytes | None:
    """
    Read the resume file and return its bytes for email attachment.
    """
    if not resume_info.get("exists"):
        return None

    try:
        with open(resume_info["path"], "rb") as f:
            return f.read()
    except Exception as e:
        print(f"   ⚠ Error reading resume: {e}")
        return None


# ============================================
# MAIN ANALYSIS FUNCTION
# ============================================

def analyze_resume() -> dict:
    """
    Full resume analysis pipeline:
    1. Load the file
    2. Extract raw text (PDF/DOCX)
    3. Parse structured profile with AI
    4. Return the complete candidate profile

    Returns:
        dict with all candidate profile fields,
        plus 'resume_text' for reference
    """
    resume_path = config.RESUME_PATH

    if not resume_path:
        print("   ⚠ No resume path configured.")
        return _empty_profile()

    resume_path = os.path.abspath(resume_path)

    if not os.path.exists(resume_path):
        print(f"   ⚠ Resume not found: {resume_path}")
        return _empty_profile()

    print(f"\n📄 RESUME ANALYSIS")
    print(f"   File: {os.path.basename(resume_path)}")
    print("-" * 50)

    # Step 1: Extract text
    print("   Extracting text...", end=" ")
    text = extract_resume_text(resume_path)
    if not text:
        print("❌ No text extracted.")
        return _empty_profile()
    print(f"✅ ({len(text)} characters)")

    # Step 2: AI-powered extraction
    print("   Analyzing with Mistral AI...", end=" ")
    profile = extract_candidate_profile(text)
    print("✅")

    # Step 3: Display extracted profile
    print("\n   📋 EXTRACTED PROFILE:")
    print(f"      Name:          {profile.get('full_name', 'N/A')}")
    print(f"      Education:     {profile.get('education', 'N/A')} — {profile.get('degree_field', 'N/A')}")
    print(f"      Skills:        {', '.join(profile.get('skills', [])[:8])}")
    print(f"      Experience:    {profile.get('experience_level', 'N/A')} ({profile.get('total_years_experience', 0)} yrs)")
    print(f"      Domain:        {profile.get('preferred_domain', 'N/A')}")
    certs = profile.get("certifications", [])
    if certs:
        print(f"      Certifications: {', '.join(certs[:3])}")
    projects = profile.get("projects", [])
    if projects:
        print(f"      Projects:      {len(projects)} found")
    print("-" * 50)

    # Store raw text for reference
    profile["resume_text"] = text[:2000]

    return profile
