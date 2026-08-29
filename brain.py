import os
from google import genai

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def _to_gemini_contents(messages: list[dict]) -> tuple[str, list[dict]]:
    system_text = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    role_map = {"user": "user", "assistant": "model", "model": "model"}
    contents = []
    for m in messages:
        if m["role"] == "system":
            continue
        gemini_role = role_map.get(m["role"], "user")
        contents.append({"role": gemini_role, "parts": [{"text": m["content"]}]})
    return system_text, contents

def llm_call(messages: list[dict]) -> str:
    system_text, contents = _to_gemini_contents(messages)
    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config={"system_instruction": system_text} if system_text else None,
    )
    return response.text

def generate_study_guide(text: str, filename: str) -> str:
    print(f"🧠 Waking up AI Brain for clean structured study guide on {filename}...")
    
    # Prompt upgraded with strict negative constraints
    system_prompt = (
        "You are an expert academic AI assistant. Generate a highly structured, "
        "comprehensive study guide and solution approach for the provided assignment text. "
        "Use clear Markdown headings, bullet points, and step-by-step logical breakdowns. "
        "STRICT CONSTRAINTS: "
        "1. DO NOT write, include, or generate any source code, programming blocks, or scripts "
        "(e.g., absolutely no C, C++, Python, Java). Focus ONLY on theory, mathematical logic, "
        "and step-by-step simulation. "
        "2. DO NOT use LaTeX formatting or complex math delimiters (like $, \\frac, \\sum). "
        "Write formulas using plain text and standard keyboard symbols (e.g., 'Avg TAT = Total TAT / N') "
        "so they render cleanly in standard word processors."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Assignment File: {filename}\n\nExtracted Text from PDF:\n{text}\n\nPlease analyze this and generate the detailed study guide."}
    ]
    
    try:
        return llm_call(messages)
    except Exception as e:
        print(f"⚠️ AI generation error: {e}")
        return ""

def list_available_models() -> None:
    for m in _client.models.list():
        print(m.name)

if __name__ == "__main__":
    list_available_models()