import os
import json
import gspread
import random
import base64
import itertools
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
TARGET_TOTAL = 1034       # The final number you want
KEEP_REAL_ORDERS = 194    # Keep these original orders
KEEP_REAL_STUDENTS = 104  # Keep these original students

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- DATA POOLS ---
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
    print("--- 🚀 STARTING REPAIR JOB (Target: 1034) ---", flush=True)
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_orders = sh.worksheet("Orders")
    ws_students = sh.worksheet("Students")

    # --- 1. CLEANUP PHASE ---
    print(f"--- ✂️  TRUNCATING DATA (Keeping {KEEP_REAL_ORDERS} Orders) ---", flush=True)
    
    # Resize Orders Sheet (Deletes everything after row 195)
    ws_orders.resize(rows=KEEP_REAL_ORDERS + 1)
    
    # Resize Students Sheet (Deletes everything after row 105)
    ws_students.resize(rows=KEEP_REAL_STUDENTS + 1)
    
    print("✅ Cleanup Done. Old bad data is gone.", flush=True)

    # --- 2. GENERATION PHASE ---
    needed = TARGET_TOTAL - KEEP_REAL_ORDERS
    print(f"--- ⚡ GENERATING {needed} NEW ROWS ---", flush=True)

    # Unique Name Logic
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
        
        # Student Row (Aligned to your screenshot: Empty, UID, Name, Pass, Email, Class)
        new_students.append(["", uid, full_name, "1234", f"s.{uid}@slps.org", cls])
        
        # Order Row
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

    # --- 3. UPLOAD PHASE (with progress bars) ---
    print("--- 📤 UPLOADING DATA (This may take 30 seconds) ---", flush=True)

    def batch_upload(worksheet, data, label):
        batch_size = 100
        total = len(data)
        for i in range(0, total, batch_size):
            chunk = data[i:i+batch_size]
            print(f"   Writing {label}: rows {i+1}-{min(i+batch_size, total)}...", flush=True)
            worksheet.append_rows(chunk, value_input_option='USER_ENTERED')
            time.sleep(1) 

    if new_students:
        batch_upload(ws_students, new_students, "Students")
    
    if new_orders:
        batch_upload(ws_orders, new_orders, "Orders")
        
    print(f"\n🎉 COMPLETED! Sheet now has exactly {TARGET_TOTAL} orders.", flush=True)

if __name__ == "__main__":
    main()
