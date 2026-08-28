import re
from pathlib import Path
import httpx
import pdfplumber
from docx import Document

def download_attachment(url: str, cookies: dict, dest: Path) -> Path:
    """Stream-download an attachment from Moodle using session cookies and proper headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://lms.vit.ac.in/"
    }
    with httpx.Client(cookies=cookies, headers=headers, follow_redirects=True, timeout=30.0, verify=False) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
                    
    # Verify if downloaded file is actually a PDF and not an HTML error page
    with open(dest, "rb") as f:
        header = f.read(5)
        if header.startswith(b"<!DOCTYPE") or header.startswith(b"<html"):
            raise ValueError("Downloaded file is an HTML page (likely session redirected or invalid assignment URL), not a PDF.")
            
    return dest

def extract_text(path: Path) -> str:
    """Pull raw text out of a PDF assignment file."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    elif suffix == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

def scaffold_markdown_to_docx(markdown_text: str, title: str, out_path: Path) -> Path:
    """Convert markdown study guide into a formatted Word document."""
    doc = Document()
    doc.add_heading(title, level=0)
    
    for line in markdown_text.split("\n"):
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.startswith("# "):
            doc.add_heading(line_str[2:], level=1)
        elif line_str.startswith("## "):
            doc.add_heading(line_str[3:], level=2)
        elif line_str.startswith(("- ", "* ")):
            doc.add_paragraph(line_str[2:], style='List Bullet')
        else:
            doc.add_paragraph(line_str)
            
    doc.save(out_path)
    return out_path
