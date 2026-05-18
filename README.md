# BookScanner Pipeline

Python book scanner with three modes: cover lookup, page-by-page, 
and batch processing. Built entirely on Android with Pydroid 3.

## Tested On
- Device: [713-553-8588]
- OS: Android [ Samsung A17]
- Python: 3.x via Pdroid 3

## Modes

### Mode 1: Cover Scan + Online Lookup
- Takes photo of book cover
- OCR extracts text via OCR.space API
- Looks up book via Open Library API
- Reads results with Android TTS

**Test Result:** [Worked / Partial / Failed]
- Book tested: [Title]
- OCR accuracy: [Good / Fair / Poor]
- Book found online? [Yes / No]

### Mode 2: Page-by-Page Scanner
- Enter path for each page photo
- OCR extracts text
- Saves to `manual_book.txt`
- Optional TTS after each page

**Test Result:** [Worked / Partial / Failed]
- Pages scanned: [Number]
- Total words: [Number]
- TTS worked? [Yes / No]

### Mode 3: Batch Folder Scanner
- Put all page photos in one folder
- Processes all images automatically
- Combines into `manual_book.txt`

**Test Result:** [Worked / Partial / Failed]
- Images processed: [Number]
- Failures: [Number and why]

## Known Issues
- [List anything that didn't work perfectly]

## Dependencies
- requests
- Pillow

Install: `pip install requests Pillow`

## Future Improvements
- Phase	Goal	Timeline	
1. Polish	Fix bugs, clean code, complete documentation	Now	
2. Web Backend	FastAPI service, deployed to cloud	3–6 months	
3. Web Frontend	Browser-based UI, camera access	6–9 months	
4. Native App	Flutter/React Native, offline OCR	1–2 years	


