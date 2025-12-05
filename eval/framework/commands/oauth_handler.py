#!/usr/bin/env python3
"""OAuth authentication handler for Google Sheets integration."""

import json
import os
import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class OAuthHandler:
    """Handle OAuth 2.0 authentication for Google Sheets."""

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]

    def __init__(self, credentials_file: str = None):
        """Initialize OAuth handler.

        Args:
            credentials_file: Path to OAuth client credentials JSON
        """
        self.credentials_file = credentials_file or self._find_credentials_file()
        self.token_file = Path.home() / ".config" / "kurt-eval" / "token.pickle"
        self.creds = None

    def _find_credentials_file(self) -> Optional[str]:
        """Find OAuth credentials file in common locations."""
        locations = [
            Path.home() / ".config" / "kurt-eval" / "oauth_credentials.json",
            Path.home() / ".config" / "kurt-eval" / "credentials.json",
            Path.cwd() / "key.json",
            Path.cwd() / "credentials.json",
        ]

        for path in locations:
            if path.exists():
                # Check if it's OAuth credentials
                with open(path) as f:
                    data = json.load(f)
                    if "installed" in data or "web" in data:
                        return str(path)
        return None

    def authenticate(self, force_new: bool = False) -> Credentials:
        """Authenticate and return credentials.

        Args:
            force_new: Force new authentication even if token exists

        Returns:
            Authenticated credentials
        """
        # Try to load existing token
        if not force_new and self.token_file.exists():
            with open(self.token_file, 'rb') as token:
                self.creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("🔄 Refreshing expired token...")
                self.creds.refresh(Request())
            else:
                if not self.credentials_file:
                    raise ValueError("No OAuth credentials file found. Please provide one.")

                print("🌐 Opening browser for authentication...")
                print("Please authorize access in your browser.")

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)

                # Try to use local server first, fall back to console if it fails
                try:
                    self.creds = flow.run_local_server(port=0)
                except Exception:
                    print("⚠️  Local server failed, using console authentication...")
                    self.creds = flow.run_console()

            # Save the credentials for the next run
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
            print(f"✅ Token saved to: {self.token_file}")

        return self.creds

    def get_sheets_service(self):
        """Get authenticated Google Sheets service.

        Returns:
            Google Sheets service object
        """
        creds = self.authenticate()
        return build('sheets', 'v4', credentials=creds)

    def get_drive_service(self):
        """Get authenticated Google Drive service.

        Returns:
            Google Drive service object
        """
        creds = self.authenticate()
        return build('drive', 'v3', credentials=creds)

    def test_connection(self) -> bool:
        """Test the connection by creating a test spreadsheet.

        Returns:
            True if successful
        """
        try:
            service = self.get_sheets_service()

            # Create a test spreadsheet
            spreadsheet = {
                'properties': {
                    'title': 'Kurt Eval - OAuth Test'
                }
            }

            result = service.spreadsheets().create(body=spreadsheet).execute()
            sheet_id = result.get('spreadsheetId')
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"

            print(f"✅ Successfully connected to Google Sheets!")
            print(f"📊 Test spreadsheet created: {sheet_url}")

            return True

        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False