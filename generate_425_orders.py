import os
import json
import gspread
import random
import base64
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
TARGET_TOTAL = 425
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- DATA POOLS ---
ITEMS = [
    ("Veg Burger", 50), ("Cheese Pizza", 120), ("Coke", 40), 
    ("Sandwich", 60), ("Fried Rice", 90), ("Pasta", 100),
    ("Samosa", 15), ("Chilli Potato", 140), ("Chips", 20)
]
NAMES = ["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Rohan", "Kavita", "Arjun", "Zara", "Satyam", "Shivam"]
CLASSES = ["10-A", "10-B", "11-A", "11-B", "12-C", "9-B", "Teacher"]

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
    ws = sh.worksheet("Orders")
    
    # 1. Get current data
    data = ws.get_all_values()
    # Filter empty rows
    data = [row for row in data if any(row)]
    
    # Header is row 1, so data count is len - 1
    current_count = max(0, len(data) - 1)
    print(f"Current Orders: {current_count}")
    
    needed = TARGET_TOTAL - current_count
    if needed <= 0:
        print(f"✅ You already have {current_count} orders (Target: {TARGET_TOTAL}).")
        return

    # 2. Determine the next Order ID
    # We look at the last row's first column. 
    # If it's a number, we use it. If it's a date/text (old format), we use row count.
    last_id = 0
    if current_count > 0:
        last_row = data[-1]
        try:
            last_id = int(last_row[0])
        except:
            # If the last row has a Date in Col A, we default to the row count
            last_id = current_count

    print(f"⚡ Generating {needed} new 'Pending' orders starting from ID {last_id + 1}...")
    
    new_rows = []
    current_id = last_id + 1
    
    for _ in range(needed):
        # 1. Order ID
        order_id = current_id
        
        # 2. Date
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 3. User Details
        name = random.choice(NAMES)
        cls = random.choice(CLASSES)
        uid = str(random.randint(100, 9999))
        
        # 4. Food Items
        picks = random.sample(ITEMS, k=random.randint(1, 3))
        # Format: "Veg Burger x 1, Coke x 2"
        item_parts = []
        cost = 0
        for p in picks:
            qty = random.randint(1, 2)
            item_parts.append(f"{p[0]} x {qty}")
            cost += (p[1] * qty)
        desc = ", ".join(item_parts)
        
        # 5. Status (Requested: Pending)
        status = "Pending"

        # CORRECT COLUMN ORDER: [ID, Date, UserID, Name, Class, Items, Price, Status]
        new_rows.append([order_id, date_str, uid, name, cls, desc, cost, status])
        
        current_id += 1

    print("--- UPLOADING DATA ---")
    ws.append_rows(new_rows, value_input_option='USER_ENTERED')
    print(f"✅ SUCCESS! Added {needed} orders. Total is now {TARGET_TOTAL}.")

if __name__ == "__main__":
    main()
