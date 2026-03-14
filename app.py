import os
import re
import logging  # <-- We still need this!
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
import pytesseract
from markupsafe import Markup
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

# IF ON APPLE SILICON (M1/M2/M3), UNCOMMENT THE LINE BELOW:
# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

app = Flask(__name__)

# === NEW: Custom Log Filter to hide only image requests ===
class NoImagesFilter(logging.Filter):
    def filter(self, record):
        # This checks the log message and returns False (don't log it) if it contains /images/
        return '/images/' not in record.getMessage()

# Get the default Werkzeug logger and add our custom filter
log = logging.getLogger('werkzeug')
log.addFilter(NoImagesFilter())
# --- End of new code ---

# Pull the secret key and folder from the .env file
app.secret_key = os.getenv("SECRET_KEY", "fallback_default_key")
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER")

# === ISOLATE DATABASE OUTSIDE OF GOOGLE DRIVE ===
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'images.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class ImageRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(250), nullable=False, unique=True)
    extracted_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.Float, nullable=False, default=0.0)

with app.app_context():
    db.create_all()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.template_filter('highlight')
def highlight_filter(text, query, exact=False):
    if not query or not text:
        return text
    escaped_query = re.escape(query)
    
    if exact:
        pattern = re.compile(rf'(\b{escaped_query}\b)', re.IGNORECASE)
    else:
        pattern = re.compile(f"({escaped_query})", re.IGNORECASE)
        
    highlighted = pattern.sub(r'<mark class="bg-warning px-1 rounded">\1</mark>', text)
    return Markup(highlighted)

STOP_WORDS = {
    "the", "and", "to", "of", "in", "is", "it", "you", "that", "he", "was", "for", 
    "on", "are", "with", "as", "we", "his", "they", "be", "at", "one", "have", "this", 
    "from", "or", "had", "by", "not", "but", "some", "what", "there", "out", "all", 
    "your", "can", "has", "any", "which", "their", "were", "when", "will", "how", 
    "pm", "am", "com", "www", "http", "https", "net", "org", "the", "too", "get", "got", "new"
}

def get_most_frequent_terms(limit=50):
    all_texts = db.session.query(ImageRecord.extracted_text).filter(ImageRecord.extracted_text.isnot(None)).all()
    document_word_counts = Counter()
    
    for text in all_texts:
        words_in_doc = re.findall(r'\b[a-z]{3,}\b', text[0].lower())
        unique_words_in_doc = set([w for w in words_in_doc if w not in STOP_WORDS])
        document_word_counts.update(unique_words_in_doc)
        
    return document_word_counts.most_common(limit)

@app.route('/images/<path:filename>')
def serve_image(filename):
    if not IMAGE_FOLDER:
        return "IMAGE_FOLDER not set in .env", 500
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    search_query = request.args.get('q', '').strip()
    sort_order = request.args.get('sort', 'desc')
    exact_match = request.args.get('exact') == 'true'
    
    top_terms = get_most_frequent_terms(limit=50)

    if sort_order == 'asc':
        all_records = ImageRecord.query.order_by(ImageRecord.created_at.asc()).all()
    else:
        all_records = ImageRecord.query.order_by(ImageRecord.created_at.desc()).all()
        
    records = []
    
    if search_query:
        escaped_query = re.escape(search_query)
        if exact_match:
            pattern = re.compile(rf'\b{escaped_query}\b', re.IGNORECASE)
        else:
            pattern = re.compile(escaped_query, re.IGNORECASE)
            
        for record in all_records:
            if record.extracted_text and pattern.search(record.extracted_text):
                records.append(record)
    else:
        records = all_records
        
    return render_template('index.html', 
                           records=records, 
                           search_query=search_query, 
                           top_terms=top_terms, 
                           sort_order=sort_order,
                           exact_match=exact_match,
                           folder_path=IMAGE_FOLDER)

@app.route('/sync', methods=['POST'])
def sync_folder():
    if not IMAGE_FOLDER or not os.path.exists(IMAGE_FOLDER):
        flash(f"Directory not found. Please check IMAGE_FOLDER in your .env file.", "danger")
        return redirect(url_for('index'))
        
    added_count = 0
    existing_records = {record.filename for record in ImageRecord.query.all()}
    
    for filename in os.listdir(IMAGE_FOLDER):
        if filename.startswith('.') or not allowed_file(filename):
            continue
            
        if filename not in existing_records:
            filepath = os.path.join(IMAGE_FOLDER, filename)
            
            file_stat = os.stat(filepath)
            creation_time = getattr(file_stat, 'st_birthtime', file_stat.st_mtime)
            
            try:
                img = Image.open(filepath)
                extracted_text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                extracted_text = f"Error processing: {e}"
            
            new_record = ImageRecord(
                filename=filename, 
                extracted_text=extracted_text,
                created_at=creation_time
            )
            db.session.add(new_record)
            added_count += 1
            
    if added_count > 0:
        db.session.commit()
        flash(f'Sync complete! {added_count} new images processed.', 'success')
    else:
        flash('Folders synced. No new images found.', 'info')
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Now you can keep debug=True for development without the spam!
    app.run(debug=True, port=5000)