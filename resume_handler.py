"""
============================================
RESUME HANDLER MODULE
============================================
Handles loading and attaching the resume PDF
file to outgoing emails.
"""

import os
import config


def load_resume() -> dict:
    """
    Load the resume file and prepare it for email attachment.

    Returns:
        dict with:
            - 'path': absolute file path
            - 'filename': just the filename
            - 'exists': bool
            - 'size_kb': file size in KB
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

    Args:
        resume_info: dict from load_resume()

    Returns:
        bytes of the file content, or None if unavailable
    """
    if not resume_info.get("exists"):
        return None

    try:
        with open(resume_info["path"], "rb") as f:
            return f.read()
    except Exception as e:
        print(f"   ⚠ Error reading resume: {e}")
        return None
