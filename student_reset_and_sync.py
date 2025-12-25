import os
import json
import gspread
import random
import base64
import time
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# --- SETTINGS ---
TARGET_ORDERS = 525
SAFE_ORDERS = 129
TARGET_STUDENTS = 550
STUDENT_RESET_LIMIT = 200

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- DATA POOL ---
FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayan", "Krishna", "Ishaan", "Shaurya", "Atharv", "Rohan", "Rahul", "Amit", "Vikram", "Kabir", "Dhruv", "Rishabh", "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Kiara", "Myra", "Riya", "Anya", "Sarah", "Kavita", "Zara", "Priya", "Nisha", "Meera", "Isha", "Pooja", "Neha", "Simran", "Tanvi", "Dev", "Yash", "Uday", "Bhavya", "Chetan", "Gaurav", "Hardik", "Imran", "Jatin", "Kunal", "Laksh", "Manish", "Naveen", "Om", "Pranav", "Rajat", "Samir", "Tushar", "Utkarsh"]
LAST_NAMES = ["Kumar", "Singh", "Sharma", "Verma", "Gupta", "Malhotra", "Bhatia", "Saxena", "Mehta", "Jain", "Agarwal", "Chopra", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Gill", "Sethi", "Joshi", "Yadav", "Mishra", "Pandey", "Chauhan", "Garg", "Bansal"]
ITEMS = [("Samosa", 15), ("Potato Patties", 30), ("Paneer Gravy Patties", 50), ("Sandwich", 30), ("Burger", 50), ("Paneer Roll", 50), ("Chilli Potato", 50), ("Pizza", 50), ("Veg Noodles", 50)]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    
    # 1. PROCESS STUDENTS
    print("--- 👨‍🎓 PROCESSING STUDENTS ---")
    ws_stu = sh.worksheet("Students")
    all_stu_rows = ws_stu.get_all_values()
    headers = all_stu_rows[0]
    
    # If more than 550, keep only first 200 (+ header)
    if len(all_stu_rows) > (TARGET_STUDENTS + 1):
        print(f"   ⚠️ Count is {len(all_stu_rows)-1}. Resetting to first {STUDENT_RESET_LIMIT}...")
        kept_rows = all_stu_rows[:STUDENT_RESET_LIMIT + 1]
    else:
        kept_rows = all_stu_rows

    student_pool = []
    # Index detection
    try:
        id_idx = [i for i, h in enumerate(headers) if "userid" in h.lower()][0]
        name_idx = [i for i, h in enumerate(headers) if "name" in h.lower()][0]
        class_idx = [i for i, h in enumerate(headers) if "class" in h.lower()][0]
    except:
        id_idx, name_idx, class_idx = 1, 2, 5

    # Prepare pool from kept rows
    for row in kept_rows[1:]:
        student_pool.append({"uid": row[id_idx], "name": row[name_idx], "class": row[class_idx], "row": row})

    # Fill the gap to 550
    print(f"   Filling gap: {len(student_pool)} -> {TARGET_STUDENTS}")
    while len(student_pool) < TARGET_STUDENTS:
        p1, p2 = random.randint(10, 25), random.randint(100, 999)
        adm = f"{p1}/{p2}"
        email = f"s.{p1}.{p2}@slps.one"
        uid = f"STU{p2}{p1}"
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        
        if random.random() < 0.4:
            cls_str = f"{random.choice([4, 5])}-{random.choice(['Green', 'Blue', 'Orange', 'Purple'])}"
        else:
            cls_str = f"{random.choice([6, 7, 8, 9])}-{random.choice(['A', 'B', 'C', 'D'])}"
        
        new_row = [adm, uid, name, "1234", email, cls_str]
        while len(new_row) < len(headers): new_row.append("")
        student_pool.append({"uid": uid, "name": name, "class": cls_str, "row": new_row})

    ws_stu.clear()
    ws_stu.update([headers] + [s['row'] for s in student_pool], value_input_option='USER_ENTERED')
    print(f"✅ Students synced at {TARGET_STUDENTS}.")

    # 2. PROCESS ORDERS
    print(f"--- 🍔 CLEANING ORDERS (Safe: {SAFE_ORDERS}) ---")
    ws_ord = sh.worksheet("Orders")
    all_ord_rows = ws_ord.get_all_values()
    ord_headers = all_ord_rows[0]
    safe_orders = all_ord_rows[1:SAFE_ORDERS+1]
    
    final_orders = [ord_headers] + safe_orders
    needed_orders = TARGET_ORDERS - len(safe_orders)
    
    start_id = SAFE_ORDERS + 1
    for i in range(needed_orders):
        s = random.choice(student_pool)
        item, price = random.choice(ITEMS)
        dt = (datetime.now() - timedelta(days=random.randint(0,10))).strftime('%Y-%m-%d %H:%M:%S')
        final_orders.append([start_id + i, dt, s['uid'], s['name'], s['class'], f"{item} x 1", price, "Pending"])

    ws_ord.clear()
    for i in range(0, len(final_orders), 100):
        ws_ord.append_rows(final_orders[i:i+100], value_input_option='USER_ENTERED')
        time.sleep(1)
        
    print(f"✅ Orders synced at {TARGET_ORDERS}.")

if __name__ == "__main__":
    main()
