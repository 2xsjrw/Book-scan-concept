"""
BookScanner API Pipeline
A Python tool for OCR-based book identification using cloud APIs.
Built for portfolio demonstration - runs on Android via Pydroid 3.

Author: [Your Name]
GitHub: [Your GitHub URL]
"""

import requests
import json
import os
import base64
from PIL import Image
from datetime import datetime

# ========== CONFIGURATION ==========
# Get free API key from Google Cloud Console (Cloud Vision API)
GOOGLE_VISION_API_KEY = "YOUR_API_KEY_HERE"

# Path to image on Android storage
# Update this after taking a photo - check your file manager
IMAGE_PATH = "/storage/emulated/0/DCIM/Camera/book_cover.jpg"

# Output file for results
OUTPUT_FILE = "scan_results.json"


# ========== OCR: GOOGLE VISION API ==========
def extract_text_from_image(image_path: str, api_key: str) -> dict:
    """
    Send image to Google Vision API for text detection.
    Returns dict with extracted text and confidence metrics.
    """
    if not os.path.exists(image_path):
        return {
            "success": False,
            "error": f"Image not found: {image_path}",
            "text": None
        }
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_content = f.read()
    
    encoded_image = base64.b64encode(image_content).decode('utf-8')
    
    # API request payload
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {
        "requests": [{
            "image": {"content": encoded_image},
            "features": [{
                "type": "TEXT_DETECTION",
                "maxResults": 1
            }]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Parse response
        if 'responses' not in result or not result['responses']:
            return {
                "success": False,
                "error": "Empty response from Vision API",
                "text": None
            }
        
        text_annotation = result['responses'][0].get('fullTextAnnotation')
        if not text_annotation:
            return {
                "success": False,
                "error": "No text detected in image",
                "text": None
            }
        
        extracted_text = text_annotation['text']
        
        # Calculate approximate confidence from individual words
        words = []
        for page in text_annotation.get('pages', []):
            for block in page.get('blocks', []):
                for para in block.get('paragraphs', []):
                    for word in para.get('words', []):
                        word_text = ''.join([s['text'] for s in word.get('symbols', [])])
                        confidence = word.get('confidence', 0.0)
                        words.append({"text": word_text, "confidence": confidence})
        
        avg_confidence = sum(w['confidence'] for w in words) / len(words) if words else 0.0
        
        return {
            "success": True,
            "text": extracted_text,
            "word_count": len(extracted_text.split()),
            "avg_confidence": round(avg_confidence, 3),
            "api_response_size": len(str(result))
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "text": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "text": None
        }


# ========== BOOK IDENTIFICATION: GOOGLE BOOKS API ==========
def identify_book(query: str, max_results: int = 3) -> dict:
    """
    Search Google Books API for a given text query.
    Returns structured book data with best match.
    """
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "maxResults": max_results,
        "printType": "books",
        "projection": "full"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        total_items = data.get('totalItems', 0)
        
        if total_items == 0 or 'items' not in data:
            return {
                "success": False,
                "error": "No books found matching query",
                "query": query,
                "total_results": 0,
                "matches": []
            }
        
        # Parse top matches
        matches = []
        for item in data['items'][:max_results]:
            info = item.get('volumeInfo', {})
            match = {
                "title": info.get('title', 'Unknown'),
                "authors": info.get('authors', ['Unknown']),
                "publisher": info.get('publisher', 'Unknown'),
                "published_date": info.get('publishedDate', 'Unknown'),
                "description": info.get('description', 'No description available'),
                "page_count": info.get('pageCount', 0),
                "categories": info.get('categories', []),
                "language": info.get('language', 'unknown'),
                "info_link": info.get('infoLink', ''),
                "preview_link": info.get('previewLink', ''),
                "isbn_13": next((id['identifier'] for id in info.get('industryIdentifiers', []) 
                               if id['type'] == 'ISBN_13'), None),
                "match_score": item.get('score', 0)
            }
            matches.append(match)
        
        return {
            "success": True,
            "query": query,
            "total_results": total_items,
            "matches_returned": len(matches),
            "matches": matches
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Books API request failed: {str(e)}",
            "query": query,
            "total_results": 0,
            "matches": []
        }


# ========== DATA PERSISTENCE ==========
def save_results(scan_data: dict, output_file: str = OUTPUT_FILE) -> bool:
    """
    Append scan results to JSON file for tracking and analysis.
    """
    # Load existing data or create new structure
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                library = json.load(f)
        except json.JSONDecodeError:
            library = {"scans": [], "metadata": {"created": str(datetime.now())}}
    else:
        library = {"scans": [], "metadata": {"created": str(datetime.now())}}
    
    # Add timestamp and append
    scan_data["scan_timestamp"] = str(datetime.now())
    library["scans"].append(scan_data)
    library["metadata"]["last_updated"] = str(datetime.now())
    library["metadata"]["total_scans"] = len(library["scans"])
    
    try:
        with open(output_file, 'w') as f:
            json.dump(library, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving results: {e}")
        return False


# ========== MAIN PIPELINE ==========
def main():
    print("=" * 60)
    print("BOOKSCANNER API PIPELINE")
    print("Portfolio Project - AI Software Engineering")
    print("=" * 60)
    
    # Validate configuration
    if GOOGLE_VISION_API_KEY == "YOUR_API_KEY_HERE":
        print("\nERROR: Please set your Google Vision API key.")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create project, enable Cloud Vision API")
        print("3. Create API key, paste above")
        return
    
    if not os.path.exists(IMAGE_PATH):
        print(f"\nERROR: Image not found at {IMAGE_PATH}")
        print("Update IMAGE_PATH to your photo location.")
        print("Common paths:")
        print("  /storage/emulated/0/DCIM/Camera/")
        print("  /storage/emulated/0/Pictures/")
        return
    
    print(f"\nProcessing image: {IMAGE_PATH}")
    
    # Step 1: OCR
    print("\n[1/3] Running OCR via Google Vision API...")
    ocr_result = extract_text_from_image(IMAGE_PATH, GOOGLE_VISION_API_KEY)
    
    if not ocr_result["success"]:
        print(f"OCR FAILED: {ocr_result['error']}")
        # Save failure for analysis
        save_results({
            "image_path": IMAGE_PATH,
            "ocr_success": False,
            "ocr_error": ocr_result["error"],
            "book_match": None
        })
        return
    
    extracted_text = ocr_result["text"]
    print(f"OCR SUCCESS: {ocr_result['word_count']} words detected")
    print(f"Confidence: {ocr_result['avg_confidence']}")
    print(f"\nExtracted text (first 150 chars):")
    print(f"  {extracted_text[:150]}...")
    
    # Step 2: Identify book
    print("\n[2/3] Identifying book via Google Books API...")
    
    # Use first line as title guess, or first 50 chars
    lines = [l.strip() for l in extracted_text.split('\n') if l.strip()]
    search_query = lines[0] if lines else extracted_text[:50]
    print(f"Search query: '{search_query}'")
    
    book_result = identify_book(search_query)
    
    # Step 3: Save and display results
    print("\n[3/3] Processing results...")
    
    if book_result["success"]:
        top_match = book_result["matches"][0]
        print(f"\n{'='*60}")
        print("BOOK IDENTIFIED")
        print(f"{'='*60}")
        print(f"Title:    {top_match['title']}")
        print(f"Authors:  {', '.join(top_match['authors'])}")
        print(f"Published: {top_match['published_date']}")
        print(f"Pages:    {top_match['page_count']}")
        print(f"Language: {top_match['language']}")
        print(f"ISBN-13:  {top_match['isbn_13'] or 'N/A'}")
        print(f"\nDescription: {top_match['description'][:200]}...")
        print(f"\nLink: {top_match['info_link']}")
        
        # Save success
        scan_record = {
            "image_path": IMAGE_PATH,
            "ocr_success": True,
            "ocr_word_count": ocr_result["word_count"],
            "ocr_confidence": ocr_result["avg_confidence"],
            "book_match": {
                "success": True,
                "title": top_match["title"],
                "authors": top_match["authors"],
                "isbn": top_match["isbn_13"],
                "published": top_match["published_date"]
            }
        }
    else:
        print(f"\nBOOK NOT FOUND: {book_result['error']}")
        print("This book may not be in Google's database.")
        
        # Save failure
        scan_record = {
            "image_path": IMAGE_PATH,
            "ocr_success": True,
            "ocr_word_count": ocr_result["word_count"],
            "ocr_confidence": ocr_result["avg_confidence"],
            "book_match": {
                "success": False,
                "error": book_result["error"],
                "query": search_query
            }
        }
    
    # Persist results
    if save_results(scan_record):
        print(f"\nResults saved to: {OUTPUT_FILE}")
        print(f"Total scans in library: {len(json.load(open(OUTPUT_FILE))['scans'])}")
    else:
        print("\nWarning: Could not save results")
    
    print(f"\n{'='*60}")
    print("Scan complete.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
