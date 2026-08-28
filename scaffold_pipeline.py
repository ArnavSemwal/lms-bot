import os
import httpx
from bs4 import BeautifulSoup
import pdfplumber
import docx

TEMP_DIR = "temp_downloads"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def grab_and_strip(client, assign_url):
    print(f"🕵️‍♂️ Hunting for attachments on: {assign_url}")
    
    try:
        res = client.get(assign_url)
    except Exception as e:
        print(f"❌ Failed to load assignment page: {e}")
        return None, None
        
    soup = BeautifulSoup(res.text, "html.parser")
    
    file_link = None
    file_name = None
    
    for a in soup.find_all('a', href=True):
        if "pluginfile.php" in a['href']:
            file_link = a['href']
            file_name = file_link.split('/')[-1].split('?')[0] 
            file_name = file_name.replace("%20", "_") 
            break
            
    if not file_link:
        print("  No attachments found on this assignment.")
        return None, None
        
    print(f"⬇️ Downloading: {file_name}")
    file_path = os.path.join(TEMP_DIR, file_name)
    
    try:
        with open(file_path, "wb") as f:
            with client.stream("GET", file_link) as response:
                for chunk in response.iter_bytes():
                    f.write(chunk)
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None, None
                
    print("✅ Download complete. Stripping text...")
    
    ext = file_name.lower().split('.')[-1]
    text = ""
    
    try:
        if ext == "pdf":
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        elif ext in ["docx", "doc"]:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            print(f"⚠️ Unsupported format for extraction: {ext}")
            return file_path, None
            
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return file_path, None
        
    print(f"🧠 Successfully extracted {len(text)} characters of text!")
    return file_path, text.strip()
