import os
import json
import gspread
import random
import time
import base64
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_TOTAL = 600
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- DATA ---
ITEMS = [
    ("Samosa", 15), ("Potato Patties", 30), ("Paneer Gravy Patties", 50),
    ("Sandwich", 30), ("Burger", 50), ("Paneer Roll", 50),
    ("Chilli Potato", 50), ("Pizza", 50)
]
NAMES = ["Rohan", "Kavita", "Arjun", "Zara", "Satyam", "Shivam", "Rahul", "Priya"]
CLASSES = ["9-A", "10-B", "11-A", "12-C"]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    print("--- 🚀 STARTING UP TO 600 ORDERS ---")
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")
    
    existing = ws_orders.get_all_values()
    current_count = max(0, len(existing) - 1)
    
    needed = TARGET_TOTAL - current_count
    
    if needed <= 0:
        print(f"✅ You already have {current_count} orders (Target: {TARGET_TOTAL}).")
        return

    # Determine last ID
    last_id = 0
    if current_count > 0:
        try:
            last_id = int(existing[-1][0])
        except:
            last_id = current_count

    print(f"⚡ Adding {needed} orders starting from ID {last_id + 1}...")
    
    new_orders = []
    new_students = []
    current_id = last_id + 1
    
    for _ in range(needed):
        # Create Student
        name = random.choice(NAMES)
        uid = str(random.randint(20000, 80000))
        new_students.append([uid, name, random.choice(CLASSES), "1234", "500", ""])
        
        # Create Order
        picks = random.sample(ITEMS, k=1)
        desc = f"{picks[0][0]} x 1"
        cost = picks[0][1]
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        new_orders.append([current_id, date_str, uid, name, "Student", desc, cost, "Pending"])
        current_id += 1

    ws_students.append_rows(new_students, value_input_option='USER_ENTERED')
    ws_orders.append_rows(new_orders, value_input_option='USER_ENTERED')
    print(f"🎉 SUCCESS! Total orders: {TARGET_TOTAL}")

if __name__ == "__main__":
    main()
