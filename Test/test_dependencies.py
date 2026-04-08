#!/usr/bin/env python3
import sys
import os

PROJECT_ROOT = os.path.abspath('.')
sys.path.insert(0, PROJECT_ROOT)

dependencies = [
    ("groq", "groq"),
    ("sentence_transformers", "sentence-transformers"),
    ("torch", "torch"),
    ("faiss", "faiss-cpu"),
    ("langchain_text_splitters", "langchain-text-splitters"),
    ("bs4", "beautifulsoup4"),
    ("pypdf", "pypdf"),
    ("docx", "python-docx"),
    ("pandas", "pandas"),
    ("loguru", "loguru"),
]

print("Checking dependencies...")
missing = []
for module, package in dependencies:
    try:
        __import__(module)
        print(f"✓ {module}")
    except ImportError:
        print(f"✗ {module} (need: {package})")
        missing.append(package)

if missing:
    print(f"\n⚠ Missing dependencies. Install with:")
    print(f"pip install {' '.join(missing)}")
else:
    print("\n✓ All dependencies are installed!")