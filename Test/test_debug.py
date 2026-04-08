#!/usr/bin/env python3
import sys
import os

PROJECT_ROOT = os.path.abspath('.')
sys.path.insert(0, PROJECT_ROOT)

print(f"Project root: {PROJECT_ROOT}")
print("Testing imports...")

# Test basic import
try:
    print("Attempting to import from app.email.email_responder...")
    from app.email.email_responder import EmailResponder
    print("✓ Import successful!")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()

print("\nChecking if files exist...")
email_responder_path = os.path.join(PROJECT_ROOT, "app", "email", "email_responder.py")
if os.path.exists(email_responder_path):
    print(f"✓ email_responder.py exists at {email_responder_path}")
    
    # Read first few lines to check syntax
    with open(email_responder_path, 'r') as f:
        lines = f.readlines()[:10]
        print("\nFirst 10 lines of email_responder.py:")
        for i, line in enumerate(lines, 1):
            print(f"{i}: {line.rstrip()}")
else:
    print(f"✗ email_responder.py not found at {email_responder_path}")

print("\nChecking app/email/__init__.py...")
init_path = os.path.join(PROJECT_ROOT, "app", "email", "__init__.py")
if os.path.exists(init_path):
    print("✓ __init__.py exists")
else:
    print("✗ __init__.py missing - creating it...")
    with open(init_path, 'w') as f:
        f.write("# Make email a package\n")
    print("✓ Created __init__.py")