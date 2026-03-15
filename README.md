# OCR Image Search

A local web app that scans a folder of images and uses OCR to make the text inside them fully searchable.

### Features
*   **Automatic Folder Syncing:** Scans a local folder on your computer and automatically processes new images.
*   **Powerful OCR:** Uses the Tesseract engine to extract text from your images.
*   **Advanced Search:** Search for text with options for broad (substring) or exact whole-word matching.
*   **Sortable Results:** Sort images by file creation date, either latest or oldest first.
*   **Interactive Lightbox:** Click any image to open a full-screen viewer with keyboard navigation (Arrow Keys to cycle, Escape to close).
*   **Frequent Term Analysis:** Automatically calculates and displays the 50 most common terms, sorted by how many unique images they appear in.
*   **Copy to Clipboard:** Instantly copy the full extracted text or the absolute file path of any image.
*   **100% Local & Private:** All your images and their text are processed and stored on your machine. Nothing is ever sent to the cloud.

---

## Setup Instructions

### 1. Install Tesseract OCR Engine
This is the core OCR engine. You must install it on your system before proceeding.

*   **macOS (via Homebrew):**
    ```bash
    brew install tesseract
    ```
*   **Linux (Debian/Ubuntu):**
    ```bash
    sudo apt update && sudo apt install tesseract-ocr
    ```
*   **Windows:**
    Download the official installer from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). During installation, **it is critical that you check the box to add Tesseract to your system's `PATH`**.

### 2. Clone the Repository
Open your terminal, navigate to where you want to store the project, and clone the repository:
```bash
git clone https://github.com/brayvid/ocr-image-search.git
cd ocr-image-search
```

### 3. Create & Activate Python Environment
It is highly recommended to use a virtual environment within the cloned project folder.

```bash
python -m venv .venv
```
Activate the environment:
*   **macOS / Linux:** `source .venv/bin/activate`
*   **Windows (Command Prompt):** `.venv\Scripts\activate`

### 4. Install Python Packages
With your virtual environment active, install all the required Python libraries:
```bash
pip install Flask Flask-SQLAlchemy Pillow pytesseract python-dotenv tqdm
```

### 5. Create Configuration File (`.env`)
This project uses a `.env` file to store your private folder path and secret key. **This is the only file you need to create manually after cloning.**

In the root of the project directory (`ocr-image-search/`), create a new file named `.env`. Copy and paste the following template into it:

```env
# A random key for Flask session security. You can change this to anything.
SECRET_KEY=my_super_secure_random_key_123

# The absolute path to the folder containing your images.
IMAGE_FOLDER=/path/to/your/image/folder

# Apple Silicon (might differ on your machine)
TESSERACT_PATH=/opt/homebrew/bin/tesseract
```
**You must replace `/path/to/your/image/folder` with the absolute path to your image directory.**
*   **Windows:** Right-click the folder, go to "Properties", and copy the "Location" path, then manually add the folder name to the end (e.g., `C:\Users\YourUser\Documents\MyImages`).
*   **macOS / Linux:** Drag and drop the folder directly into your terminal window, and it will paste the full path (e.g., `/Users/youruser/Documents/MyImages`).

**Common Tesseract Locations:**
*   **macOS (Apple Silicon):** `'/opt/homebrew/bin/tesseract'`
*   **macOS (Intel):** `'/usr/local/bin/tesseract'`
*   **Linux:** `'/usr/bin/tesseract'`
*   **Windows:** `'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'`

---

## Usage Instructions

### 1. Initial Sync (For Large Batches)
If you have hundreds or thousands of images to process for the first time, using the web interface might cause your browser to time out. The `bulk_sync.py` script is designed for this.

Make sure your virtual environment is active and run:
```bash
python bulk_sync.py
```
This will scan your `IMAGE_FOLDER`, process all images with a progress bar, and populate your database.

### 2. Running the Web App
To start the main application, run:
```bash
python app.py
```
Your terminal will show that the server is running on `http://127.0.0.1:5000`. Now, open your web browser and go to that address.

### 3. Keeping the Database Updated
After you've added new images to your folder, simply click the green **"Sync New Images"** button in the top-right corner of the web app. It will quickly process only the new files and add them to your database.