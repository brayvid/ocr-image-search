import os
import re
import logging
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
import pytesseract
from markupsafe import Markup, escape
from dotenv import load_dotenv

load_dotenv()

tess_path = os.getenv("TESSERACT_PATH")
if tess_path:
    pytesseract.pytesseract.tesseract_cmd = tess_path

app = Flask(__name__)

# Silence image request logs
class NoImagesFilter(logging.Filter):
    def filter(self, record):
        return '/images/' not in record.getMessage()

log = logging.getLogger('werkzeug')
log.addFilter(NoImagesFilter())

app.secret_key = os.getenv("SECRET_KEY", "fallback_default_key")
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'images.db')
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
    if not query or not text: return text
    # First, escape the text to prevent OCR junk from breaking HTML
    safe_text = str(escape(text))
    escaped_query = re.escape(query)
    pattern = re.compile(rf'(\b{escaped_query}\b)', re.IGNORECASE) if exact else re.compile(f"({escaped_query})", re.IGNORECASE)
    return Markup(pattern.sub(r'<mark class="bg-warning px-1 rounded">\1</mark>', safe_text))

STOP_WORDS = {"the", "and", "to", "of", "in", "is", "it", "you", "that", "he", "was", "for", "on", "are", "with", "as", "we", "his", "they", "be", "at", "one", "have", "this", "from", "or", "had", "by", "not", "but", "some", "what", "there", "out", "all", "your", "can", "has", "any", "which", "their", "were", "when", "will", "how", "pm", "am", "com", "www", "http", "https", "net", "org", "get", "got", "new"}

def get_most_frequent_terms(limit=20):
    all_texts = db.session.query(ImageRecord.extracted_text).filter(ImageRecord.extracted_text.isnot(None)).all()
    document_word_counts = Counter()
    for text in all_texts:
        words_in_doc = re.findall(r'\b[a-z]{3,}\b', text[0].lower())
        unique_words_in_doc = set([w for w in words_in_doc if w not in STOP_WORDS])
        document_word_counts.update(unique_words_in_doc)
    return document_word_counts.most_common(limit)

# Logic to generate page numbers with ellipses
def get_pagination_range(current_page, total_pages):
    if total_pages <= 1: return []
    pages = set([1, 2, 3, total_pages, total_pages-1, total_pages-2, current_page, current_page-1, current_page+1])
    sorted_pages = sorted([p for p in pages if 1 <= p <= total_pages])
    res = []
    prev = 0
    for p in sorted_pages:
        if prev and p - prev > 1: res.append(None)
        res.append(p)
        prev = p
    return res

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    query_text = request.args.get('q', '').strip()
    sort_order = request.args.get('sort', 'desc')
    exact_match = request.args.get('exact') == 'true'
    page = request.args.get('page', 1, type=int)
    
    stmt = ImageRecord.query
    if query_text:
        if exact_match:
            # For exact match, we use a regex search in SQLite or filter after fetching
            # For simplicity and reliability with 3000 images, we fetch IDs and filter
            all_data = stmt.all()
            pattern = re.compile(rf'\b{re.escape(query_text)}\b', re.IGNORECASE)
            valid_ids = [r.id for r in all_data if r.extracted_text and pattern.search(r.extracted_text)]
            stmt = ImageRecord.query.filter(ImageRecord.id.in_(valid_ids))
        else:
            stmt = stmt.filter(ImageRecord.extracted_text.contains(query_text))

    if sort_order == 'asc': stmt = stmt.order_by(ImageRecord.created_at.asc())
    else: stmt = stmt.order_by(ImageRecord.created_at.desc())

    # USE BUILT-IN PAGINATE
    pagination = stmt.paginate(page=page, per_page=50, error_out=False)
    
    return render_template('index.html', 
                           pagination=pagination,
                           records=pagination.items, 
                           search_query=query_text, 
                           top_terms=get_most_frequent_terms(20), 
                           sort_order=sort_order, 
                           exact_match=exact_match,
                           folder_path=IMAGE_FOLDER,
                           pages_to_show=get_pagination_range(page, pagination.pages))

@app.route('/sync', methods=['POST'])
def sync_folder():
    existing = {r.filename for r in db.session.query(ImageRecord.filename).all()}
    for filename in os.listdir(IMAGE_FOLDER):
        if filename.startswith('.') or not allowed_file(filename): continue
        if filename not in existing:
            path = os.path.join(IMAGE_FOLDER, filename)
            stat = os.stat(path)
            ctime = getattr(stat, 'st_birthtime', stat.st_mtime)
            try:
                text = pytesseract.image_to_string(Image.open(path)).strip()
                db.session.add(ImageRecord(filename=filename, extracted_text=text, created_at=ctime))
            except: continue
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)