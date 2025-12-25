import os
import json
import gspread
import random
import base64
import time
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_FEEDBACKS = 250
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

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
    print("--- 🚀 STARTING VERIFIED FEEDBACK GENERATOR (250) ---", flush=True)
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)

    # --- STEP 1: READ REAL STUDENTS ---
    print("--- 🔍 FETCHING CURRENT STUDENT LIST ---", flush=True)
    ws_students = sh.worksheet("Students")
    student_data = ws_students.get_all_values()
    
    headers = [h.lower().strip() for h in student_data[0]]
    try:
        name_idx = headers.index("name")
        email_idx = headers.index("email")
    except:
        name_idx, email_idx = 2, 4 # Standard fallback

    real_students = []
    for row in student_data[1:]:
        if len(row) > max(name_idx, email_idx):
            s_name = row[name_idx].strip()
            s_email = row[email_idx].strip()
            if s_name and s_email and "@" in s_email:
                real_students.append({"name": s_name, "email": s_email})
    
    print(f"✅ Found {len(real_students)} students to pick from.", flush=True)

    # --- STEP 2: PREPARE FEEDBACK DATA ---
    new_feedbacks = []
    base_date = datetime.now() - timedelta(days=30)

    for _ in range(TARGET_FEEDBACKS):
        student = random.choice(real_students)
        message = random.choice(FEEDBACK_MESSAGES)
        
        # Random time in last 30 days
        rand_dt = base_date + timedelta(seconds=random.randint(0, 30*24*60*60))
        
        new_feedbacks.append([
            student['name'], 
            student['email'], 
            message, 
            rand_dt.strftime('%Y-%m-%d'), 
            rand_dt.strftime('%H:%M:%S')
        ])

    # --- STEP 3: CLEANUP & UPLOAD ---
    print("--- 🧹 CLEANING FEEDBACK SHEET ---", flush=True)
    ws_feedback = sh.worksheet("Feedback")
    ws_feedback.clear()
    
    # Restore Header
    ws_feedback.append_row(["Name", "Email", "Message", "Date", "Time"])

    print(f"--- 📤 UPLOADING {TARGET_FEEDBACKS} NEW ENTRIES ---", flush=True)
    ws_feedback.append_rows(new_feedbacks, value_input_option='USER_ENTERED')

    print(f"\n🎉 SUCCESS! 250 feedbacks linked to your student list are now live.", flush=True)

if __name__ == "__main__":
    main()
