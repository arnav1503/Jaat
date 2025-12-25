import os
import json
import gspread
import random
import base64
import time
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_FEEDBACKS = 750
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
    print("--- 🚀 STARTING VERIFIED FEEDBACK GENERATOR ---", flush=True)
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)

    # --- STEP 1: READ REAL STUDENTS ---
    print("--- 🔍 READING REGISTERED STUDENTS ---", flush=True)
    try:
        ws_students = sh.worksheet("Students")
        student_data = ws_students.get_all_values()
        
        if len(student_data) < 2:
            print("❌ 'Students' sheet is empty! Cannot match real names.", flush=True)
            return

        headers = [h.lower().strip() for h in student_data[0]]
        
        # Smart Column Detection
        try:
            name_idx = headers.index("name")
        except:
            name_idx = 2  # Fallback based on your screenshot
            
        try:
            email_idx = headers.index("email")
        except:
            email_idx = 4 # Fallback based on your screenshot

        # Extract valid students
        real_students = []
        for row in student_data[1:]:
            if len(row) > max(name_idx, email_idx):
                s_name = row[name_idx].strip()
                s_email = row[email_idx].strip()
                # Ensure we only get rows that actually have data
                if s_name and s_email and "@" in s_email:
                    real_students.append({"name": s_name, "email": s_email})
        
        print(f"✅ Found {len(real_students)} registered students to use.", flush=True)
        if not real_students:
            print("❌ No valid students found to generate feedback from.", flush=True)
            return

    except Exception as e:
        print(f"❌ Error reading students: {e}", flush=True)
        return

    # --- STEP 2: PREPARE FEEDBACK DATA ---
    print(f"--- ⚡ GENERATING {TARGET_FEEDBACKS} NEW ENTRIES ---", flush=True)
    
    new_feedbacks = []
    base_date = datetime.now() - timedelta(days=30)

    for _ in range(TARGET_FEEDBACKS):
        # 1. Pick a REAL student
        student = random.choice(real_students)
        
        # 2. Pick a random message
        message = random.choice(FEEDBACK_MESSAGES)
        
        # 3. Generate random time in last 30 days
        random_days = random.randint(0, 29)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        feedback_date = base_date + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
        
        date_str = feedback_date.strftime('%Y-%m-%d')
        time_str = feedback_date.strftime('%H:%M:%S')
        
        new_feedbacks.append([student['name'], student['email'], message, date_str, time_str])

    # --- STEP 3: CLEANUP & UPLOAD ---
    print("--- 🧹 CLEANING UP OLD DATA ---", flush=True)
    try:
        ws_feedback = sh.worksheet("Feedback")
        ws_feedback.clear()  # <--- THIS WIPES EVERYTHING
        print("   ✅ Old feedback deleted.", flush=True)
    except:
        print("   ⚠️ Feedback sheet not found. Creating new one...", flush=True)
        ws_feedback = sh.add_worksheet("Feedback", rows=TARGET_FEEDBACKS+50, cols=5)

    # Restore Header
    ws_feedback.append_row(["Name", "Email", "Message", "Date", "Time"])

    print("--- 📤 UPLOADING NEW DATA (Batches of 100) ---", flush=True)
    batch_size = 100
    total = len(new_feedbacks)
    
    for i in range(0, total, batch_size):
        chunk = new_feedbacks[i:i+batch_size]
        print(f"   Writing rows {i+1}-{min(i+batch_size, total)}...", flush=True)
        ws_feedback.append_rows(chunk, value_input_option='USER_ENTERED')
        time.sleep(1.5)

    print(f"\n🎉 SUCCESS! {TARGET_FEEDBACKS} verified feedbacks uploaded.", flush=True)

if __name__ == "__main__":
    main()
