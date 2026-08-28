import scraper
import scaffold_pipeline
import brain

def run_test():
    print("🚀 Starting full Grab -> Strip -> Brain Pipeline...")
    client = scraper.get_client()
    url = "https://lms.vit.ac.in/mod/assign/view.php?id=21334"
    
    file_path, text = scaffold_pipeline.grab_and_strip(client, url)
    
    if text:
        file_name = file_path.split("\\")[-1] if "\\" in file_path else file_path.split("/")[-1]
        
        print("\n⏳ Piping text to Gemini API...")
        study_guide = brain.generate_study_guide(text, file_name)
        
        if study_guide:
            print("\n✅ AI Response Received:\n")
            print("=" * 60)
            print(study_guide)
            print("=" * 60)
    else:
        print("⚠️ Extracted text is empty, skipping AI phase.")

if __name__ == "__main__":
    run_test()
