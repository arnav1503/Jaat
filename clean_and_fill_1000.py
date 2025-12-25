import os
import json
import gspread
import random
import base64
import itertools
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_TOTAL = 1000
KEEP_REAL_ORDERS = 194
KEEP_REAL_STUDENTS = 104

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- EXPANDED NAME POOLS (Ensures >1000 Unique Combinations) ---
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayan", "Krishna", "Ishaan", 
    "Shaurya", "Atharv", "Rohan", "Rahul", "Amit", "Vikram", "Siddharth", "Kabir", "Dhruv", "Rishabh", 
    "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Kiara", "Myra", "Riya", "Anya", "Sarah", 
    "Kavita", "Zara", "Priya", "Nisha", "Meera", "Isha", "Pooja", "Neha", "Simran", "Tanvi",
    "Dev", "Yash", "Uday", "Bhavya", "Chetan", "Gaurav", "Hardik", "Imran", "Jatin", "Kunal",
    "Laksh", "Manish", "Naveen", "Om", "Pranav", "Qasim", "Rajat", "Samir", "Tushar", "Utkarsh",
    "Akash", "Bhuvan", "Chirag", "Deepak", "Eshan", "Faizan", "Girish", "Hemant", "Inder", "Jay"
]
LAST_NAMES = [
    "Kumar", "Singh", "Sharma", "Verma", "Gupta", "Malhotra", "Bhatia", "Saxena", "Mehta", "Jain", 
    "Agarwal", "Chopra", "Deshmukh", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Gill", "Sethi", 
    "Joshi", "Rawat", "Yadav", "Mishra", "Pandey", "Kaushik", "Thakur", "Chauhan", "Bisht", "Negi",
    "Sood", "Dutt", "Bakshi", "Khurana", "Garg", "Bansal", "Mittall", "Goel", "Rana", "Dewan",
    "Soni", "Kohli", "Wadhwa", "Mahajan", "Oberoi", "Sarin", "Puri", "Bahl", "Talwar", "Duggal"
]

CLASSES = ["9-A", "9-B", "10-A", "10-B", "11-A", "11-B", "11-C", "12-A", "12-B", "12-C"]
ITEMS = [("Samosa", 15), ("Potato Patties", 30), ("Paneer Gravy Patties", 50), ("Sandwich", 30), ("Burger", 50), ("Paneer Roll", 50), ("Pasta Roll", 50), ("Chilli Potato", 50), ("Pizza", 50), ("Chips (Medium)", 20), ("Veg Noodles", 50)]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    print("--- 🧹 STEP 1: CLEANING UP BAD DATA ---")
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")

    # 1. Truncate Sheets to safe limits
    # We add 1 to keep the header row
    print(f"   - Keeping first {KEEP_REAL_ORDERS} Orders. Deleting the rest...")
    ws_orders.resize(rows=KEEP_REAL_ORDERS + 1)
    
    print(f"   - Keeping first {KEEP_REAL_STUDENTS} Students. Deleting the rest...")
    ws_students.resize(rows=KEEP_REAL_STUDENTS + 1)
    
    print("✅ Cleanup Complete. Starting Generation...")

    # 2. Calculate needed rows
    needed = TARGET_TOTAL - KEEP_REAL_ORDERS
    print(f"--- ⚡ STEP 2: GENERATING {needed} UNIQUE ENTRIES ---")

    # 3. Create Unique Name Combinations
    # itertools.product creates EVERY possible combination (no duplicates)
    all_combos = list(itertools.product(FIRST_NAMES, LAST_NAMES))
    unique_names_list = [f"{f} {l}" for f, l in all_combos]
    random.shuffle(unique_names_list)
    
    # Slice exactly what we need
    selected_names = unique_names_list[:needed]
    
    new_orders = []
    new_students = []
    current_id = KEEP_REAL_ORDERS + 1
    
    for full_name in selected_names:
        uid = str(random.randint(10000, 99999))
        cls = random.choice(CLASSES)
        
        # --- STUDENT (Corrected Columns) ---
        # Col A: Empty | Col B: UID | Col C: Name | Col D: Password | Col E: Email | Col F: Class
        new_students.append([
            "",                     
            uid,                    
            full_name,              
            "1234",                 
            f"s.{uid}@slps.org",    
            cls                     
        ])
        
        # --- ORDER ---
        picks = random.sample(ITEMS, k=random.randint(1, 2))
        item_parts = []
        cost = 0
        for p in picks:
            qty = random.randint(1, 2)
            item_parts.append(f"{p[0]} x {qty}")
            cost += (p[1] * qty)
        desc = ", ".join(item_parts)
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # --- STATUS ---
        status = "Pending"
        
        new_orders.append([current_id, date_str, uid, full_name, cls, desc, cost, status])
        current_id += 1

    # 4. Upload
    print("📤 Uploading new data...")
    if new_students:
        ws_students.append_rows(new_students, value_input_option='USER_ENTERED')
    if new_orders:
        ws_orders.append_rows(new_orders, value_input_option='USER_ENTERED')
    
    print(f"🎉 SUCCESS! \n   - Cleaned back to ID {KEEP_REAL_ORDERS}\n   - Filled up to ID {TARGET_TOTAL}\n   - All Names Unique\n   - All Statuses Pending")

if __name__ == "__main__":
    main()
