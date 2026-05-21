"""
One-time script to generate Google OAuth2 refresh token.

Run this once locally:
    python scripts/google_auth_setup.py

It will open a browser for you to log in with your Google account.
After login, it prints the refresh token — copy it to your .env file as:
    GOOGLE_OAUTH_REFRESH_TOKEN=<printed value>
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]

def main():
    client_id = input("Enter your GOOGLE_OAUTH_CLIENT_ID: ").strip()
    client_secret = input("Enter your GOOGLE_OAUTH_CLIENT_SECRET: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("Copy these values to your .env file:")
    print("=" * 60)
    print(f"GOOGLE_OAUTH_CLIENT_ID={client_id}")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 60)

if __name__ == "__main__":
    main()
