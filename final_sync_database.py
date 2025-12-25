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

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- DATA POOL FOR NEW STUDENTS ---
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
    
    # 1. READ & UPDATE STUDENTS
    print("--- 👨‍🎓 PROCESSING STUDENTS (Keeping existing + adding new) ---")
    ws_stu = sh.worksheet("Students")
    existing_rows = ws_stu.get_all_values()
    stu_headers = existing_rows[0]
    
    # Extract existing student data into objects
    student_pool = []
    # Identify column indices
    try:
        id_idx = [i for i, h in enumerate(stu_headers) if "userid" in h.lower()][0]
        name_idx = [i for i, h in enumerate(stu_headers) if "name" in h.lower()][0]
        class_idx = [i for i, h in enumerate(stu_headers) if "class" in h.lower()][0]
    except:
        id_idx, name_idx, class_idx = 1, 2, 5

    for row in existing_rows[1:]:
        if len(row) > max(id_idx, name_idx, class_idx):
            student_pool.append({
                "uid": row[id_idx],
                "name": row[name_idx],
                "class": row[class_idx],
                "full_row": row
            })

    print(f"   Existing students found: {len(student_pool)}")
    
    # Add new students until we hit 550
    added_count = 0
    while len(student_pool) < TARGET_STUDENTS:
        p1, p2 = random.randint(10, 25), random.randint(100, 999)
        adm_id = f"{p1}/{p2}"
        email = f"s.{p1}.{p2}@slps.one"
        uid = f"STU{p2}{p1}"
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        
        if random.random() < 0.4:
            cls_str = f"{random.choice([4, 5])}-{random.choice(['Green', 'Blue', 'Orange', 'Purple'])}"
        else:
            cls_str = f"{random.choice([6, 7, 8, 9])}-{random.choice(['A', 'B', 'C', 'D'])}"
        
        # Construct the row to match headers (admissionId, userId, name, password, email, className...)
        new_row = [adm_id, uid, name, "1234", email, cls_str]
        # Pad row if headers are longer
        while len(new_row) < len(stu_headers): new_row.append("")
        
        student_pool.append({"uid": uid, "name": name, "class": cls_str, "full_row": new_row})
        added_count += 1

    # Upload updated student list
    ws_stu.clear()
    ws_stu.update([stu_headers] + [s['full_row'] for s in student_pool], value_input_option='USER_ENTERED')
    print(f"✅ Students sheet synced. Total: {len(student_pool)} ({added_count} new added).")

    # 2. UPDATE ORDERS
    print(f"--- 🍔 CLEANING ORDERS (Safe: {SAFE_ORDERS}) AND FILLING TO {TARGET_ORDERS} ---")
    ws_ord = sh.worksheet("Orders")
    all_orders = ws_ord.get_all_values()
    ord_headers = all_orders[0]
    safe_data = all_orders[1:SAFE_ORDERS+1] 
    
    current_orders = [ord_headers] + safe_data
    needed = TARGET_ORDERS - len(safe_data)
    
    start_id = SAFE_ORDERS + 1
    for i in range(needed):
        student = random.choice(student_pool)
        item, price = random.choice(ITEMS)
        date = (datetime.now() - timedelta(days=random.randint(0,10))).strftime('%Y-%m-%d %H:%M:%S')
        
        # orderId, timestamp, userId, userName, userClass, items, totalPrice, status
        current_orders.append([start_id + i, date, student['uid'], student['name'], student['class'], f"{item} x 1", price, "Pending"])

    ws_ord.clear()
    for i in range(0, len(current_orders), 100):
        ws_ord.append_rows(current_orders[i:i+100], value_input_option='USER_ENTERED')
        time.sleep(1)
        
    print(f"✅ Orders updated. Total: {len(current_orders)-1}")

if __name__ == "__main__":
    main()
