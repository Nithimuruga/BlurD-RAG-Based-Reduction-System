# Document Text Extractor Implementation

## Overview
This document describes the implementation of the `extractor.py` service that provides comprehensive document text extraction capabilities with OCR and MRZ detection.

## Features Implemented

1. **Enhanced Text Extraction**
   - PDF text extraction using PyMuPDF/Fitz
   - DOCX document parsing with python-docx
   - XLSX spreadsheet parsing with openpyxl
   - Image text extraction with pytesseract OCR

2. **Advanced OCR Processing**
   - Automatic detection of scanned vs. text-based PDF pages
   - Image preprocessing for improved OCR accuracy
   - Multiple language support
   - Confidence scoring for extracted text

3. **Passport MRZ Detection**
   - Enhanced MRZ detection with pattern matching
   - Both text-based and image-based MRZ detection
   - Validation of MRZ data
   - Multiple MRZ format support (TD1, TD2, TD3, MRVA, MRVB)

4. **Document Layout Analysis**
   - PDF page rotation detection and correction
   - Bounding box normalization
   - Text block extraction with position information

5. **Error Handling and Robustness**
   - Graceful degradation for damaged files
   - Consistent error reporting
   - File type detection and validation

## Output Format

The extractor produces a consistent JSON output format:

```json
[
  {
    "page": 1,
    "text_blocks": [
      {
        "text": "Sample text",
        "bbox": [x1, y1, x2, y2],
        "conf": 0.98,
        "type": "text|ocr|mrz",
        "metadata": {
          "block_num": 1,
          "line_num": 1,
          "word_num": 1,
          "mrz_data": { /* MRZ data if applicable */ }
        }
      }
    ],
    "page_info": {
      "width": 612,
      "height": 792,
      "rotation": 0,
      "is_scanned": false
    }
  }
]
```

## Dependencies Added
- pdfplumber - For advanced PDF text extraction
- passporteye - For MRZ detection in passport images
- opencv-python - For image processing and enhancement
- pdf2image - For converting PDF pages to images for OCR

## Testing
The implementation includes a test script (`test_extractor.py`) to verify extraction functionality across different file types.

## Integration with Existing System
The extractor maintains backward compatibility through the `extract_text` function used by the extraction router, ensuring seamless integration with the existing API endpoints.