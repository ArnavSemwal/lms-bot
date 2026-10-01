import os
from openai import OpenAI

XAI_MODEL = os.environ.get("XAI_MODEL", "grok-2-latest")
_client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY", ""),
    base_url="https://api.xai.com/v1",
)

def llm_call(messages: list[dict]) -> str:
    response = _client.chat.completions.create(
        model=XAI_MODEL,
        messages=messages,
    )
    return response.choices[0].message.content

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
    for m in _client.models.list().data:
        print(m.id)

if __name__ == "__main__":
    list_available_models()