"""
BookScanner API Pipeline - Full Version
Modes:
  1. Cover scan + online lookup (original)
  2. Page-by-page manual scanner
  3. Batch folder scanner (multiple pages)
Uses OCR.space + Open Library API + Android TTS
Built for Pydroid 3 on Android
"""

import requests
import json
import os
import subprocess
import glob
from PIL import Image
from datetime import datetime

# ========== CONFIGURATION ==========
# Default paths - update these
COVER_IMAGE = "/storage/emulated/0/DCIM/Camera/YOUR-PHOTO-NAME.jpg"
PAGES_FOLDER = "/storage/emulated/0/DCIM/Camera/book_pages/"
OUTPUT_FILE = "scan_results.json"
MANUAL_BOOK_FILE = "manual_book.txt"
OCR_SPACE_URL = "https://api.ocr.space/parse/image"


# ========== TTS: ANDROID TEXT TO SPEECH ==========
def speak_text(text: str, voice_type: str = "default") -> bool:
    """Use Android's native TTS via termux-tts-speak or am start."""
    max_chars = 3000
    if len(text) > max_chars:
        text = text[:max_chars] + "... text truncated for speech"
    
    clean_text = text.replace('"', '').replace("'", "").replace("\n", " ")
    
    # Try termux-tts-speak first
    try:
        voice_param = ""
        if voice_type == "male":
            voice_param = "-e VOICE 'male'"
        elif voice_type == "female":
            voice_param = "-e VOICE 'female'"
        
        cmd = f'termux-tts-speak {voice_param} "{clean_text}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
        if result.returncode == 0:
            return True
    except Exception:
        pass
    
    # Fallback: Android share intent
    try:
        cmd = f'am start -a android.intent.action.SEND -t text/plain -e android.intent.extra.TEXT "{clean_text[:500]}"'
        subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
        print("\n[TTS: Opened Android share dialog - select 'Read aloud']")
        return True
    except Exception as e:
        print(f"\n[TTS Error: {e}]")
        print("[Install Termux + termux-api for full TTS support]")
        return False


# ========== OCR: OCR.SPACE FREE API ==========
def ocr_image(image_path: str) -> dict:
    """Send image to OCR.space free API for text detection."""
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image not found: {image_path}", "text": None}
    
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
    except Exception as e:
        return {"success": False, "error": f"Cannot read image: {str(e)}", "text": None}
    
    payload = {
        'isOverlayRequired': False,
        'apikey': 'helloworld',
        'language': 'eng',
        'detectOrientation': True,
        'scale': True,
    }
    files = {'file': (os.path.basename(image_path), image_data)}
    
    try:
        response = requests.post(OCR_SPACE_URL, data=payload, files=files, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get('IsErroredOnProcessing', False):
            error_msg = result.get('ErrorMessage', ['Unknown error'])
            return {"success": False, "error": f"OCR.space error: {error_msg}", "text": None}
        
        parsed_results = result.get('ParsedResults', [])
        if not parsed_results:
            return {"success": False, "error": "No text detected in image", "text": None}
        
        full_text = ""
        for parsed in parsed_results:
            full_text += parsed.get('ParsedText', '') + "\n"
        
        full_text = full_text.strip()
        if not full_text:
            return {"success": False, "error": "Image parsed but no readable text found", "text": None}
        
        return {
            "success": True,
            "text": full_text,
            "word_count": len(full_text.split()),
            "avg_confidence": 0.85,
            "api_response_size": len(str(result))
        }
        
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"OCR API request failed: {str(e)}", "text": None}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}", "text": None}


# ========== BOOK IDENTIFICATION: OPEN LIBRARY API ==========
def identify_book(query: str, max_results: int = 3) -> dict:
    """Search Open Library API for a given text query."""
    url = "https://openlibrary.org/search.json"
    params = {"q": query, "limit": max_results}
    
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
        
        matches = []
        for doc in data['docs'][:max_results]:
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
    """Append scan results to JSON file."""
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


def save_manual_text(text: str, book_title: str = "Unknown Book", append: bool = True) -> bool:
    """Save manually scanned text to a book file."""
    mode = 'a' if append else 'w'
    header = f"\n\n{'='*60}\n" if append else f"BOOK: {book_title}\n{'='*60}\n"
    
    try:
        with open(MANUAL_BOOK_FILE, mode, encoding='utf-8') as f:
            if append:
                f.write(header)
            f.write(text)
            f.write("\n")
        return True
    except Exception as e:
        print(f"Error saving manual text: {e}")
        return False


# ========== MODE 1: COVER SCAN + ONLINE LOOKUP ==========
def mode_cover_scan():
    """Original mode: scan cover, look up online, TTS results."""
    print("\n" + "="*60)
    print("MODE 1: COVER SCAN + ONLINE LOOKUP")
    print("="*60)
    
    if not os.path.exists(COVER_IMAGE):
        print(f"\nERROR: Cover image not found: {COVER_IMAGE}")
        print("Update COVER_IMAGE path or take a photo first.")
        return
    
    print(f"\nProcessing cover: {COVER_IMAGE}")
    
    # OCR
    print("\n[1/3] Running OCR...")
    ocr_result = ocr_image(COVER_IMAGE)
    
    if not ocr_result["success"]:
        print(f"OCR FAILED: {ocr_result['error']}")
        save_results({
            "mode": "cover_scan",
            "image_path": COVER_IMAGE,
            "ocr_success": False,
            "ocr_error": ocr_result["error"],
            "book_match": None
        })
        return
    
    extracted_text = ocr_result["text"]
    print(f"OCR SUCCESS: {ocr_result['word_count']} words")
    print(f"Text preview: {extracted_text[:150]}...")
    
    # Book lookup
    print("\n[2/3] Looking up book online...")
    lines = [l.strip() for l in extracted_text.split('\n') if l.strip()]
    search_query = lines[0] if lines else extracted_text[:50]
    
    book_result = identify_book(search_query)
    
    # Display and prepare TTS
    text_to_speak = ""
    
    if book_result["success"]:
        top_match = book_result["matches"][0]
        print(f"\n{'='*60}")
        print("BOOK FOUND!")
        print(f"{'='*60}")
        print(f"Title:     {top_match['title']}")
        print(f"Authors:   {', '.join(top_match['authors'])}")
        print(f"Published: {top_match['published_date']}")
        print(f"Link: {top_match['info_link']}")
        
        text_to_speak = (
            f"Book found: {top_match['title']} by {', '.join(top_match['authors'])}. "
            f"Published {top_match['published_date']}. "
            f"{top_match['description'][:300]}"
        )
        
        scan_record = {
            "mode": "cover_scan",
            "image_path": COVER_IMAGE,
            "ocr_success": True,
            "book_found": True,
            "title": top_match["title"],
            "authors": top_match["authors"],
            "isbn": top_match["isbn_13"]
        }
    else:
        print(f"\nBook not found online.")
        print("You can still read the extracted text.")
        
        text_to_speak = f"Book not found. Extracted text reads: {extracted_text[:500]}"
        
        scan_record = {
            "mode": "cover_scan",
            "image_path": COVER_IMAGE,
            "ocr_success": True,
            "book_found": False,
            "extracted_text": extracted_text[:200]
        }
    
    # Save results
    save_results(scan_record)
    print(f"\nResults saved to: {OUTPUT_FILE}")
    
    # TTS
    print("\n[3/3] Text to Speech...")
    voice = select_voice()
    if voice:
        speak_text(text_to_speak, voice)


# ========== MODE 2: PAGE-BY-PAGE MANUAL SCANNER ==========
def mode_page_by_page():
    """Scan pages one at a time, save and read each."""
    print("\n" + "="*60)
    print("MODE 2: PAGE-BY-PAGE MANUAL SCANNER")
    print("="*60)
    print("Take photos of each page and save them.")
    print("Enter the full path for each page.")
    print("Type 'done' when finished.")
    print("-"*60)
    
    book_title = input("Enter book title (for saving): ").strip() or "Unknown Book"
    page_num = 1
    total_words = 0
    
    while True:
        print(f"\n--- Page {page_num} ---")
        page_path = input(f"Enter image path (or 'done'): ").strip()
        
        if page_path.lower() == 'done':
            break
        
        if not os.path.exists(page_path):
            print(f"File not found: {page_path}")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry != 'y':
                break
            continue
        
        # OCR this page
        print(f"Scanning page {page_num}...")
        ocr_result = ocr_image(page_path)
        
        if not ocr_result["success"]:
            print(f"OCR failed: {ocr_result['error']}")
            skip = input("Skip this page? (y/n): ").strip().lower()
            if skip == 'y':
                page_num += 1
                continue
            else:
                break
        
        page_text = ocr_result["text"]
        word_count = ocr_result["word_count"]
        total_words += word_count
        
        print(f"Page {page_num}: {word_count} words extracted")
        print(f"Preview: {page_text[:100]}...")
        
        # Save to manual book file
        page_header = f"\n--- PAGE {page_num} ---\n"
        save_manual_text(page_header + page_text, book_title, append=(page_num > 1))
        
        # TTS option
        read_now = input("Read this page now? (y/n): ").strip().lower()
        if read_now == 'y':
            voice = select_voice()
            if voice:
                speak_text(page_text, voice)
        
        page_num += 1
    
    print(f"\n{'='*60}")
    print(f"Finished scanning.")
    print(f"Total pages: {page_num - 1}")
    print(f"Total words: {total_words}")
    print(f"Saved to: {MANUAL_BOOK_FILE}")
    print(f"{'='*60}")
    
    # Final TTS option
    read_all = input("Read entire book now? (y/n): ").strip().lower()
    if read_all == 'y':
        try:
            with open(MANUAL_BOOK_FILE, 'r', encoding='utf-8') as f:
                full_text = f.read()
            voice = select_voice()
            if voice:
                speak_text(full_text, voice)
        except Exception as e:
            print(f"Error reading file: {e}")


# ========== MODE 3: BATCH FOLDER SCANNER ==========
def mode_batch_folder():
    """Process all images in a folder at once."""
    print("\n" + "="*60)
    print("MODE 3: BATCH FOLDER SCANNER")
    print("="*60)
    
    folder = input(f"Enter folder path [{PAGES_FOLDER}]: ").strip() or PAGES_FOLDER
    
    if not os.path.exists(folder):
        print(f"Folder not found: {folder}")
        print("Create the folder and put page images in it.")
        print("Name files in order: page01.jpg, page02.jpg, etc.")
        return
    
    # Find all image files
    patterns = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    image_files = []
    for pattern in patterns:
        image_files.extend(glob.glob(os.path.join(folder, pattern)))
    
    # Sort by filename
    image_files.sort()
    
    if not image_files:
        print(f"No images found in: {folder}")
        print("Supported formats: jpg, jpeg, png, bmp")
        return
    
    print(f"\nFound {len(image_files)} images:")
    for i, img in enumerate(image_files[:5], 1):
        print(f"  {i}. {os.path.basename(img)}")
    if len(image_files) > 5:
        print(f"  ... and {len(image_files) - 5} more")
    
    book_title = input("Enter book title (for saving): ").strip() or "Unknown Book"
    confirm = input(f"\nProcess all {len(image_files)} images? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Batch scan cancelled.")
        return
    
    # Process all images
    print(f"\nProcessing {len(image_files)} pages...")
    total_words = 0
    failed_pages = []
    
    for i, image_path in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] {os.path.basename(image_path)}...")
        
        ocr_result = ocr_image(image_path)
        
        if not ocr_result["success"]:
            print(f"  FAILED: {ocr_result['error']}")
            failed_pages.append((i, os.path.basename(image_path), ocr_result["error"]))
            continue
        
        page_text = ocr_result["text"]
        word_count = ocr_result["word_count"]
        total_words += word_count
        
        print(f"  SUCCESS: {word_count} words")
        
        # Save to file
        page_header = f"\n--- PAGE {i} ---\n" if i > 1 else f"BOOK: {book_title}\n{'='*60}\n--- PAGE {i} ---\n"
        save_manual_text(page_header + page_text, book_title, append=(i > 1))
    
    # Summary
    print(f"\n{'='*60}")
    print("BATCH SCAN COMPLETE")
    print(f"{'='*60}")
    print(f"Total images: {len(image_files)}")
    print(f"Successful: {len(image_files) - len(failed_pages)}")
    print(f"Failed: {len(failed_pages)}")
    print(f"Total words: {total_words}")
    print(f"Saved to: {MANUAL_BOOK_FILE}")
    
    if failed_pages:
        print(f"\nFailed pages:")
        for page_num, filename, error in failed_pages:
            print(f"  Page {page_num}: {filename} - {error}")
    
    # TTS option
    print(f"\n{'='*60}")
    read_all = input("Read entire scanned book now? (y/n): ").strip().lower()
    if read_all == 'y':
        try:
            with open(MANUAL_BOOK_FILE, 'r', encoding='utf-8') as f:
                full_text = f.read()
            voice = select_voice()
            if voice:
                speak_text(full_text, voice)
        except Exception as e:
            print(f"Error reading file: {e}")
    
    # Save JSON record
    save_results({
        "mode": "batch_scan",
        "folder": folder,
        "total_images": len(image_files),
        "successful": len(image_files) - len(failed_pages),
        "failed": len(failed_pages),
        "total_words": total_words,
        "book_title": book_title
    })


# ========== VOICE SELECTION ==========
def select_voice() -> str:
    """Let user select TTS voice."""
    print("\nVoice options:")
    print("1. Default")
    print("2. Male")
    print("3. Female")
    print("4. Skip TTS")
    
    try:
        choice = input("Select (1-4): ").strip()
    except EOFError:
        return "default"
    
    voice_map = {
        "1": "default",
        "2": "male",
        "3": "female",
        "4": None
    }
    
    return voice_map.get(choice, "default")


# ========== MAIN MENU ==========
def main():
    print("=" * 60)
    print("BOOKSCANNER - FULL VERSION")
    print("=" * 60)
    print("Select mode:")
    print("1. Cover scan + online lookup (find book online)")
    print("2. Page-by-page scanner (scan each page manually)")
    print("3. Batch folder scanner (process all images in folder)")
    print("4. Exit")
    print("-" * 60)
    
    try:
        choice = input("Enter mode (1-4): ").strip()
    except EOFError:
        print("Input error. Exiting.")
        return
    
    if choice == "1":
        mode_cover_scan()
    elif choice == "2":
        mode_page_by_page()
    elif choice == "3":
        mode_batch_folder()
    elif choice == "4":
        print("Goodbye.")
    else:
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()


