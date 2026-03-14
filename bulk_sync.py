import os
import sys # For exiting
from PIL import Image
import pytesseract
from tqdm import tqdm
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

# Import your database and app context from your main app
# IMPORTANT: Use the TESSERACT_PATH from .env defined in app.py's context
from app import app, db, ImageRecord, IMAGE_FOLDER, allowed_file, pytesseract

def run_bulk_sync():
    # Pre-check Tesseract path
    if not pytesseract.pytesseract.tesseract_cmd or not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
        print(f"❌ ERROR: Tesseract executable not found at '{pytesseract.pytesseract.tesseract_cmd}'.")
        print("Please check TESSERACT_PATH in your .env file and ensure Tesseract is installed correctly.")
        sys.exit(1) # Exit immediately if Tesseract isn't ready
        
    if not IMAGE_FOLDER or not os.path.exists(IMAGE_FOLDER):
        print(f"❌ ERROR: Image directory not found at '{IMAGE_FOLDER}'.")
        print("Please check IMAGE_FOLDER in your .env file.")
        sys.exit(1) # Exit immediately if image folder isn't ready

    print(f"Scanning folder: {IMAGE_FOLDER}")
    
    with app.app_context():
        existing_records = {record.filename for record in ImageRecord.query.all()}
        
        all_files = [f for f in os.listdir(IMAGE_FOLDER) 
                     if not f.startswith('.') and allowed_file(f)]
        
        new_files = [f for f in all_files if f not in existing_records]
        
        if not new_files:
            print("No new images to process. You are fully synced!")
            return
            
        print(f"Found {len(new_files)} new images. Starting OCR processing...")
        
        added_count = 0
        
        for filename in tqdm(new_files, desc="Processing Images", unit="img"):
            filepath = os.path.join(IMAGE_FOLDER, filename)
            
            file_stat = os.stat(filepath)
            creation_time = getattr(file_stat, 'st_birthtime', file_stat.st_mtime)
            
            try:
                img = Image.open(filepath)
                extracted_text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                # --- NEW: Immediately stop and report the specific error ---
                print(f"\n\n❌ CRITICAL ERROR processing '{filename}': {e}")
                print("Bulk sync halted to prevent further processing issues. Please resolve the error and re-run.")
                sys.exit(1) # Exit the script here
            
            new_record = ImageRecord(
                filename=filename, 
                extracted_text=extracted_text,
                created_at=creation_time
            )
            db.session.add(new_record)
            added_count += 1
            
            if added_count % 50 == 0:
                db.session.commit()
                
        db.session.commit()
        print(f"\n✅ Success! Processed and saved {added_count} new images to the database.")

if __name__ == '__main__':
    run_bulk_sync()