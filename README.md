
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

### 1. Prerequisites
*   **Python 3.7+**
*   **Tesseract OCR Engine:** You must install the Tesseract engine on your system.

### 2. Install Tesseract
This is the core OCR engine. Choose the instructions for your operating system.

*   **macOS (via Homebrew):**
    ```bash
    brew install tesseract
    ```

*   **Linux (Debian/Ubuntu):**
    ```bash
    sudo apt update
    sudo apt install tesseract-ocr
    ```

*   **Windows:**
    Download and run the official installer from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). During installation, **it is critical that you check the box to add Tesseract to your system's `PATH`**, otherwise the application will not be able to find it.

### 3. Set Up the Project
First, create a folder for the project and navigate into it. Then, set up a Python virtual environment.

```bash
mkdir ocr-image-search
cd ocr-image-search
python -m venv .venv
```
Next, activate the virtual environment:
*   **macOS / Linux:**
    ```bash
    source .venv/bin/activate
    ```
*   **Windows (Command Prompt):**
    ```bash
    .venv\Scripts\activate
    ```

### 4. Install Python Packages
Install all the necessary Python libraries with this single command:
```bash
pip install Flask Flask-SQLAlchemy Pillow pytesseract python-dotenv tqdm
```

### 5. Create Project Files
Inside your `ocr-image-search` folder, create the following files:
*   `app.py`
*   `bulk_sync.py`
*   `.env`
*   A folder named `templates`, and inside it, a file named `index.html`.

Your final project structure should look like this:
```
ocr-image-search/
│
├── .env
├── app.py
├── bulk_sync.py
├── templates/
│   └── index.html
└── .venv/
```

### 6. Configure the Application
Open the `.env` file you just created and add the following lines. This is where you tell the app where to find your images.

```env
# A random key for Flask session security. You can change this to anything.
SECRET_KEY=my_super_secure_random_key_123

# The absolute path to the folder containing your images.
IMAGE_FOLDER=/path/to/your/image/folder
```

To get the absolute path to your folder:
*   **Windows:** Right-click the folder, go to "Properties", and copy the "Location" path, then add the folder name to the end.
*   **macOS / Linux:** Drag and drop the folder directly into your terminal window and it will paste the full path.

### 7. Troubleshooting: "Tesseract is not in your PATH"
If you run the app and get an error that Tesseract cannot be found, it means Python doesn't know where to look for the Tesseract executable you installed.

**Solution:**
1.  Find where Tesseract was installed on your system.
2.  Open **both `app.py` and `bulk_sync.py`**.
3.  Uncomment (remove the `#`) the line that starts with `pytesseract.pytesseract.tesseract_cmd = ...`
4.  Replace the path with the correct one for your system.

**Common Locations:**
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