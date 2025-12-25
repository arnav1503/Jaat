import os
import json
import gspread
import random
import base64
import itertools
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_TOTAL = 1000
KEEP_REAL_ORDERS = 194
KEEP_REAL_STUDENTS = 104

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- NAMES ---
FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayan", "Krishna", "Ishaan", "Shaurya", "Atharv", "Rohan", "Rahul", "Amit", "Vikram", "Siddharth", "Kabir", "Dhruv", "Rishabh", "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Kiara", "Myra", "Riya", "Anya", "Sarah", "Kavita", "Zara", "Priya", "Nisha", "Meera", "Isha", "Pooja", "Neha", "Simran", "Tanvi", "Dev", "Yash", "Uday", "Bhavya", "Chetan", "Gaurav", "Hardik", "Imran", "Jatin", "Kunal", "Laksh", "Manish", "Naveen", "Om", "Pranav", "Qasim", "Rajat", "Samir", "Tushar", "Utkarsh"]
LAST_NAMES = ["Kumar", "Singh", "Sharma", "Verma", "Gupta", "Malhotra", "Bhatia", "Saxena", "Mehta", "Jain", "Agarwal", "Chopra", "Deshmukh", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Gill", "Sethi", "Joshi", "Rawat", "Yadav", "Mishra", "Pandey", "Kaushik", "Thakur", "Chauhan", "Bisht", "Negi", "Sood", "Dutt", "Bakshi", "Khurana", "Garg", "Bansal", "Mittall", "Goel", "Rana", "Dewan", "Soni", "Kohli", "Wadhwa"]

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
    print("--- 🟢 SCRIPT STARTED ---", flush=True)
    client = get_client()
    print("--- 📡 CONNECTED TO GOOGLE ---", flush=True)
    
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")

    # --- STEP 1: CLEANUP ---
    print(f"--- 🧹 CLEANING DATA (Keeping top {KEEP_REAL_ORDERS} Orders) ---", flush=True)
    
    # Resize Orders
    current_rows = len(ws_orders.get_all_values())
    if current_rows > KEEP_REAL_ORDERS + 1:
        print(f"   Deleting {current_rows - (KEEP_REAL_ORDERS + 1)} bad order rows...", flush=True)
        ws_orders.resize(rows=KEEP_REAL_ORDERS + 1)
    else:
        print("   Orders sheet already clean.", flush=True)

    # Resize Students
    current_stu_rows = len(ws_students.get_all_values())
    if current_stu_rows > KEEP_REAL_STUDENTS + 1:
        print(f"   Deleting {current_stu_rows - (KEEP_REAL_STUDENTS + 1)} bad student rows...", flush=True)
        ws_students.resize(rows=KEEP_REAL_STUDENTS + 1)
    else:
        print("   Students sheet already clean.", flush=True)

    # --- STEP 2: GENERATION ---
    needed = TARGET_TOTAL - KEEP_REAL_ORDERS
    print(f"--- ⚡ GENERATING {needed} NEW ENTRIES IN MEMORY ---", flush=True)

    all_combos = list(itertools.product(FIRST_NAMES, LAST_NAMES))
    unique_names_list = [f"{f} {l}" for f, l in all_combos]
    random.shuffle(unique_names_list)
    selected_names = unique_names_list[:needed]
    
    new_orders = []
    new_students = []
    current_id = KEEP_REAL_ORDERS + 1
    
    for full_name in selected_names:
        uid = str(random.randint(10000, 99999))
        cls = random.choice(CLASSES)
        
        # Student (Aligned Columns)
        new_students.append(["", uid, full_name, "1234", f"s.{uid}@slps.org", cls])
        
        # Order
        picks = random.sample(ITEMS, k=random.randint(1, 2))
        item_parts = []
        cost = 0
        for p in picks:
            qty = random.randint(1, 2)
            item_parts.append(f"{p[0]} x {qty}")
            cost += (p[1] * qty)
        
        new_orders.append([
            current_id, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
            uid, full_name, cls, ", ".join(item_parts), cost, "Pending"
        ])
        current_id += 1

    # --- STEP 3: BATCH UPLOAD ---
    print("--- 📤 STARTING UPLOAD (In Batches of 100) ---", flush=True)
    
    def batch_upload(worksheet, data, name):
        total = len(data)
        batch_size = 100
        for i in range(0, total, batch_size):
            batch = data[i:i + batch_size]
            print(f"   Uploading {name}: rows {i+1} to {min(i+batch_size, total)}...", flush=True)
            worksheet.append_rows(batch, value_input_option='USER_ENTERED')
            time.sleep(1) # Tiny pause to be nice to API
    
    if new_students:
        batch_upload(ws_students, new_students, "Students")
        
    if new_orders:
        batch_upload(ws_orders, new_orders, "Orders")
    
    print("\n✅ SUCCESS! Process Complete.", flush=True)
    print(f"   - Total Orders: {TARGET_TOTAL}", flush=True)

if __name__ == "__main__":
    main()
