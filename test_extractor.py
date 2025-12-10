"""
Test script for document text extraction with OCR and MRZ detection
"""
import asyncio
import os
import json
from app.services.extractor import DocumentExtractor

async def test_extraction():
    """
    Test document extraction for different file types
    """
    extractor = DocumentExtractor()
    
    # Test directory with sample files
    test_dir = "temp_uploads"
    
    # Test PDF extraction
    pdf_files = [f for f in os.listdir(test_dir) if f.endswith('.pdf')]
    if pdf_files:
        print(f"Testing PDF extraction with {pdf_files[0]}")
        pdf_path = os.path.join(test_dir, pdf_files[0])
        results = await extractor.extract_text(pdf_path, "pdf")
        print(f"PDF extraction completed. Found {sum(len(page['text_blocks']) for page in results)} text blocks across {len(results)} pages")
        # Save the results to a JSON file for inspection
        with open('pdf_extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
    
    # Test image extraction
    image_files = [f for f in os.listdir(test_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if image_files:
        print(f"Testing image extraction with {image_files[0]}")
        image_path = os.path.join(test_dir, image_files[0])
        results = await extractor.extract_text(image_path)
        print(f"Image extraction completed. Found {sum(len(page['text_blocks']) for page in results)} text blocks")
        # Save the results to a JSON file for inspection
        with open('image_extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
    
    print("Extraction tests completed")

if __name__ == "__main__":
    asyncio.run(test_extraction())