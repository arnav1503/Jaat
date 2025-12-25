import os
import json
import gspread
import base64
import sys
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
SPREADSHEET_ID = "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def main():
    print("--- 🔍 DIAGNOSTIC TEST STARTING ---", flush=True)

    # 1. Check Credentials
    creds = None
    if os.environ.get("GCP_BASE64_CREDS"):
        print("   ✅ Found 'GCP_BASE64_CREDS' environment variable.", flush=True)
        try:
            creds_json = base64.b64decode(os.environ["GCP_BASE64_CREDS"])
            creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
        except Exception as e:
            print(f"   ❌ Error decoding Env Var: {e}", flush=True)
            return
    elif os.path.exists('canteen-app-376c7-eaaf8790c170.json'):
        print("   ✅ Found local JSON file: canteen-app-376c7-eaaf8790c170.json", flush=True)
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    else:
        print("   ❌ CRITICAL ERROR: No credentials found!", flush=True)
        print("      - Make sure 'canteen-app-376c7-eaaf8790c170.json' is in this folder.", flush=True)
        print("      - OR set the 'GCP_BASE64_CREDS' variable.", flush=True)
        return

    # 2. Connect to Google
    try:
        print("   📡 Connecting to Google API...", flush=True)
        client = gspread.authorize(creds)
        print("   ✅ Authorized successfully.", flush=True)
    except Exception as e:
        print(f"   ❌ Auth Failed: {e}", flush=True)
        return

    # 3. Open Spreadsheet
    try:
        print(f"   📂 Opening Spreadsheet ID: {SPREADSHEET_ID}", flush=True)
        sh = client.open_by_key(SPREADSHEET_ID)
        print(f"   ✅ Sheet opened: {sh.title}", flush=True)
    except Exception as e:
        print(f"   ❌ Could not open sheet: {e}", flush=True)
        return

    # 4. Write Test Data
    try:
        print("   ✍️  Attempting to write to 'Sheet1' (cell A1)...", flush=True)
        # Try to get Sheet1, or create it if missing
        try:
            ws = sh.worksheet("Sheet1")
        except:
            ws = sh.add_worksheet("Sheet1", 10, 5)
        
        ws.update_acell('A1', f"TEST CONNECTION SUCCESS: {datetime.now()}")
        print("   ✅ Write successful! Check cell A1 in 'Sheet1'.", flush=True)
    except Exception as e:
        print(f"   ❌ Write Failed: {e}", flush=True)

    print("--- 🏁 TEST COMPLETE ---", flush=True)

if __name__ == "__main__":
    main()
