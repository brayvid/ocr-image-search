import os
import sys
from PIL import Image
import pytesseract
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

from app import app, db, ImageRecord, IMAGE_FOLDER, allowed_file, pytesseract

def run_bulk_sync():
    with app.app_context():
        # 1. PRUNE MISSING FILES
        print("Cleaning up database (removing missing files)...")
        all_records = ImageRecord.query.all()
        removed = 0
        for record in all_records:
            if not os.path.exists(os.path.join(IMAGE_FOLDER, record.filename)):
                db.session.delete(record)
                removed += 1
        if removed > 0:
            db.session.commit()
            print(f"Removed {removed} records for missing files.")

        # 2. ADD NEW FILES
        existing_records = {record.filename for record in ImageRecord.query.all()}
        all_files = [f for f in os.listdir(IMAGE_FOLDER) if not f.startswith('.') and allowed_file(f)]
        new_files = [f for f in all_files if f not in existing_records]
        
        if not new_files:
            print("No new images to process. Database is clean and synced!")
            return
            
        print(f"Found {len(new_files)} new images. Starting OCR...")
        added_count = 0
        for filename in tqdm(new_files, desc="Processing", unit="img"):
            filepath = os.path.join(IMAGE_FOLDER, filename)
            file_stat = os.stat(filepath)
            creation_time = getattr(file_stat, 'st_birthtime', file_stat.st_mtime)
            try:
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img).strip()
                db.session.add(ImageRecord(filename=filename, extracted_text=text, created_at=creation_time))
                added_count += 1
                if added_count % 50 == 0: db.session.commit()
            except Exception as e:
                print(f"\n❌ Error on {filename}: {e}")
                sys.exit(1)
                
        db.session.commit()
        print(f"\n✅ Success! Added {added_count} new images.")

if __name__ == '__main__':
    run_bulk_sync()