# BookScanner API Pipeline

A Python tool for OCR-based book identification using cloud APIs. Built for portfolio demonstration and runs on Android via Pydroid 3.

## Overview

This project demonstrates an end-to-end pipeline for:
1. **Image capture** - Photo of a book cover
2. **OCR (Optical Character Recognition)** - Extract text using Google Vision API
3. **Book identification** - Match extracted text to books using Google Books API
4. **Data persistence** - Store results in JSON format for analysis

## Features

- 📸 Processes book cover images from Android device
- 🔍 Extracts text with confidence metrics
- 📚 Identifies books with metadata (title, authors, ISBN, etc.)
- 💾 Maintains scan history in JSON format
- 🛡️ Error handling for network and API failures
- 📊 Confidence scoring for OCR results

## Requirements

```
requests>=2.28.0
Pillow>=9.0.0
```

Install with:
```bash
pip install -r requirements.txt
```

## Setup

### 1. Get API Keys

**Google Vision API:**
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create a new project
- Enable the Cloud Vision API
- Create an API key (Credentials → Create Credentials → API Key)
- Copy and paste into `main.py` (line ~13)

**Google Books API:**
- Already public! No key needed.

### 2. Configure Image Path

Update `IMAGE_PATH` in `main.py` (line ~17) to your Android photo location:

```python
IMAGE_PATH = "/storage/emulated/0/DCIM/Camera/book_cover.jpg"
```

Common Android paths:
- Camera photos: `/storage/emulated/0/DCIM/Camera/`
- Screenshots: `/storage/emulated/0/Pictures/`
- Custom folder: `/storage/emulated/0/YourFolder/`

### 3. Run on Android (Pydroid 3)

1. Install Pydroid 3 from Google Play Store
2. Copy `main.py` to Pydroid 3
3. Tap play to run
4. Check console for results

## Usage

### Basic Run

```bash
python main.py
```

### Expected Output

```
============================================================
BOOKSCANNER API PIPELINE
Portfolio Project - AI Software Engineering
============================================================

Processing image: /storage/emulated/0/DCIM/Camera/book_cover.jpg

[1/3] Running OCR via Google Vision API...
OCR SUCCESS: 42 words detected
Confidence: 0.956

[2/3] Identifying book via Google Books API...
Search query: 'Python Crash Course'

[3/3] Processing results...

============================================================
BOOK IDENTIFIED
============================================================
Title:    Python Crash Course
Authors:  Eric Matthes
Published: 2015-01-01
Pages:    544
Language: en
ISBN-13:  9781593275099

Description: Learn Python programming from scratch with practical projects...

Link: https://books.google.com/books?id=...

Results saved to: scan_results.json
Total scans in library: 1
```

## Output Format

Results are stored in `scan_results.json`:

```json
{
  "scans": [
    {
      "image_path": "/storage/emulated/0/DCIM/Camera/book_cover.jpg",
      "ocr_success": true,
      "ocr_word_count": 42,
      "ocr_confidence": 0.956,
      "scan_timestamp": "2026-05-16 14:30:45.123456",
      "book_match": {
        "success": true,
        "title": "Python Crash Course",
        "authors": ["Eric Matthes"],
        "isbn": "9781593275099",
        "published": "2015-01-01"
      }
    }
  ],
  "metadata": {
    "created": "2026-05-16 14:30:00.000000",
    "last_updated": "2026-05-16 14:30:45.123456",
    "total_scans": 1
  }
}
```

## API Limits

**Google Vision API:**
- Free tier: 1,000 requests/month
- ~3¢ per request after free tier

**Google Books API:**
- Free tier: 100 requests/second
- No authentication required

## Troubleshooting

### "Image not found" Error
- Check file path is correct
- Verify image exists in file manager
- Use absolute paths

### "No text detected" Error
- Image might be too blurry
- Try a better lit photo
- Ensure book cover is clearly visible

### "No books found" Error
- Book might not be in Google Books database
- Try with author name instead of title
- Check for typos in OCR extraction

### API Key Errors
- Verify API key is correct in `main.py`
- Ensure Vision API is enabled in Google Cloud Console
- Check that billing is enabled (free tier available)

## Project Structure

```
book-scan-concept/
├── main.py              # Main pipeline script
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── scan_results.json   # Generated: scan history
```

## Next Steps

- [ ] Add barcode detection (EAN/ISBN)
- [ ] Implement local SQLite database
- [ ] Add web UI for results visualization
- [ ] Support batch processing multiple images
- [ ] Add Tesseract OCR fallback (offline)
- [ ] Create Android app wrapper

## License

MIT License - feel free to fork and modify!

## Author

Built as a portfolio project demonstrating:
- Cloud API integration (Google Vision, Google Books)
- Python data processing pipelines
- Error handling and logging
- JSON data persistence
- Mobile development (Android/Pydroid 3)
