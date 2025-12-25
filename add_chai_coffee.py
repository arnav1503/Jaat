#!/usr/bin/env python3
"""Quick script to add chai and coffee to the Google Sheets menu"""

import os
import json
import base64
from google.oauth2.service_account import Credentials
import gspread

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI"

try:
    # Initialize sheets client
    base64_creds = os.environ.get("GCP_BASE64_CREDS")
    if base64_creds:
        creds_bytes = base64.b64decode(base64_creds)
        creds_info = json.loads(creds_bytes)
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            'canteen-app-376c7-eaaf8790c170.json',
            scopes=SCOPES
        )
    
    sheets_client = gspread.authorize(creds)
    spreadsheet = sheets_client.open_by_key(SPREADSHEET_ID)
    menu_sheet = spreadsheet.worksheet("Menu")
    
    # Get existing items to avoid duplicates
    existing = menu_sheet.get_all_records()
    existing_names = [item.get('name', '').lower() for item in existing]
    
    # Add chai if not exists
    if 'chai' not in existing_names:
        menu_sheet.append_row(['item6', 'Chai', '30', 'Warm and refreshing Indian tea', '/static/images/chai.jpg', 'No'], value_input_option='USER_ENTERED')
        print("✓ Added Chai to menu")
    else:
        print("⚠ Chai already exists in menu")
    
    # Add coffee if not exists
    if 'coffee' not in existing_names:
        menu_sheet.append_row(['item7', 'Coffee', '40', 'Strong and aromatic coffee', '/static/images/coffee.jpg', 'No'], value_input_option='USER_ENTERED')
        print("✓ Added Coffee to menu")
    else:
        print("⚠ Coffee already exists in menu")
    
    print("\n✅ Done! Chai and Coffee have been added to the menu.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
