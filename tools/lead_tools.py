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
    file_path = "/tmp/leads.csv"
    headers = ["name", "email", "phone", "company", "project_description", "date", "time"]

    now = datetime.now()
    lead_data["date"] = now.strftime("%Y-%m-%d")
    lead_data["time"] = now.strftime("%H:%M:%S")

    file_exists = os.path.isfile(file_path)

    try:
        # 1. Write to local CSV as backup
        with open(file_path, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            row = {field: lead_data.get(field, "") for field in headers}
            writer.writerow(row)

        # 2. Upload to Google Sheets
        google_creds_raw = os.getenv("GOOGLE_CREDENTIALS")
        google_creds_file = settings.GOOGLE_CREDENTIALS_FILE
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        client = None

        # Resolve credentials file to absolute path relative to project root
        if google_creds_file and not os.path.isabs(google_creds_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            google_creds_file = os.path.join(base_dir, google_creds_file)

        if settings.GOOGLE_SHEET_ID and google_creds_raw:
            # Production (Vercel) — credentials from env var JSON string
            print("[Lead Capture] Uploading to Google Sheets via env var...")
            creds_dict = json.loads(google_creds_raw)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)

        elif settings.GOOGLE_SHEET_ID and google_creds_file and os.path.isfile(google_creds_file):
            # Local development — credentials from file
            print("[Lead Capture] Uploading to Google Sheets via credentials file...")
            creds = Credentials.from_service_account_file(google_creds_file, scopes=scopes)
            client = gspread.authorize(creds)

        else:
            print(f"[Lead Capture] Google Sheets skipping (credentials not configured in .env)")
            print(f"[Lead Capture] Debug — GOOGLE_SHEET_ID: {settings.GOOGLE_SHEET_ID}, creds_file: {google_creds_file}, file_exists: {os.path.isfile(google_creds_file) if google_creds_file else False}")

        if client:
            sheet = client.open_by_key(settings.GOOGLE_SHEET_ID).worksheet(settings.GOOGLE_SHEET_NAME)

            # Add headers if sheet is empty
            all_data = sheet.get_all_values()
            if not all_data:
                _headers = [h.replace("_", " ").title() for h in headers]
                sheet.append_row(_headers)

            # Append lead data
            row_values = [lead_data.get(field, "") for field in headers]
            sheet.append_row(row_values)
            print(f"[Lead Capture] Google Sheets sync complete for: {lead_data.get('email')}")

        print(f"[Lead Capture] Successfully stored lead: {lead_data.get('email')}")
        return "Lead successfully submitted to the database."

    except Exception as e:
        print(f"[Lead Capture] Error storing lead: {e}")
        return "Failed to submit lead fully due to internal error."
