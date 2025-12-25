import os
import json
import gspread
import random
import base64
import itertools
import time
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_FEEDBACKS = 500
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- NAMES ---
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayan", "Krishna", "Ishaan", 
    "Shaurya", "Atharv", "Rohan", "Rahul", "Amit", "Vikram", "Siddharth", "Kabir", "Dhruv", "Rishabh", 
    "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Kiara", "Myra", "Riya", "Anya", "Sarah", 
    "Kavita", "Zara", "Priya", "Nisha", "Meera", "Isha", "Pooja", "Neha", "Simran", "Tanvi",
    "Dev", "Yash", "Uday", "Bhavya", "Chetan", "Gaurav", "Hardik", "Imran", "Jatin", "Kunal",
    "Laksh", "Manish", "Naveen", "Om", "Pranav", "Qasim", "Rajat", "Samir", "Tushar", "Utkarsh"
]
LAST_NAMES = [
    "Kumar", "Singh", "Sharma", "Verma", "Gupta", "Malhotra", "Bhatia", "Saxena", "Mehta", "Jain", 
    "Agarwal", "Chopra", "Deshmukh", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Gill", "Sethi", 
    "Joshi", "Rawat", "Yadav", "Mishra", "Pandey", "Kaushik", "Thakur", "Chauhan", "Bisht", "Negi",
    "Sood", "Dutt", "Bakshi", "Khurana", "Garg", "Bansal", "Mittall", "Goel", "Rana", "Dewan"
]

FEEDBACK_MESSAGES = [
    "Great food quality! Very satisfied with today's menu.",
    "The food was delicious. Would love to see more variety.",
    "Excellent service. Keep up the good work!",
    "The canteen staff is very helpful and friendly.",
    "Food was fresh and tasty. Highly recommended!",
    "Amazing dishes today. Best meal this week!",
    "Very good quality. Could improve portion sizes though.",
    "The food taste is consistently good. Love it!",
    "Staff was courteous and quick in serving.",
    "Wonderful experience. Will definitely come back!",
    "The menu options are great. Loved today's special.",
    "Food quality is excellent. Very satisfied.",
    "Best canteen food I've had in a while!",
    "Great variety of options. Something for everyone.",
    "The food is always fresh and well-prepared.",
    "Excellent value for money. Highly appreciate it.",
    "The canteen team does a fantastic job!",
    "Food taste is fantastic. Keep it up!",
    "Very impressed with the quality and service.",
    "The dishes are prepared with care. Amazing!",
    "The food is delicious and prices are fair.",
    "Loved the special today. Please make it again!",
    "Excellent quality and taste. Perfect lunch!",
    "The canteen staff is always polite and efficient.",
    "Amazing food and great service. Thank you!",
    "Very good meal. Satisfied with the quality.",
    "The food is tasty and well-cooked. Great job!",
    "Best canteen experience so far. Really happy!",
    "Food quality is top-notch. Very pleased."
]

def get_client():
    if os.environ.get("GCP_BASE64_CREDS"):
        creds = Credentials.from_service_account_info(
            json.loads(base64.b64decode(os.environ["GCP_BASE64_CREDS"])), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file('canteen-app-376c7-eaaf8790c170.json', scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    print("--- 🚀 GENERATING 500 FAKE FEEDBACKS ---", flush=True)
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    
    # Check if 'Feedback' sheet exists, if not create it
    try:
        ws_feedback = sh.worksheet("Feedback")
        print("--- 🧹 CLEARING OLD FEEDBACK ---", flush=True)
        # Clear everything below the header (row 2 onwards)
        ws_feedback.resize(rows=1) 
        ws_feedback.resize(rows=TARGET_FEEDBACKS + 10) # Resize back up
    except gspread.exceptions.WorksheetNotFound:
        print("--- ⚠️ 'Feedback' sheet not found. Creating it... ---", flush=True)
        ws_feedback = sh.add_worksheet(title="Feedback", rows=TARGET_FEEDBACKS+50, cols=5)
        ws_feedback.append_row(["Name", "Email", "Message", "Date", "Time"])

    # --- GENERATION PHASE ---
    print(f"--- ⚡ GENERATING {TARGET_FEEDBACKS} ENTRIES ---", flush=True)

    all_combos = list(itertools.product(FIRST_NAMES, LAST_NAMES))
    unique_names_list = [f"{f} {l}" for f, l in all_combos]
    random.shuffle(unique_names_list)
    
    selected_names = unique_names_list[:TARGET_FEEDBACKS]
    
    new_feedbacks = []
    base_date = datetime.now() - timedelta(days=30)
    
    for full_name in selected_names:
        # Generate ID numbers for email: s.XX.XX@slps.one
        part1 = random.randint(11, 25)  # e.g., Class or Year
        part2 = random.randint(10, 99)  # e.g., Roll number
        
        email = f"s.{part1}.{part2}@slps.one"
        message = random.choice(FEEDBACK_MESSAGES)
        
        # Random date within last 30 days
        random_days = random.randint(0, 29)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        feedback_date = base_date + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
        
        date_str = feedback_date.strftime('%Y-%m-%d')
        time_str = feedback_date.strftime('%H:%M:%S')
        
        # Feedback Row: Name | Email | Message | Date | Time
        new_feedbacks.append([full_name, email, message, date_str, time_str])

    # --- UPLOAD PHASE ---
    print("--- 📤 UPLOADING (Batches of 100) ---", flush=True)

    def batch_upload(worksheet, data, label):
        batch_size = 100
        total = len(data)
        for i in range(0, total, batch_size):
            chunk = data[i:i+batch_size]
            print(f"   Writing {label}: rows {i+1}-{min(i+batch_size, total)}...", flush=True)
            worksheet.append_rows(chunk, value_input_option='USER_ENTERED')
            time.sleep(1.5)

    if new_feedbacks:
        batch_upload(ws_feedback, new_feedbacks, "Feedbacks")
        
    print(f"\n🎉 DONE! Generated {TARGET_FEEDBACKS} feedbacks with email format s.XX.XX@slps.one", flush=True)

if __name__ == "__main__":
    main()
