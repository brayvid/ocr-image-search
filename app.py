import os
import re
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
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

app = Flask(__name__)

# Pull the secret key from the .env file (with a fallback just in case)
app.secret_key = os.getenv("SECRET_KEY", "fallback_default_key")

# Pull the folder path from the .env file
SCREENSHOTS_FOLDER = os.getenv("SCREENSHOTS_FOLDER")

# === ISOLATE DATABASE OUTSIDE OF GOOGLE DRIVE ===
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'images.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class ImageRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(250), nullable=False, unique=True)
    extracted_text = db.Column(db.Text, nullable=True)

with app.app_context():
    db.create_all()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.template_filter('highlight')
def highlight_filter(text, query):
    if not query or not text:
        return text
    escaped_query = re.escape(query)
    pattern = re.compile(f"({escaped_query})", re.IGNORECASE)
    highlighted = pattern.sub(r'<mark class="bg-warning px-1 rounded">\1</mark>', text)
    return Markup(highlighted)

STOP_WORDS = {
    "the", "and", "to", "of", "in", "is", "it", "you", "that", "he", "was", "for", 
    "on", "are", "with", "as", "we", "his", "they", "be", "at", "one", "have", "this", 
    "from", "or", "had", "by", "not", "but", "some", "what", "there", "out", "all", 
    "your", "can", "has", "any", "which", "their", "were", "when", "will", "how", "pm", "am"
}

def get_most_frequent_terms(limit=12):
    all_texts = db.session.query(ImageRecord.extracted_text).filter(ImageRecord.extracted_text.isnot(None)).all()
    combined_text = " ".join([text[0] for text in all_texts])
    words = re.findall(r'\b[a-z]{3,}\b', combined_text.lower())
    meaningful_words = [w for w in words if w not in STOP_WORDS]
    word_counts = Counter(meaningful_words)
    return word_counts.most_common(limit)

# === READ-ONLY IMAGE SERVING ===
@app.route('/images/<path:filename>')
def serve_image(filename):
    if not SCREENSHOTS_FOLDER:
        return "SCREENSHOTS_FOLDER not set in .env", 500
    return send_from_directory(SCREENSHOTS_FOLDER, filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    search_query = request.args.get('q', '').strip()
    top_terms = get_most_frequent_terms(limit=12)

    if search_query:
        records = ImageRecord.query.filter(ImageRecord.extracted_text.contains(search_query)).order_by(ImageRecord.id.desc()).all()
    else:
        records = ImageRecord.query.order_by(ImageRecord.id.desc()).all()
        
    return render_template('index.html', records=records, search_query=search_query, top_terms=top_terms)

# === READ-ONLY SYNC LOGIC ===
@app.route('/sync', methods=['POST'])
def sync_folder():
    if not SCREENSHOTS_FOLDER or not os.path.exists(SCREENSHOTS_FOLDER):
        flash(f"Directory not found. Please check SCREENSHOTS_FOLDER in your .env file.", "danger")
        return redirect(url_for('index'))
        
    added_count = 0
    existing_records = {record.filename for record in ImageRecord.query.all()}
    
    for filename in os.listdir(SCREENSHOTS_FOLDER):
        if filename.startswith('.') or not allowed_file(filename):
            continue
            
        if filename not in existing_records:
            filepath = os.path.join(SCREENSHOTS_FOLDER, filename)
            
            try:
                img = Image.open(filepath)
                extracted_text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                extracted_text = f"Error processing: {e}"
            
            new_record = ImageRecord(filename=filename, extracted_text=extracted_text)
            db.session.add(new_record)
            added_count += 1
            
    if added_count > 0:
        db.session.commit()
        flash(f'Sync complete! {added_count} new screenshots processed.', 'success')
    else:
        flash('Folders synced. No new screenshots found.', 'info')
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)