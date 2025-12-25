import os
import json
import gspread
import base64
from collections import Counter
from google.oauth2.service_account import Credentials

# --- CONFIG ---
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def check_students(sh):
    print(f"\n{YELLOW}--- 🕵️ CHECKING STUDENTS SHEET ---{RESET}")
    try:
        ws = sh.worksheet("Students")
        rows = ws.get_all_values()
        
        if len(rows) < 2:
            print(f"{RED}❌ Sheet is empty!{RESET}")
            return set(), set()

        headers = rows[0]
        data = rows[1:]
        
        print(f"   Stats: Found {len(data)} students.")

        # Heuristic to find columns based on content
        email_idx = -1
        uid_idx = -1
        
        # Try to find Email column
        for i, val in enumerate(data[0]):
            if "@" in str(val):
                email_idx = i
                break
        
        # Try to find UID column (usually short number)
        for i, val in enumerate(data[0]):
            if str(val).isdigit() and len(str(val)) in [4, 5]:
                uid_idx = i
                break
                
        if email_idx == -1: 
            # Fallback to column E (index 4) if heuristic fails
            email_idx = 4 
            print(f"{YELLOW}   ⚠️ Could not auto-detect Email column. Assuming Column E.{RESET}")

        if uid_idx == -1:
            # Fallback to column B (index 1)
            uid_idx = 1
            print(f"{YELLOW}   ⚠️ Could not auto-detect UID column. Assuming Column B.{RESET}")

        student_ids = set()
        student_emails = set()
        duplicates_id = []
        misaligned_rows = []

        for r_num, row in enumerate(data, start=2):
            # Check Alignment (Is the Email column actually an email?)
            if len(row) > email_idx:
                email = row[email_idx].strip()
                if "@" not in email:
                    misaligned_rows.append(f"Row {r_num}: '{email}' is not a valid email.")
                else:
                    student_emails.add(email)
            
            # Check ID Duplicates
            if len(row) > uid_idx:
                uid = row[uid_idx].strip()
                if uid in student_ids:
                    duplicates_id.append(f"Row {r_num} (ID: {uid})")
                student_ids.add(uid)

        # REPORT
        if misaligned_rows:
            print(f"{RED}❌ COLUMN MISALIGNMENT FOUND ({len(misaligned_rows)} rows):{RESET}")
            for m in misaligned_rows[:5]: print(f"   - {m}")
            if len(misaligned_rows) > 5: print(f"   - ... and {len(misaligned_rows)-5} more.")
        else:
            print(f"{GREEN}✅ Columns look aligned.{RESET}")

        if duplicates_id:
            print(f"{RED}❌ DUPLICATE IDs FOUND ({len(duplicates_id)}):{RESET}")
            for d in duplicates_id[:5]: print(f"   - {d}")
        else:
            print(f"{GREEN}✅ All IDs are unique.{RESET}")

        return student_ids, student_emails

    except Exception as e:
        print(f"{RED}❌ Error reading Students: {e}{RESET}")
        return set(), set()

def check_orders(sh, valid_student_ids):
    print(f"\n{YELLOW}--- 🕵️ CHECKING ORDERS SHEET ---{RESET}")
    try:
        ws = sh.worksheet("Orders")
        rows = ws.get_all_values()
        data = rows[1:]
        
        print(f"   Stats: Found {len(data)} orders.")
        
        # Assuming format: ID, Date, UID, Name, Class...
        # UID is usually Column C (index 2)
        uid_idx = 2 
        price_idx = 6 # Column G

        orphaned_orders = []
        bad_prices = []

        for r_num, row in enumerate(data, start=2):
            # Check Foreign Key (Does user exist?)
            if len(row) > uid_idx:
                uid = row[uid_idx].strip()
                # Skip check if UID is empty (sometimes happens in bad data)
                if uid and uid not in valid_student_ids:
                    orphaned_orders.append(f"Row {r_num} (UID: {uid})")
            
            # Check Price
            if len(row) > price_idx:
                price = row[price_idx]
                try:
                    float(price)
                except:
                    bad_prices.append(f"Row {r_num} (Price: '{price}')")

        # REPORT
        if orphaned_orders:
            print(f"{RED}❌ ORPHANED ORDERS DETECTED ({len(orphaned_orders)}):{RESET}")
            print(f"   (These orders belong to students who are NOT in the Students sheet)")
            for o in orphaned_orders[:5]: print(f"   - {o}")
            if len(orphaned_orders) > 5: print(f"   - ...and {len(orphaned_orders)-5} more.")
        else:
            print(f"{GREEN}✅ All orders linked to valid students.{RESET}")

        if bad_prices:
            print(f"{RED}❌ INVALID PRICES FOUND ({len(bad_prices)}):{RESET}")
            for p in bad_prices[:5]: print(f"   - {p}")
        else:
            print(f"{GREEN}✅ Price data looks numeric.{RESET}")

    except Exception as e:
        print(f"{RED}❌ Error reading Orders: {e}{RESET}")

def check_feedback(sh, valid_emails):
    print(f"\n{YELLOW}--- 🕵️ CHECKING FEEDBACK SHEET ---{RESET}")
    try:
        ws = sh.worksheet("Feedback")
        rows = ws.get_all_values()
        data = rows[1:]
        
        print(f"   Stats: Found {len(data)} feedbacks.")

        # Feedback: Name, Email, Message...
        email_idx = 1
        
        unknown_emails = []

        for r_num, row in enumerate(data, start=2):
            if len(row) > email_idx:
                email = row[email_idx].strip()
                if email and email not in valid_emails:
                    unknown_emails.append(f"Row {r_num} (Email: {email})")

        if unknown_emails:
            print(f"{YELLOW}⚠️  UNKNOWN EMAILS IN FEEDBACK ({len(unknown_emails)}):{RESET}")
            print(f"   (This might be okay if feedbacks are anonymous or from old users)")
            for u in unknown_emails[:5]: print(f"   - {u}")
        else:
            print(f"{GREEN}✅ All feedback emails match registered students.{RESET}")

    except Exception as e:
        print(f"{RED}❌ Error reading Feedback: {e}{RESET}")

def main():
    print(f"{YELLOW}--- 🚀 STARTING FULL SYSTEM DIAGNOSTIC ---{RESET}")
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)

    valid_ids, valid_emails = check_students(sh)
    
    if valid_ids:
        check_orders(sh, valid_ids)
    
    if valid_emails:
        check_feedback(sh, valid_emails)

    print(f"\n{YELLOW}--- 🏁 DIAGNOSTIC COMPLETE ---{RESET}")

if __name__ == "__main__":
    main()
