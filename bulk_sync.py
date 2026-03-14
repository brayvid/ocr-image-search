import os
from PIL import Image
import pytesseract
from tqdm import tqdm
from dotenv import load_dotenv

# Import your database and app context from your main app
from app import app, db, ImageRecord, SCREENSHOTS_FOLDER, allowed_file

# IF ON APPLE SILICON, UNCOMMENT THIS:
# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

def run_bulk_sync():
    print(f"Scanning folder: {SCREENSHOTS_FOLDER}")
    
    with app.app_context():
        # Get list of what is already in the database
        existing_records = {record.filename for record in ImageRecord.query.all()}
        
        # Get all valid images in the Google Drive folder
        all_files = [f for f in os.listdir(SCREENSHOTS_FOLDER) 
                     if not f.startswith('.') and allowed_file(f)]
        
        # Filter down to ONLY the new images
        new_files = [f for f in all_files if f not in existing_records]
        
        if not new_files:
            print("No new images to process. You are fully synced!")
            return
            
        print(f"Found {len(new_files)} new images. Starting OCR processing...")
        
        added_count = 0
        
        # tqdm creates a beautiful loading bar in your terminal!
        for filename in tqdm(new_files, desc="Processing Images", unit="img"):
            filepath = os.path.join(SCREENSHOTS_FOLDER, filename)
            
            try:
                img = Image.open(filepath)
                extracted_text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                extracted_text = f"Error processing: {e}"
            
            new_record = ImageRecord(filename=filename, extracted_text=extracted_text)
            db.session.add(new_record)
            added_count += 1
            
            # Save to database every 50 images so you don't lose progress if you cancel
            if added_count % 50 == 0:
                db.session.commit()
                
        # Final save
        db.session.commit()
        print(f"\n✅ Success! Processed and saved {added_count} new images to the database.")

if __name__ == '__main__':
    run_bulk_sync()