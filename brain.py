import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

EXACT_SOLUTION_PROMPT = """
Analyze the assignment provided below thoroughly.
First, provide a clear, concise 3 to 4-line summary explaining what the assignment is asking for and what key concepts or elements need to be included in the response.
Next, provide the complete, comprehensive theoretical solution for every single requirement and instruction mentioned in the assignment (such as Gantt charts, step-by-step logs, calculation tables, metrics, and analysis). 

CRITICAL NEGATIVE CONSTRAINT:
- DO NOT WRITE ANY C, C++, Python, or any other programming code. 
- DO NOT include code snippets, class structures, skeleton code, or implementation scripts. 
- Deliver purely theoretical analysis and answers only.

Keep the tone straightforward, practical, and strictly in English.
"""

def generate_study_guide(text, file_name):
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY missing in .env file!")
        return None
        
    print(f"🧠 Waking up AI Brain for theoretical assignment solution on {file_name}...")
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"Assignment text:\n{text}"
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=EXACT_SOLUTION_PROMPT,
            )
        )
        return response.text
    except Exception as e:
        print(f"❌ AI Generation Error: {e}")
        return None
