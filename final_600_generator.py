import os
import json
import gspread
import random
import base64
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_TOTAL = 600  # We want exactly 600 orders for now
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- REAL MENU ---
ITEMS = [
    ("Samosa", 15), ("Potato Patties", 30), ("Paneer Gravy Patties", 50),
    ("Sandwich", 30), ("Burger", 50), ("Paneer Roll", 50),
    ("Chilli Potato", 50), ("Pizza", 50), ("Chips (Medium)", 20)
]
NAMES = ["Rohan", "Kavita", "Arjun", "Zara", "Satyam", "Shivam", "Rahul", "Priya", "Amit", "Sneha"]
CLASSES = ["9-A", "10-B", "11-A", "12-C", "11-B"]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    print("--- 🚀 STARTING ORDER GENERATION (TARGET: 600) ---")
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")
    
    # 1. Check current progress
    existing = ws_orders.get_all_values()
    current_count = max(0, len(existing) - 1) # Exclude header
    
    needed = TARGET_TOTAL - current_count
    
    if needed <= 0:
        print(f"✅ You already have {current_count} orders. No more needed.")
        return

    # 2. Find the last Order ID used
    last_id = 0
    if current_count > 0:
        try:
            # Grab ID from the last row, Column A
            last_id = int(existing[-1][0])
        except:
            last_id = current_count

    print(f"⚡ Generating {needed} new orders starting from ID {last_id + 1}...")
    
    new_orders = []
    new_students = []
    current_id = last_id + 1
    
    for _ in range(needed):
        # A. Create a Student Identity
        name = random.choice(NAMES) + " " + random.choice(["Singh", "Sharma", "Verma"])
        uid = str(random.randint(10000, 99999))
        user_class = random.choice(CLASSES)
        
        # Add to Students list [ID, Name, Class, Pass, Bal, Photo]
        new_students.append([uid, name, user_class, "1234", "500", ""])
        
        # B. Create the Order
        picks = random.sample(ITEMS, k=random.randint(1, 2))
        item_parts = []
        cost = 0
        for p in picks:
            qty = random.randint(1, 2)
            item_parts.append(f"{p[0]} x {qty}")
            cost += (p[1] * qty)
        desc = ", ".join(item_parts)
        
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Add to Orders list [ID, Date, UserID, Name, Class, Items, Price, Status]
        new_orders.append([current_id, date_str, uid, name, user_class, desc, cost, "Pending"])
        current_id += 1

    # 3. Upload in one go
    print("📝 Uploading Students...")
    ws_students.append_rows(new_students, value_input_option='USER_ENTERED')
    
    print("🛒 Uploading Orders...")
    ws_orders.append_rows(new_orders, value_input_option='USER_ENTERED')
    
    print(f"🎉 SUCCESS! Added {needed} orders. Total orders: {TARGET_TOTAL}")

if __name__ == "__main__":
    main()
