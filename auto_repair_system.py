import os
import json
import gspread
import base64
from google.oauth2.service_account import Credentials

# --- CONFIG ---
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
    print("--- 🚑 STARTING AUTO-REPAIR SYSTEM ---", flush=True)
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)

    # ==========================================
    # STAGE 1: FIX STUDENTS (Duplicates & Bad Data)
    # ==========================================
    print("--- 👨‍🎓 STAGE 1: CLEANING STUDENTS SHEET ---", flush=True)
    ws_students = sh.worksheet("Students")
    student_rows = ws_students.get_all_values()
    
    headers = student_rows[0]
    data = student_rows[1:]
    
    # Auto-detect columns
    try:
        # Looking for 'email' or '@'
        email_idx = [i for i, h in enumerate(headers) if 'email' in h.lower()][0]
    except:
        email_idx = 4 # Fallback
        
    try:
        # Looking for 'id' or 'uid'
        uid_idx = [i for i, h in enumerate(headers) if 'id' in h.lower() or 'uid' in h.lower()][0]
    except:
        uid_idx = 1 # Fallback

    seen_ids = set()
    clean_students = [headers] # Start with headers
    valid_student_ids = set()
    valid_student_emails = set()
    
    removed_count = 0
    
    for row in data:
        # SAFETY CHECK 1: Row Length
        if len(row) <= max(email_idx, uid_idx):
            continue

        uid = row[uid_idx].strip()
        email = row[email_idx].strip()

        # SAFETY CHECK 2: Invalid Data (The '500' error)
        if "@" not in email:
            print(f"   🗑️  Removing corrupted row: Email='{email}'", flush=True)
            removed_count += 1
            continue
            
        # SAFETY CHECK 3: Duplicates
        if uid in seen_ids:
            # This is a duplicate, skip it (delete it)
            # We don't print every duplicate to keep output clean
            removed_count += 1
            continue
        
        # If passed, keep it
        seen_ids.add(uid)
        valid_student_ids.add(uid)
        valid_student_emails.add(email)
        clean_students.append(row)

    if removed_count > 0:
        print(f"   🧹 Removing {removed_count} bad/duplicate student rows...", flush=True)
        ws_students.clear()
        ws_students.update(clean_students, value_input_option='USER_ENTERED')
        print("   ✅ Students Sheet Repaired.", flush=True)
    else:
        print("   ✅ Students Sheet was already healthy.", flush=True)


    # ==========================================
    # STAGE 2: FIX ORDERS (Orphans)
    # ==========================================
    print("--- 🍔 STAGE 2: PRUNING ORPHANED ORDERS ---", flush=True)
    ws_orders = sh.worksheet("Orders")
    order_rows = ws_orders.get_all_values()
    
    o_headers = order_rows[0]
    o_data = order_rows[1:]
    
    # UID is typically column C (index 2)
    o_uid_idx = 2
    
    clean_orders = [o_headers]
    orphan_count = 0
    
    for row in o_data:
        if len(row) > o_uid_idx:
            uid = row[o_uid_idx].strip()
            
            # CHECK: Does this student exist in our verified list?
            if uid in valid_student_ids:
                clean_orders.append(row)
            else:
                orphan_count += 1
        else:
            # Malformed row, remove it
            orphan_count += 1

    if orphan_count > 0:
        print(f"   🧹 Removing {orphan_count} orphaned orders (Ghost IDs)...", flush=True)
        ws_orders.clear()
        ws_orders.update(clean_orders, value_input_option='USER_ENTERED')
        print("   ✅ Orders Sheet Repaired.", flush=True)
    else:
        print("   ✅ Orders Sheet was already healthy.", flush=True)

    # ==========================================
    # STAGE 3: SYNC FEEDBACK
    # ==========================================
    print("--- 💬 STAGE 3: SYNCING FEEDBACK ---", flush=True)
    try:
        ws_feedback = sh.worksheet("Feedback")
        fb_rows = ws_feedback.get_all_values()
        
        if len(fb_rows) > 1:
            fb_headers = fb_rows[0]
            fb_data = fb_rows[1:]
            
            # Email is typically col B (index 1)
            f_email_idx = 1
            
            clean_feedback = [fb_headers]
            fb_removed = 0
            
            for row in fb_data:
                if len(row) > f_email_idx:
                    email = row[f_email_idx].strip()
                    if email in valid_student_emails:
                        clean_feedback.append(row)
                    else:
                        fb_removed += 1
            
            if fb_removed > 0:
                print(f"   🧹 Removing {fb_removed} feedback entries from unknown students...", flush=True)
                ws_feedback.clear()
                ws_feedback.update(clean_feedback, value_input_option='USER_ENTERED')
                print("   ✅ Feedback Sheet Repaired.", flush=True)
            else:
                print("   ✅ Feedback Sheet was already healthy.", flush=True)
    except:
        print("   ⚠️ Feedback sheet not found or empty. Skipping.")

    print("\n🎉 SUCCESS! All sheets are now strictly consistent.", flush=True)

if __name__ == "__main__":
    main()
