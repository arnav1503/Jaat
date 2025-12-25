import os
import json
import gspread
import random
import base64
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_ORDER_TOTAL = 600  # Total orders we want in the end
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- DATA POOLS ---
FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayan", "Krishna", "Ishaan", "Shaurya", "Atharv", "Rohan", "Rahul", "Amit", "Vikram", "Siddharth", "Kabir", "Dhruv", "Rishabh", "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Kiara", "Myra", "Riya", "Anya", "Sarah", "Kavita", "Zara", "Priya", "Nisha", "Meera", "Isha", "Pooja", "Neha", "Simran", "Tanvi"]
LAST_NAMES = ["Kumar", "Singh", "Sharma", "Verma", "Gupta", "Malhotra", "Bhatia", "Saxena", "Mehta", "Jain", "Agarwal", "Chopra", "Deshmukh", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Gill", "Sethi", "Joshi", "Rawat", "Yadav", "Mishra", "Pandey"]
CLASSES = ["9-A", "9-B", "10-A", "10-B", "11-A", "11-B", "11-C", "12-A", "12-B", "12-C"]

ITEMS = [("Samosa", 15), ("Potato Patties", 30), ("Paneer Gravy Patties", 50), ("Sandwich", 30), ("Burger", 50), ("Paneer Roll", 50), ("Pasta Roll", 50), ("Chilli Potato", 50), ("Pizza", 50), ("Chips (Medium)", 20), ("Veg Noodles", 50)]

STATUS_OPTIONS = ["Delivered", "Ready", "Pending", "Cancelled"]
STATUS_WEIGHTS = [70, 15, 10, 5]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    print("--- ➕ STARTING SAFE APPEND MODE ---")
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")

    # 1. CHECK EXISTING DATA
    print("🔍 Analyzing existing data...")
    existing_orders = ws_orders.get_all_values()
    existing_students = ws_students.get_all_values()
    
    # Subtract 1 for header
    current_order_count = max(0, len(existing_orders) - 1)
    current_student_count = max(0, len(existing_students) - 1)
    
    print(f"   - Found {current_order_count} existing orders.")
    print(f"   - Found {current_student_count} existing students.")

    # 2. CALCULATE WHAT IS NEEDED
    needed = TARGET_ORDER_TOTAL - current_order_count
    
    if needed <= 0:
        print(f"✅ Target reached! You have {current_order_count} orders (Target: {TARGET_ORDER_TOTAL}). Exiting.")
        return

    # Find the last used ID to continue numbering correctly
    try:
        last_id = int(existing_orders[-1][0]) # ID from last row
    except:
        last_id = current_order_count

    print(f"⚡ Generating {needed} NEW orders (Starting from ID {last_id + 1})...")

    # 3. GENERATE NEW CONTENT
    # Create unique name pool
    all_names = [f"{f} {l}" for f in FIRST_NAMES for l in LAST_NAMES]
    random.shuffle(all_names)
    # Ensure we pick names not likely to collide, but for 600 total it's safe
    selected_names = all_names[:needed]
    
    new_orders = []
    new_students = []
    current_id = last_id + 1
    
    for full_name in selected_names:
        uid = str(random.randint(10000, 99999))
        cls = random.choice(CLASSES)
        
        # Add Student
        new_students.append([uid, full_name, cls, "1234", "500", ""])
        
        # Add Order
        picks = random.sample(ITEMS, k=random.randint(1, 2))
        item_parts = []
        cost = 0
        for p in picks:
            qty = random.randint(1, 2)
            item_parts.append(f"{p[0]} x {qty}")
            cost += (p[1] * qty)
        desc = ", ".join(item_parts)
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        status = random.choices(STATUS_OPTIONS, weights=STATUS_WEIGHTS, k=1)[0]
        
        new_orders.append([current_id, date_str, uid, full_name, cls, desc, cost, status])
        current_id += 1

    # 4. APPEND ONLY (DO NOT CLEAR)
    print("📤 Appending new data to the bottom of the sheets...")
    
    if new_students:
        ws_students.append_rows(new_students, value_input_option='USER_ENTERED')
    
    if new_orders:
        ws_orders.append_rows(new_orders, value_input_option='USER_ENTERED')
    
    print("🎉 SUCCESS!")
    print(f"   - Added {len(new_orders)} new orders.")
    print(f"   - Total Orders in Sheet: {current_order_count + len(new_orders)}")
    print(f"   - Original {current_order_count} orders were PRESERVED.")

if __name__ == "__main__":
    main()
