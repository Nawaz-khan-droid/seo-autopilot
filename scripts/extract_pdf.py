"""Extract text from Beautiful India reference PDF for analysis."""
import os, sys

d = r"C:\Users\nawaz\OneDrive\Desktop\SEO Demo\seo-autopilot\output"
pdf_path = os.path.join(d, "Beautiful India Monthly SEO Report-June 2025.pdf")

# Try different PDF libraries
try:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            print(f"\n{'='*60}")
            print(f"PAGE {i+1}")
            print(f"{'='*60}")
            print(text[:2000] if text else "(no text extracted)")
            if text and len(text) > 2000:
                print(f"\n... ({len(text)-2000} more chars)")
except ImportError:
    pass

try:
    from pdfminer.high_level import extract_text
    text = extract_text(pdf_path)
    pages = text.split("\x0c")
    for i, page_text in enumerate(pages):
        print(f"\n{'='*60}")
        print(f"PAGE {i+1}")
        print(f"{'='*60}")
        print(page_text[:2000] if page_text.strip() else "(empty)")
        if len(page_text) > 2000:
            print(f"\n... ({len(page_text)-2000} more chars)")
except ImportError:
    pass

try:
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        text = page.get_text()
        print(f"\n{'='*60}")
        print(f"PAGE {i+1}")
        print(f"{'='*60}")
        print(text[:2000] if text.strip() else "(no text)")
        if len(text) > 2000:
            print(f"\n... ({len(text)-2000} more chars)")
except ImportError:
    print("No PDF library available. Install with: pip install pdfplumber")
