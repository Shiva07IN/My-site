#!/usr/bin/env python3
"""
Test script for PDF generation functionality
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import DocumentGenerator

def test_pdf_generation():
    """Test PDF generation with sample content"""
    
    # Sample document content
    test_content = """
AFFIDAVIT

I, JOHN DOE, son of ROBERT DOE, aged 30 years, resident of 123 Main Street, New Delhi - 110001, do hereby solemnly affirm and declare as under:

1. That I am the deponent herein and I am competent to swear to this affidavit.

2. That I am a resident of the above mentioned address for the past 5 years.

3. That I require this affidavit for address proof purposes.

4. That I undertake to inform the concerned authorities if any of the above information is found to be false or incorrect.

5. That this affidavit is made for address proof and no other purpose.

DEPONENT

VERIFICATION

I, the above named deponent, do hereby verify that the contents of this affidavit are true and correct to the best of my knowledge and belief and nothing material has been concealed therefrom.

Verified at New Delhi on this 15th day of December, 2024.

DEPONENT
"""
    
    try:
        print("Testing PDF generation...")
        
        # Test the PDF generation
        pdf_path = DocumentGenerator.generate_pdf(
            text=test_content,
            title="Affidavit Document",
            user_data={"full_name": "John Doe", "address": "123 Main Street, New Delhi"}
        )
        
        if pdf_path and os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            print(f"PDF generated successfully!")
            print(f"File: {pdf_path}")
            print(f"Size: {file_size} bytes")
            
            # Clean up test file
            try:
                os.remove(pdf_path)
                print("Test file cleaned up")
            except:
                pass
                
            return True
        else:
            print("PDF generation failed - file not created")
            return False
            
    except Exception as e:
        print(f"PDF generation failed: {e}")
        return False

def test_text_cleaning():
    """Test text cleaning functionality"""
    
    test_cases = [
        "Normal text content",
        "Text with <b>HTML</b> tags",
        "Text with &amp; entities &lt;test&gt;",
        "Text with\n\n\nmultiple\n\n\nline breaks",
        "Text with    extra    spaces"
    ]
    
    print("\nTesting text cleaning...")
    
    for i, test_text in enumerate(test_cases, 1):
        try:
            cleaned = DocumentGenerator.clean_text_for_pdf(test_text)
            print(f"Test {i}: '{test_text[:30]}...' -> '{cleaned[:30]}...'")
        except Exception as e:
            print(f"Test {i} failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("Running PDF Generation Tests")
    print("=" * 50)
    
    # Test text cleaning
    if not test_text_cleaning():
        print("Text cleaning tests failed")
        sys.exit(1)
    
    # Test PDF generation
    if not test_pdf_generation():
        print("PDF generation tests failed")
        sys.exit(1)
    
    print("\nAll tests passed!")
    print("PDF generation system is working correctly")