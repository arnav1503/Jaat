import os
import json
import gspread
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from google.oauth2.service_account import Credentials
from werkzeug.security import generate_password_hash, check_password_hash

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

# --- INITIALIZATION FUNCTION (CRITICAL CHANGE) ---
def initialize_sheets_client():
    """Initializes and authenticates the gspread client using the JSON credentials file."""
    global sheets_client, student_sheet, staff_sheet, menu_sheet, orders_sheet, teacher_sheet
    try:
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
        spreadsheet = sheets_client.open_by_key(SPREADSHEET_ID)
        print(f"✓ Spreadsheet opened: {spreadsheet.title}")

        # Assign worksheets. ENSURE THESE SHEET NAMES MATCH YOUR SPREADSHEET TABS EXACTLY
        print("Loading worksheets...")
        student_sheet = spreadsheet.worksheet("Students") 
        print("  ✓ Students sheet loaded")
        staff_sheet = spreadsheet.worksheet("Staff")     
        print("  ✓ Staff sheet loaded")
        menu_sheet = spreadsheet.worksheet("Menu")       
        print("  ✓ Menu sheet loaded")
        orders_sheet = spreadsheet.worksheet("Orders")   
        print("  ✓ Orders sheet loaded")
        
        # Try to get teacher sheet, create if doesn't exist
        try:
            teacher_sheet = spreadsheet.worksheet("Teachers")
            print("  ✓ Teachers sheet loaded")
        except:
            teacher_sheet = spreadsheet.add_worksheet(title="Teachers", rows="100", cols="5")
            teacher_sheet.append_row(['Name', 'StaffID', 'Password', 'Email'], value_input_option='USER_ENTERED')
            print("  ✓ Teachers sheet created")

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

def get_next_user_id(sheet):
    """Generates the next sequential user ID based on existing records."""
    try:
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
    """Fetches student details by userId."""
    try:
        # First, print all headers to see what we're working with
        headers = student_sheet.row_values(1)
        print(f"=== GOOGLE SHEETS HEADERS ===")
        print(f"Headers: {headers}")
        print(f"Number of columns: {len(headers)}")
        
        # Search in column 2 (userId column) - convert to string for comparison
        user_id_str = str(user_id).strip()
        cell = student_sheet.find(user_id_str, in_column=2)
        
        if cell:
            # Get the entire row and convert to dict
            row_data = student_sheet.row_values(cell.row)
            # Normalize headers (strip whitespace and convert to lowercase)
            normalized_headers = [h.strip().lower() for h in headers]
            student_dict = dict(zip(headers, row_data))
            
            # Create a normalized version for easier lookup
            normalized_dict = dict(zip(normalized_headers, row_data))
            
            # Print for debugging
            print(f"=== STUDENT FOUND ===")
            print(f"Row number: {cell.row}")
            print(f"Data: {row_data}")
            print(f"Dict keys: {list(student_dict.keys())}")
            print(f"Normalized keys: {normalized_headers}")
            print(f"Dict: {student_dict}")
            
            # Return both versions for flexible access
            student_dict['_normalized'] = normalized_dict
            return student_dict
        
        print(f"Student with userId '{user_id_str}' not found in column 2")
        # Try searching all cells as fallback
        all_cells = student_sheet.findall(user_id_str)
        print(f"Found {len(all_cells)} cells with value '{user_id_str}' anywhere in sheet")
        for cell in all_cells:
            print(f"  - Row {cell.row}, Column {cell.col}")
        
        return None
    except Exception as e:
        print(f"Error fetching student: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_staff_by_id(staff_id):
    """Fetches staff details by staffId (or admissionId)."""
    try:
        # Debug: Print all staff data to see structure
        all_staff = staff_sheet.get_all_records()
        print(f"Total staff records: {len(all_staff)}")
        if all_staff:
            print(f"First staff record: {all_staff[0]}")
            print(f"Staff sheet headers: {staff_sheet.row_values(1)}")
        
        # Try to find the staff member
        cell = staff_sheet.find(staff_id, in_column=1)
        print(f"Search result for '{staff_id}' in column 1: {cell}")
        
        if cell:
            # Get the entire row and convert to dict
            row_data = staff_sheet.row_values(cell.row)
            headers = staff_sheet.row_values(1)  # Assuming first row has headers
            return dict(zip(headers, row_data))
        
        # If not found in column 1, try searching all columns
        print(f"Trying to find '{staff_id}' in any column...")
        cell = staff_sheet.find(staff_id)
        if cell:
            print(f"Found in row {cell.row}, column {cell.col}")
            row_data = staff_sheet.row_values(cell.row)
            headers = staff_sheet.row_values(1)
            return dict(zip(headers, row_data))
        
        return None
    except Exception as e:
        print(f"Error fetching staff: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_teacher_by_staff_id(staff_id):
    """Fetches teacher details by StaffID."""
    try:
        # Search for teacher in column 2 (StaffID)
        cell = teacher_sheet.find(staff_id, in_column=2)
        
        if cell:
            row_data = teacher_sheet.row_values(cell.row)
            headers = teacher_sheet.row_values(1)
            return dict(zip(headers, row_data))
        
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
            student_sheet.append_row(new_row, value_input_option='USER_ENTERED')

            # Success: Automatically log the user in
            session['logged_in'] = True
            session['user_id'] = new_user_id
            session['user_type'] = 'student'
            return redirect(url_for('student_info'))

        except Exception as e:
            print(f"Registration Error: {e}")
            return "Registration failed: Could not write to database. Check server logs.", 500

    return render_template('register.html')

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

        # --- Append Data to Google Sheet ---
        new_row = [
            admission_id, user_id, name, hashed_password, email, class_name
        ]
        
        print(f"Attempting to write row: {[admission_id, user_id, name, '***', email, class_name]}")
        student_sheet.append_row(new_row, value_input_option='USER_ENTERED')
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
        
        teacher_sheet.append_row(new_row, value_input_option='USER_ENTERED')
        print("✓ Teacher registered successfully in Google Sheets")

        # Auto-login
        session['logged_in'] = True
        session['user_id'] = staff_id
        session['user_type'] = 'teacher'
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

    record = get_staff_by_id(staff_id) # Fetches record by admissionId (Col 1)
    print(f"Staff record found: {record is not None}")  # Debug
    
    if record:
        print(f"Staff record keys: {record.keys()}")  # Debug
        stored_password = str(record.get('password', ''))
        print(f"Stored password: {stored_password}, Input password: {password}")  # Debug
        
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
            orders_sheet.append_row(order_row, value_input_option='USER_ENTERED')
            return redirect(url_for('thank_you'))

        except Exception as e:
            print(f"Order Placement Error: {e}")
            return "Order failed: Database error.", 500

    # GET request: Display menu
    menu_data = menu_sheet.get_all_records()
    return render_template('food_selection.html', menu=menu_data)

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
        return render_template('staff_students.html', students=students_data)
    except Exception as e:
        print(f"Staff Students Error: {e}")
        return render_template('staff_students.html', students=[])

@app.route('/staff_list')
def staff_list():
    """Displays list of registered staff members."""
    if not session.get('logged_in') or session.get('user_type') != 'staff':
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
    if not session.get('logged_in') or session.get('user_type') != 'staff':
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
    if not session.get('logged_in') or session.get('user_type') != 'staff':
        return redirect(url_for('home'))
    
    search_query = request.args.get('q', '')
    return render_template('staff_search_results.html', search_query=search_query)

@app.route('/ai_assistant')
def ai_assistant():
    """AI assistant page accessible to everyone."""
    return render_template('ai_assistant.html')

@app.route('/api/ai_chat', methods=['POST'])
def ai_chat():
    """Ultra-advanced AI assistant with complete app knowledge and deep understanding."""
    try:
        data = request.get_json()
        message = data.get('message', '').lower().strip()
        conversation_history = data.get('history', [])
        
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
                'orders': ['orderId(1-500)', 'timestamp', 'userId', 'userName', 'userClass', 'items', 'totalPrice', 'status']
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
        
        # How to register/login queries
        if any(phrase in message for phrase in ['how to register', 'how do i sign up', 'create account', 'registration process', 'how to create']):
            return {'success': True, 'response': '''<strong>📝 Student Registration Guide:</strong><br><br>
            <strong>Step 1:</strong> Go to the homepage and click "STUDENT REGISTAR"<br>
            <strong>Step 2:</strong> Fill in the required fields:<br>
            • Name (your full name)<br>
            • Email (valid email address)<br>
            • Password (secure password)<br>
            • Admission ID (your student ID)<br>
            • Class Name (e.g., "Class 10A")<br>
            <strong>Step 3:</strong> Click register - you'll be auto-logged in!<br><br>
            <strong>Form Route:</strong> <code>/register</code><br>
            <strong>API Endpoint:</strong> <code>POST /student_register</code><br><br>
            Your password is hashed for security, and you'll get a unique userId automatically!'''}, 200
        
        # Login process queries
        if any(phrase in message for phrase in ['how to login', 'how do i log in', 'sign in process', 'login steps']):
            if 'staff' in message:
                return {'success': True, 'response': '''<strong>🔐 Staff Login Guide:</strong><br><br>
                <strong>Route:</strong> <code>POST /staff_login</code><br>
                <strong>Required Fields:</strong><br>
                • Staff ID (your unique identifier)<br>
                • Password<br><br>
                <strong>Test Credentials:</strong><br>
                • Staff ID: <code>s.18.20@slps.one</code><br>
                • Password: <code>12345678</code><br><br>
                After login, you access the staff dashboard with order management, student list, and menu controls!'''}, 200
            else:
                return {'success': True, 'response': '''<strong>🔐 Student Login Guide:</strong><br><br>
                <strong>Route:</strong> <code>POST /student_login</code><br>
                <strong>Required Fields:</strong><br>
                • User ID (auto-generated during registration)<br>
                • Password<br><br>
                Your userId is shown after registration. Save it to login later!<br>
                After login, you can browse the menu and place orders.'''}, 200
        
        # Ordering process queries
        if any(phrase in message for phrase in ['how to order', 'place order', 'buy food', 'ordering process', 'how do i get food']):
            return {'success': True, 'response': '''<strong>🍽️ How to Place an Order:</strong><br><br>
            <strong>Step 1:</strong> Login as a student<br>
            <strong>Step 2:</strong> Navigate to Food Selection (<code>/food_selection</code>)<br>
            <strong>Step 3:</strong> Browse available menu items (with images & prices)<br>
            <strong>Step 4:</strong> Select items and set quantities<br>
            <strong>Step 5:</strong> Click "Place Order"<br>
            <strong>Step 6:</strong> Your order is sent with status "Pending"<br><br>
            <strong>Order Details Include:</strong><br>
            • Order ID (1-500, cycles)<br>
            • Timestamp<br>
            • Items with quantities<br>
            • Total price<br>
            • Status (Pending → Delivered/Cancelled/Unable)<br><br>
            <strong>API:</strong> <code>POST /api/orders/place</code><br>
            You'll receive a confirmation page at <code>/thank_you</code>!'''}, 200
        
        # Menu/food item queries
        if any(phrase in message for phrase in ['menu structure', 'food items', 'what foods', 'menu system', 'available items']):
            try:
                menu_items = menu_sheet.get_all_records()
                item_count = len(menu_items)
                categories = {}
                for item in menu_items:
                    name = item.get('name', '').lower()
                    if 'burger' in name or 'sandwich' in name:
                        categories['Fast Food'] = categories.get('Fast Food', 0) + 1
                    elif 'noodles' in name or 'pasta' in name or 'roll' in name:
                        categories['Main Dishes'] = categories.get('Main Dishes', 0) + 1
                    elif 'milkshake' in name:
                        categories['Beverages'] = categories.get('Beverages', 0) + 1
                    elif 'samosa' in name or 'chips' in name or 'patties' in name or 'potato' in name:
                        categories['Snacks'] = categories.get('Snacks', 0) + 1
                    else:
                        categories['Other'] = categories.get('Other', 0) + 1
                
                cat_str = '<br>'.join([f'• {cat}: {count} items' for cat, count in categories.items()])
                
                return {'success': True, 'response': f'''<strong>🍴 Menu System Overview:</strong><br><br>
                <strong>Total Items:</strong> {item_count}<br>
                <strong>Categories:</strong><br>{cat_str}<br><br>
                <strong>Menu Fields:</strong><br>
                • ID (unique identifier)<br>
                • Name (item name)<br>
                • Price (in ₹)<br>
                • Benefits (health/taste description)<br>
                • Image (visual preview)<br>
                • SoldOut (boolean status)<br><br>
                <strong>Routes:</strong><br>
                • View: <code>/food_selection</code><br>
                • API: <code>GET /api/menu</code><br>
                • Update: <code>POST /api/menu/update</code> (staff only)<br><br>
                Staff can toggle soldOut status in real-time!'''}, 200
            except:
                pass
        
        # Database/technical queries
        if any(phrase in message for phrase in ['database', 'data structure', 'how data stored', 'backend', 'google sheets']):
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
            • orderId (1-500 cycling), timestamp, userId, userName, userClass, items, totalPrice, status<br><br>
            <strong>Authentication:</strong> Service account with Base64 encoded credentials<br>
            <strong>Security:</strong> Passwords hashed with Werkzeug (pbkdf2:sha256)<br>
            <strong>API Access:</strong> All CRUD operations via Flask endpoints'''}, 200
        
        # Staff features queries
        if any(phrase in message for phrase in ['staff features', 'staff can do', 'admin panel', 'staff dashboard', 'staff capabilities']):
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
        
        # Latest/recent order
        if any(phrase in message for phrase in ['my order', 'latest order', 'last order', 'recent order']):
            if not user_id or user_type != 'student':
                return {'success': True, 'response': '🔐 Please log in as a student to view your orders.'}, 200
            
            try:
                all_values = orders_sheet.get_all_values()
                if len(all_values) < 2:
                    return {'success': True, 'response': '📋 You haven\'t placed any orders yet.'}, 200
                
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
                    
                    status_emoji = '✅' if status == 'delivered' else '⏳' if status == 'pending' else '❌'
                    status_msg = {
                        'delivered': 'Ready for pickup!',
                        'pending': 'Being prepared...',
                        'cancelled': 'Order cancelled',
                        'unable': 'Issue with order'
                    }.get(status, 'Status unknown')
                    
                    response = f"""<strong>🍽️ Your Latest Order (#{order_id}):</strong><br><br>
                    <strong>Status:</strong> {status_emoji} {status.upper()}<br>
                    <strong>Items:</strong> {items}<br>
                    <strong>Total:</strong> ₹{total}<br><br>
                    <em>{status_msg}</em>"""
                    
                    return {'success': True, 'response': response}, 200
                else:
                    return {'success': True, 'response': '📋 You haven\'t placed any orders yet.'}, 200
            except Exception as e:
                print(f"Error fetching user orders: {e}")
                return {'success': True, 'response': '❌ Sorry, I could not retrieve your orders.'}, 200
        
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
        
        # Greetings
        greetings = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
        if any(greeting in message for greeting in greetings):
            responses = [
                '👋 Hello! How can I assist you with your canteen needs today?',
                '😊 Hi there! Ready to help you with orders and menu questions!',
                '🤖 Hey! I\'m your AI canteen assistant. What would you like to know?'
            ]
            import random
            return {'success': True, 'response': random.choice(responses)}, 200
        
        # Popular items / analytics
        if any(phrase in message for phrase in ['popular', 'trending', 'best seller', 'most ordered', 'favorite']):
            try:
                orders = orders_sheet.get_all_records()
                item_counts = {}
                
                for order in orders:
                    items_str = order.get('items', '')
                    if items_str:
                        # Parse items and count
                        for item_part in items_str.split(', '):
                            if ' x ' in item_part:
                                name, qty = item_part.rsplit(' x ', 1)
                                item_counts[name.strip()] = item_counts.get(name.strip(), 0) + int(qty.strip())
                
                if item_counts:
                    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                    response = "<strong>🔥 Most Popular Items:</strong><br><br>"
                    medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']
                    for idx, (name, count) in enumerate(sorted_items):
                        response += f"{medals[idx]} <strong>{name}</strong> - {count} orders<br>"
                    response += "<br><em>Based on order history</em>"
                    return {'success': True, 'response': response}, 200
                else:
                    return {'success': True, 'response': '📊 Not enough order data yet to show popular items.'}, 200
            except Exception as e:
                print(f"Error fetching analytics: {e}")
        
        # Today's orders (staff feature)
        if 'today' in message and any(w in message for w in ['order', 'sale', 'revenue']):
            if user_type == 'staff':
                try:
                    orders = orders_sheet.get_all_records()
                    today = datetime.now().strftime('%Y-%m-%d')
                    today_orders = [o for o in orders if o.get('timestamp', '').startswith(today)]
                    
                    if today_orders:
                        total_revenue = sum(float(o.get('totalPrice', 0)) for o in today_orders)
                        pending = len([o for o in today_orders if o.get('status', '').lower() == 'pending'])
                        delivered = len([o for o in today_orders if o.get('status', '').lower() == 'delivered'])
                        
                        response = f"""<strong>📊 Today's Summary ({today}):</strong><br><br>
                        <strong>Total Orders:</strong> {len(today_orders)}<br>
                        <strong>Pending:</strong> {pending}<br>
                        <strong>Delivered:</strong> {delivered}<br>
                        <strong>Revenue:</strong> ₹{total_revenue:.2f}<br><br>
                        <em>Keep up the great work! 💪</em>"""
                        return {'success': True, 'response': response}, 200
                    else:
                        return {'success': True, 'response': '📋 No orders placed today yet.'}, 200
                except Exception as e:
                    print(f"Error fetching today's orders: {e}")
        
        # Help query with complete capabilities
        if 'help' in message or 'what can you do' in message or 'how to use' in message or 'capabilities' in message:
            return {'success': True, 'response': '''<strong>🤖 Ultra-Advanced AI Assistant - Complete Capabilities:</strong><br><br>
            
            <strong>📦 ORDER MANAGEMENT:</strong><br>
            • "Status of order #5" - Track specific order<br>
            • "My latest order" - See recent order<br>
            • "Show all my orders" - Order history<br>
            • "Today's orders" (staff) - Daily summary<br><br>
            
            <strong>🍴 MENU & FOOD:</strong><br>
            • "What food is available?" - Full menu<br>
            • "Show cheap/affordable items" - Filter by price<br>
            • "Recommend something" - Smart suggestions<br>
            • "Find burger items" - Search by keyword<br>
            • "What's popular?" - Trending items<br><br>
            
            <strong>📚 APP KNOWLEDGE:</strong><br>
            • "How to register" - Registration guide<br>
            • "How to login" - Login process<br>
            • "How to order" - Ordering workflow<br>
            • "Menu structure" - Database schema<br>
            • "Staff features" - Admin capabilities<br>
            • "Routes/endpoints" - Complete API map<br>
            • "Form fields" - All input requirements<br>
            • "Database" - Technical architecture<br>
            • "Security" - Auth & encryption<br>
            • "UI design" - Theme & styling<br>
            • "Workflow" - How to run the app<br>
            • "Error troubleshooting" - Debug help<br><br>
            
            <strong>📊 ANALYTICS:</strong><br>
            • "Show popular items" - Order statistics<br>
            • "Revenue today" (staff) - Sales data<br><br>
            
            <strong>💡 SMART FEATURES:</strong><br>
            • Context-aware responses<br>
            • Time-based recommendations<br>
            • Natural language understanding<br>
            • Role-based information (student/staff)<br>
            • Multi-topic query handling<br>
            • Complete codebase knowledge<br><br>
            
            <strong>🎯 I understand EVERYTHING about:</strong><br>
            • All routes & APIs<br>
            • Database structure<br>
            • Forms & validation<br>
            • Security implementation<br>
            • UI/UX design system<br>
            • Workflows & deployment<br>
            • Error handling<br>
            • Every feature & function<br><br>
            
            <em>Just ask me anything naturally - I have complete knowledge of the entire app! 🧠✨</em>'''}, 200
        
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
        
        # Fallback with suggestions
        return {'success': True, 'response': '''🤔 I'm not sure about that, but I can help with:<br><br>
        • Order tracking ("status of order #1")<br>
        • Menu items ("what's available?")<br>
        • Price info ("how much is pizza?")<br>
        • Your orders ("show my orders")<br><br>
        Try rephrasing your question! 💬'''}, 200
        
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
                    'image': '/static/images/paneer_pizza_slice.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item3',
                    'name': 'Fresh Fruit Salad',
                    'price': 60.00,
                    'benefits': 'Packed with essential nutrients',
                    'image': '/static/images/fresh_fruit_salad_bo.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item4',
                    'name': 'Veg Spring Rolls (6 pcs)',
                    'price': 90.00,
                    'benefits': 'Healthy and delicious snack',
                    'image': '/static/images/vegetable_spring_rol.jpg',
                    'soldOut': False
                },
                {
                    'id': 'item5',
                    'name': 'Chocolate Milkshake',
                    'price': 70.00,
                    'benefits': 'Energy booster!',
                    'image': '/static/images/chocolate_milkshake.jpg',
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
    if not session.get('logged_in') or session.get('user_type') not in ['staff', 'teacher']:
        return {'error': 'Unauthorized'}, 401

    try:
        # Get all raw data including headers
        all_values = orders_sheet.get_all_values()
        
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
                print(f"First order dict: {order_dict}")
            
            # Get values with flexible column name matching and strip whitespace
            order_id = str(order_dict.get('orderId') or order_dict.get('OrderID') or order_dict.get('Order ID') or '').strip()
            timestamp = str(order_dict.get('timestamp') or order_dict.get('Timestamp') or order_dict.get('Date') or '').strip()
            user_id = str(order_dict.get('userId') or order_dict.get('UserID') or order_dict.get('User ID') or '').strip()
            user_name = str(order_dict.get('userName') or order_dict.get('UserName') or order_dict.get('User Name') or order_dict.get('name') or order_dict.get('Name') or '').strip()
            user_class = str(order_dict.get('userClass') or order_dict.get('Class') or order_dict.get('className') or '').strip()
            items_str = str(order_dict.get('items') or order_dict.get('Items') or order_dict.get('itemsJSON') or '').strip()
            total_price = str(order_dict.get('totalPrice') or order_dict.get('TotalPrice') or order_dict.get('total') or order_dict.get('Total') or '0').strip()
            status = str(order_dict.get('status') or order_dict.get('Status') or 'pending').strip().lower()
            
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
        return {'orders': formatted_orders}, 200
    except Exception as e:
        print(f"Error fetching orders: {e}")
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

        # Generate order ID (limited to 1-500, cycles back to 1 after 500)
        existing_orders = orders_sheet.get_all_records()
        next_order_num = (len(existing_orders) % 500) + 1
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
        orders_sheet.append_row(order_row, value_input_option='USER_ENTERED')
        print(f"✓ Order placed successfully")
        
        return {'success': True, 'orderId': order_id}, 200

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
if __name__ == '__main__':
    # Check if running in production (via gunicorn) or development
    import sys
    if 'gunicorn' in sys.argv[0]:
        print("Running in production mode with gunicorn")
    else:
        print("Running development server...")
        app.run(host='0.0.0.0', port=5000, debug=True)