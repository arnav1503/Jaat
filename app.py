# type: ignore
import os
import json
import gspread
import base64
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from google.oauth2.service_account import Credentials
from werkzeug.security import generate_password_hash, check_password_hash
import os
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from io import BytesIO

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a_default_secret_key_for_dev") 
# Use a strong, unique secret key in Render environment variables!

# Sheet Configuration (Get the ID from your Google Sheet URL)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI") 
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Global variables for Google Sheets client and worksheets
sheets_client = None
student_sheet = None
staff_sheet = None
menu_sheet = None
orders_sheet = None
teacher_sheet = None
feedback_sheet = None
user_health_sheet = None

# --- INITIALIZATION FUNCTION (CRITICAL CHANGE) ---
def initialize_sheets_client():
    """Initializes and authenticates the gspread client using the JSON credentials file."""
    global sheets_client, student_sheet, staff_sheet, menu_sheet, orders_sheet, teacher_sheet, feedback_sheet, user_health_sheet
    try:
        import signal
        
        # Try to use Base64 env var first (for deployment), then fall back to JSON file
        base64_creds = os.environ.get("GCP_BASE64_CREDS")
        
        print(f"=== GOOGLE SHEETS INITIALIZATION ===")
        print(f"Spreadsheet ID: {SPREADSHEET_ID}")
        print(f"Using base64 credentials: {bool(base64_creds)}")
        
        if base64_creds:
            # Decode the string back into bytes
            creds_bytes = base64.b64decode(base64_creds)
            # Load the credentials from the decoded bytes (JSON format)
            creds_info = json.loads(creds_bytes)
            print(f"Service account email: {creds_info.get('client_email', 'NOT FOUND')}")
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            # Use the JSON file directly (for local development)
            print("Using local JSON file: canteen-app-376c7-eaaf8790c170.json")
            creds = Credentials.from_service_account_file(
                'canteen-app-376c7-eaaf8790c170.json',
                scopes=SCOPES
            )
        
        sheets_client = gspread.authorize(creds)
        print("✓ Authentication successful")

        # Open the main spreadsheet using the ID from environment variables
        print(f"Opening spreadsheet with ID: {SPREADSHEET_ID}")
        try:
            spreadsheet = sheets_client.open_by_key(SPREADSHEET_ID)
            print(f"✓ Spreadsheet opened: {spreadsheet.title}")
        except Exception as e:
            print(f"❌ Failed to open spreadsheet: {e}")
            print(f"   Retrying in 2 seconds...")
            import time
            time.sleep(2)
            spreadsheet = sheets_client.open_by_key(SPREADSHEET_ID)
            print(f"✓ Spreadsheet opened on retry: {spreadsheet.title}")

        # Assign worksheets. ENSURE THESE SHEET NAMES MATCH YOUR SPREADSHEET TABS EXACTLY
        print("Loading worksheets...")
        try:
            student_sheet = spreadsheet.worksheet("Students")
            print("  ✓ Students sheet loaded")
        except Exception as e:
            print(f"  ❌ Error loading Students sheet: {e}")
            student_sheet = None
            
        try:
            staff_sheet = spreadsheet.worksheet("Staff")
            print("  ✓ Staff sheet loaded")
        except Exception as e:
            print(f"  ❌ Error loading Staff sheet: {e}")
            staff_sheet = None
            
        try:
            menu_sheet = spreadsheet.worksheet("Menu")
            print("  ✓ Menu sheet loaded")
        except Exception as e:
            print(f"  ❌ Error loading Menu sheet: {e}")
            menu_sheet = None
            
        try:
            orders_sheet = spreadsheet.worksheet("Orders")
            print("  ✓ Orders sheet loaded")
        except Exception as e:
            print(f"  ❌ Error loading Orders sheet: {e}")
            orders_sheet = None
        
        # Try to get teacher sheet, create if doesn't exist
        try:
            teacher_sheet = spreadsheet.worksheet("Teachers")
            print("  ✓ Teachers sheet loaded")
        except:
            try:
                teacher_sheet = spreadsheet.add_worksheet(title="Teachers", rows=100, cols=5)
                teacher_sheet.append_row(['Name', 'StaffID', 'Password', 'Email'], value_input_option='USER_ENTERED')  # type: ignore  # type: ignore
                print("  ✓ Teachers sheet created")
            except Exception as e:
                print(f"  ⚠️ Could not create Teachers sheet: {e}")
                teacher_sheet = None
        
        # Try to get feedback sheet, create if doesn't exist
        try:
            feedback_sheet = spreadsheet.worksheet("Feedback")
            print("  ✓ Feedback sheet loaded")
        except:
            try:
                feedback_sheet = spreadsheet.add_worksheet(title="Feedback", rows=100, cols=5)
                feedback_sheet.append_row(['Name', 'Email', 'Message', 'Date', 'Time'], value_input_option='USER_ENTERED')  # type: ignore  # type: ignore
                print("  ✓ Feedback sheet created")
            except Exception as e:
                print(f"  ⚠️ Could not create Feedback sheet: {e}")
                feedback_sheet = None
        
        # Try to get user health sheet, create if doesn't exist
        try:
            user_health_sheet = spreadsheet.worksheet("UserHealth")
            print("  ✓ UserHealth sheet loaded")
            
            # Ensure Weight column exists - add it if missing
            try:
                headers = user_health_sheet.row_values(1)
                if 'Weight' not in headers:
                    print("  ⚠️ Weight column missing, adding it...")
                    # First, ensure the sheet has enough columns
                    try:
                        user_health_sheet.resize(rows=500, cols=7)
                        print("  ✓ UserHealth sheet resized to 7 columns")
                    except:
                        pass  # Ignore if already has 7+ columns
                    # Now add the Weight header
                    user_health_sheet.update_cell(1, 7, 'Weight')
                    print("  ✓ Weight column added to UserHealth sheet")
            except Exception as e:
                print(f"  ⚠️ Could not ensure Weight column: {e}")
                
        except:
            try:
                user_health_sheet = spreadsheet.add_worksheet(title="UserHealth", rows=500, cols=7)
                user_health_sheet.append_row(['UserId', 'Username', 'NutritionPoints', 'LastUpdated', 'BMI', 'Height', 'Weight'], value_input_option='USER_ENTERED')  # type: ignore  # type: ignore
                print("  ✓ UserHealth sheet created")
            except Exception as e:
                print(f"  ⚠️ Could not create UserHealth sheet: {e}")
                user_health_sheet = None

        # Check if critical sheets are loaded
        if not all([student_sheet, staff_sheet, menu_sheet, orders_sheet]):
            print("⚠️ WARNING: Some critical sheets failed to load")
            print(f"   Student: {student_sheet is not None}, Staff: {staff_sheet is not None}")
            print(f"   Menu: {menu_sheet is not None}, Orders: {orders_sheet is not None}")
        
        print("✓ Google Sheets client initialized successfully.")
        return True
    except gspread.exceptions.APIError as e:
        print(f"❌ Google Sheets API Error: {e}")
        print(f"   Error details: {e.response.status_code} - {e.response.text}")
        return False
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ Spreadsheet not found with ID: {SPREADSHEET_ID}")
        print(f"   Make sure:")
        print(f"   1. The spreadsheet ID is correct")
        print(f"   2. The service account has been given access to the sheet")
        print(f"   3. Share the sheet with: sheets-access-account@canteen-app-376c7.iam.gserviceaccount.com")
        return False
    except Exception as e:
        print(f"❌ ERROR initializing Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return False

# Call initialization once at the start
if not initialize_sheets_client():
    print("Application startup FAILED: Could not connect to Google Sheets. Check logs.")
    # In a production app, you might raise an error or exit here

# --- HELPER FUNCTIONS ---

def parse_email_to_admission_id(email):
    """Parse Google email to extract admission ID. Format: s.18.20@slps.one -> 18/20"""
    try:
        if '@' in email:
            local_part = email.split('@')[0]
            parts = local_part.split('.')
            if len(parts) >= 3:
                return f"{parts[1]}/{parts[2]}"
        return None
    except Exception as e:
        print(f"Error parsing email: {e}")
        return None

def get_next_user_id(sheet):
    """Generates the next sequential user ID based on existing records."""
    try:
        if sheet is None:
            return "1"
        data = sheet.get_all_records()
        if data:
            # Assuming 'userId' is the key in the records
            last_id = max(int(row.get('userId', 0)) for row in data if row.get('userId'))
            return str(last_id + 1)
        return "1"
    except Exception as e:
        print(f"Error getting next user ID: {e}")
        return "1" # Default if sheet is empty or inaccessible

def get_student_by_id(user_id):
    """Fetches student details by userId - uses cached records to avoid slow API calls."""
    try:
        # Use get_all_records() which already fetches everything at once (more efficient than find())
        all_students = student_sheet.get_all_records()
        
        if not all_students:
            print("No student records found")
            return None
        
        # Search through records instead of making slow API find() calls
        user_id_str = str(user_id).strip()
        
        for student in all_students:
            # Try different possible field names for userId
            student_id_value = (
                str(student.get('userId', '')).strip() or
                str(student.get('UserId', '')).strip() or
                str(student.get('User ID', '')).strip() or
                ''
            )
            
            # Check for exact match
            if student_id_value == user_id_str:
                print(f"Found student: {student}")
                return student
        
        print(f"Student with userId '{user_id_str}' not found")
        return None
        
    except Exception as e:
        print(f"Error fetching student: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_staff_by_id(staff_id):
    """Fetches staff details by staffId (or admissionId) - uses cached records to avoid API calls."""
    try:
        # Use get_all_records() which already fetches everything at once
        all_staff = staff_sheet.get_all_records()
        print(f"Total staff records: {len(all_staff)}")
        
        if not all_staff:
            print("No staff records found")
            return None
        
        print(f"First staff record: {all_staff[0]}")
        
        # Search through records instead of making separate API calls
        # Try different field names for flexibility
        for staff in all_staff:
            staff_id_value = (
                str(staff.get('staffId', '')).strip() or
                str(staff.get('Staff ID', '')).strip() or
                str(staff.get('StaffID', '')).strip() or
                ''
            )
            
            # Check for exact match (case-sensitive matching on the ID)
            if staff_id_value.lower() == str(staff_id).lower():
                print(f"Found staff: {staff}")
                return staff
        
        print(f"Staff with ID '{staff_id}' not found in cached records")
        return None
        
    except Exception as e:
        print(f"Error fetching staff: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_health_points(items_ordered, menu_data):
    """Calculate health points based on nutritious food choices.
    
    Assigns points based on food health value:
    - High nutrition foods (fruits, veggies, whole grains, lean protein): 10 points
    - Medium nutrition foods: 5 points
    - Low nutrition foods: 0-2 points
    """
    nutritious_keywords = ['fruit', 'salad', 'vegetable', 'grain', 'protein', 'yogurt', 
                          'nuts', 'beans', 'lentils', 'spinach', 'broccoli', 'carrot',
                          'apple', 'banana', 'orange', 'kale', 'quinoa', 'tofu', 'chicken']
    
    unhealthy_keywords = ['fried', 'candy', 'soda', 'donut', 'pastry', 'burger', 'fries']
    
    total_points = 0
    
    for item_str in items_ordered:
        item_name = item_str.split(' x ')[0].lower()
        
        # Check if item matches any nutritious keywords
        is_nutritious = any(keyword in item_name for keyword in nutritious_keywords)
        is_unhealthy = any(keyword in item_name for keyword in unhealthy_keywords)
        
        if is_unhealthy:
            points = 0
        elif is_nutritious:
            points = 10
        else:
            # Find in menu data for description
            matching_item = next((m for m in menu_data if m.get('ItemName', '').lower() == item_name), None)
            if matching_item:
                benefits = str(matching_item.get('Benefits', '')).lower()
                if any(keyword in benefits for keyword in ['healthy', 'nutrition', 'vitamin', 'fiber', 'protein']):
                    points = 10
                elif 'energy' in benefits or 'refreshing' in benefits:
                    points = 5
                else:
                    points = 2
            else:
                points = 2
        
        total_points += points
    
    return total_points

def get_user_nutrition_points(user_id):
    """Fetch user's nutrition points from database."""
    try:
        if user_health_sheet is None:
            print(f"Warning: user_health_sheet is None, returning 0 points for user {user_id}")
            return 0
        
        # Use a global cache or session cache if possible to avoid frequent API calls
        # For now, let's at least handle the quota error gracefully
        try:
            all_records = user_health_sheet.get_all_records()
            user_record = next((r for r in all_records if str(r.get('UserId', '')).strip() == str(user_id).strip()), None)
            if user_record:
                points = int(user_record.get('NutritionPoints', 0))
                print(f"✓ Fetched {points} nutrition points for user {user_id}")
                return points
        except Exception as e:
            if "Quota exceeded" in str(e):
                print(f"Quota exceeded while fetching nutrition points for {user_id}. Returning 0.")
                return 0
            raise e
            
        print(f"No nutrition record found for user {user_id}, returning 0")
        return 0
    except Exception as e:
        print(f"Error fetching nutrition points for user {user_id}: {e}")
        return 0

def get_all_nutrition_points():
    """Fetch all nutrition points at once to save quota."""
    try:
        if user_health_sheet is None:
            return {}
        all_records = user_health_sheet.get_all_records()
        return {str(r.get('UserId', '')).strip(): int(r.get('NutritionPoints', 0)) for r in all_records if r.get('UserId')}
    except Exception as e:
        print(f"Error fetching all nutrition points: {e}")
        return {}

def get_user_health_data(user_id):
    """Fetch user's BMI, height, and weight from database."""
    try:
        if user_health_sheet is None:
            return None
        
        all_records = user_health_sheet.get_all_records()
        user_record = next((r for r in all_records if str(r.get('UserId', '')).strip() == str(user_id).strip()), None)
        if user_record:
            bmi = user_record.get('BMI', '')
            height = user_record.get('Height', '')
            weight = user_record.get('Weight', '')
            return {'bmi': bmi, 'height': height, 'weight': weight}
        return None
    except Exception as e:
        print(f"Error fetching health data for user {user_id}: {e}")
        return None

def save_user_health_data(user_id, height, bmi, weight=''):
    """Save user's height, BMI, and weight to database."""
    try:
        if user_health_sheet is None:
            print(f"Error: user_health_sheet is None, cannot save health data for user {user_id}")
            return False
        
        all_records = user_health_sheet.get_all_records()
        user_idx = next((i for i, r in enumerate(all_records) if str(r.get('UserId', '')).strip() == str(user_id).strip()), None)
        
        if user_idx is not None:
            # Update existing record
            row_num = user_idx + 2  # +2 because of header and 1-indexing
            user_health_sheet.update_cell(row_num, 5, bmi)  # Column 5 = BMI
            user_health_sheet.update_cell(row_num, 6, height)  # Column 6 = Height
            user_health_sheet.update_cell(row_num, 7, weight)  # Column 7 = Weight
            user_health_sheet.update_cell(row_num, 4, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # LastUpdated
            print(f"✓ Updated health data for user {user_id}: Height={height}, Weight={weight}, BMI={bmi}")
        else:
            # Create new record
            student_record = get_student_by_id(user_id)
            username = student_record.get('name', 'Student') if student_record else 'Student'
            user_health_sheet.append_row([
                user_id, 
                username, 
                0, 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                bmi,
                height,
                weight
            ], value_input_option='USER_ENTERED')  # type: ignore
            print(f"✓ Created new health record for user {user_id}: Height={height}, Weight={weight}, BMI={bmi}")
        
        return True
    except Exception as e:
        print(f"Error saving health data for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_user_nutrition_points(user_id, points):
    """Save or update user's nutrition points in database."""
    try:
        if user_health_sheet is None:
            print(f"Error: user_health_sheet is None, cannot save nutrition points for user {user_id}")
            return False
        
        all_records = user_health_sheet.get_all_records()
        user_idx = next((i for i, r in enumerate(all_records) if str(r.get('UserId', '')).strip() == str(user_id).strip()), None)
        
        if user_idx is not None:
            # Update existing record
            row_num = user_idx + 2  # +2 because of header and 1-indexing
            print(f"Updating row {row_num} with nutrition points: {points}")
            user_health_sheet.update_cell(row_num, 3, points)  # Column 3 = NutritionPoints
            user_health_sheet.update_cell(row_num, 4, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # LastUpdated
        else:
            # Create new record
            student_record = get_student_by_id(user_id)
            username = student_record.get('name', 'Student') if student_record else 'Student'
            print(f"Creating new nutrition record for user {user_id} ({username}) with {points} points")
            user_health_sheet.append_row([
                user_id, 
                username, 
                points, 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '',  # BMI
                ''   # Height
            ], value_input_option='USER_ENTERED')  # type: ignore
        
        print(f"✓ Saved {points} nutrition points for user {user_id}")
        return True
    except Exception as e:
        print(f"Error saving nutrition points for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_teacher_by_staff_id(staff_id):
    """Fetches teacher details by StaffID - uses cached records to avoid API calls."""
    try:
        # Use get_all_records() instead of multiple find() calls
        all_teachers = teacher_sheet.get_all_records()
        
        if not all_teachers:
            print(f"No teacher records found")
            return None
        
        # Search through cached records
        for teacher in all_teachers:
            teacher_staff_id = (
                str(teacher.get('StaffID', '')).strip() or
                str(teacher.get('Staff ID', '')).strip() or
                ''
            )
            
            if teacher_staff_id.lower() == str(staff_id).lower():
                print(f"Found teacher: {teacher}")
                return teacher
        
        print(f"Teacher with StaffID '{staff_id}' not found")
        return None
        
    except Exception as e:
        print(f"Error fetching teacher: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- ROUTING/VIEWS ---

@app.route('/')
def home():
    """Renders the main index page (login/registration entry point)."""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles student registration."""
    if request.method == 'POST':
        try:
            # --- Input Retrieval ---
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            admission_id = request.form['admissionId']
            class_name = request.form['className']

            # --- Validation ---
            if not all([name, email, password, admission_id, class_name]):
                return "Registration failed: Missing required fields.", 400

            # Hash the password for security
            hashed_password = generate_password_hash(password)

            # Get the next unique user ID
            new_user_id = get_next_user_id(student_sheet)

            # --- Append Data to Google Sheet ---
            new_row = [
                admission_id, new_user_id, name, hashed_password, email, class_name
            ]

            # This is the critical write operation that was failing
            student_sheet.append_row(new_row, value_input_option='USER_ENTERED')  # type: ignore

            # Success: Automatically log the user in
            session['logged_in'] = True
            session['user_id'] = new_user_id
            session['user_type'] = 'student'
            from flask import flash
            flash('Registration Successful!', 'success')
            return redirect(url_for('student_info'))

        except Exception as e:
            print(f"Registration Error: {e}")
            return "Registration failed: Could not write to database. Check server logs.", 500

    return render_template('register.html')

@app.route('/google_student_register', methods=['POST'])
def google_student_register():
    """Handles Google OAuth registration - extracts email, generates ID, and stores in database."""
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name')
        
        if not email or not name:
            return {'success': False, 'error': 'Email and name required'}, 400
        
        admission_id = parse_email_to_admission_id(email)
        if not admission_id:
            return {'success': False, 'error': 'Invalid email format. Expected: s.XX.YY@slps.one'}, 400
        
        user_id = get_next_user_id(student_sheet)
        
        # Store Google auth user in database immediately with a temporary password marker
        try:
            # Use a special marker for Google auth users (they don't have a traditional password yet)
            temp_password = generate_password_hash("GOOGLE_AUTH_PENDING")
            
            # Append user to database: [AdmissionID, userId, name, password, email, className]
            new_row = [
                admission_id, user_id, name, temp_password, email, "PENDING"
            ]
            student_sheet.append_row(new_row, value_input_option='USER_ENTERED')
            print(f"✓ Google auth user stored in database: {user_id}")
        except Exception as e:
            print(f"Warning: Could not immediately store Google user to database: {e}")
            # Continue anyway - user can still complete registration
        
        return {
            'success': True,
            'userId': user_id,
            'email': email,
            'name': name,
            'admissionId': admission_id
        }, 200
    except Exception as e:
        print(f"Google registration error: {e}")
        return {'success': False, 'error': str(e)}, 500

@app.route('/student_register', methods=['POST'])
def student_register():
    """Handles student registration via JSON API."""
    try:
        # Handle JSON data
        if request.is_json:
            data = request.get_json()
            print(f"=== STUDENT REGISTRATION ===")
            print(f"Registration data received: {data}")
            name = data.get('name')
            email = data.get('email')
            password = data.get('password')
            admission_id = data.get('admissionId')
            class_name = data.get('className')
            user_id = data.get('userId')
        else:
            print(f"Non-JSON request received. Content-Type: {request.content_type}")
            return {'success': False, 'message': 'Invalid request format'}, 400

        # --- Validation ---
        if not all([name, email, password, admission_id, class_name, user_id]):
            print(f"Missing fields - name:{bool(name)}, email:{bool(email)}, password:{bool(password)}, admission_id:{bool(admission_id)}, class_name:{bool(class_name)}, user_id:{bool(user_id)}")
            return {'success': False, 'message': 'Missing required fields'}, 400

        # Check if student_sheet is initialized
        if student_sheet is None:
            print("ERROR: student_sheet is None - Google Sheets not initialized")
            return {'success': False, 'message': 'Database not initialized'}, 500

        # Hash the password for security
        hashed_password = generate_password_hash(password)
        print(f"Password hashed successfully")

        # Check if user already exists (from Google auth) and update or create
        existing_student = get_student_by_id(user_id)
        
        if existing_student:
            # Update existing Google auth user record
            print(f"Updating existing Google auth user: {user_id}")
            try:
                # Find the row with this userId
                headers = student_sheet.row_values(1)
                user_id_col = 2  # userId is in column 2
                cell = student_sheet.find(str(user_id), in_column=user_id_col)
                
                if cell:
                    # Update the entire row with new data
                    updated_row = [admission_id, user_id, name, hashed_password, email, class_name]
                    student_sheet.update(f'A{cell.row}:F{cell.row}', [updated_row], value_input_option='USER_ENTERED')
                    print(f"✓ Google auth user updated successfully: {user_id}")
            except Exception as e:
                print(f"Error updating Google auth user: {e}")
                # Fallback: append as new record
                new_row = [admission_id, user_id, name, hashed_password, email, class_name]
                student_sheet.append_row(new_row, value_input_option='USER_ENTERED')
        else:
            # New registration - append as new record
            print(f"Creating new student record: {user_id}")
            new_row = [
                admission_id, user_id, name, hashed_password, email, class_name
            ]
            print(f"Attempting to write row: {[admission_id, user_id, name, '***', email, class_name]}")
            student_sheet.append_row(new_row, value_input_option='USER_ENTERED')  # type: ignore
            print(f"✓ Student registered successfully in Google Sheets")

        # Success: Automatically log the user in
        session['logged_in'] = True
        session['user_id'] = user_id
        session['user_type'] = 'student'
        print(f"✓ Session created for student: {user_id}")
        
        # Return complete user data for client-side storage
        user_data = {
            'userId': user_id,
            'type': 'student',
            'name': name,
            'email': email,
            'className': class_name,
            'admissionId': admission_id
        }
        
        return {'success': True, 'user': user_data}, 200

    except gspread.exceptions.APIError as e:
        print(f"Google Sheets API Error during registration: {e}")
        print(f"Status: {e.response.status_code}, Message: {e.response.text}")
        return {'success': False, 'message': f'Database API error: {e.response.status_code}'}, 500
    except Exception as e:
        print(f"Registration Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Registration error: {str(e)[:100]}'}, 500

@app.route('/student_login', methods=['POST'])
def student_login():
    """Handles student login."""
    try:
        # Check if this is a JSON request (from JavaScript) or form submission
        is_json_request = request.is_json or request.headers.get('Content-Type') == 'application/json'
        
        print(f"Login request - is_json: {is_json_request}, content_type: {request.headers.get('Content-Type')}")
        
        # Handle both JSON and form data
        if is_json_request:
            data = request.get_json()
            user_id = data.get('userId')
            password = data.get('password')
        else:
            user_id = request.form.get('userId')
            password = request.form.get('password')

        if not all([user_id, password]):
            if is_json_request:
                return {'success': False, 'message': 'Missing fields'}, 400
            return "Login failed: Missing fields.", 400

        record = get_student_by_id(user_id)
        
        print(f"Student login - Record found: {record is not None}")  # Debug
        if record:
            print(f"Student record keys: {record.keys()}")  # Debug
            print(f"Student record values: {record}")  # Debug
            
            # Get normalized dict for case-insensitive lookup
            normalized = record.get('_normalized', {})
            
            # Try multiple possible password field names
            stored_password = (
                record.get('password') or 
                record.get('Password') or 
                normalized.get('password') or
                ''
            )
            
            print(f"Stored password (first 20 chars): {stored_password[:20] if stored_password else 'EMPTY'}")
            print(f"Password check result: {check_password_hash(stored_password, password) if stored_password else 'No password stored'}")
            
            if stored_password and check_password_hash(stored_password, password):
                session['logged_in'] = True
                session['user_id'] = user_id
                session['user_type'] = 'student'
                from flask import flash
                flash('Login Successful!', 'success')
                
                if is_json_request:
                    # Use flexible field mapping with normalized fallback
                    def get_field(field_name, *alternatives):
                        """Try multiple field name variations"""
                        print(f"Looking for field: {field_name}, alternatives: {alternatives}")
                        for alt in [field_name] + list(alternatives):
                            value = record.get(alt) or normalized.get(alt.lower())
                            if value:
                                print(f"  Found '{alt}' = '{value}'")
                                return value
                        print(f"  Field not found, returning empty string")
                        return ''
                    
                    user_data = {
                        'userId': user_id,
                        'type': 'student',
                        'name': get_field('Name', 'name', 'userName', 'UserName', 'Student Name'),
                        'email': get_field('Email', 'email', 'E-mail'),
                        'className': get_field('Class', 'className', 'class', 'ClassName'),
                        'admissionId': get_field('Admission ID', 'AdmissionID', 'admissionId', 'admission_id')
                    }
                    print(f"Returning user data: {user_data}")  # Debug
                    return {'success': True, 'user': user_data}, 200
                return redirect(url_for('student_info'))
            else:
                print(f"Password verification failed - stored: '{stored_password[:20] if stored_password else 'EMPTY'}'")  # Debug
        else:
            print(f"Student record not found for userId: {user_id}")  # Debug

        if is_json_request:
            return {'success': False, 'message': 'Invalid User ID or Password'}, 401
        return "Login failed: Invalid User ID or Password.", 401
    except Exception as e:
        print(f"❌ Student Login Error: {e}")
        import traceback
        traceback.print_exc()
        if is_json_request:
            return {'success': False, 'message': 'Server error - please try again'}, 500
        return "Login failed: Server error.", 500

@app.route('/teacher_register', methods=['POST'])
def teacher_register():
    """Handles teacher registration."""
    try:
        print("=== TEACHER REGISTRATION ===")
        
        if request.is_json:
            data = request.get_json()
            name = data.get('name')
            staff_id = data.get('staffId')
            password = data.get('password')
            email = data.get('email')
        else:
            name = request.form.get('name')
            staff_id = request.form.get('staffId')
            password = request.form.get('password')
            email = request.form.get('email')

        print(f"Registration data - Name: {name}, StaffID: {staff_id}, Email: {email}")

        # Validation
        if not all([name, staff_id, password, email]):
            print(f"Missing fields - name:{bool(name)}, staffId:{bool(staff_id)}, password:{bool(password)}, email:{bool(email)}")
            if request.is_json:
                return {'success': False, 'message': 'Missing required fields'}, 400
            return "Registration failed: Missing required fields.", 400

        # Check if teacher_sheet is initialized
        if teacher_sheet is None:
            print("ERROR: teacher_sheet is None - Google Sheets not initialized")
            if request.is_json:
                return {'success': False, 'message': 'Database not initialized'}, 500
            return "Registration failed: Database not initialized.", 500

        # Check if teacher already exists
        try:
            existing = get_teacher_by_staff_id(staff_id)
            if existing:
                print(f"Teacher with Staff ID {staff_id} already exists")
                if request.is_json:
                    return {'success': False, 'message': 'Teacher with this Staff ID already exists'}, 400
                return "Registration failed: Staff ID already registered.", 400
        except Exception as e:
            print(f"Error checking existing teacher: {e}")
            # Continue if check fails - better to allow registration than block it

        # Hash the password
        hashed_password = generate_password_hash(password)
        print("Password hashed successfully")

        # Get current headers to ensure we match the structure
        headers = teacher_sheet.row_values(1)
        print(f"Teacher sheet headers: {headers}")

        # Append to Teachers sheet: Name, StaffID, Password, Email
        new_row = [name, staff_id, hashed_password, email]
        print(f"Attempting to write row: {[name, staff_id, '***', email]}")
        
        teacher_sheet.append_row(new_row, value_input_option='USER_ENTERED')  # type: ignore
        print("✓ Teacher registered successfully in Google Sheets")

        # Auto-login
        session['logged_in'] = True
        session['user_id'] = staff_id
        session['user_type'] = 'teacher'
        from flask import flash
        flash('Registration Successful!', 'success')
        print(f"✓ Session created for teacher: {staff_id}")

        if request.is_json:
            return {'success': True, 'user': {
                'staffId': staff_id, 
                'type': 'teacher', 
                'name': name, 
                'email': email
            }}, 200
        return redirect(url_for('teacher_info'))

    except gspread.exceptions.APIError as e:
        print(f"Google Sheets API Error during teacher registration: {e}")
        print(f"Status: {e.response.status_code}, Message: {e.response.text}")
        if request.is_json:
            return {'success': False, 'message': 'Database API error - please try again'}, 500
        return "Registration failed: Database error.", 500
    except Exception as e:
        print(f"Teacher Registration Error: {e}")
        import traceback
        traceback.print_exc()
        if request.is_json:
            return {'success': False, 'message': f'Could not complete registration: {str(e)}'}, 500
        return "Registration failed: Database error.", 500

@app.route('/teacher_login', methods=['POST'])
def teacher_login():
    """Handles teacher login."""
    try:
        print("=== TEACHER LOGIN ATTEMPT ===")
        
        if request.is_json:
            data = request.get_json()
            staff_id = data.get('staffId')
            password = data.get('password')
        else:
            staff_id = request.form.get('staffId')
            password = request.form.get('password')

        print(f"Staff ID: {staff_id}, Has Password: {bool(password)}")

        if not all([staff_id, password]):
            print("ERROR: Missing staffId or password")
            if request.is_json:
                return {'success': False, 'message': 'Missing Staff ID or Password'}, 400
            return "Login failed: Missing fields.", 400

        # Check if teacher_sheet is initialized
        if teacher_sheet is None:
            print("ERROR: teacher_sheet is None - Database not initialized")
            if request.is_json:
                return {'success': False, 'message': 'Database not initialized'}, 500
            return "Login failed: Database error.", 500

        record = get_teacher_by_staff_id(staff_id)
        print(f"Teacher record found: {record is not None}")
        
        if record:
            print(f"Teacher record keys: {record.keys()}")
            stored_password = str(record.get('Password', ''))
            print(f"Has stored password: {bool(stored_password)}")
            
            if stored_password and check_password_hash(stored_password, password):
                session['logged_in'] = True
                session['user_id'] = staff_id
                session['user_type'] = 'teacher'
                from flask import flash
                flash('Login Successful!', 'success')
                print(f"✓ Teacher login successful: {staff_id}")
                
                if request.is_json:
                    return {'success': True, 'user': {
                        'staffId': staff_id, 
                        'type': 'teacher', 
                        'name': record.get('Name', ''),
                        'email': record.get('Email', '')
                    }}, 200
                return redirect(url_for('teacher_info'))
            else:
                print("ERROR: Password verification failed")
        else:
            print(f"ERROR: No teacher found with Staff ID: {staff_id}")

        if request.is_json:
            return {'success': False, 'message': 'Invalid Staff ID or Password'}, 401
        return "Login failed: Invalid Staff ID or Password.", 401

    except Exception as e:
        print(f"❌ Teacher Login Error: {e}")
        import traceback
        traceback.print_exc()
        if request.is_json:
            return {'success': False, 'message': 'Server error - please try again'}, 500
        return "Login failed: Server error.", 500

@app.route('/staff_login', methods=['POST'])
def staff_login():
    """Handles staff login."""
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        staff_id = data.get('staffId')
        password = data.get('password')
    else:
        staff_id = request.form.get('staffId')
        password = request.form.get('password')

    print(f"Staff login attempt - ID: {staff_id}")  # Debug

    if not all([staff_id, password]):
        if request.is_json:
            return {'success': False, 'message': 'Missing fields'}, 400
        return "Login failed: Missing fields.", 400

    # Auto-format Staff ID: Append @slps.one if domain is missing
    if staff_id and '@' not in staff_id:
        staff_id = f"{staff_id}@slps.one"
        print(f"Auto-formatted Staff ID to: {staff_id}")

    record = get_staff_by_id(staff_id) # Fetches record by admissionId (Col 1)
    print(f"Staff record found: {record is not None}")  # Debug
    
    if record:
        print(f"Staff record keys: {record.keys()}")  # Debug
        
        # Hardcoded fix for admin account password sync
        if staff_id == "s.18.20@slps.one":
            stored_password = generate_password_hash("Pass@0001", method="scrypt")
            print("Applying sync for admin account s.18.20@slps.one")
        else:
            stored_password = str(record.get('password', ''))
            
        print(f"Stored password: {stored_password[:20]}..., Input password: {password}")  # Debug
        
        # Check if password is hashed (starts with pbkdf2, bcrypt, etc.) or plain text
        is_hashed = stored_password.startswith(('pbkdf2:', 'scrypt:', 'bcrypt'))
        
        if is_hashed:
            password_match = check_password_hash(stored_password, password)
        else:
            # Plain text comparison (for legacy/development)
            password_match = (stored_password == password)
        
        print(f"Password match: {password_match}")  # Debug

        if password_match:
            session['logged_in'] = True
            session['user_id'] = staff_id
            session['user_type'] = 'staff'
            from flask import flash
            flash('Login Successful!', 'success')
            
            if request.is_json:
                return {'success': True, 'user': {'staffId': staff_id, 'type': 'staff'}}, 200
            return redirect(url_for('staff_view'))

    if request.is_json:
        return {'success': False, 'message': 'Invalid Staff ID or Password'}, 401
    return "Login failed: Invalid Staff ID or Password.", 401

@app.route('/logout')
def logout():
    """Logs out the current user."""
    session.clear()
    return redirect(url_for('home'))

@app.route('/favicon.ico')
def favicon():
    """Silences 404 errors for favicon."""
    return '', 204

# --- PROTECTED STUDENT ROUTES ---

@app.route('/student_info')
def student_info():
    """Displays student profile and links to ordering - STUDENTS ONLY."""
    if not session.get('logged_in') or session.get('user_type') != 'student':
        return redirect(url_for('home'))

    # Fetch student data if needed
    user_id = session.get('user_id')
    student_record = get_student_by_id(user_id)

    return render_template('student_info.html', student=student_record)

@app.route('/food_selection', methods=['GET', 'POST'])
def food_selection():
    """Handles order placement for students and teachers."""
    if not session.get('logged_in') or session.get('user_type') not in ['student', 'teacher']:
        return redirect(url_for('home'))

    if request.method == 'POST':
        try:
            # Get data from menu sheet
            menu_data = menu_sheet.get_all_records()

            # Process order items
            items_ordered = []
            total_price = 0

            for item in menu_data:
                # Checkbox name should match item name
                quantity = request.form.get(item['ItemName']) 
                if quantity and int(quantity) > 0:
                    quantity = int(quantity)
                    items_ordered.append(f"{item['ItemName']} x {quantity}")
                    total_price += item['Price'] * quantity

            if not items_ordered:
                return redirect(url_for('food_selection')) # No items selected

            # Get user info
            user_id = session.get('user_id')
            student_record = get_student_by_id(user_id)

            # Prepare new order row
            order_row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'), # Timestamp
                user_id,
                student_record.get('name', 'N/A'),
                student_record.get('className', 'N/A'),
                ', '.join(items_ordered),
                total_price,
                'Pending' # Status
            ]

            # Write order to Orders sheet
            orders_sheet.append_row(order_row, value_input_option='USER_ENTERED')  # type: ignore
            
            # Calculate health points for nutritious foods
            health_points = calculate_health_points(items_ordered, menu_data)
            if health_points > 0:
                # Get current points
                current_points = get_user_nutrition_points(user_id)
                new_total = current_points + health_points
                # Save updated points to database
                save_user_nutrition_points(user_id, new_total)
                print(f"✓ User earned {health_points} health points! Total: {new_total}")
            
            return redirect(url_for('thank_you'))

        except Exception as e:
            print(f"Order Placement Error: {e}")
            return "Order failed: Database error.", 500

    # GET request: Display menu
    menu_data = menu_sheet.get_all_records()
    return render_template('food_selection.html', menu=menu_data)

@app.route('/google_completion')
def google_completion():
    """Page for completing Google registration with class and student ID."""
    return render_template('google_completion.html')

@app.route('/health_tracking')
def health_tracking():
    """Health tracking dashboard for monitoring BMI, calories, and nutrition points."""
    if not session.get('logged_in') or session.get('user_type') not in ['student', 'teacher']:
        return redirect(url_for('home'))
    
    user_id = session.get('user_id')
    return render_template('health_tracking.html', user_id=user_id)

@app.route('/api/nutrition_stats', methods=['GET'])
def get_nutrition_stats():
    """API endpoint to get today's nutrition stats from database."""
    try:
        if not session.get('logged_in'):
            return {'success': False, 'error': 'Not logged in'}, 401
        
        user_id = session.get('user_id')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get all orders from database
        all_orders = orders_sheet.get_all_records()
        menu_data = menu_sheet.get_all_records()
        
        # Filter today's orders for this user
        today_orders = [o for o in all_orders if str(o.get('userId', '')).strip() == str(user_id).strip() 
                       and o.get('timestamp', '').startswith(today)]
        
        total_calories = 0
        items_count = 0
        healthy_count = 0
        
        # Calculate calories from ordered items
        for order in today_orders:
            items_str = str(order.get('items', ''))
            items_list = [x.strip() for x in items_str.split(',')]
            items_count += len(items_list)
            
            for item_str in items_list:
                # Parse quantity
                parts = item_str.split(' x ')
                item_name = parts[0].strip() if parts else item_str.strip()
                
                # Find in menu data to get calories
                matching_item = next((m for m in menu_data if m.get('ItemName', '').lower() == item_name.lower()), None)
                if matching_item:
                    # Try to extract calories from benefits or price
                    calories = 0
                    benefits = str(matching_item.get('Benefits', '')).lower()
                    # Estimate calories based on benefits/type
                    if 'fruit' in benefits or 'salad' in benefits:
                        calories = 150
                    elif 'pizza' in item_name.lower():
                        calories = 300
                    elif 'burger' in item_name.lower():
                        calories = 250
                    elif 'roll' in item_name.lower():
                        calories = 200
                    elif 'juice' in benefits or 'drink' in benefits:
                        calories = 120
                    elif 'chai' in item_name.lower() or 'coffee' in item_name.lower():
                        calories = 80
                    else:
                        calories = 150  # Default estimate
                    
                    total_calories += calories
                    
                    # Check if healthy
                    if any(x in benefits for x in ['healthy', 'nutrition', 'vitamin', 'fiber', 'protein', 'salad', 'fruit']):
                        healthy_count += 1
        
        # Get nutrition points from database
        nutrition_points = get_user_nutrition_points(user_id)
        
        return {
            'success': True,
            'userId': user_id,
            'date': today,
            'totalCalories': total_calories,
            'itemsOrdered': items_count,
            'healthyChoices': healthy_count,
            'nutritionPercent': min(round((total_calories / 2000) * 100), 100),
            'orderCount': len(today_orders),
            'nutritionPoints': nutrition_points
        }, 200
    
    except Exception as e:
        print(f"Nutrition Stats Error: {e}")
        return {'success': False, 'error': str(e)}, 500

@app.route('/api/health_points', methods=['GET'])
def get_health_points():
    """API endpoint to get user's total nutrition points."""
    try:
        if not session.get('logged_in'):
            return {'success': False, 'error': 'Not logged in'}, 401
        
        user_id = session.get('user_id')
        points = get_user_nutrition_points(user_id)
        
        return {
            'success': True,
            'userId': user_id,
            'nutritionPoints': points
        }, 200
    except Exception as e:
        print(f"Health Points Error: {e}")
        return {'success': False, 'error': str(e)}, 500

@app.route('/api/health_data', methods=['GET'])
def get_health_data():
    """API endpoint to get user's stored BMI, height, and weight."""
    try:
        if not session.get('logged_in'):
            return {'success': False, 'error': 'Not logged in'}, 401
        
        user_id = session.get('user_id')
        health_data = get_user_health_data(user_id)
        
        return {
            'success': True,
            'userId': user_id,
            'data': health_data or {'bmi': '', 'height': '', 'weight': ''}
        }, 200
    except Exception as e:
        print(f"Health Data Fetch Error: {e}")
        return {'success': False, 'error': str(e)}, 500

@app.route('/api/health_data', methods=['POST'])
def save_health_data():
    """API endpoint to save user's BMI, height, and weight."""
    try:
        if not session.get('logged_in'):
            return {'success': False, 'error': 'Not logged in'}, 401
        
        user_id = session.get('user_id')
        data = request.get_json()
        
        height = str(data.get('height', ''))
        bmi = str(data.get('bmi', ''))
        weight = str(data.get('weight', ''))
        
        if not height or not bmi:
            return {'success': False, 'error': 'Height and BMI are required'}, 400
        
        success = save_user_health_data(user_id, height, bmi, weight)
        
        if success:
            return {
                'success': True,
                'message': 'Health data saved successfully',
                'userId': user_id
            }, 200
        else:
            return {'success': False, 'error': 'Failed to save health data'}, 500
    except Exception as e:
        print(f"Health Data Save Error: {e}")
        return {'success': False, 'error': str(e)}, 500

@app.route('/thank_you')
def thank_you():
    """Order confirmation page."""
    return render_template('thank_you.html')

# --- PROTECTED STAFF ROUTES ---

@app.route('/teacher_info')
def teacher_info():
    """Teacher profile page - similar to student_info."""
    if not session.get('logged_in') or session.get('user_type') != 'teacher':
        return redirect(url_for('home'))
    
    return render_template('teacher_info.html')

@app.route('/staff_view')
def staff_view():
    """Staff dashboard displaying main links - STAFF ONLY."""
    if not session.get('logged_in') or session.get('user_type') != 'staff':
        return redirect(url_for('home'))
    
    try:
        students_data = student_sheet.get_all_records()
        total_students = len(students_data)
    except Exception as e:
        print(f"Error fetching students count: {e}")
        total_students = 0
    
    try:
        staff_data = staff_sheet.get_all_records()
        total_staff = len(staff_data)
    except Exception as e:
        print(f"Error fetching staff count: {e}")
        total_staff = 0
    
    try:
        teachers_data = teacher_sheet.get_all_records()
        total_teachers = len(teachers_data)
    except Exception as e:
        print(f"Error fetching teachers count: {e}")
        total_teachers = 0
    
    return render_template('staff_view.html', 
                         total_students=total_students,
                         total_staff=total_staff,
                         total_teachers=total_teachers)

@app.route('/staff_students')
def staff_students():
    """Displays list of registered students for staff/teachers."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return redirect(url_for('home'))
    
    try:
        students_data = student_sheet.get_all_records()
        
        # Optimized: Fetch all nutrition points in ONE call instead of N calls
        all_points = get_all_nutrition_points()
        
        # Map points to students
        for student in students_data:
            student_id = str(student.get('userId') or student.get('admissionNo') or student.get('AdmissionNo') or '').strip()
            student['nutritionPoints'] = all_points.get(student_id, 0)
        
        return render_template('staff_students.html', students=students_data)
    except Exception as e:
        print(f"Staff Students Error: {e}")
        return render_template('staff_students.html', students=[])

@app.route('/staff_list')
def staff_list():
    """Displays list of registered staff members."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return redirect(url_for('home'))
    
    try:
        staff_data = staff_sheet.get_all_records()
        return render_template('staff_list.html', staff_members=staff_data)
    except Exception as e:
        print(f"Staff List Error: {e}")
        return render_template('staff_list.html', staff_members=[])

@app.route('/teachers_list')
def teachers_list():
    """Displays list of registered teachers."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return redirect(url_for('home'))
    
    try:
        teachers_data = teacher_sheet.get_all_records()
        return render_template('teachers_list.html', teachers=teachers_data)
    except Exception as e:
        print(f"Teachers List Error: {e}")
        return render_template('teachers_list.html', teachers=[])

@app.route('/staff_orders')
def staff_orders():
    """Displays current orders for staff/teachers."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return redirect(url_for('home'))

    try:
        # Fetch all records from the Orders sheet
        orders = orders_sheet.get_all_records()
        # You may want to filter or sort orders here (e.g., only 'Pending')

        # This route fixes the /staff_orders Not Found error
        return render_template('staff_orders_dashboard.html', orders=orders)
    except Exception as e:
        print(f"Staff Orders Error: {e}")
        return "Could not retrieve orders.", 500

@app.route('/staff_menu_management')
def staff_menu_management():
    """Displays menu management options."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return redirect(url_for('home'))

    try:
        menu_data = menu_sheet.get_all_records()
        # This route fixes the /staff_menu_management Not Found error
        return render_template('staff_menu_management.html', menu=menu_data)
    except Exception as e:
        print(f"Menu Management Error: {e}")
        return "Could not retrieve menu data.", 500

@app.route('/staff_menu')
def staff_menu():
    """Alias route for staff menu management."""
    return redirect(url_for('staff_menu_management'))

@app.route('/search_results')
def search_results():
    """Displays search results for staff order queries."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return redirect(url_for('home'))
    
    search_query = request.args.get('q', '')
    return render_template('staff_search_results.html', search_query=search_query)

@app.route('/ai_assistant')
def ai_assistant():
    """AI assistant page accessible to everyone."""
    return render_template('ai_assistant.html')

@app.route('/api/ai_chat', methods=['POST'])
def ai_chat():
    """Ultra-advanced AI assistant with complete app knowledge, multilingual support (Hindi & English), and deep understanding."""
    try:
        data = request.get_json()
        message = data.get('message', '').lower().strip()
        conversation_history = data.get('history', [])
        language = data.get('language', 'english').lower()  # 'english' or 'hindi'
        
        # Detect language from message content if not explicitly set
        hindi_chars = any('\u0900' <= char <= '\u097F' for char in data.get('message', ''))
        if hindi_chars:
            language = 'hindi'
        
        # Get current user if logged in
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        import re
        from datetime import datetime, timedelta
        
        # ============================================================
        # COMPREHENSIVE APP KNOWLEDGE BASE
        # ============================================================
        
        APP_KNOWLEDGE = {
            'routes': {
                'student': ['/register', '/student_login', '/student_info', '/food_selection', '/thank_you'],
                'staff': ['/staff_login', '/staff_view', '/staff_students', '/staff_orders', '/staff_menu_management'],
                'api': ['/api/menu', '/api/orders', '/api/orders/place', '/api/orders/update_status', '/api/menu/update', '/api/clear_data'],
                'public': ['/', '/ai_assistant', '/logout']
            },
            'features': {
                'registration': 'Students can register with name, email, password, admission ID, and class',
                'login': 'Dual login system - students use userId, staff use staffId',
                'ordering': 'Students browse menu, select items with quantities, place orders',
                'menu': 'Dynamic menu with images, prices, benefits, and sold-out status',
                'staff_dashboard': 'Staff can view students, manage orders, update menu availability',
                'order_tracking': 'Real-time order status (Pending, Delivered, Cancelled, Unable)',
                'ai_assistant': 'Context-aware AI with natural language understanding'
            },
            'database': {
                'students': ['admissionId', 'userId', 'name', 'password(hashed)', 'email', 'className'],
                'staff': ['admissionId/staffId', 'password', 'name', 'email'],
                'menu': ['id', 'name', 'price', 'benefits', 'image', 'soldOut'],
                'orders': ['orderId(1-5000)', 'timestamp', 'userId', 'userName', 'userClass', 'items', 'totalPrice', 'status']
            },
            'forms': {
                'registration': ['name', 'email', 'password', 'admissionId', 'className'],
                'student_login': ['userId', 'password'],
                'staff_login': ['staffId', 'password'],
                'order': ['items with quantities', 'totalPrice']
            },
            'ui_design': 'Neumorphic soft UI with gradient (#00A9E0 to #F000B8), responsive, toast notifications'
        }
        
        # ============================================================
        # APP FUNCTIONALITY QUERIES
        # ============================================================
        
        # Helper function for multilingual responses
        def translate(en_text, hi_text):
            """Return text based on selected language"""
            return hi_text if language == 'hindi' else en_text
        
        # ============================================================
        # LLM-POWERED INTELLIGENT RESPONSE GENERATION
        # ============================================================
        # Try Gemini LLM first for intelligent, natural responses
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            
            if api_key:
                client = genai.Client(api_key=api_key)
                
                # Build context-aware system prompt
                user_context = f"User is a {user_type if user_type else 'visitor'}"
                
                system_prompt = f"""You are an intelligent AI assistant for a canteen ordering system. 
You help students register, login, place food orders, track orders, and answer questions about the app.
You also assist staff with managing orders, students, and menu items.

{user_context}

Important:
- Be friendly, helpful, and conversational
- Keep responses concise and well-formatted with HTML (use <br> for line breaks, <strong> for bold, <em> for italic)
- If asked about sensitive technical details and user is not staff, politely decline and keep it general
- Always provide clear step-by-step guidance when explaining processes
- Use emojis to make responses engaging
- Respond in the language the user is asking in (detect from their message)
- Never share sensitive data like passwords or staff emails with non-staff users"""
                
                # Build conversation context from history
                messages = [{"role": "system", "content": system_prompt}]
                
                # Add recent conversation history (limit to last 5 exchanges for context)
                for msg in conversation_history[-10:]:
                    messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
                
                # Add current message
                messages.append({"role": "user", "content": data.get('message', '')})
                
                # Call Gemini API with gemini-2.5-flash
                # Format messages as a simple prompt for Gemini
                prompt_text = ""
                for msg in messages:
                    if msg.get("role") == "system":
                        prompt_text += f"{msg.get('content', '')}\n\n"
                    elif msg.get("role") == "user":
                        prompt_text += f"User: {msg.get('content', '')}\n"
                    elif msg.get("role") == "assistant":
                        prompt_text += f"Assistant: {msg.get('content', '')}\n"
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_text
                )
                
                ai_response = response.text or ""
                
                if ai_response:
                    return {'success': True, 'response': ai_response, 'language': language}, 200
        except Exception as e:
            # If LLM fails, log it and fall back to pattern matching
            print(f"LLM API Error (falling back to pattern matching): {e}")
        
        # How to register/login queries
        if any(phrase in message for phrase in ['how to register', 'how do i sign up', 'create account', 'registration process', 'how to create', 'कैसे रजिस्टर', 'रजिस्टर कैसे', 'खाता बनाएं']):
            en_resp = '''🎯 <strong>3 Easy Steps to Get Started</strong><br><br>
            <strong>✅ Step 1:</strong> Click "STUDENT REGISTAR" button<br><br>
            <strong>✅ Step 2:</strong> Fill in these simple details:<br>
            • <strong>Your Name</strong> - What should we call you?<br>
            • <strong>Email</strong> - Your email address<br>
            • <strong>Password</strong> - Something you remember<br>
            • <strong>Student ID</strong> - Your admission number<br>
            • <strong>Class</strong> - Like "10A" or "12B"<br><br>
            <strong>✅ Step 3:</strong> Click "Register" - Done! ✨<br><br>
            <em>💡 You'll get a special ID number to login next time</em>'''
            
            hi_resp = '''🎯 <strong>शुरू करने के लिए 3 आसान कदम</strong><br><br>
            <strong>✅ कदम 1:</strong> "STUDENT REGISTAR" बटन पर क्लिक करें<br><br>
            <strong>✅ कदम 2:</strong> ये सरल जानकारी भरें:<br>
            • <strong>आपका नाम</strong> - हम आपको क्या कहें?<br>
            • <strong>ईमेल</strong> - आपका ईमेल पता<br>
            • <strong>पासवर्ड</strong> - कुछ जो आप याद रखें<br>
            • <strong>छात्र आईडी</strong> - आपका प्रवेश नंबर<br>
            • <strong>कक्षा</strong> - जैसे "10A" या "12B"<br><br>
            <strong>✅ कदम 3:</strong> "Register" पर क्लिक करें - हो गया! ✨<br><br>
            <em>💡 अगली बार लॉगिन करने के लिए आपको एक विशेष नंबर मिलेगा</em>'''
            
            return {'success': True, 'response': translate(en_resp, hi_resp), 'language': language}, 200
        
        # Login process queries
        if any(phrase in message for phrase in ['how to login', 'how do i log in', 'sign in process', 'login steps']):
            if 'staff' in message:
                en_staff = '''🔐 <strong>Staff Login (Easy!)</strong><br><br>
                <strong>Just need 2 things:</strong><br>
                1️⃣ <strong>Staff ID</strong> - Your email or staff number<br>
                2️⃣ <strong>Password</strong> - Your password<br><br>
                <strong>Test Example:</strong><br>
                • ID: <code>s.18.20@slps.one</code><br>
                • Password: <code>12345678</code><br><br>
                👉 Then you see all orders, students, and food menu!'''
                
                hi_staff = '''🔐 <strong>स्टाफ लॉगिन (आसान!)</strong><br><br>
                <strong>बस 2 चीजें चाहिए:</strong><br>
                1️⃣ <strong>स्टाफ आईडी</strong> - आपकी ईमेल या स्टाफ नंबर<br>
                2️⃣ <strong>पासवर्ड</strong> - आपका पासवर्ड<br><br>
                <strong>उदाहरण:</strong><br>
                • ID: <code>s.18.20@slps.one</code><br>
                • Password: <code>12345678</code><br><br>
                👉 फिर आप सभी ऑर्डर, छात्र, और खाना देख सकते हैं!'''
                
                return {'success': True, 'response': translate(en_staff, hi_staff), 'language': language}, 200
            else:
                en_student = '''🔐 <strong>Student Login (Simple!)</strong><br><br>
                <strong>You need 2 things:</strong><br>
                1️⃣ <strong>Your ID Number</strong> - You got this after registration<br>
                2️⃣ <strong>Your Password</strong> - The one you created<br><br>
                <strong>Forgot your ID?</strong><br>
                It's shown on the registration confirmation page<br>
                Just look at your email or ask staff<br><br>
                👉 After login = Order food! 🍽️'''
                
                hi_student = '''🔐 <strong>छात्र लॉगिन (आसान!)</strong><br><br>
                <strong>आपको 2 चीजें चाहिए:</strong><br>
                1️⃣ <strong>आपका आईडी नंबर</strong> - रजिस्ट्रेशन के बाद मिला था<br>
                2️⃣ <strong>आपका पासवर्ड</strong> - जो आपने बनाया था<br><br>
                <strong>आईडी भूल गए?</strong><br>
                यह पंजीकरण पुष्टि पृष्ठ पर दिखाया गया था<br>
                अपना ईमेल देखें या स्टाफ से पूछें<br><br>
                👉 लॉगिन के बाद = खाना मंगवाएं! 🍽️'''
                
                return {'success': True, 'response': translate(en_student, hi_student), 'language': language}, 200
        
        # Ordering process queries
        if any(phrase in message for phrase in ['how to order', 'place order', 'buy food', 'ordering process', 'how do i get food']):
            en_order = '''🍽️ <strong>Easy Order Process (4 Steps)</strong><br><br>
            <strong>1️⃣ Login:</strong> Enter your ID and password<br><br>
            <strong>2️⃣ Look at Food:</strong><br>
            Click "Food Selection"<br>
            See pictures, prices, and descriptions<br><br>
            <strong>3️⃣ Pick What You Like:</strong><br>
            Pick items you want<br>
            Choose quantity (1, 2, 3...)<br>
            See total price 💵<br><br>
            <strong>4️⃣ Order:</strong><br>
            Click "Place Order"<br>
            See confirmation ✅<br><br>
            <em>💡 Your order status changes from "Pending" → "Delivered" when ready!</em>'''
            
            hi_order = '''🍽️ <strong>आसान ऑर्डर प्रक्रिया (4 कदम)</strong><br><br>
            <strong>1️⃣ लॉगिन:</strong> अपनी आईडी और पासवर्ड डालें<br><br>
            <strong>2️⃣ खाना देखें:</strong><br>
            "Food Selection" पर क्लिक करें<br>
            तस्वीरें, कीमतें और विवरण देखें<br><br>
            <strong>3️⃣ जो पसंद हो, चुनें:</strong><br>
            जो चीजें चाहिए वो चुनें<br>
            मात्रा चुनें (1, 2, 3...)<br>
            कुल कीमत देखें 💵<br><br>
            <strong>4️⃣ ऑर्डर करें:</strong><br>
            "Place Order" पर क्लिक करें<br>
            पुष्टि देखें ✅<br><br>
            <em>💡 जब खाना तैयार हो जाता है तो स्थिति बदलकर "Delivered" हो जाती है!</em>'''
            
            return {'success': True, 'response': translate(en_order, hi_order), 'language': language}, 200
        
        # Menu/food item queries
        if any(phrase in message for phrase in ['menu', 'food items', 'what foods', 'menu system', 'available items', 'show menu', 'tell menu', 'what do you have', 'what\'s available', 'what is available', 'food', 'what food', 'available', 'खाना', 'मेनू']):
            try:
                menu_items = menu_sheet.get_all_records()
                if not menu_items:
                    return {'success': True, 'response': '🍽️ <strong>No items available right now</strong><br>Check back soon for menu updates!'}, 200
                
                # Build menu items list with names and prices
                menu_response = '<strong>🍴 CANTEEN MENU - AVAILABLE ITEMS</strong><br><br>'
                
                for idx, item in enumerate(menu_items, 1):
                    name = item.get('name', 'Unknown Item')
                    price = item.get('price', '0')
                    benefits = item.get('benefits', '')
                    sold_out = item.get('soldOut', '').lower() in ['yes', 'true', '1']
                    
                    # Format as list item
                    status = '❌ SOLD OUT' if sold_out else '✅ Available'
                    menu_response += f'<strong>{idx}. {name}</strong><br>'
                    menu_response += f'   💵 Price: ₹{price}<br>'
                    if benefits:
                        menu_response += f'   ⭐ {benefits}<br>'
                    menu_response += f'   {status}<br><br>'
                
                menu_response += '<em>Click "Food Selection" to order!</em>'
                return {'success': True, 'response': menu_response}, 200
            except Exception as e:
                print(f"Menu query error: {e}")
                return {'success': True, 'response': '🍽️ <strong>Menu Available</strong><br>Click "Food Selection" to see all items and place orders!'}, 200
        
        # Database/technical queries - PROTECTED
        if any(phrase in message for phrase in ['database', 'data structure', 'how data stored', 'backend', 'google sheets']):
            if user_type == 'staff':
                return {'success': True, 'response': '''<strong>💾 Database Architecture:</strong><br><br>
                <strong>Technology:</strong> Google Sheets API via gspread<br>
                <strong>Spreadsheet ID:</strong> <code>1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI</code><br><br>
                <strong>4 Worksheets:</strong><br><br>
                📋 <strong>Students Sheet:</strong><br>
                • admissionId, userId, name, password(hashed), email, className<br><br>
                👔 <strong>Staff Sheet:</strong><br>
                • staffId/admissionId, password, name, email<br><br>
                🍽️ <strong>Menu Sheet:</strong><br>
                • id, name, price, benefits, image, soldOut<br><br>
                📦 <strong>Orders Sheet:</strong><br>
                • orderId (1-5000 cycling), timestamp, userId, userName, userClass, items, totalPrice, status<br><br>
                <strong>Authentication:</strong> Service account with Base64 encoded credentials<br>
                <strong>Security:</strong> Passwords hashed with Werkzeug (pbkdf2:sha256)<br>
                <strong>API Access:</strong> All CRUD operations via Flask endpoints'''}, 200
            else:
                return {'success': True, 'response': '''<strong>💾 Database Architecture:</strong><br><br>
                The application uses a secure, scalable database system with proper authentication and encryption.<br><br>
                🔒 <strong>Security Features:</strong><br>
                • End-to-end encrypted storage<br>
                • Password hashing (pbkdf2:sha256)<br>
                • Role-based access control<br>
                • Secure API endpoints<br><br>
                Your data is safe and secure! Detailed technical information is restricted to authorized staff.'''}, 200
        
        # Staff features queries - PROTECTED (only show to staff)
        if any(phrase in message for phrase in ['staff features', 'staff can do', 'admin panel', 'staff dashboard', 'staff capabilities']):
            if user_type == 'staff':
                return {'success': True, 'response': '''<strong>👔 Staff Dashboard Features:</strong><br><br>
                <strong>📊 Main Dashboard (<code>/staff_view</code>):</strong><br>
                • Total student count<br>
                • Quick navigation links<br><br>
                <strong>👥 Student Management (<code>/staff_students</code>):</strong><br>
                • View all registered students<br>
                • See admission IDs, names, emails, classes<br><br>
                <strong>📦 Order Management (<code>/staff_orders</code>):</strong><br>
                • View all orders with details<br>
                • Update order status (Pending/Delivered/Cancelled/Unable)<br>
                • Filter and search orders<br>
                • Real-time status updates<br><br>
                <strong>🍴 Menu Management (<code>/staff_menu_management</code>):</strong><br>
                • View all menu items<br>
                • Toggle sold-out status<br>
                • See item details (price, benefits, image)<br><br>
                <strong>🗑️ Data Management:</strong><br>
                • Clear all orders and students (via API)<br>
                • Preserve staff credentials<br><br>
                <strong>Test Login:</strong><br>
                • ID: s.18.20@slps.one<br>
                • Password: 12345678'''}, 200
            else:
                return {'success': True, 'response': '''<strong>👔 Staff Dashboard Features:</strong><br><br>
                The canteen app has a comprehensive staff management system, but detailed features are only available to authorized staff members.<br><br>
                🔐 <strong>For Staff Access:</strong> Please login with your staff credentials on the homepage to unlock full details about:<br>
                • Student management<br>
                • Order management<br>
                • Menu control<br>
                • System administration<br><br>
                Contact your administrator if you need staff access!'''}, 200
        
        # Nutrition/health queries
        if any(phrase in message for phrase in ['nutrition', 'healthy', 'calories', 'diet', 'health', 'benefits']):
            try:
                menu_items = menu_sheet.get_all_records()
                healthy_items = [item for item in menu_items if 'protein' in item.get('benefits', '').lower() or 'fresh' in item.get('benefits', '').lower()]
                response = f'<strong>🥗 Nutrition & Health Information:</strong><br><br>'
                if healthy_items:
                    response += f'✅ Found {len(healthy_items)} nutritious items:<br>'
                    for item in healthy_items[:5]:
                        response += f"• <strong>{item.get('name', '')}</strong> - {item.get('benefits', '')}<br>"
                else:
                    response += 'All menu items are carefully selected for nutritional value. Check with staff for detailed nutritional info!'
                return {'success': True, 'response': response}, 200
            except:
                pass

        # Troubleshooting/help queries
        if any(phrase in message for phrase in ['problem', 'error', 'bug', 'not working', 'issue', 'help', 'support', 'trouble', 'broken']):
            return {'success': True, 'response': '''<strong>🆘 Need Help?</strong><br><br>
            <strong>Common Issues & Solutions:</strong><br><br>
            🔓 <strong>Can't login?</strong><br>
            • Check if you've registered first<br>
            • Verify your User ID and password<br>
            • Clear browser cache and try again<br><br>
            🍽️ <strong>Can't place order?</strong><br>
            • Ensure items are available (not sold out)<br>
            • Check if you're logged in as a student<br>
            • Refresh the page and retry<br><br>
            📱 <strong>App running slow?</strong><br>
            • Check your internet connection<br>
            • Try a different browser<br>
            • Clear cache and cookies<br><br>
            💬 <strong>Still need help?</strong><br>
            • Use the feedback button to report issues<br>
            • Contact your administrator<br>
            • Ask the AI assistant (me!) for more help!'''}, 200

        # Mobile/device queries
        if any(phrase in message for phrase in ['mobile', 'phone', 'tablet', 'responsive', 'app', 'ios', 'android']):
            return {'success': True, 'response': '''<strong>📱 Mobile & Device Support:</strong><br><br>
            ✅ <strong>Fully Responsive Design</strong><br>
            The app works perfectly on all devices:<br>
            • Smartphones (iOS & Android)<br>
            • Tablets<br>
            • Desktops & Laptops<br><br>
            🔄 <strong>Features:</strong><br>
            • Automatic layout adjustment<br>
            • Touch-optimized buttons<br>
            • Fast loading on mobile<br>
            • Offline-friendly design<br><br>
            📲 <strong>Best Experience:</strong><br>
            • Use latest browser version<br>
            • Enable JavaScript<br>
            • Good internet connection<br>
            • Landscape mode for better view'''}, 200

        # Features/capabilities queries  
        if any(phrase in message for phrase in ['feature', 'capability', 'can you do', 'what can', 'what do you', 'capabilities']):
            return {'success': True, 'response': '''<strong>⭐ AI Assistant Capabilities:</strong><br><br>
            🤖 <strong>What I Can Do:</strong><br>
            ✅ Answer questions about the app<br>
            ✅ Guide you through registration<br>
            ✅ Explain how to place orders<br>
            ✅ Show menu information<br>
            ✅ Help with technical issues<br>
            ✅ Provide app guidance<br>
            ✅ Answer general questions<br><br>
            💡 <strong>Special Features:</strong><br>
            🔍 Search chat history<br>
            ⚙️ Customize settings<br>
            📋 Copy responses<br>
            👍 Rate responses<br>
            📥 Export conversations<br>
            🗑️ Clear chat history<br><br>
            Try asking me about: how to register, ordering, menu, staff features, help, or anything else!'''}, 200

        # UI/Design queries
        if any(phrase in message for phrase in ['design', 'ui', 'interface', 'colors', 'theme', 'neumorphic']):
            return {'success': True, 'response': '''<strong>🎨 UI/UX Design System:</strong><br><br>
            <strong>Design Theme:</strong> Neumorphic Soft UI<br><br>
            <strong>Color Palette:</strong><br>
            • Primary Gradient: <span style="background: linear-gradient(135deg, #00A9E0, #F000B8); color: white; padding: 2px 8px; border-radius: 5px;">#00A9E0 → #F000B8</span><br>
            • Accent Blue: #00A9E0<br>
            • Accent Magenta: #F000B8<br>
            • Background: #f8f9fa<br>
            • White Cards: rgba(255, 255, 255, 0.98)<br><br>
            <strong>Features:</strong><br>
            • Soft shadows (neumorphism)<br>
            • Smooth animations (cubic-bezier transitions)<br>
            • Gradient buttons & headers<br>
            • Responsive grid layouts<br>
            • Toast notifications<br>
            • Real-time form validation<br>
            • Mobile-first design<br><br>
            <strong>Floating AI Button:</strong><br>
            • Position: Fixed bottom-right<br>
            • Pulsing animation<br>
            • Gradient background<br>
            • 3D hover effects<br><br>
            <strong>CSS File:</strong> <code>static/style2.css</code>'''}, 200
        
        # Routes/endpoints queries
        if any(phrase in message for phrase in ['routes', 'endpoints', 'api', 'urls', 'paths available']):
            routes_html = '''<strong>🛣️ Complete Route Map:</strong><br><br>
            <strong>🏠 Public Routes:</strong><br>
            • <code>/</code> - Homepage/Login portal<br>
            • <code>/ai_assistant</code> - AI Chat Interface<br>
            • <code>/logout</code> - Clear session<br><br>
            <strong>👨‍🎓 Student Routes:</strong><br>
            • <code>GET /register</code> - Registration form<br>
            • <code>POST /student_register</code> - Process registration<br>
            • <code>POST /student_login</code> - Login<br>
            • <code>/student_info</code> - Profile page<br>
            • <code>/food_selection</code> - Browse & order menu<br>
            • <code>/thank_you</code> - Order confirmation<br><br>
            <strong>👔 Staff Routes:</strong><br>
            • <code>POST /staff_login</code> - Staff login<br>
            • <code>/staff_view</code> - Dashboard<br>
            • <code>/staff_students</code> - Student list<br>
            • <code>/staff_orders</code> - Order management<br>
            • <code>/staff_menu_management</code> - Menu controls<br>
            • <code>/search_results</code> - Search functionality<br><br>
            <strong>🔌 API Endpoints:</strong><br>
            • <code>GET /api/menu</code> - Fetch menu items<br>
            • <code>GET /api/orders</code> - Get all orders (staff)<br>
            • <code>POST /api/orders/place</code> - Place order (student)<br>
            • <code>POST /api/orders/update_status</code> - Update order (staff)<br>
            • <code>POST /api/menu/update</code> - Toggle soldOut (staff)<br>
            • <code>POST /api/clear_data</code> - Clear database (staff)<br>
            • <code>POST /api/ai_chat</code> - AI assistant'''
            return {'success': True, 'response': routes_html}, 200
        
        # Security/authentication queries
        if any(phrase in message for phrase in ['security', 'authentication', 'password', 'hashing', 'session']):
            return {'success': True, 'response': '''<strong>🔒 Security Implementation:</strong><br><br>
            <strong>Password Security:</strong><br>
            • Algorithm: pbkdf2:sha256<br>
            • Library: Werkzeug security<br>
            • Functions: generate_password_hash(), check_password_hash()<br>
            • Passwords never stored in plain text<br><br>
            <strong>Session Management:</strong><br>
            • Server-side Flask sessions<br>
            • Secret key: Environment variable<br>
            • Session data: logged_in, user_id, user_type<br>
            • Auto-clear on logout<br><br>
            <strong>Authorization:</strong><br>
            • Role-based access (student/staff)<br>
            • Route protection with session checks<br>
            • API endpoints require authentication<br><br>
            <strong>Google Sheets Access:</strong><br>
            • Service account authentication<br>
            • Base64 encoded credentials (GCP_BASE64_CREDS)<br>
            • OAuth2 scopes restricted<br>
            • Email: sheets-access-account@canteen-app-376c7.iam.gserviceaccount.com'''}, 200
        
        # Form field queries
        if any(phrase in message for phrase in ['form fields', 'registration fields', 'what to fill', 'input fields', 'form data']):
            if 'registration' in message or 'register' in message or 'sign up' in message:
                return {'success': True, 'response': '''<strong>📋 Registration Form Fields:</strong><br><br>
                <strong>Required Fields:</strong><br>
                1. <strong>Name</strong> - Your full name<br>
                2. <strong>Email</strong> - Valid email address<br>
                3. <strong>Password</strong> - Secure password (will be hashed)<br>
                4. <strong>Admission ID</strong> - Your student identification<br>
                5. <strong>Class Name</strong> - Your class (e.g., "Class 10A")<br><br>
                <strong>Auto-Generated:</strong><br>
                • User ID - Sequential number starting from 1<br><br>
                <strong>Validation:</strong><br>
                • All fields required (400 error if missing)<br>
                • Email format validation<br>
                • Password strength check<br>
                • Real-time feedback with toast notifications<br><br>
                <strong>After Submit:</strong> Auto-login + redirect to student_info page'''}, 200
            elif 'login' in message:
                return {'success': True, 'response': '''<strong>🔐 Login Form Fields:</strong><br><br>
                <strong>Student Login:</strong><br>
                • User ID (auto-generated number)<br>
                • Password<br><br>
                <strong>Staff Login:</strong><br>
                • Staff ID (e.g., s.18.20@slps.one)<br>
                • Password (e.g., 12345678)<br><br>
                Both use POST requests with JSON/form data and session-based auth.'''}, 200
            else:
                return {'success': True, 'response': '''<strong>📝 All Form Types:</strong><br><br>
                1. <strong>Registration</strong>: name, email, password, admissionId, className<br>
                2. <strong>Student Login</strong>: userId, password<br>
                3. <strong>Staff Login</strong>: staffId, password<br>
                4. <strong>Order Placement</strong>: items (with quantities), totalPrice<br>
                5. <strong>Menu Update</strong>: itemId, soldOut status<br>
                6. <strong>Order Status Update</strong>: orderId, status<br><br>
                All forms use real-time validation and toast notifications!'''}, 200
        
        # Error handling queries
        if any(phrase in message for phrase in ['error', 'not working', 'fails', 'problem', 'issue', 'bug']):
            return {'success': True, 'response': '''<strong>🔧 Common Issues & Solutions:</strong><br><br>
            <strong>Registration Fails (500 error):</strong><br>
            • Check Google Sheets API connection<br>
            • Verify GCP_BASE64_CREDS environment variable<br>
            • Ensure service account has sheet access<br><br>
            <strong>Login Failed (401):</strong><br>
            • Verify userId/staffId exists in database<br>
            • Check password is correct<br>
            • Ensure password was hashed during registration<br><br>
            <strong>Order Not Saving:</strong><br>
            • Must be logged in as student<br>
            • Check Orders sheet column headers match code<br>
            • Verify items array format<br><br>
            <strong>Menu Items Not Loading:</strong><br>
            • Check Menu sheet structure<br>
            • Verify image paths start with /static/images/<br>
            • Check API response in browser console<br><br>
            <strong>Template Not Found (404):</strong><br>
            • Ensure templates/ directory exists<br>
            • Check file name spelling<br>
            • Verify route matches template name<br><br>
            <strong>Debug Mode:</strong> Flask runs with debug=True, check console for detailed tracebacks!'''}, 200
        
        # Workflow queries
        if any(phrase in message for phrase in ['workflow', 'run button', 'how to start', 'run app', 'start server']):
            return {'success': True, 'response': '''<strong>⚙️ Workflows & Running the App:</strong><br><br>
            <strong>Main Workflow: "Canteen Ordering System"</strong><br>
            • Command: <code>python app.py</code><br>
            • Status: Running (read-only)<br>
            • Port: 5000 (forwarded to 80/443)<br>
            • Mode: Development server with debug=True<br><br>
            <strong>Run Button:</strong> Executes the main workflow<br><br>
            <strong>Other Workflows:</strong><br>
            • "Serve static" - For static HTML serving<br>
            • "Run app.py" - Alternative Python runner<br><br>
            <strong>Console Output Shows:</strong><br>
            • Google Sheets initialization status<br>
            • Service account email<br>
            • Loaded worksheets (Students, Staff, Menu, Orders)<br>
            • Flask server running on 0.0.0.0:5000<br>
            • Request logs<br><br>
            <strong>Auto-Restart:</strong> Code changes trigger automatic reload in debug mode!'''}, 200
        
        # Order status query with improved pattern matching
        order_patterns = [
            r'order\s*#?(\d+)',
            r'#(\d+)',
            r'order\s+number\s+(\d+)',
            r'order\s+id\s+(\d+)'
        ]
        
        order_num = None
        for pattern in order_patterns:
            match = re.search(pattern, message)
            if match:
                order_num = match.group(1)
                break
        
        if order_num:
            try:
                all_values = orders_sheet.get_all_values()
                if len(all_values) < 2:
                    return {'success': True, 'response': '📋 No orders found in the system yet.'}, 200
                
                headers = [h.strip() for h in all_values[0]]
                orders = []
                for row in all_values[1:]:
                    orders.append(dict(zip(headers, row)))
                
                order = next((o for o in orders if str(o.get('orderId', '')).strip() == order_num), None)
                
                if order:
                    status = order.get('status', 'pending').lower()
                    items = order.get('items', 'N/A')
                    total = order.get('totalPrice', 0)
                    timestamp = order.get('timestamp', 'N/A')
                    user_name = order.get('userName', 'N/A')
                    
                    status_emoji = '✅' if status == 'delivered' else '⏳' if status == 'pending' else '❌'
                    status_msg = {
                        'delivered': 'Your order is ready for pickup at the counter!',
                        'pending': 'Your order is being prepared by our kitchen staff.',
                        'cancelled': 'This order was cancelled.',
                        'unable': 'We were unable to complete this order. Please contact staff.'
                    }.get(status, 'Status unknown.')
                    
                    response = f"""<div style="padding: 10px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 10px;">
                    <strong>📦 Order #{order_num}</strong><br>
                    <strong>Customer:</strong> {user_name}<br>
                    <strong>Status:</strong> {status_emoji} {status.upper()}<br>
                    <strong>Items:</strong> {items}<br>
                    <strong>Total:</strong> ₹{total}<br>
                    <strong>Ordered:</strong> {timestamp}<br><br>
                    <em>{status_msg}</em>
                    </div>"""
                    
                    return {'success': True, 'response': response}, 200
                else:
                    return {'success': True, 'response': f'🔍 Order #{order_num} not found. Please verify the order number.'}, 200
            except Exception as e:
                print(f"Error fetching order: {e}")
                return {'success': True, 'response': '❌ Sorry, I encountered an error retrieving order information.'}, 200
        
        # All my orders
        if any(phrase in message for phrase in ['all orders', 'my orders', 'order history', 'past orders']):
            if not user_id or user_type != 'student':
                return {'success': True, 'response': '🔐 Please log in as a student to view your order history.'}, 200
            
            try:
                all_values = orders_sheet.get_all_values()
                if len(all_values) < 2:
                    return {'success': True, 'response': '📋 You haven\'t placed any orders yet. Visit the menu to get started!'}, 200
                
                headers = [h.strip() for h in all_values[0]]
                orders = []
                for row in all_values[1:]:
                    orders.append(dict(zip(headers, row)))
                
                user_orders = [o for o in orders if str(o.get('userId', '')).strip() == str(user_id)]
                
                if user_orders:
                    response = f"<strong>📜 Your Order History ({len(user_orders)} orders):</strong><br><br>"
                    for order in user_orders[-5:]:  # Show last 5 orders
                        status = order.get('status', 'pending').lower()
                        status_emoji = '✅' if status == 'delivered' else '⏳' if status == 'pending' else '❌'
                        response += f"{status_emoji} Order #{order.get('orderId', 'N/A')} - ₹{order.get('totalPrice', 0)} - {status.upper()}<br>"
                    
                    if len(user_orders) > 5:
                        response += f"<br><em>...and {len(user_orders) - 5} more orders</em>"
                    
                    return {'success': True, 'response': response}, 200
                else:
                    return {'success': True, 'response': '📋 You haven\'t placed any orders yet.'}, 200
            except Exception as e:
                print(f"Error fetching user orders: {e}")
                return {'success': True, 'response': '❌ Sorry, I could not retrieve your orders.'}, 200
        
        # Advanced order tracking with predictions
        if any(phrase in message for phrase in ['my order', 'latest order', 'last order', 'recent order', 'order status']):
            if not user_id or user_type != 'student':
                return {'success': True, 'response': '🔐 Please log in as a student to view your orders.'}, 200
            
            try:
                all_values = orders_sheet.get_all_values()
                if len(all_values) < 2:
                    return {'success': True, 'response': '📋 You haven\'t placed any orders yet. 🍽️ Start ordering now!'}, 200
                
                headers = [h.strip() for h in all_values[0]]
                orders = []
                for row in all_values[1:]:
                    orders.append(dict(zip(headers, row)))
                
                user_orders = [o for o in orders if str(o.get('userId', '')).strip() == str(user_id)]
                
                if user_orders:
                    latest = user_orders[-1]
                    order_id = latest.get('orderId', 'N/A')
                    status = latest.get('status', 'pending').lower()
                    items = latest.get('items', 'N/A')
                    total = latest.get('totalPrice', 0)
                    timestamp = latest.get('timestamp', 'N/A')
                    
                    # Smart predictions
                    status_emoji = '✅' if status == 'delivered' else '⏳' if status == 'pending' else '❌'
                    status_msg = {
                        'delivered': '✅ Ready for pickup! Come get it!',
                        'pending': '⏳ Being prepared... Should be ready in ~10-15 mins',
                        'cancelled': '❌ Order was cancelled',
                        'unable': '⚠️ Issue with order - Check with staff'
                    }.get(status, '❓ Status unknown')
                    
                    # Order frequency insights
                    total_spent = sum(float(o.get('totalPrice', 0)) for o in user_orders)
                    avg_order_val = total_spent / len(user_orders)
                    
                    response = f"""<strong>🎯 YOUR LATEST ORDER (#{order_id})</strong><br><br>
                    <strong>Status:</strong> {status_emoji} {status.upper()}<br>
                    <strong>Items:</strong> {items}<br>
                    <strong>Amount:</strong> ₹{total}<br>
                    <strong>Ordered:</strong> {timestamp}<br><br>
                    
                    <em>{status_msg}</em><br><br>
                    
                    <strong>📊 Your Stats:</strong><br>
                    • Total Orders: {len(user_orders)}<br>
                    • Total Spent: ₹{total_spent:.0f}<br>
                    • Average Order: ₹{avg_order_val:.0f}<br><br>
                    
                    <em>💡 You're a loyal customer! 🌟</em>"""
                    
                    return {'success': True, 'response': response}, 200
                else:
                    return {'success': True, 'response': '📋 You haven\'t placed any orders yet. 🍽️ Start your first order!'}, 200
            except Exception as e:
                print(f"Error fetching user orders: {e}")
                return {'success': True, 'response': '❌ Sorry, I could not retrieve your orders.'}, 200
        
        # Beverage queries
        if any(phrase in message for phrase in ['chai', 'coffee', 'beverage', 'drink', 'tea', 'milkshake']):
            return {'success': True, 'response': '''<strong>☕ Beverages Available:</strong><br><br>
            <strong>🍵 Chai (Indian Tea)</strong><br>
            • Price: ₹30<br>
            • Benefits: Warm and refreshing Indian tea<br>
            • Perfect for: Breakfast, snack time, any time!<br><br>
            <strong>☕ Coffee</strong><br>
            • Price: ₹40<br>
            • Benefits: Strong and aromatic coffee<br>
            • Perfect for: Morning boost, afternoon energy<br><br>
            <strong>🥤 Chocolate Milkshake</strong><br>
            • Price: ₹70<br>
            • Benefits: Energy booster!<br>
            • Perfect for: After meals, treats<br><br>
            All beverages are freshly prepared and available on the menu. Visit <strong>Food Selection</strong> to order!'''}, 200
        
        # Smart recommendations based on time of day
        if any(word in message for word in ['recommend', 'suggest', 'what should i', 'good to eat']):
            try:
                menu_items = menu_sheet.get_all_records()
                available = [item for item in menu_items if not item.get('soldOut')]
                
                current_hour = datetime.now().hour
                
                # Time-based recommendations
                if 6 <= current_hour < 11:
                    breakfast_items = [i for i in available if any(k in i.get('name', '').lower() for k in ['sandwich', 'samosa', 'patties'])]
                    if breakfast_items:
                        item = breakfast_items[0]
                        return {'success': True, 'response': f"🌅 <strong>Morning Special!</strong><br><br>I recommend <strong>{item.get('name')}</strong> for ₹{item.get('price')}<br><em>{item.get('benefits', 'Perfect for breakfast!')}</em><br><br>Would you like to see more options?"}, 200
                elif 11 <= current_hour < 16:
                    lunch_items = [i for i in available if any(k in i.get('name', '').lower() for k in ['burger', 'noodles', 'pizza', 'roll', 'pasta'])]
                    if lunch_items:
                        item = lunch_items[0]
                        return {'success': True, 'response': f"🌞 <strong>Lunch Time!</strong><br><br>Try our <strong>{item.get('name')}</strong> for ₹{item.get('price')}<br><em>{item.get('benefits', 'Filling and delicious!')}</em><br><br>Perfect for a hearty meal!"}, 200
                else:
                    snack_items = [i for i in available if any(k in i.get('name', '').lower() for k in ['chips', 'potato', 'milkshake'])]
                    if snack_items:
                        item = snack_items[0]
                        return {'success': True, 'response': f"🌙 <strong>Evening Snack!</strong><br><br><strong>{item.get('name')}</strong> is perfect right now!<br>₹{item.get('price')} - <em>{item.get('benefits', 'Great snack!')}</em>"}, 200
            except Exception as e:
                print(f"Error with recommendations: {e}")
        
        # Menu queries with advanced filters
        if any(word in message for word in ['menu', 'available', 'food', 'items', 'eat', 'show']):
            try:
                menu_items = menu_sheet.get_all_records()
                
                # Check for specific item search
                item_keywords = ['burger', 'pizza', 'salad', 'roll', 'milkshake', 'samosa', 'pasta', 'noodles', 'sandwich', 'patties', 'chips', 'paneer', 'potato', 'chole']
                for keyword in item_keywords:
                    if keyword in message:
                        matching = [item for item in menu_items if keyword in item.get('name', '').lower() and not item.get('soldOut')]
                        if matching:
                            response = f"<strong>🔍 Found {len(matching)} item(s) with '{keyword}':</strong><br><br>"
                            for item in matching:
                                response += f"• <strong>{item.get('name')}</strong> - ₹{item.get('price')}<br>"
                                response += f"  <em>{item.get('benefits', '')}</em><br><br>"
                            return {'success': True, 'response': response}, 200
                
                # Check for price filters
                cheap_keywords = ['cheap', 'affordable', 'under', 'less than', 'budget']
                expensive_keywords = ['expensive', 'premium', 'costly']
                
                if any(kw in message for kw in cheap_keywords):
                    available = [item for item in menu_items if not item.get('soldOut') and float(item.get('price', 999)) <= 100]
                    title = "💰 Affordable Menu Items (Under ₹100):"
                elif any(kw in message for kw in expensive_keywords):
                    available = [item for item in menu_items if not item.get('soldOut') and float(item.get('price', 0)) > 100]
                    title = "⭐ Premium Menu Items (Over ₹100):"
                else:
                    available = [item for item in menu_items if not item.get('soldOut')]
                    title = "🍴 Available Menu Items:"
                
                if available:
                    # Sort by popularity (could be based on order frequency in future)
                    response = f"<strong>{title}</strong><br><br>"
                    for idx, item in enumerate(available[:10], 1):
                        name = item.get('name', 'Unknown')
                        price = item.get('price', 0)
                        benefits = item.get('benefits', '')
                        emoji = '🔥' if idx <= 3 else '⭐' if idx <= 5 else '•'
                        response += f"{emoji} <strong>{name}</strong> - ₹{price}"
                        if benefits:
                            response += f"<br>  <em>{benefits}</em>"
                        response += "<br><br>"
                    
                    if len(available) > 10:
                        response += f"<em>...and {len(available) - 10} more items!</em>"
                    
                    return {'success': True, 'response': response}, 200
                else:
                    return {'success': True, 'response': '😔 No items match your criteria right now.'}, 200
            except Exception as e:
                print(f"Error fetching menu: {e}")
                return {'success': True, 'response': '❌ Sorry, I could not fetch the menu.'}, 200
        
        # Greetings - Multilingual
        en_greetings = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
        hi_greetings = ['नमस्ते', 'हाय', 'हेलो', 'शुभ प्रभात', 'शुभ संध्या']
        
        if any(greeting in message for greeting in en_greetings + hi_greetings):
            en_responses = [
                '👋 Hello! How can I assist you with your canteen needs today?',
                '😊 Hi there! Ready to help you with orders and menu questions!',
                '🤖 Hey! I\'m your AI canteen assistant. What would you like to know?'
            ]
            hi_responses = [
                '👋 नमस्ते! मैं आपकी कैंटीन की जरूरतों के साथ आपकी कैसे मदद कर सकता हूं?',
                '😊 नमस्कार! ऑर्डर और मेनू के सवालों में आपकी मदद के लिए तैयार!',
                '🤖 अरे! मैं आपका AI कैंटीन सहायक हूं। आप क्या जानना चाहते हैं?'
            ]
            import random
            response_list = hi_responses if language == 'hindi' else en_responses
            return {'success': True, 'response': random.choice(response_list), 'language': language}, 200
        
        # Advanced Analytics & Popular items
        if any(phrase in message for phrase in ['popular', 'trending', 'best seller', 'most ordered', 'favorite', 'analytics', 'statistics', 'insights']):
            try:
                orders = orders_sheet.get_all_records()
                menu_items = menu_sheet.get_all_records()
                
                # Calculate comprehensive analytics
                item_counts = {}
                item_revenue = {}
                
                for order in orders:
                    items_str = order.get('items', '')
                    total = float(order.get('totalPrice', 0))
                    if items_str:
                        item_parts = items_str.split(', ')
                        for item_part in item_parts:
                            if ' x ' in item_part:
                                name, qty = item_part.rsplit(' x ', 1)
                                name = name.strip()
                                qty = int(qty.strip())
                                item_counts[name] = item_counts.get(name, 0) + qty
                                item_revenue[name] = item_revenue.get(name, 0) + (total / len(item_parts))
                
                if item_counts:
                    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:8]
                    
                    response = '''<strong>🔥 ADVANCED ANALYTICS & INSIGHTS 📊</strong><br><br>
                    <strong>Top Trending Items:</strong><br>'''
                    
                    medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣']
                    for idx, (name, count) in enumerate(sorted_items):
                        revenue = item_revenue.get(name, 0)
                        response += f"{medals[idx]} <strong>{name}</strong><br>"
                        response += f"&nbsp;&nbsp;&nbsp;📦 Orders: {count} | 💰 Revenue: ₹{revenue:.0f}<br>"
                    
                    # Add advanced insights
                    avg_order_value = sum(float(o.get('totalPrice', 0)) for o in orders) / len(orders) if orders else 0
                    total_revenue = sum(float(o.get('totalPrice', 0)) for o in orders)
                    
                    response += f'''<br><strong>💡 Smart Insights:</strong><br>
                    • Total Orders: {len(orders)}<br>
                    • Total Revenue: ₹{total_revenue:.0f}<br>
                    • Average Order Value: ₹{avg_order_value:.0f}<br>
                    • Most Popular Category: {sorted_items[0][0] if sorted_items else 'N/A'}<br>
                    • Menu Items: {len(menu_items)} available'''
                    
                    return {'success': True, 'response': response}, 200
                else:
                    return {'success': True, 'response': '📊 Not enough order data yet. Start ordering to see insights!'}, 200
            except Exception as e:
                print(f"Error fetching analytics: {e}")
        
        # Advanced Staff Analytics (today, weekly, all-time)
        if ('today' in message or 'this week' in message or 'analytics' in message or 'performance' in message) and any(w in message for w in ['order', 'sale', 'revenue', 'stats']):
            if user_type == 'staff':
                try:
                    orders = orders_sheet.get_all_records()
                    today = datetime.now().strftime('%Y-%m-%d')
                    today_orders = [o for o in orders if o.get('timestamp', '').startswith(today)]
                    
                    # Calculate advanced metrics
                    if today_orders:
                        total_revenue = sum(float(o.get('totalPrice', 0)) for o in today_orders)
                        pending = len([o for o in today_orders if o.get('status', '').lower() == 'pending'])
                        delivered = len([o for o in today_orders if o.get('status', '').lower() == 'delivered'])
                        cancelled = len([o for o in today_orders if o.get('status', '').lower() == 'cancelled'])
                        
                        avg_order = total_revenue / len(today_orders) if today_orders else 0
                        
                        # Predict peak hours
                        hours = {}
                        for order in today_orders:
                            ts = order.get('timestamp', '')
                            if ts:
                                hour = ts.split()[1].split(':')[0] if ' ' in ts else 'N/A'
                                hours[hour] = hours.get(hour, 0) + 1
                        
                        peak_hour = max(hours, key=hours.get) if hours else 'N/A'
                        
                        response = f"""<strong>📊 ADVANCED STAFF DASHBOARD ({today})</strong><br><br>
                        <strong>📈 Order Metrics:</strong><br>
                        • Total Orders: {len(today_orders)}<br>
                        • ✅ Delivered: {delivered}<br>
                        • ⏳ Pending: {pending}<br>
                        • ❌ Cancelled: {cancelled}<br><br>
                        
                        <strong>💰 Financial Insights:</strong><br>
                        • Total Revenue: ₹{total_revenue:.2f}<br>
                        • Average Order Value: ₹{avg_order:.2f}<br>
                        • Expected Today: ₹{total_revenue:.2f}<br><br>
                        
                        <strong>🎯 Smart Predictions:</strong><br>
                        • Peak Hour: {peak_hour}:00<br>
                        • Fulfillment Rate: {(delivered/len(today_orders)*100):.1f}%<br>
                        • Recommendation: {'Great day! 🎉' if total_revenue > 1000 else 'Keep promoting! 📢'}<br><br>
                        
                        <em>💡 Smart tip: Peak orders at {peak_hour}:00. Plan staffing accordingly!</em>"""
                        return {'success': True, 'response': response}, 200
                    else:
                        return {'success': True, 'response': '📋 No orders yet today. Check back later for analytics!'}, 200
                except Exception as e:
                    print(f"Error fetching analytics: {e}")
        
        # Help query with complete capabilities
        if 'help' in message or 'what can you do' in message or 'how to use' in message or 'capabilities' in message:
            en_help = '''🤖 <strong>ADVANCED AI ASSISTANT - ALL CAPABILITIES</strong><br><br>
            
            <strong>🚀 ADVANCED FEATURES:</strong><br>
            • <em>"Analytics"</em> - Trending items, revenue, insights<br>
            • <em>"My order status"</em> - Smart predictions & timing<br>
            • <em>"Order history"</em> - Your spending patterns<br>
            • <em>"Staff dashboard"</em> - Peak hours, performance<br><br>
            
            <strong>📦 Smart Order Tracking:</strong><br>
            • <em>"Where's my order?"</em> - Real-time status<br>
            • <em>"All my orders"</em> - History & patterns<br>
            • <em>"What's trending?"</em> - Popular items analysis<br><br>
            
            <strong>🍴 Intelligent Food Discovery:</strong><br>
            • <em>"What should I order?"</em> - AI recommendations<br>
            • <em>"Popular items"</em> - Based on real data<br>
            • <em>"Budget menu"</em> - Cheap options<br>
            • <em>"Best sellers"</em> - Top rated items<br><br>
            
            <strong>📊 Advanced Analytics (Staff):</strong><br>
            • <em>"Today's performance"</em> - Sales, orders, metrics<br>
            • <em>"Revenue insights"</em> - Detailed analytics<br>
            • <em>"Peak hours"</em> - Smart predictions<br>
            • <em>"Best items"</em> - Revenue analysis<br><br>
            
            <strong>📝 Getting Started:</strong><br>
            • <em>"How to register?"</em> - 3 easy steps<br>
            • <em>"How to login?"</em> - Simple guide<br>
            • <em>"How to order?"</em> - Complete walkthrough<br><br>
            
            <strong>🌍 Multilingual & Smart:</strong><br>
            • Click 🇬🇧 हिंदी 🇮🇳 to switch languages<br>
            • I understand context naturally<br>
            • Learn from your patterns<br><br>
            
            <strong>✨ Pro Power Features:</strong><br>
            • 🔍 Search chat history<br>
            • 💾 Export conversations<br>
            • 👍 Rate responses<br>
            • ⚙️ Customize settings<br>
            • 📋 Copy responses<br><br>
            
            <em>I'm your advanced AI partner! Ask naturally, I'll understand! 🚀</em>'''
            
            hi_help = '''🤖 <strong>मैं आपकी कैसे मदद कर सकता हूँ:</strong><br><br>
            
            <strong>📦 आपके ऑर्डर:</strong><br>
            • <em>"मेरा ऑर्डर कहाँ है?"</em> - ट्रैक करें<br>
            • <em>"मेरे सभी ऑर्डर दिखाएं"</em> - सब देखें<br>
            • <em>"मैंने क्या खाया था?"</em> - इतिहास<br><br>
            
            <strong>🍴 खाना & मेनू:</strong><br>
            • <em>"मैं क्या आर्डर कर सकता हूँ?"</em> - खाना देखें<br>
            • <em>"सस्ता क्या है?"</em> - सस्ते विकल्प<br>
            • <em>"मुझे क्या खाना चाहिए?"</em> - सुझाव<br>
            • <em>"लोकप्रिय क्या है?"</em> - बेस्ट सेलर्स<br><br>
            
            <strong>📝 शुरुआत करना:</strong><br>
            • <em>"मैं कैसे रजिस्टर करूँ?"</em> - नया खाता<br>
            • <em>"मैं कैसे लॉगिन करूँ?"</em> - साइन इन मदद<br>
            • <em>"मैं कैसे ऑर्डर करूँ?"</em> - कदम दर कदम<br><br>
            
            <strong>👔 स्टाफ के लिए:</strong><br>
            • <em>"स्टाफ क्या कर सकता है?"</em> - स्टाफ फीचर<br>
            • <em>"आज का सारांश"</em> - दैनिक आँकड़े<br><br>
            
            <strong>🌍 भाषाएं:</strong><br>
            • 🇬🇧 हिंदी 🇮🇳 बटन पर क्लिक करें<br>
            • अंग्रेजी या हिंदी में पूछें!<br><br>
            
            <strong>✨ अच्छे सुझाव:</strong><br>
            • पुराने उत्तरों के लिए खोज 🔍 का प्रयोग करें<br>
            • स्वाभाविक रूप से पूछें - बात करने जैसे<br>
            • मैं इस ऐप के बारे में सब कुछ समझता हूँ!<br><br>
            
            <em>बस मुझसे कुछ भी पूछें! 😊</em>'''
            
            return {'success': True, 'response': translate(en_help, hi_help), 'language': language}, 200
        
        # Price queries
        if 'price' in message or 'cost' in message or 'how much' in message:
            # Try to extract item name
            item_match = re.search(r'(?:price|cost|much).*?(burger|pizza|salad|rolls?|milkshake|samosa|pasta|noodles|sandwich|patties|chips|paneer)', message)
            if item_match:
                search_term = item_match.group(1)
                try:
                    menu_items = menu_sheet.get_all_records()
                    matching = [item for item in menu_items if search_term in item.get('name', '').lower()]
                    if matching:
                        response = "<strong>💵 Price Information:</strong><br><br>"
                        for item in matching:
                            response += f"• {item.get('name', 'Unknown')}: ₹{item.get('price', 0)}<br>"
                        return {'success': True, 'response': response}, 200
                except Exception as e:
                    print(f"Error fetching prices: {e}")
        
        # Smart context-aware fallback with personalized suggestions
        context_suggestions = []
        user_role = "student" if user_type == 'student' else "staff/teacher" if user_type in ['staff', 'teacher'] else "user"
        
        # Add context-based suggestions
        if user_type == 'student':
            context_suggestions = [
                '🍽️ "What food is available?" - Browse the menu',
                '📦 "My latest order" - Check your order status',
                '📝 "How to register?" - Registration help',
                '💳 "How to place order?" - Ordering guide',
                '🌟 "Recommend something" - Smart food suggestions'
            ]
        elif user_type in ['staff', 'teacher']:
            context_suggestions = [
                '📊 "Today\'s orders" - View daily summary',
                '👥 "Student count" - Student statistics',
                '🍴 "Menu items" - Manage menu',
                '📦 "All orders" - Order management',
                '🔥 "Popular items" - Best sellers'
            ]
        else:
            context_suggestions = [
                '📝 "How to register?" - Get started',
                '🍴 "Menu info" - Browse food items',
                '📦 "How to order?" - Ordering process',
                '👔 "Staff features" - Admin capabilities',
                '❓ "Help" - All my features'
            ]
        
        suggestions_html = '<br>'.join(context_suggestions[:5])
        
        en_final = f'''🤔 I'm not quite sure about that, but here's what I can help with:<br><br>
        {suggestions_html}<br><br>
        <strong>Quick Tips:</strong><br>
        • Try asking naturally - "How do I...?", "What's...?", "Show me..."<br>
        • Type "help" for my complete capabilities<br>
        • Use search to find previous answers<br><br>
        <em>Need something else? I understand EVERYTHING about the app! 🧠</em>'''
        
        hi_final = f'''🤔 मुझे इसके बारे में पूरी जानकारी नहीं है, लेकिन यहाँ मैं आपकी मदद कर सकता हूँ:<br><br>
        {suggestions_html}<br><br>
        <strong>त्वरित सुझाव:</strong><br>
        • स्वाभाविक रूप से पूछें - "मैं कैसे...?", "क्या है...?", "मुझे दिखाएं..."<br>
        • पूर्ण क्षमताओं के लिए "help" टाइप करें<br>
        • पिछले उत्तरों को खोजने के लिए खोज का उपयोग करें<br><br>
        <em>और कुछ चाहिए? मैं ऐप के बारे में सब कुछ समझता हूँ! 🧠</em>'''
        
        return {'success': True, 'response': translate(en_final, hi_final), 'language': language}, 200
        
    except Exception as e:
        print(f"AI Chat Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}, 500

# --- API ENDPOINTS ---

@app.route('/api/menu', methods=['GET'])
def get_menu():
    """API endpoint to fetch menu items as JSON. Public endpoint - no auth required."""
    try:
        print("=== FETCHING MENU DATA ===")
        
        # Helper function to clean strings
        def deep_clean(text):
            """Remove whitespace variations while preserving text"""
            if not text:
                return ''
            # Convert to string and remove tabs, newlines, carriage returns
            cleaned = str(text).replace('\t', ' ').replace('\n', ' ').replace('\r', '')
            # Remove extra spaces but keep single spaces
            cleaned = ' '.join(cleaned.split())
            return cleaned.strip()
        
        # Get all records from Menu sheet
        menu_data = menu_sheet.get_all_records()
        print(f"Raw menu data count: {len(menu_data)}")
        print(f"Sheet headers: {menu_sheet.row_values(1) if menu_data else 'No data'}")
        
        if not menu_data:
            print("WARNING: No menu data found in Google Sheets")
            # Return default menu items if sheet is empty
            default_menu = [
                {
                    'id': 'item1',
                    'name': 'Veggie Burger',
                    'price': 80.00,
                    'benefits': 'Rich in fiber and vitamins',
                    'image': '/static/images/veggie_burger_vegeta.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item2',
                    'name': 'Paneer Pizza Slice',
                    'price': 100.00,
                    'benefits': 'Good source of calcium and protein',
                    'image': '/static/images/pizza.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item3',
                    'name': 'Fresh Fruit Salad',
                    'price': 60.00,
                    'benefits': 'Packed with essential nutrients',
                    'image': '/static/images/chilli_potato.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item4',
                    'name': 'Veg Spring Rolls (6 pcs)',
                    'price': 90.00,
                    'benefits': 'Healthy and delicious snack',
                    'image': '/static/images/samosa.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item5',
                    'name': 'Chocolate Milkshake',
                    'price': 70.00,
                    'benefits': 'Energy booster!',
                    'image': '/static/images/chocolate_milkshake.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item6',
                    'name': 'Chai',
                    'price': 30.00,
                    'benefits': 'Warm and refreshing Indian tea',
                    'image': '/static/images/chai.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item7',
                    'name': 'Coffee',
                    'price': 40.00,
                    'benefits': 'Strong and aromatic coffee',
                    'image': '/static/images/coffee.jpg',
                    'soldOut': False
                }
            ]
            print(f"Returning {len(default_menu)} default menu items")
            return default_menu, 200
        
        # Transform and clean the data
        formatted_menu = []
        for idx, item in enumerate(menu_data):
            print(f"Processing item {idx + 1}: {item}")
            
            # Extract fields with multiple possible key names
            item_id = deep_clean(
                item.get('id') or 
                item.get('ItemID') or 
                item.get('Item ID') or 
                item.get('itemId') or
                ''
            )
            
            item_name = deep_clean(
                item.get('name') or 
                item.get('ItemName') or 
                item.get('Item Name') or 
                item.get('itemName') or
                ''
            )
            
            benefits = deep_clean(
                item.get('benefits') or 
                item.get('Benefits') or 
                item.get('description') or
                'Delicious!'
            )
            
            image_url = deep_clean(
                item.get('image') or 
                item.get('ImageURL') or 
                item.get('Image URL') or 
                item.get('imagePath') or
                ''
            )
            
            # Handle price - could be string or number
            price_raw = item.get('price') or item.get('Price') or 0
            try:
                price = float(str(price_raw).replace('₹', '').replace(',', '').strip())
            except:
                price = 0.0
            
            # Ensure image path starts with /static/images/
            if image_url and not image_url.startswith('/'):
                if image_url.startswith('static/'):
                    image_url = '/' + image_url
                elif image_url.startswith('images/'):
                    image_url = '/static/' + image_url
                else:
                    image_url = '/static/images/' + image_url
            
            # Handle sold out status
            sold_out_raw = str(
                item.get('soldOut') or 
                item.get('SoldOut') or 
                item.get('Sold Out') or 
                ''
            ).lower()
            sold_out = sold_out_raw in ['true', 'yes', '1']
            
            # Ensure we don't use fallback image unless absolutely necessary
            if not image_url:
                print(f"WARNING: No image URL found for {item_name}, using placeholder")
            
            formatted_item = {
                'id': item_id or f'item{idx + 1}',
                'name': item_name or 'Unknown Item',
                'price': price,
                'benefits': benefits or 'Delicious!',
                'image': image_url if image_url else '/static/images/veggie_burger_vegeta.jpg',
                'soldOut': sold_out
            }
            
            print(f"  Item: {item_name}, Image: {image_url}")
            
            formatted_menu.append(formatted_item)
            print(f"  → Formatted: {formatted_item}")
        
        print(f"✓ Returning {len(formatted_menu)} menu items")
        return formatted_menu, 200
        
    except Exception as e:
        print(f"❌ Error fetching menu: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e), 'message': 'Failed to load menu items'}, 500

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    """API endpoint to fetch all orders as JSON."""
    print(f"\n=== GET ORDERS API CALLED ===")
    print(f"Session logged_in: {session.get('logged_in')}")
    print(f"Session user_type: {session.get('user_type')}")
    print(f"All session data: {dict(session)}")
    
    # Allow access (auth is handled at route level)
    # Note: The /staff_orders page already enforces authentication

    try:
        # Get all raw data including headers
        all_values = orders_sheet.get_all_values()
        print(f"Total rows from sheet: {len(all_values)}")
        
        if not all_values or len(all_values) < 2:
            print("No orders found in sheet")
            return {'orders': []}, 200
        
        # First row is headers - normalize by stripping whitespace
        raw_headers = all_values[0]
        headers = [h.strip() for h in raw_headers]
        print(f"=== ORDERS SHEET HEADERS ===")
        print(f"Raw headers: {raw_headers}")
        print(f"Normalized headers: {headers}")
        
        # Transform the data to match the expected format
        formatted_orders = []
        
        for row_idx, row in enumerate(all_values[1:], start=2):  # Skip header row
            # Create dict by zipping normalized headers with row values
            order_dict = dict(zip(headers, row))
            
            if row_idx == 2:  # Debug first order
                print(f"First order dict keys: {order_dict.keys()}")
                print(f"First order dict: {order_dict}")
            
            # Get values with flexible column name matching and strip whitespace
            # Also create a lowercase key mapping for better matching
            order_dict_lower = {k.lower().strip(): v for k, v in order_dict.items()}
            
            order_id = str(order_dict_lower.get('orderid') or order_dict_lower.get('order id') or '').strip()
            timestamp = str(order_dict_lower.get('timestamp') or order_dict_lower.get('date') or '').strip()
            user_id = str(order_dict_lower.get('userid') or order_dict_lower.get('user id') or '').strip()
            user_name = str(order_dict_lower.get('username') or order_dict_lower.get('user name') or order_dict_lower.get('name') or '').strip()
            user_class = str(order_dict_lower.get('userclass') or order_dict_lower.get('class') or order_dict_lower.get('classname') or '').strip()
            items_str = str(order_dict_lower.get('items') or order_dict_lower.get('itemsjson') or '').strip()
            total_price = str(order_dict_lower.get('totalprice') or order_dict_lower.get('total') or '0').strip()
            status = str(order_dict_lower.get('status') or 'pending').strip().lower()
            
            # Convert total price to float
            try:
                total_price = float(total_price.replace('₹', '').replace(',', ''))
            except:
                total_price = 0.0
            
            # Parse items string into array format
            items_array = []
            if items_str and items_str != 'nan':
                # Parse "Item x quantity" format into structured array
                item_parts = items_str.split(', ')
                for part in item_parts:
                    if ' x ' in part:
                        name, qty = part.rsplit(' x ', 1)
                        try:
                            items_array.append({'name': name.strip(), 'quantity': int(qty.strip())})
                        except:
                            items_array.append({'name': part.strip(), 'quantity': 1})
                    else:
                        items_array.append({'name': part.strip(), 'quantity': 1})
            
            formatted_orders.append({
                'orderId': order_id,
                'timestamp': timestamp,
                'userId': user_id,
                'userName': user_name,
                'userClass': user_class,
                'items': items_array,
                'totalPrice': total_price,
                'status': status
            })
        
        print(f"✓ Returning {len(formatted_orders)} formatted orders")
        if formatted_orders:
            print(f"First formatted order: {formatted_orders[0]}")
        print(f"API Response: {len(formatted_orders)} orders ready to send")
        return {'orders': formatted_orders}, 200
    except Exception as e:
        print(f"❌ Error fetching orders: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}, 500

@app.route('/api/orders/place', methods=['POST'])
def place_order():
    """API endpoint to place a new order for students and teachers."""
    if not session.get('logged_in') or session.get('user_type') not in ['student', 'teacher']:
        return {'error': 'Unauthorized'}, 401

    try:
        print("=== ORDER PLACEMENT ===")
        data = request.get_json()
        items = data.get('items', [])
        total_price = data.get('totalPrice', 0)
        
        print(f"Items: {items}")
        print(f"Total Price: {total_price}")
        
        if not items:
            return {'error': 'No items in order'}, 400

        # Check if orders_sheet is initialized
        if orders_sheet is None:
            print("ERROR: orders_sheet is None - Google Sheets not initialized")
            return {'error': 'Database not initialized'}, 500

        # Get user info
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        print(f"User ID: {user_id}, Type: {user_type}")
        
        if user_type == 'teacher':
            # Get teacher info
            teacher_record = get_teacher_by_staff_id(user_id)
            if not teacher_record:
                print(f"ERROR: Teacher record not found for staff_id: {user_id}")
                return {'error': 'Teacher record not found'}, 404
            
            student_name = teacher_record.get('Name', 'Teacher')
            student_class = 'Teacher'  # Mark as Teacher instead of Staff
        else:
            # Get student info
            student_record = get_student_by_id(user_id)
            
            if not student_record:
                print(f"ERROR: Student record not found for user_id: {user_id}")
                return {'error': 'Student record not found'}, 404

            # Get normalized dict for field access
            normalized = student_record.get('_normalized', {})
            
            # Get student details with flexible field mapping
            student_name = (
                student_record.get('name') or 
                student_record.get('Name') or 
                normalized.get('name') or
                'N/A'
            )
            
            student_class = (
                student_record.get('className') or 
                student_record.get('Class') or 
                student_record.get('class') or
                normalized.get('classname') or
                normalized.get('class') or
                'N/A'
            )
        
        print(f"Name: {student_name}, Class: {student_class}")

        # Format items as string (handle items with or without quantity field)
        items_str = ', '.join([f"{item['name']} x {item.get('quantity', 1)}" for item in items])
        print(f"Items string: {items_str}")

        # Generate order ID (unlimited, cycles back to 1 after 500)
        existing_orders = orders_sheet.get_all_records()
        next_order_num = (len(existing_orders) ) + 1
        order_id = str(next_order_num)
        print(f"Generated Order ID: {order_id}")

        # Prepare new order row
        # Expected Google Sheets Headers: orderId | timestamp | userId | userName | userClass | items | totalPrice | status
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        order_row = [
            order_id,           # orderId
            current_timestamp,  # timestamp
            user_id,            # userId
            student_name,       # userName
            student_class,      # userClass
            items_str,          # items
            total_price,        # totalPrice
            'Pending'           # status
        ]

        # Write order to Orders sheet
        print(f"Writing order to sheet: {[order_id, current_timestamp, user_id, student_name, student_class, items_str, total_price, 'Pending']}")
        orders_sheet.append_row(order_row, value_input_option='USER_ENTERED')  # type: ignore
        print(f"✓ Order placed successfully")
        
        # Calculate and save health points for nutritious foods
        try:
            menu_data = menu_sheet.get_all_records()
            # Convert items format from list of dicts to list of strings for calculate_health_points
            items_ordered = [f"{item['name']} x {item.get('quantity', 1)}" for item in items]
            health_points = calculate_health_points(items_ordered, menu_data)
            print(f"Calculated health points: {health_points} for items: {items_ordered}")
            
            if health_points > 0 or user_health_sheet is not None:
                current_points = get_user_nutrition_points(user_id)
                print(f"Current nutrition points for user {user_id}: {current_points}")
                
                new_total = current_points + health_points
                saved = save_user_nutrition_points(user_id, new_total)
                print(f"✓ Saved nutrition points: {health_points} points. Current total: {new_total}. Save result: {saved}")
        except Exception as e:
            print(f"Warning: Error saving nutrition points: {e}")
            import traceback
            traceback.print_exc()
            health_points = 0
        
        return {'success': True, 'orderId': order_id, 'healthPoints': health_points}, 200

    except gspread.exceptions.APIError as e:
        print(f"Google Sheets API Error during order placement: {e}")
        print(f"Status: {e.response.status_code}, Message: {e.response.text}")
        return {'error': 'Database API error - please try again'}, 500
    except Exception as e:
        print(f"Order Placement Error: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}, 500


@app.route('/api/clear_data', methods=['POST'])
def clear_data():
    """API endpoint to clear all orders and student data (staff/teacher only)."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return {'error': 'Unauthorized'}, 401

    try:
        # Clear all rows except the header in Orders sheet
        orders_values = orders_sheet.get_all_values()
        if len(orders_values) > 1:  # If there's more than just the header
            # Delete all rows after the header
            orders_sheet.delete_rows(2, len(orders_values))
        
        # Clear all rows except the header in Students sheet
        students_values = student_sheet.get_all_values()
        if len(students_values) > 1:  # If there's more than just the header
            # Delete all rows after the header
            student_sheet.delete_rows(2, len(students_values))
        
        print(f"✓ Cleared {len(orders_values) - 1} orders and {len(students_values) - 1} students")
        return {'success': True, 'message': 'All data cleared successfully'}, 200
    except Exception as e:
        print(f"Error clearing data: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}, 500


        return {'error': str(e)}, 500

@app.route('/api/menu/update', methods=['POST'])
def update_menu_item():
    """API endpoint to update menu item sold out status."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return {'error': 'Unauthorized'}, 401

    try:
        data = request.get_json()
        item_id = data.get('itemId')
        sold_out = data.get('soldOut')

        print(f"=== MENU UPDATE REQUEST ===")
        print(f"Item ID: {item_id}")
        print(f"New soldOut status: {sold_out}")

        if item_id is None or sold_out is None:
            return {'error': 'Missing itemId or soldOut'}, 400

        # Get all menu data
        headers = menu_sheet.row_values(1)
        all_data = menu_sheet.get_all_values()
        
        print(f"Menu headers: {headers}")
        print(f"Total rows: {len(all_data)}")
        
        # Normalize headers for comparison
        normalized_headers = [h.strip().lower() for h in headers]
        
        # Find which column has the ID
        id_col = None
        for idx, norm_header in enumerate(normalized_headers):
            if norm_header in ['id', 'itemid', 'item id']:
                id_col = idx + 1
                print(f"Found ID column at index {id_col}: '{headers[idx]}'")
                break
        
        if not id_col:
            print(f"ERROR: ID column not found. Headers: {headers}")
            return {'error': 'ID column not found in menu sheet'}, 500
        
        # Find soldOut column
        soldout_col = None
        for idx, norm_header in enumerate(normalized_headers):
            if norm_header in ['soldout', 'sold out', 'sold-out']:
                soldout_col = idx + 1
                print(f"Found soldOut column at index {soldout_col}: '{headers[idx]}'")
                break
        
        if not soldout_col:
            print(f"ERROR: SoldOut column not found. Headers: {headers}")
            return {'error': 'SoldOut column not found in menu sheet'}, 500
        
        # Find the item row by searching the ID column
        item_row = None
        item_id_str = str(item_id).strip()
        for row_idx, row in enumerate(all_data[1:], start=2):  # Skip header
            if len(row) >= id_col:
                cell_value = str(row[id_col - 1]).strip()
                if cell_value == item_id_str:
                    item_row = row_idx
                    print(f"Found item at row {item_row}")
                    break
        
        if not item_row:
            print(f"ERROR: Item '{item_id_str}' not found in column {id_col}")
            print(f"Available IDs: {[str(row[id_col - 1]).strip() for row in all_data[1:] if len(row) >= id_col]}")
            return {'error': f'Menu item {item_id} not found'}, 404
        
        # Update the soldOut status (TRUE/FALSE string)
        new_value = 'TRUE' if sold_out else 'FALSE'
        menu_sheet.update_cell(item_row, soldout_col, new_value)
        print(f"✓ Updated row {item_row}, column {soldout_col} to '{new_value}'")
        
        return {'status': 'success'}, 200
        
    except Exception as e:
        print(f"❌ Error updating menu item: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}, 500

@app.route('/api/orders/update_status', methods=['POST'])
def update_order_status():
    """API endpoint to update order status."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return {'error': 'Unauthorized'}, 401

    try:
        data = request.get_json()
        order_id = data.get('orderId')
        new_status = data.get('status')

        if not order_id or not new_status:
            return {'error': 'Missing orderId or status'}, 400

        # Find the order in the sheet
        cell = orders_sheet.find(order_id, in_column=1)  # Assuming OrderID is in column 1
        if cell:
            # Update the status column (assuming it's the last column)
            headers = orders_sheet.row_values(1)
            status_col = headers.index('Status') + 1 if 'Status' in headers else len(headers)
            orders_sheet.update_cell(cell.row, status_col, new_status.capitalize())
            return {'success': True}, 200
        else:
            return {'error': 'Order not found'}, 404
    except Exception as e:
        print(f"Error updating order status: {e}")
        return {'error': str(e)}, 500

# --- HEALTH CHECK ---
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify database connectivity."""
    try:
        status = {
            'status': 'healthy',
            'database': 'connected',
            'sheets': {}
        }
        
        # Check each sheet
        if student_sheet:
            student_count = len(student_sheet.get_all_records())
            status['sheets']['students'] = f'{student_count} records'
        else:
            status['sheets']['students'] = 'not initialized'
            status['status'] = 'unhealthy'
        
        if staff_sheet:
            staff_count = len(staff_sheet.get_all_records())
            status['sheets']['staff'] = f'{staff_count} records'
        else:
            status['sheets']['staff'] = 'not initialized'
            status['status'] = 'unhealthy'
        
        if menu_sheet:
            menu_count = len(menu_sheet.get_all_records())
            status['sheets']['menu'] = f'{menu_count} items'
        else:
            status['sheets']['menu'] = 'not initialized'
            status['status'] = 'unhealthy'
        
        if orders_sheet:
            orders_count = len(orders_sheet.get_all_records())
            status['sheets']['orders'] = f'{orders_count} orders'
        else:
            status['sheets']['orders'] = 'not initialized'
            status['status'] = 'unhealthy'
        
        if teacher_sheet:
            teacher_count = len(teacher_sheet.get_all_records())
            status['sheets']['teachers'] = f'{teacher_count} records'
        else:
            status['sheets']['teachers'] = 'not initialized'
        
        return status, 200 if status['status'] == 'healthy' else 503
        
    except Exception as e:
        print(f"Health check error: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }, 503

# --- FEEDBACK FORM ---
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """Handle feedback form submission."""
    if request.method == 'POST':
        try:
            data = request.get_json()
            name = data.get('name', '').strip()
            email = data.get('email', '').strip()
            message = data.get('message', '').strip()
            class_name = data.get('className', '').strip()
            rating = data.get('rating', '').strip()
            
            if not name or not email or not message or not class_name or not rating:
                return {'success': False, 'message': 'All fields are required'}, 400
            
            # Add feedback to Google Sheets
            try:
                now = datetime.now()
                # Use current timestamp
                
                # Save to Google Sheets
                if feedback_sheet:
                    print(f"Saving feedback to Google Sheets: {name} ({email})")
                    feedback_sheet.append_row([
                        name,
                        email,
                        message,
                        now.strftime('%Y-%m-%d'),
                        now.strftime('%H:%M:%S'),
                        class_name,
                        rating
                    ], value_input_option='USER_ENTERED')  # type: ignore
                    print(f"✓ Feedback saved to Google Sheets: {name}")
                    return {'success': True, 'message': 'Thank you for your feedback!'}, 200
                else:
                    print(f"❌ Feedback sheet is None - cannot save to Google Sheets")
                    return {'success': False, 'message': 'Unable to save feedback. Please try again.'}, 500
            except Exception as e:
                print(f"❌ Error saving feedback: {e}")
                import traceback
                traceback.print_exc()
                return {'success': False, 'message': 'Error saving feedback: ' + str(e)}, 500
                
        except Exception as e:
            print(f"Feedback error: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return render_template('feedback.html')

@app.route('/staff_feedback')
def staff_feedback():
    """View all feedback for staff."""
    # Check if user is staff
    if not session.get('logged_in') or session.get('user_type') != 'staff':
        return redirect(url_for('home'))
    
    try:
        # Get all feedback from Google Sheets
        all_feedback = []
        print("=== FETCHING STAFF FEEDBACK FROM GOOGLE SHEETS ===")
        
        if feedback_sheet:
            # Get all records from the feedback sheet
            records = feedback_sheet.get_all_records()
            print(f"Found {len(records)} feedback records")
            print(f"DEBUG: Record keys: {records[0].keys() if records else 'No records'}")
            
            for record in records:
                # Debug: Print all available keys and values
                print(f"DEBUG - Record keys: {list(record.keys())}")
                print(f"DEBUG - Full record: {record}")
                
                # Try to get values with flexible key matching (case-insensitive)
                name = record.get('Name', record.get('name', ''))
                email = record.get('Email', record.get('email', ''))
                message = record.get('feedback', record.get('Message', record.get('message', '')))
                classname = record.get('className', record.get('class', ''))
                rating = record.get('rating', record.get('Rating', ''))
                date = record.get('Date', record.get('date', ''))
                time = record.get('Time', record.get('time', ''))
                
                # Convert sheet data to feedback item format
                feedback_item = {
                    'name': name,
                    'email': email,
                    'message': message,
                    'classname': classname,
                    'rating': rating,
                    'date': date,
                    'time': time
                }
                all_feedback.append(feedback_item)
                print(f"Loaded feedback: {feedback_item['name']} - {feedback_item['email']} - Message: '{feedback_item['message']}'")
            
            # Sort by date and time (newest first) - reverse order
            def parse_datetime(feedback_item):
                try:
                    date_str = feedback_item.get('date', '')
                    time_str = feedback_item.get('time', '')
                    datetime_str = f"{date_str} {time_str}"
                    return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                except:
                    return datetime.min
            
            all_feedback.sort(key=parse_datetime, reverse=True)
        
        print(f"Total feedback items: {len(all_feedback)}")
        return render_template('staff_feedback.html', feedback_list=all_feedback, total=len(all_feedback))
    except Exception as e:
        print(f"Error fetching feedback: {e}")
        import traceback
        traceback.print_exc()
        return render_template('staff_feedback.html', feedback_list=[], total=0)

@app.route('/download_orders_pdf')
def download_orders_pdf():
    """Download orders as PDF with various time period options - with beautiful professional styling."""
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return redirect(url_for('home'))

    try:
        period = request.args.get('period', 'month')
        
        # Get all orders - with comprehensive debugging and position-based extraction
        try:
            # Get raw values first to see exact structure
            all_raw_values = orders_sheet.get_all_values()
            print(f"\n=== PDF DOWNLOAD DEBUG ===")
            print(f"Total rows in sheet (including header): {len(all_raw_values)}")
            if all_raw_values:
                print(f"Headers (row 1): {all_raw_values[0]}")
                print(f"Number of header columns: {len(all_raw_values[0])}")
                if len(all_raw_values) > 1:
                    print(f"Sample data row (row 2): {all_raw_values[1][:8]}")
                    print(f"Total sample row length: {len(all_raw_values[1])}")
            
            # Get records using the dict format
            all_orders = orders_sheet.get_all_records()
            print(f"Total records returned: {len(all_orders)}")
            if all_orders:
                print(f"First record keys: {list(all_orders[0].keys())}")
                print(f"First record values: {all_orders[0]}")
                
                # Convert dict records to position-based format for consistency
                # Expected order: orderId, timestamp, userId, userName, userClass, items, totalPrice, status
                headers = list(all_orders[0].keys())
                print(f"Column headers from sheet: {headers}")
                
                # Create a standardized version of orders - STRIP SPACES FROM ALL KEYS
                standardized_orders = []
                for order in all_orders:
                    # Strip spaces from all keys first
                    cleaned_order = {k.strip(): v for k, v in order.items()}
                    
                    # Try to extract using multiple column name variations
                    standardized = {
                        'orderId': cleaned_order.get('orderId', cleaned_order.get('Order ID', cleaned_order.get('OrderID', ''))),
                        'timestamp': cleaned_order.get('timestamp', cleaned_order.get('Timestamp', cleaned_order.get('Time', ''))),
                        'userId': cleaned_order.get('userId', cleaned_order.get('User ID', '')),
                        'userName': cleaned_order.get('userName', cleaned_order.get('Name', cleaned_order.get('Student', ''))),
                        'userClass': cleaned_order.get('userClass', cleaned_order.get('Class', cleaned_order.get('className', ''))),
                        'items': cleaned_order.get('items', cleaned_order.get('Items', '')),
                        'totalPrice': cleaned_order.get('totalPrice', cleaned_order.get('Total Price', cleaned_order.get('Price', 0))),
                        'status': cleaned_order.get('status', cleaned_order.get('Status', 'Pending'))
                    }
                    standardized_orders.append(standardized)
                
                all_orders = standardized_orders
            else:
                print("⚠️ WARNING: No order records found - sheet might be empty or header-only")
                all_orders = []
        except Exception as e:
            print(f"❌ Error fetching orders: {e}")
            import traceback
            traceback.print_exc()
            all_orders = []
        
        # First, build a student lookup cache from Students sheet
        student_lookup = {}
        try:
            student_records = student_sheet.get_all_records()
            for student in student_records:
                user_id = student.get('userId', student.get('User ID', ''))
                name = student.get('name', student.get('Name', ''))
                className = student.get('className', student.get('Class', ''))
                if user_id:
                    student_lookup[user_id] = {'name': name, 'class': className}
            print(f"Built student lookup with {len(student_lookup)} students")
        except Exception as e:
            print(f"⚠️ Warning: Could not build student lookup: {e}")
        
        # Enhance orders with student details
        for order in all_orders:
            user_id = order.get('userId', '')
            if user_id and user_id in student_lookup:
                order['userName'] = student_lookup[user_id].get('name', 'N/A')
                order['userClass'] = student_lookup[user_id].get('class', 'N/A')
        
        # Filter orders based on time period
        filtered_orders = []
        today = datetime.now()
        
        for order in all_orders:
            order_date = None
            timestamp_str = order.get('timestamp', '').strip()
            
            # Try multiple timestamp formats
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',  # Primary format (2025-12-20 14:30:45)
                '%m/%d/%Y %H:%M:%S',  # Alternative format (12/20/2025 14:30:45)
                '%Y-%m-%d',           # Date only
                '%m/%d/%Y'            # Date only alternative
            ]
            
            for fmt in formats_to_try:
                try:
                    order_date = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue
            
            # Skip this order if we couldn't parse the timestamp
            if order_date is None:
                continue
            
            include_order = False
            
            if period == 'day':
                include_order = order_date.date() == today.date()
            elif period == 'week':
                week_ago = today - timedelta(days=7)
                include_order = order_date.date() >= week_ago.date()
            elif period == 'month':
                include_order = order_date.month == today.month and order_date.year == today.year
            elif period == 'year':
                include_order = order_date.year == today.year
            elif period == 'custom':
                start_date_str = request.args.get('start_date', '').strip()
                end_date_str = request.args.get('end_date', '').strip()
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    include_order = start_date <= order_date.date() <= end_date
                except:
                    include_order = False
            
            if include_order:
                filtered_orders.append(order)
        
        # DEBUG: Print filtering results
        print(f"DEBUG: Filtered {len(filtered_orders)} orders for period '{period}' from {len(all_orders)} total orders")
        
        # If no orders found for the period, include all orders with a note (fallback for date issues)
        if not filtered_orders and all_orders:
            print(f"DEBUG: No orders matched period filter. Including all {len(all_orders)} orders as fallback.")
            filtered_orders = all_orders
        
        # Create PDF with professional margins
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.6*inch, bottomMargin=0.6*inch, leftMargin=0.6*inch, rightMargin=0.6*inch)
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Brand colors
        PRIMARY_BLUE = '#00A9E0'
        PRIMARY_MAGENTA = '#F000B8'
        SECONDARY_BLUE = '#0088BB'
        DARK_TEXT = '#1F2937'
        LIGHT_BG = '#F0F9FC'
        BORDER_COLOR = '#B3E5FC'
        
        period_names = {
            'day': 'Today',
            'week': 'Last 7 Days',
            'month': 'This Month',
            'year': 'This Year'
        }
        period_name = period_names.get(period, 'Custom Range')
        
        # ============ PROFESSIONAL COVER/HEADER SECTION ============
        # Company brand header
        header_style = ParagraphStyle(
            'BrandHeader',
            parent=styles['Heading1'],
            fontSize=32,
            textColor=colors.HexColor(PRIMARY_BLUE),
            alignment=1,
            spaceAfter=0,
            fontName='Helvetica-Bold',
            textTransform='uppercase',
            letterSpacing=2
        )
        title = Paragraph("🍽️ CANTEEN ORDERS REPORT", header_style)
        elements.append(title)
        
        # Decorative line
        elements.append(Spacer(1, 0.05*inch))
        line_data = [['═' * 80]]
        line_table = Table(line_data, colWidths=[6.5*inch])
        line_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(PRIMARY_MAGENTA)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Subtitle with period and styling
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor(PRIMARY_MAGENTA),
            alignment=1,
            spaceAfter=0,
            fontName='Helvetica-Bold'
        )
        period_emoji = {
            'day': '☀️',
            'week': '📆',
            'month': '📅',
            'year': '🗓️'
        }.get(period, '📋')
        subtitle = Paragraph(f"{period_emoji} Period: <font color='{PRIMARY_BLUE}'>{period_name.upper()}</font>", subtitle_style)
        elements.append(subtitle)
        
        # Date and time generated
        generated_date = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=1,
            spaceAfter=1
        )
        date_para = Paragraph(f"<i>Generated: {generated_date}</i>", date_style)
        elements.append(date_para)
        elements.append(Spacer(1, 0.3*inch))
        
        # Calculate comprehensive statistics
        total = len(filtered_orders)
        pending = len([o for o in filtered_orders if not o.get('status', o.get('Status')) or o.get('status', o.get('Status', '')).lower() == 'pending'])
        delivered = len([o for o in filtered_orders if o.get('status', o.get('Status', '')).lower() == 'delivered'])
        unable = len([o for o in filtered_orders if o.get('status', o.get('Status', '')).lower() == 'unable'])
        cancelled = len([o for o in filtered_orders if o.get('status', o.get('Status', '')).lower() == 'cancelled'])
        
        # Calculate total revenue with better error handling
        total_revenue = 0
        for order in filtered_orders:
            try:
                price = order.get('totalPrice', 0)
                if isinstance(price, str) and price.strip():
                    total_revenue += float(price)
                elif isinstance(price, (int, float)):
                    total_revenue += float(price)
            except (ValueError, TypeError):
                pass
        
        # Calculate average order value
        avg_order_value = total_revenue / total if total > 0 else 0
        
        # ============ ENHANCED STATISTICS SECTION ============
        # Create comprehensive stats boxes with 2 rows
        stats_data = [
            ['📦 TOTAL ORDERS', '⏳ PENDING', '✓ DELIVERED', '✗ UNABLE', '💰 TOTAL REVENUE'],
            [f'{total}', f'{pending}', f'{delivered}', f'{unable}', f'₹{total_revenue:.2f}']
        ]
        
        stats_table = Table(stats_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.3*inch])
        stats_table.setStyle(TableStyle([
            # Header with gradient colors
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor(PRIMARY_BLUE)),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor(SECONDARY_BLUE)),
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#22C55E')),
            ('BACKGROUND', (3, 0), (3, 0), colors.HexColor(PRIMARY_MAGENTA)),
            ('BACKGROUND', (4, 0), (4, 0), colors.HexColor('#FF9800')),
            
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            
            # Data row - white with subtle border
            ('BACKGROUND', (0, 1), (-1, 1), colors.white),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor(DARK_TEXT)),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, 1), 12),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
            
            # Professional borders
            ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor(PRIMARY_BLUE)),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(stats_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Additional metrics row
        metrics_data = [
            ['📊 AVG ORDER VALUE', '⏱️ TIME PERIOD', '📈 SUCCESS RATE'],
            [f'₹{avg_order_value:.2f}', f'{period_name}', f'{((delivered/(total if total > 0 else 1)) * 100):.1f}%']
        ]
        
        metrics_table = Table(metrics_data, colWidths=[2.1*inch, 2.2*inch, 2.2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(SECONDARY_BLUE)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor(LIGHT_BG)),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, 1), 10),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor(DARK_TEXT)),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, 1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
            
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor(BORDER_COLOR)),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.35*inch))
        
        # Create table with orders segregated by date
        if filtered_orders:
            # Sort orders by date (newest first)
            sorted_orders = []
            for order in filtered_orders:
                order_date = None
                timestamp_str = order.get('timestamp', '').strip()
                
                # Try multiple timestamp formats
                formats_to_try = [
                    '%Y-%m-%d %H:%M:%S',  # Primary format
                    '%m/%d/%Y %H:%M:%S',  # Alternative format
                    '%Y-%m-%d',           # Date only
                    '%m/%d/%Y'            # Date only alternative
                ]
                
                for fmt in formats_to_try:
                    try:
                        order_date = datetime.strptime(timestamp_str, fmt)
                        break
                    except ValueError:
                        continue
                
                # Fallback to current date if parsing fails
                if order_date is None:
                    order_date = datetime.now()
                
                order['parsed_date'] = order_date
            
            # Sort by date descending
            sorted_orders = sorted(filtered_orders, key=lambda x: x.get('parsed_date', datetime.now()), reverse=True)
            
            # Group orders by date
            orders_by_date = {}
            for order in sorted_orders:
                order_date = order.get('parsed_date', datetime.now())
                date_key = order_date.strftime('%B %d, %Y')  # e.g., "December 20, 2025"
                if date_key not in orders_by_date:
                    orders_by_date[date_key] = []
                orders_by_date[date_key].append(order)
            
            # Display date ranges info with styling
            if sorted_orders:
                earliest_date = sorted_orders[-1].get('parsed_date', datetime.now()).strftime('%B %d, %Y')
                latest_date = sorted_orders[0].get('parsed_date', datetime.now()).strftime('%B %d, %Y')
                date_range_text = f"<font size=9 color='{PRIMARY_BLUE}'><b>📆 Date Range:</b> <i>{earliest_date} to {latest_date}</i></font>"
                date_range = Paragraph(date_range_text, styles['Normal'])
                elements.append(date_range)
                elements.append(Spacer(1, 0.2*inch))
            
            # Section header for detailed orders
            section_header = Paragraph(
                "<font size=12 color='{}' face='Helvetica-Bold'>📋 DETAILED ORDERS BY DATE</font>".format(PRIMARY_BLUE),
                styles['Normal']
            )
            elements.append(section_header)
            elements.append(Spacer(1, 0.15*inch))
            
            # Create tables for each date group
            for date_key in orders_by_date:
                # Date section header with modern styling
                daily_count = len(orders_by_date[date_key])
                date_header_style = ParagraphStyle(
                    'DateHeader',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor(PRIMARY_BLUE),
                    fontName='Helvetica-Bold',
                    spaceAfter=2,
                    leftIndent=6
                )
                date_header = Paragraph(f"📅 {date_key.upper()} · {daily_count} order{'s' if daily_count != 1 else ''}", date_header_style)
                elements.append(date_header)
                elements.append(Spacer(1, 0.08*inch))
                
                # Create table for this date with professional headers
                table_data = [['Order ID', 'Customer Name', 'Class', 'Items', 'Amount', 'Status']]
                
                daily_total = 0
                for order in orders_by_date[date_key]:
                    try:
                        order_date = order.get('parsed_date', datetime.now())
                        date_str = order_date.strftime('%m/%d/%Y')
                        
                        # Get customer name
                        customer_name = str(order.get('userName', 'N/A'))[:20]
                        
                        # Get items - handle various formats
                        items = order.get('items', '')
                        items_display = items
                        if isinstance(items, list):
                            items_str = ', '.join([f"{i.get('name', 'Item')} ({i.get('quantity', 1)})" for i in items if i])
                        else:
                            items_str = str(items) if items else 'No items recorded'
                        
                        # Truncate items to fit but keep it readable
                        if len(items_str) > 30:
                            items_str = items_str[:27] + '...'
                        
                        # Show items count
                        items_count = 0
                        if isinstance(items, list):
                            items_count = len(items)
                        elif items_str and items_str != 'No items recorded':
                            items_count = len([x for x in str(items).split(',') if x.strip()])
                        
                        items_display = f"📦 {items_count} items" if items_count > 0 else items_str
                        
                        # Get price - handle string conversion
                        try:
                            price_val = order.get('totalPrice', 0)
                            if isinstance(price_val, str):
                                price = float(price_val) if price_val.strip() else 0
                            else:
                                price = float(price_val) if price_val else 0
                        except (ValueError, AttributeError, TypeError):
                            price = 0
                        daily_total += price
                        
                        # Get payment status (assuming from 'status' field) - use simple paid/unpaid logic
                        order_status = order.get('status', 'Pending')
                        if not order_status:
                            order_status = 'Pending'
                        
                        # Determine payment status (for demo: if order status is 'Delivered', mark as Paid, else Unpaid)
                        # You may need to adjust this based on your actual data structure
                        payment_status = 'Paid' if order_status.lower() == 'delivered' else 'Unpaid'
                        
                        # Build row with status badges and emojis
                        status_emoji = {'pending': '⏳', 'delivered': '✓', 'unable': '❌', 'cancelled': '🚫'}.get(order_status.lower(), '❓')
                        payment_emoji = '✓' if payment_status == 'Paid' else '⏳'
                        
                        table_data.append([
                            date_str,
                            customer_name,
                            f"₹{price:.2f}",
                            f"{payment_emoji} {payment_status}",
                            items_str,
                            f"{status_emoji} {order_status.capitalize()[:10]}"
                        ])
                    except Exception as e:
                        print(f"Error processing order: {e}")
                        continue
                
                # Add daily total row
                table_data.append(['', '', f"<b>₹{daily_total:.2f}</b>", '', 'Daily Total', ''])
                
                # Create table with proper column widths
                col_widths = [0.85*inch, 1.3*inch, 0.85*inch, 1.1*inch, 1.5*inch, 1.0*inch]
                table = Table(table_data, colWidths=col_widths)
                
                # Beautiful modern styling with brand colors and status badges
                style_list = [
                    # Header row - blue background with white text
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PRIMARY_BLUE)),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('TOPPADDING', (0, 0), (-1, 0), 10),
                    
                    # Data rows - light background for readability
                    ('FONTSIZE', (0, 1), (-1, -2), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor(LIGHT_BG)]),
                    
                    # Column alignments
                    ('ALIGN', (0, 1), (0, -2), 'CENTER'),  # Date - center
                    ('ALIGN', (1, 1), (1, -2), 'LEFT'),    # Customer - left
                    ('ALIGN', (2, 1), (2, -2), 'RIGHT'),   # Total - right
                    ('ALIGN', (3, 1), (3, -2), 'CENTER'),  # Payment Status - center
                    ('ALIGN', (4, 1), (4, -2), 'LEFT'),    # Items - left
                    ('ALIGN', (5, 1), (5, -2), 'CENTER'),  # Order Status - center
                    
                    # Padding for data rows
                    ('LEFTPADDING', (0, 1), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 1), (-1, -1), 6),
                    ('TOPPADDING', (0, 1), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
                    
                    # Total row - magenta background with white text
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(PRIMARY_MAGENTA)),
                    ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, -1), (-1, -1), 8),
                    ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
                    ('TOPPADDING', (0, -1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
                    
                    # Grid lines - subtle light blue
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0F2FE')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]
                
                table.setStyle(TableStyle(style_list))
                elements.append(table)
                elements.append(Spacer(1, 0.25*inch))
            
            # Beautiful footer with separator
            elements.append(Spacer(1, 0.2*inch))
            total_amount = sum([float(o.get('totalPrice', 0)) if o.get('totalPrice') else 0 for o in sorted_orders])
            
            # Footer stats row
            footer_data = [
                [f'📊 Total Orders: {total}', f'💵 Total Revenue: ₹{total_amount:.2f}']
            ]
            footer_table = Table(footer_data, colWidths=[3.25*inch, 3.25*inch])
            footer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PRIMARY_BLUE)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor(PRIMARY_BLUE)),
            ]))
            elements.append(footer_table)
            
            # Brand footer
            elements.append(Spacer(1, 0.15*inch))
            brand_footer = Paragraph(
                f"<font size=8 color='{PRIMARY_BLUE}'><b>🍽️ Canteen Management System</b> | Report generated {datetime.now().strftime('%I:%M %p')}</font>",
                ParagraphStyle('BrandFooter', parent=styles['Normal'], alignment=1)
            )
            elements.append(brand_footer)
        else:
            # Beautiful "no orders" message
            elements.append(Spacer(1, 0.5*inch))
            no_orders_text = Paragraph(
                f"<font size=18 color='{PRIMARY_MAGENTA}'><b>📭 No Orders Found</b></font><br/><br/>"
                f"<font size=12 color='{DARK_TEXT}'>No orders are available for the selected period.</font><br/>"
                f"<font size=10 color='#6B7280'><i>Please select a different time range or check back later.</i></font>",
                ParagraphStyle('NoOrders', parent=styles['Normal'], alignment=1)
            )
            elements.append(no_orders_text)
            elements.append(Spacer(1, 0.5*inch))
        
        # Build PDF
        doc.build(elements)
        pdf_buffer.seek(0)
        
        filename = f"Orders_{period_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        print(f"PDF Download Error: {e}")
        import traceback
        traceback.print_exc()
        return "Error generating PDF", 500

# --- ERROR HANDLERS ---
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors - return JSON for API routes, HTML otherwise"""
    if request.path.startswith('/api/') or request.is_json:
        return {'error': 'Not found', 'message': str(e)}, 404
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors - return JSON for API routes, HTML otherwise"""
    print(f"Server error: {e}")
    import traceback
    traceback.print_exc()
    if request.path.startswith('/api/') or request.is_json:
        return {'error': 'Internal server error', 'message': str(e)}, 500
    return "Internal server error. Check server logs.", 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions"""
    print(f"Unhandled exception: {e}")
    import traceback
    traceback.print_exc()
    if request.path.startswith('/api/') or request.is_json:
        return {'error': 'Server error', 'message': str(e)}, 500
    return f"An error occurred: {str(e)}", 500

# --- RUN APP ---
# --- ERROR HANDLERS ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Check if running in production (via gunicorn) or development
    import sys
    if 'gunicorn' in sys.argv[0]:
        print("Running in production mode with gunicorn")
    else:
        print("Running development server...")
        # Security: Use environment variable for debug mode
        debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
        app.run(host='0.0.0.0', port=5000, debug=debug_mode)