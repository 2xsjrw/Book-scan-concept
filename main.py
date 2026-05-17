"""
BookScanner API Pipeline - No API Key Version
Uses OCR.space free tier + Open Library API
Built for Pydroid 3 on Android
"""

import requests
import json
import os
from PIL import Image
from datetime import datetime

# ========== CONFIGURATION ==========
# Path to image on Android storage
# Update this after taking a photo
IMAGE_PATH = "/storage/emulated/0/DCIM/Camera/book_cover.jpg"

# Output file for results
OUTPUT_FILE = "scan_results.json"

# OCR.space free API endpoint (no key needed for limited use)
OCR_SPACE_URL = "https://api.ocr.space/parse/image"


# ========== OCR: OCR.SPACE FREE API ==========
def ocr_image(image_path: str) -> dict:
    """
    Send image to OCR.space free API for text detection.
    Returns dict with extracted text and confidence.
    """
    if not os.path.exists(image_path):
        return {
            "success": False,
            "error": f"Image not found: {image_path}",
            "text": None
        }
    
    # Prepare image for upload
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
    except Exception as e:
        return {
            "success": False,
            "error": f"Cannot read image: {str(e)}",
            "text": None
        }
    
    # OCR.space accepts multipart form with image file
    payload = {
        'isOverlayRequired': False,
        'apikey': 'helloworld',  # Free demo key
        'language': 'eng',
        'detectOrientation': True,
        'scale': True,
    }
    
    files = {
        'file': (os.path.basename(image_path), image_data)
    }
    
    try:
        response = requests.post(
            OCR_SPACE_URL,
            data=payload,
            files=files,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        # Check for API errors
        if result.get('IsErroredOnProcessing', False):
            error_msg = result.get('ErrorMessage', ['Unknown error'])
            return {
                "success": False,
                "error": f"OCR.space error: {error_msg}",
                "text": None
            }
        
        # Extract text from results
        parsed_results = result.get('ParsedResults', [])
        if not parsed_results:
            return {
                "success": False,
                "error": "No text detected in image",
                "text": None
            }
        
        # Combine all parsed text
        full_text = ""
        total_confidence = 0
        for parsed in parsed_results:
            text_overlay = parsed.get('ParsedText', '')
            full_text += text_overlay + "\n"
            # OCR.space doesn't give per-word confidence easily, 
            # so we estimate from overall result
            total_confidence += parsed.get('FileParseExitCode', 1)
        
        # Clean up the text
        full_text = full_text.strip()
        
        if not full_text:
            return {
                "success": False,
                "error": "Image parsed but no readable text found",
                "text": None
            }
        
        return {
            "success": True,
            "text": full_text,
            "word_count": len(full_text.split()),
            "avg_confidence": 0.85,  # OCR.space free tier doesn't expose detailed confidence
            "api_response_size": len(str(result))
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"OCR API request failed: {str(e)}",
            "text": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "text": None
        }


# ========== BOOK IDENTIFICATION: OPEN LIBRARY API ==========
def identify_book(query: str, max_results: int = 3) -> dict:
    """
    Search Open Library API for a given text query.
    Returns structured book data with best match.
    """
    # Open Library search endpoint
    url = "https://openlibrary.org/search.json"
    params = {
        "q": query,
        "limit": max_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        total_items = data.get('numFound', 0)
        
        if total_items == 0 or 'docs' not in data or not data['docs']:
            return {
                "success": False,
                "error": "No books found matching query",
                "query": query,
                "total_results": 0,
                "matches": []
            }
        
        # Parse top matches
        matches = []
        for doc in data['docs'][:max_results]:
            # Extract ISBN for cover image link
            isbn_list = doc.get('isbn', [])
            isbn_13 = next((i for i in isbn_list if len(i) == 13), isbn_list[0] if isbn_list else None)
            
            match = {
                "title": doc.get('title', 'Unknown'),
                "authors": doc.get('author_name', ['Unknown']),
                "publisher": doc.get('publisher', ['Unknown'])[0] if doc.get('publisher') else 'Unknown',
                "published_date": str(doc.get('first_publish_year', 'Unknown')),
                "description": f"Subject: {', '.join(doc.get('subject', ['No description'])[:3])}",
                "page_count": doc.get('number_of_pages_median', 0),
                "categories": doc.get('subject', [])[:3],
                "language": doc.get('language', ['unknown'])[0] if doc.get('language') else 'unknown',
                "info_link": f"https://openlibrary.org{doc.get('key', '')}" if doc.get('key') else '',
                "isbn_13": isbn_13,
                "match_score": doc.get('ratings_count', 0)
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
            "error": f"Open Library API request failed: {str(e)}",
            "query": query,
            "total_results": 0,
            "matches": []
        }


# ========== DATA PERSISTENCE ==========
def save_results(scan_data: dict, output_file: str = OUTPUT_FILE) -> bool:
    """
    Append scan results to JSON file for tracking and analysis.
    """
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                library = json.load(f)
        except json.JSONDecodeError:
            library = {"scans": [], "metadata": {"created": str(datetime.now())}}
    else:
        library = {"scans": [], "metadata": {"created": str(datetime.now())}}
    
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
    print("BOOKSCANNER API PIPELINE - NO API KEY VERSION")
    print("Uses OCR.space + Open Library API")
    print("=" * 60)
    
    if not os.path.exists(IMAGE_PATH):
        print(f"\nERROR: Image not found at {IMAGE_PATH}")
        print("Update IMAGE_PATH to your photo location.")
        print("Common paths:")
        print("  /storage/emulated/0/DCIM/Camera/")
        print("  /storage/emulated/0/Pictures/")
        print("\nTake a photo of a book cover first!")
        return
    
    print(f"\nProcessing image: {IMAGE_PATH}")
    
    # Step 1: OCR
    print("\n[1/3] Running OCR via OCR.space free API...")
    ocr_result = ocr_image(IMAGE_PATH)
    
    if not ocr_result["success"]:
        print(f"OCR FAILED: {ocr_result['error']}")
        save_results({
            "image_path": IMAGE_PATH,
            "ocr_success": False,
            "ocr_error": ocr_result["error"],
            "book_match": None
        })
        return
    
    extracted_text = ocr_result["text"]
    print(f"OCR SUCCESS: {ocr_result['word_count']} words detected")
    print(f"\nExtracted text (first 200 chars):")
    print(f"  {extracted_text[:200]}...")
    
    # Step 2: Identify book
    print("\n[2/3] Identifying book via Open Library API...")
    
    # Use first non-empty line as title guess
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
        print(f"Title:     {top_match['title']}")
        print(f"Authors:   {', '.join(top_match['authors'])}")
        print(f"Published: {top_match['published_date']}")
        print(f"Pages:     {top_match['page_count']}")
        print(f"Language:  {top_match['language']}")
        print(f"ISBN-13:   {top_match['isbn_13'] or 'N/A'}")
        print(f"\nCategories: {', '.join(top_match['categories'])}")
        print(f"\nLink: {top_match['info_link']}")
        
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
        print("This book may not be in Open Library's database.")
        print("Try a clearer photo or a more well-known book.")
        
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
        try:
            with open(OUTPUT_FILE, 'r') as f:
                total = len(json.load(f)['scans'])
            print(f"Total scans in library: {total}")
        except:
            pass
    else:
        print("\nWarning: Could not save results")
    
    print(f"\n{'='*60}")
    print("Scan complete.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

