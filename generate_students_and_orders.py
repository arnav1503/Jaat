import os
import json
import gspread
import random
import base64
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
TARGET_TOTAL_ORDERS = 425
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- DATA POOLS ---
# 1. Real Menu (No Sold Out items)
ITEMS = [
    ("Samosa", 15), ("Potato Patties", 30), ("Paneer Gravy Patties", 50),
    ("Sandwich", 30), ("Burger", 50), ("Paneer Roll", 50),
    ("Pasta Roll", 50), ("Chips (Small)", 10), ("Chips (Medium)", 20),
    ("Chips (Large)", 50), ("Chilli Potato", 50), ("Pizza", 50)
]

# 2. Student Data (NO TEACHERS)
NAMES = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayan", 
         "Krishna", "Ishaan", "Shaurya", "Atharv", "Diya", "Saanvi", "Ananya", 
         "Aadhya", "Pari", "Kiara", "Myra", "Riya", "Anya", "Sarah"]
CLASSES = ["9-A", "9-B", "10-A", "10-B", "11-A", "11-B", "12-A", "12-B", "12-C"]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    print("--- CONNECTING TO SHEETS ---")
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")
    
    # 1. Check current Order count
    order_data = ws_orders.get_all_values()
    # Subtract header
    current_order_count = max(0, len(order_data) - 1)
    
    needed = TARGET_TOTAL_ORDERS - current_order_count
    
    if needed <= 0:
        print(f"✅ You already have {current_order_count} orders (Target: {TARGET_TOTAL_ORDERS}).")
        return

    # 2. Determine next Order ID
    last_order_id = 0
    if current_order_count > 0:
        try:
            # Try to grab the ID from the last row (Column A)
            last_order_id = int(order_data[-1][0])
        except:
            last_order_id = current_order_count

    print(f"⚡ Generating {needed} new Students AND Orders...")
    
    new_orders = []
    new_students = []
    
    current_order_id = last_order_id + 1
    
    # Track used IDs to avoid duplicates in this batch
    used_ids = set()

    for _ in range(needed):
        # --- A. CREATE USER ---
        name = random.choice(NAMES) + " " + random.choice(["Kumar", "Singh", "Sharma", "Verma", "Gupta"])
        cls = random.choice(CLASSES)
        
        # Generate unique User ID (4-5 digits)
        while True:
            uid = str(random.randint(1000, 99999))
            if uid not in used_ids:
                used_ids.add(uid)
                break
        
        password = "1234"  # Default password
        balance = "500"    # Default balance
        photo = ""         # Empty photo
        
        # Student Sheet Columns: [UserID, Name, Class, Password, Balance, Photo]
        new_students.append([uid, name, cls, password, balance, photo])

        # --- B. CREATE ORDER ---
        # Date
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Food Items
        picks = random.sample(ITEMS, k=random.randint(1, 3))
        item_parts = []
        cost = 0
        for p in picks:
            qty = random.randint(1, 2)
            item_parts.append(f"{p[0]} x {qty}")
            cost += (p[1] * qty)
        desc = ", ".join(item_parts)
        status = "Pending"

        # Order Sheet Columns: [OrderID, Date, UserID, Name, Class, Items, Price, Status]
        new_orders.append([current_order_id, date_str, uid, name, cls, desc, cost, status])
        
        current_order_id += 1

    # 3. Upload Data
    print(f"📝 Adding {len(new_students)} rows to 'Students' sheet...")
    ws_students.append_rows(new_students, value_input_option='USER_ENTERED')
    
    print(f"🛒 Adding {len(new_orders)} rows to 'Orders' sheet...")
    ws_orders.append_rows(new_orders, value_input_option='USER_ENTERED')
    
    print(f"✅ SUCCESS! Generated {needed} orders and registered corresponding students.")

if __name__ == "__main__":
    main()
