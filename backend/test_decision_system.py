#!/usr/bin/env python3
"""
Complete Email Support System with Ibtcode Decision Layer Integration
"""

import sys
import os

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

print(f"Project root: {PROJECT_ROOT}")

import logging
from typing import Dict, Any

# CORRECTED IMPORT - email_responder is inside app/email/
try:
    from app.email.email_responder import EmailResponder
    print("✓ EmailResponder imported successfully from app.email.email_responder")
except ImportError as e:
    print(f"✗ Failed to import EmailResponder: {e}")
    
    # Try alternative import
    try:
        from email_responder import EmailResponder
        print("✓ EmailResponder imported successfully from local import")
    except ImportError as e2:
        print(f"✗ Also failed: {e2}")
        
        # Check if file exists
        email_responder_path = os.path.join(PROJECT_ROOT, "app", "email", "email_responder.py")
        if os.path.exists(email_responder_path):
            print(f"✓ email_responder.py found at {email_responder_path}")
        else:
            print(f"✗ email_responder.py not found at {email_responder_path}")
        sys.exit(1)


def setup_logging():
    """Configure production logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('email_system.log'),
            logging.StreamHandler()
        ]
    )


def process_customer_email(email_content: str, user_id: str) -> Dict[str, Any]:
    """
    Process a single customer email through the system.
    
    Args:
        email_content: Raw customer email text
        user_id: Customer/user identifier
    
    Returns:
        Dictionary with response and analysis
    """
    responder = EmailResponder(user_id)
    result = responder.generate_reply(email_content)
    return result


def print_analysis_report(result: Dict[str, Any]):
    """Print detailed analysis report"""
    print("\n" + "="*60)
    print("RESPONSE")
    print("="*60)
    print(result["response"])
    
    print("\n" + "="*60)
    print("DECISION LAYER ANALYSIS")
    print("="*60)
    analysis = result["analysis"]
    print(f"Emotion: {analysis['emotion']} (Level: {analysis['emotion_level']}/5)")
    print(f"Intent: {analysis['intent']}")
    print(f"Context: {analysis['context']}")
    print(f"Risk: {analysis['risk']}/5")
    print(f"Urgency: {analysis['urgency']}/5")
    print(f"Priority: {analysis['priority']:.2f}")
    print(f"Strategy: {analysis['strategy']}")
    print(f"Action: {analysis['action']}")
    print(f"Confidence: {analysis['confidence']:.2f}")
    print(f"Reasoning: {analysis['reasoning']}")
    
    print("\n" + "="*60)
    print("EXTRACTED IDENTIFIERS")
    print("="*60)
    identifiers = result["identifiers"]
    for key, value in identifiers.items():
        if value:
            print(f"{key}: {value}")


def main():
    """Main execution function"""
    setup_logging()
    logging.info("Email Support System Started with Ibtcode Decision Layer")
    
    # Example customer emails
    test_emails = [
        {
            "content": """Subject: Payment Failed

My payment failed 3 times! I need this resolved immediately. 
Project: "Alpha Launch"
Order ID: 12345678

This is urgent. Please fix now.""",
            "user_id": "customer_001"
        },
        {
            "content": """Subject: Login Issue

Hello, I cannot login to my account. I tried resetting password but still not working.
Can you help me?""",
            "user_id": "customer_002"
        },
        {
            "content": """Subject: Question about features

Hi team, does your platform support API integration? I need to connect with our internal systems.
Thanks!""",
            "user_id": "customer_003"
        }
    ]
    
    for email_data in test_emails:
        print("\n" + "#"*60)
        print(f"PROCESSING EMAIL FOR USER: {email_data['user_id']}")
        print("#"*60)
        print("\nCUSTOMER EMAIL:")
        print(email_data["content"])
        
        try:
            result = process_customer_email(
                email_content=email_data["content"],
                user_id=email_data["user_id"]
            )
            print_analysis_report(result)
        except Exception as e:
            print(f"\nError processing email: {e}")
            import traceback
            traceback.print_exc()
        
        if email_data != test_emails[-1]:
            input("\nPress Enter to process next email...")


if __name__ == "__main__":
    main()