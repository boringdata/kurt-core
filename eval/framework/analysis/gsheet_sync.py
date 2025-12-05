#!/usr/bin/env python3
"""Sync evaluation reports to Google Sheets with GitHub links."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import pandas as pd


class GSheetReportSync:
    """Syncs evaluation reports to Google Sheets with GitHub integration."""

    def __init__(
        self,
        repo_url: str = "https://github.com/anthropics/kurt-core",
        branch: str = "main",
        credentials_path: Optional[str] = None,
    ):
        """Initialize the sync handler.

        Args:
            repo_url: GitHub repository URL
            branch: Branch name for file links
            credentials_path: Path to Google Service Account credentials JSON
        """
        self.repo_url = repo_url.rstrip("/")
        self.branch = branch
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        # Will be initialized lazily when needed
        self._sheets_client = None
        self._drive_client = None

    def _get_credentials(self):
        """Get credentials, supporting both Service Account and OAuth."""
        import json
        from pathlib import Path

        # Check common locations for credentials
        cred_locations = [
            self.credentials_path,
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            str(Path.home() / ".config" / "kurt-eval" / "service_account.json"),
            str(Path.cwd() / "key.json"),
        ]

        for cred_path in cred_locations:
            if cred_path and Path(cred_path).exists():
                # Read the file to determine credential type
                with open(cred_path) as f:
                    cred_data = json.load(f)

                # Check if it's a service account
                if cred_data.get("type") == "service_account":
                    from google.oauth2 import service_account
                    print(f"🔑 Using Service Account credentials from: {cred_path}")
                    return service_account.Credentials.from_service_account_file(
                        cred_path,
                        scopes=[
                            "https://www.googleapis.com/auth/spreadsheets",
                            "https://www.googleapis.com/auth/drive.file",
                        ],
                    )

                # Check if it's OAuth client credentials
                elif "installed" in cred_data or "web" in cred_data:
                    print(f"🔑 Using OAuth Client credentials from: {cred_path}")
                    # Use OAuth handler
                    from ..commands.oauth_handler import OAuthHandler
                    oauth = OAuthHandler(credentials_file=cred_path)
                    return oauth.authenticate()

        # If no credentials found, try OAuth without specific file
        print("🔍 No credentials file found, trying OAuth authentication...")
        from ..commands.oauth_handler import OAuthHandler
        oauth = OAuthHandler()
        if oauth.credentials_file:
            return oauth.authenticate()

        raise ValueError(
            "No Google credentials found. Please run:\n"
            "  uv run python -m eval gsheet-auth\n"
            "Or set GOOGLE_APPLICATION_CREDENTIALS environment variable."
        )

    def _init_google_clients(self):
        """Initialize Google API clients lazily."""
        if self._sheets_client is not None:
            return

        try:
            from googleapiclient.discovery import build

            # Try to detect credential type and use appropriate auth
            credentials = self._get_credentials()

            self._sheets_client = build("sheets", "v4", credentials=credentials)
            self._drive_client = build("drive", "v3", credentials=credentials)
        except ImportError:
            raise ImportError(
                "Google API client libraries not installed. "
                "Run: pip install google-api-python-client google-auth"
            )

    def create_github_link(self, file_path: str, line_number: Optional[int] = None) -> str:
        """Create a GitHub link to a file.

        Args:
            file_path: Relative path to file from repo root
            line_number: Optional line number to link to

        Returns:
            GitHub URL to the file
        """
        # Clean the path
        if file_path.startswith("/"):
            file_path = file_path[1:]

        url = f"{self.repo_url}/blob/{self.branch}/{file_path}"

        if line_number:
            url += f"#L{line_number}"

        return url

    def format_csv_for_sheets(self, csv_path: Path) -> pd.DataFrame:
        """Load and format CSV data for Google Sheets.

        Args:
            csv_path: Path to the CSV file

        Returns:
            Formatted DataFrame ready for upload
        """
        # Read pipe-delimited CSV
        df = pd.read_csv(csv_path, delimiter="|")

        # Add GitHub links for answer files
        if "Answer File" in df.columns:
            df["Answer Link"] = df["Answer File"].apply(
                lambda x: self.create_github_link(x) if pd.notna(x) and x else ""
            )

        # Add timestamp
        df["Last Updated"] = datetime.now().isoformat()

        # Format numeric columns
        for col in ["Judge Overall Score", "Tokens Used", "Duration (seconds)"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def create_or_update_sheet(
        self,
        df: pd.DataFrame,
        spreadsheet_name: str = "Kurt Eval Report",
        sheet_name: str = "Comparison Results",
    ) -> str:
        """Create or update a Google Sheet with the evaluation data.

        Args:
            df: DataFrame to upload
            spreadsheet_name: Name of the spreadsheet
            sheet_name: Name of the worksheet

        Returns:
            URL to the created/updated sheet
        """
        self._init_google_clients()

        try:
            # Try to find existing spreadsheet
            results = self._drive_client.files().list(
                q=f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet'",
                fields="files(id, name)",
            ).execute()

            files = results.get("files", [])

            if files:
                spreadsheet_id = files[0]["id"]
                print(f"📝 Updating existing spreadsheet: {spreadsheet_name}")
            else:
                # Create new spreadsheet
                spreadsheet = self._sheets_client.spreadsheets().create(
                    body={"properties": {"title": spreadsheet_name}}
                ).execute()
                spreadsheet_id = spreadsheet["spreadsheetId"]
                print(f"📊 Created new spreadsheet: {spreadsheet_name}")

            # Prepare data for upload
            values = [df.columns.tolist()] + df.values.tolist()

            # Clear existing content and update with new data
            self._sheets_client.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:Z"
            ).execute()

            self._sheets_client.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": values},
            ).execute()

            # Format the sheet
            self._format_sheet(spreadsheet_id, sheet_name, len(df.columns), len(df) + 1)

            sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            print(f"✅ Sheet updated: {sheet_url}")
            return sheet_url

        except Exception as e:
            print(f"❌ Error syncing to Google Sheets: {e}")
            raise

    def _format_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        num_cols: int,
        num_rows: int,
    ):
        """Apply formatting to the Google Sheet.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the worksheet
            num_cols: Number of columns
            num_rows: Number of rows including header
        """
        requests = [
            # Freeze header row
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": 0,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            # Bold header row
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True},
                            "backgroundColor": {
                                "red": 0.9,
                                "green": 0.9,
                                "blue": 0.9,
                            },
                        }
                    },
                    "fields": "userEnteredFormat(textFormat,backgroundColor)",
                }
            },
            # Auto-resize columns
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": 0,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": num_cols,
                    }
                }
            },
            # Apply conditional formatting for scores
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": 1,
                                "endRowIndex": num_rows,
                                "startColumnIndex": 7,  # Assuming score columns start at H
                                "endColumnIndex": 8,
                            }
                        ],
                        "gradientRule": {
                            "minpoint": {
                                "color": {"red": 1, "green": 0.2, "blue": 0.2},
                                "type": "NUMBER",
                                "value": "0",
                            },
                            "midpoint": {
                                "color": {"red": 1, "green": 1, "blue": 0.2},
                                "type": "NUMBER",
                                "value": "0.5",
                            },
                            "maxpoint": {
                                "color": {"red": 0.2, "green": 1, "blue": 0.2},
                                "type": "NUMBER",
                                "value": "1",
                            },
                        },
                    },
                    "index": 0,
                }
            },
        ]

        self._sheets_client.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests},
        ).execute()

    def add_summary_sheet(
        self,
        spreadsheet_id: str,
        json_report_path: Path,
    ):
        """Add a summary sheet with aggregate metrics.

        Args:
            spreadsheet_id: ID of the spreadsheet
            json_report_path: Path to the JSON report file
        """
        with open(json_report_path) as f:
            data = json.load(f)

        # Extract summary data
        summaries = []
        for scenario in ["with_kg", "without_kg"]:
            if scenario in data:
                summary = data[scenario].get("summary", {})
                summaries.append({
                    "Scenario": scenario,
                    "Average Score": summary.get("average_score", 0),
                    "Total Tokens": summary.get("tokens_total", 0),
                    "Total Duration (s)": summary.get("duration_total", 0),
                    "Cached Responses": summary.get("cached_responses", 0),
                    "Questions Evaluated": summary.get("num_questions", 0),
                })

        df_summary = pd.DataFrame(summaries)

        # Add to sheet
        values = [df_summary.columns.tolist()] + df_summary.values.tolist()

        self._sheets_client.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="Summary!A1",
            valueInputOption="RAW",
            body={"values": values},
        ).execute()

    def sync_report(
        self,
        csv_path: str,
        json_path: Optional[str] = None,
        spreadsheet_name: str = "Kurt Eval Report",
    ) -> str:
        """Main method to sync a report to Google Sheets.

        Args:
            csv_path: Path to the CSV comparison file
            json_path: Optional path to JSON report for summary data
            spreadsheet_name: Name for the Google Sheet

        Returns:
            URL to the Google Sheet
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Format the CSV data
        df = self.format_csv_for_sheets(csv_path)

        # Create or update the main sheet
        sheet_url = self.create_or_update_sheet(df, spreadsheet_name, "Comparison Results")

        # Add summary sheet if JSON provided
        if json_path:
            json_path = Path(json_path)
            if json_path.exists():
                spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
                self.add_summary_sheet(spreadsheet_id, json_path)

        return sheet_url


def main():
    """CLI for syncing reports to Google Sheets."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync evaluation reports to Google Sheets"
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to the CSV comparison file",
    )
    parser.add_argument(
        "--json",
        help="Optional path to JSON report for summary data",
    )
    parser.add_argument(
        "--name",
        default="Kurt Eval Report",
        help="Name for the Google Sheet",
    )
    parser.add_argument(
        "--repo",
        default="https://github.com/anthropics/kurt-core",
        help="GitHub repository URL",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="GitHub branch name",
    )
    parser.add_argument(
        "--credentials",
        help="Path to Google Service Account credentials JSON",
    )

    args = parser.parse_args()

    # Create sync handler
    sync = GSheetReportSync(
        repo_url=args.repo,
        branch=args.branch,
        credentials_path=args.credentials,
    )

    # Sync the report
    try:
        sheet_url = sync.sync_report(
            csv_path=args.csv,
            json_path=args.json,
            spreadsheet_name=args.name,
        )
        print(f"\n🎉 Report successfully synced to Google Sheets!")
        print(f"📋 View at: {sheet_url}")
    except Exception as e:
        print(f"\n❌ Failed to sync report: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())