import os
import json
import gspread
import random
import base64
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_TOTAL = 600
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- DATA POOLS (Designed for Max Combinations) ---
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayan", "Krishna", "Ishaan",
    "Shaurya", "Atharv", "Rohan", "Rahul", "Amit", "Vikram", "Siddharth", "Kabir", "Dhruv", "Rishabh",
    "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Kiara", "Myra", "Riya", "Anya", "Sarah",
    "Kavita", "Zara", "Priya", "Nisha", "Meera", "Isha", "Pooja", "Neha", "Simran", "Tanvi"
]

LAST_NAMES = [
    "Kumar", "Singh", "Sharma", "Verma", "Gupta", "Malhotra", "Bhatia", "Saxena", "Mehta", "Jain",
    "Agarwal", "Chopra", "Deshmukh", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Gill", "Sethi",
    "Joshi", "Rawat", "Yadav", "Mishra", "Pandey"
]

CLASSES = ["9-A", "9-B", "10-A", "10-B", "11-A", "11-B", "11-C", "12-A", "12-B", "12-C"]

ITEMS = [
    ("Samosa", 15), ("Potato Patties", 30), ("Paneer Gravy Patties", 50),
    ("Sandwich", 30), ("Burger", 50), ("Paneer Roll", 50),
    ("Pasta Roll", 50), ("Chilli Potato", 50), ("Pizza", 50), 
    ("Chips (Medium)", 20), ("Veg Noodles", 50)
]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    print("--- 🚀 STARTING SCRIPT ---")
    client = get_client()
    print("--- 📡 CONNECTING TO GOOGLE ---")
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")

    # 1. Clear Sheets
    print("--- 🧹 CLEARING OLD DATA (Please wait...) ---")
    ws_orders.clear()
    ws_orders.append_row(["Order ID", "Date", "User ID", "Name", "Class", "Items", "Price", "Status"])
    
    ws_students.clear()
    ws_students.append_row(["User ID", "Name", "Class", "Password", "Balance", "Photo"])

    # 2. Generate Names
    print("--- ⚡ GENERATING UNIQUE NAMES ---")
    all_possible_names = [f"{f} {l}" for f in FIRST_NAMES for l in LAST_NAMES]
    random.shuffle(all_possible_names)
    selected_names = all_possible_names[:TARGET_TOTAL]

    print(f"--- 📦 BUILDING {len(selected_names)} ORDERS IN MEMORY ---")
    
    new_orders = []
    new_students = []
    current_id = 1
    
    for full_name in selected_names:
        uid = str(random.randint(10000, 99999))
        cls = random.choice(CLASSES)
        
        # Student
        new_students.append([uid, full_name, cls, "1234", "500", ""])
        
        # Order
        picks = random.sample(ITEMS, k=random.randint(1, 2))
        item_parts = []
        cost = 0
        for p in picks:
            qty = random.randint(1, 2)
            item_parts.append(f"{p[0]} x {qty}")
            cost += (p[1] * qty)
        desc = ", ".join(item_parts)
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        new_orders.append([current_id, date_str, uid, full_name, cls, desc, cost, "Pending"])
        current_id += 1

    # 3. Upload
    print("--- 📤 UPLOADING TO GOOGLE SHEETS (This takes ~10 seconds) ---")
    ws_students.append_rows(new_students, value_input_option='USER_ENTERED')
    ws_orders.append_rows(new_orders, value_input_option='USER_ENTERED')
    
    print("\n✅ DONE! 600 Unique Orders Generated!")
    print(f"Total Names Used: {len(selected_names)}")

if __name__ == "__main__":
    main()
