import os
import json
import gspread
import base64
from google.oauth2.service_account import Credentials

# --- CONFIG ---
# We trust these counts are your REAL data.
# Anything after these rows will be deleted.
SAFE_STUDENT_COUNT = 104
SAFE_ORDER_COUNT = 194

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    print("--- 🧹 STARTING SAFETY CLEANUP ---")
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")

    # --- 1. CLEAN STUDENTS ---
    print(f"Checking Students (Safe limit: {SAFE_STUDENT_COUNT})...")
    student_vals = ws_students.get_all_values()
    
    # We keep header + safe count
    rows_to_keep_students = 1 + SAFE_STUDENT_COUNT
    
    if len(student_vals) > rows_to_keep_students:
        print(f"⚠️  Found {len(student_vals) - rows_to_keep_students} bad rows. Deleting...")
        # We resize the sheet to cut off the bottom rows
        ws_students.resize(rows=rows_to_keep_students)
        print("✅ Students cleaned.")
    else:
        print("✅ Students sheet is already clean.")

    # --- 2. CLEAN ORDERS ---
    print(f"Checking Orders (Safe limit: {SAFE_ORDER_COUNT})...")
    order_vals = ws_orders.get_all_values()
    
    rows_to_keep_orders = 1 + SAFE_ORDER_COUNT
    
    if len(order_vals) > rows_to_keep_orders:
        print(f"⚠️  Found {len(order_vals) - rows_to_keep_orders} bad rows. Deleting...")
        ws_orders.resize(rows=rows_to_keep_orders)
        print("✅ Orders cleaned.")
    else:
        print("✅ Orders sheet is already clean.")
        
    print("\n🎉 CLEANUP DONE. Ready for correct generation.")

if __name__ == "__main__":
    main()
