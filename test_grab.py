import scraper
import scaffold_pipeline

def run_test():
    print("🚀 Starting test for Grab & Strip...")
    client = scraper.get_client()
    url = "https://lms.vit.ac.in/mod/assign/view.php?id=21334"
    
    file_path, text = scaffold_pipeline.grab_and_strip(client, url)
    
    if file_path:
        print(f"\n✅ File successfully downloaded at: {file_path}")
    if text:
        print(f"\n✅ Extracted Text Preview (First 500 chars):\n")
        print("-" * 50)
        print(text[:500])
        print("...\n" + "-" * 50)
    else:
        print("\n⚠️ No text extracted. Check if it's an image-based PDF or unsupported format.")

if __name__ == "__main__":
    run_test()
