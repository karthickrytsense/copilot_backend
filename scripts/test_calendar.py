"""
Quick test script to verify Google Calendar event creation.
Run from the project root:
    python scripts/test_calendar.py
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

from tools.calendar_tools import create_calendar_event

result = create_calendar_event(
    lead_name="Test Lead",
    lead_email="karthick2.rytsense@gmail.com",  # change to any email you want to test with
    date="2026-05-20",
    time="15:00",
    lead_timezone="America/New_York",
)

print("\n" + "=" * 60)
print("Result:")
print("=" * 60)
for key, value in result.items():
    print(f"{key}: {value}")
