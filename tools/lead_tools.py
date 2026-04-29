import csv
import os
import json
from typing import Dict, Any
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import settings

def get_lead_requirements() -> list[str]:
    """Returns the list of required fields for capturing a lead."""
    return [
        "name",
        "email", 
        "phone", 
        "company", 
        "project_description"
    ]

def submit_lead(lead_data: Dict[str, Any]) -> str:
    """
    Submits a completed lead entry. Appends the data 
    to a local leads.csv file.
    
    Expected fields in lead_data:
    - name: str
    - email: str
    - phone: str
    - company: str
    - project_description: str
    """
    file_path = "/tmp/leads.csv"
    headers = ["name", "email", "phone", "company", "project_description", "date", "time"]

    now = datetime.now()
    lead_data["date"] = now.strftime("%Y-%m-%d")
    lead_data["time"] = now.strftime("%H:%M:%S")

    file_exists = os.path.isfile(file_path)

    try:
        # 1. First, always write to local CSV as a backup
        with open(file_path, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=headers)

            if not file_exists:
                writer.writeheader()

            row = {field: lead_data.get(field, "") for field in headers}
            writer.writerow(row)
            
        # 2. Upload to Google Sheets if configured
        google_creds_raw = os.getenv("GOOGLE_CREDENTIALS")
        if settings.GOOGLE_SHEET_ID and google_creds_raw:
            print("[Lead Capture] Uploading to Google Sheets...")
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds_dict = json.loads(google_creds_raw)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            
            sheet = client.open_by_key(settings.GOOGLE_SHEET_ID).worksheet(settings.GOOGLE_SHEET_NAME)
            
            # Check if headers exist, if sheet is empty add them
            all_data = sheet.get_all_values()
            if not all_data:
                _headers = [h.replace("_", " ").title() for h in headers]
                sheet.append_row(_headers)

            
            # Append lead data
            row_values = [lead_data.get(field, "") for field in headers]
            sheet.append_row(row_values)
            print(f"[Lead Capture] Google Sheets sync complete for: {lead_data.get('email')}")
        else:
            print("[Lead Capture] Google Sheets skipping (credentials not configured in .env)")

        print(f"[Lead Capture] Successfully stored lead: {lead_data.get('email')}")
        return "Lead successfully submitted to the database."
    except Exception as e:
        print(f"[Lead Capture] Error storing lead: {e}")
        return "Failed to submit lead fully due to internal error."
