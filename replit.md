# Canteen Management System

## Overview

A comprehensive web-based canteen ordering and management system for schools. Students can register, log in, place food orders, track their nutrition points, and provide feedback. Staff manages the menu, monitors orders, views student information, and analyzes feedback. Teachers can access student lists and order information.

The system uses Google Sheets for all data storage and includes an AI chat assistant powered by OpenAI/Gemini for real-time support.

**Status**: Fully functional and production-ready  
**Last Updated**: December 25, 2025

## How It Works

### For Students
- Register with admission ID, name, email, class, and password
- Log in and manage personal profile
- Browse complete food menu with prices, descriptions, and images
- Place orders and receive real-time total calculations
- Track order confirmation and history
- Earn nutrition points based on healthy food choices
- Submit feedback and suggestions
- Chat with AI assistant for canteen-related questions

### For Staff
- Secure login to access admin dashboard
- View all students in the system
- Monitor all orders with status updates
- Manage menu items (add, edit, mark as sold out)
- View and respond to student feedback
- Generate PDF reports of orders with student details
- Track system usage and statistics

### For Teachers
- Login to view student information lists
- Access order dashboard
- Monitor ordering trends

## Technical Architecture

### Technology Stack
- **Backend**: Python 3 with Flask web framework
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: Google Sheets (gspread library)
- **AI Integration**: OpenAI API + Gemini integration
- **PDF Generation**: ReportLab
- **Authentication**: Google Service Account + werkzeug password hashing
- **Session Management**: Flask-Login

### File Structure
```
app.py                                  - Main Flask application (3600+ lines)
templates/
  ├── index.html                       - Home/login page
  ├── register.html                    - Student registration form
  ├── student_info.html                - Student profile dashboard
  ├── food_selection.html              - Menu browsing & ordering interface
  ├── thank_you.html                   - Order confirmation
  ├── feedback.html                    - Feedback submission form
  ├── ai_assistant.html                - AI chat interface
  ├── staff_view.html                  - Staff dashboard home
  ├── staff_students.html              - Student management view
  ├── staff_orders_dashboard.html      - Order tracking & status updates
  ├── staff_menu_management.html       - Menu item management
  ├── staff_feedback.html              - Feedback review panel
  └── teachers_list.html               - Teacher student view

static/
  ├── style2.css                       - Complete styling (responsive design)
  └── images/                          - Food item images
```

### Google Sheets Database Schema

The system requires a Google Sheet named "Database Final" with these worksheets:

1. **Students** - Student account information
   - Columns: admissionId, userId, name, password (hashed), email, className

2. **Staff** - Staff/admin accounts
   - Columns: Name, staffId, password (hashed), type

3. **Menu** - Available food items
   - Columns: ItemName, Price, Available, Description, Image, Benefits

4. **Orders** - All placed orders
   - Columns: OrderID, UserId, StudentName, Class, Items, TotalPrice, Date, Time, Status

5. **Teachers** - Teacher accounts
   - Columns: Name, StaffID, Password (hashed), Email

6. **Feedback** - Student feedback entries
   - Columns: Name, Email, Message, Date, Time

7. **UserHealth** - Nutrition tracking
   - Columns: UserId, Username, NutritionPoints, LastUpdated, BMI, Height

## API Routes

### Public Routes
- `GET /` - Home page
- `GET /register` - Student registration page
- `POST /register` - Process student registration
- `GET /feedback` - Feedback submission page
- `POST /feedback` - Submit feedback

### Authentication Routes
- `POST /student_login` - Student login (JSON/form)
- `POST /staff_login` - Staff login (JSON/form)
- `POST /teacher_login` - Teacher login (JSON/form)
- `POST /logout` - Clear session

### Student Routes (Protected)
- `GET /student_info` - Student profile
- `GET /food_selection` - Order menu
- `POST /place_order` - Process order
- `GET /ai_assistant` - Chat interface

### Staff Routes (Protected)
- `GET /staff_view` - Dashboard
- `GET /staff_students` - Student list
- `GET /staff_orders` - Orders dashboard
- `GET /staff_menu_management` - Menu editor
- `GET /staff_feedback` - Feedback viewer
- `POST /update_order_status` - Update order status
- `GET /download_orders_pdf` - Export orders as PDF

### API Endpoints
- `POST /api/chat` - AI chat responses
- `POST /google_student_register` - Google OAuth registration
- `POST /student_register` - JSON student registration
- `POST /teacher_register` - JSON teacher registration
- `GET /api/help` - System documentation

## Features & Functionality

### Core Features ✓
- ✓ Multi-role authentication (student, staff, teacher)
- ✓ User registration with validation
- ✓ Secure password hashing (scrypt)
- ✓ Food ordering with real-time calculations
- ✓ Order confirmation and history
- ✓ Order status management
- ✓ Nutrition point tracking system
- ✓ Feedback collection and storage
- ✓ AI chat assistant (English & Hindi support)
- ✓ PDF report generation
- ✓ Google Sheets integration
- ✓ Session management
- ✓ Responsive design

### Advanced Features ✓
- ✓ Automatic user ID generation
- ✓ Menu item availability management
- ✓ Student search and filtering
- ✓ Order history tracking
- ✓ Health/nutrition point calculation
- ✓ Multiple language support (AI)
- ✓ Professional PDF reports with formatting

## Security Implementation

- **Password Security**: Passwords hashed using werkzeug.security (scrypt algorithm)
- **Authentication**: Server-side session management with Flask-Login
- **Authorization**: Role-based access control (student, staff, teacher)
- **API Key Management**: Google Service Account for Sheets API
- **Data Protection**: All sensitive operations validated server-side

## Current Credentials

### Staff Login (Updated December 25, 2025)
- **Staff ID**: (As defined in Staff sheet)
- **Password**: Pass@0001

## Dependencies

### Python Packages
- flask==2.x - Web framework
- flask-login - Session management
- gspread - Google Sheets API client
- google-auth - Google authentication
- google-cloud-auth - GCP authentication
- openai - OpenAI API client
- werkzeug - Password hashing & utilities
- reportlab - PDF generation
- requests - HTTP library
- oauthlib - OAuth2 support

## Environment Variables

Required for deployment:
- `GCP_BASE64_CREDS` - Base64 encoded Google Service Account JSON credentials
- `SPREADSHEET_ID` - Google Sheet ID for data storage
- `FLASK_SECRET_KEY` - Secret key for session management (default provided for dev)

Optional:
- `OPENAI_API_KEY` - OpenAI API key (if using OpenAI for AI chat)
- `GEMINI_API_KEY` - Gemini API key (if using Google Gemini)

## Deployment

The application runs on **port 5000** and is configured for production deployment.

### Local Development
```bash
python app.py
```

### Production
- Use production WSGI server (gunicorn, etc.)
- Set environment variables for GCP credentials and Sheets ID
- Ensure Flask secret key is strong and unique
- Configure appropriate session timeout

## Recent Changes (December 2025)

### Latest Updates
- ✓ Staff password reset to "Pass@0001" (December 25, 2025)
- ✓ All Google Sheets worksheets fully functional
- ✓ Password hashing implemented for all user types
- ✓ AI chat integration working
- ✓ PDF export functionality verified
- ✓ Nutrition point tracking operational

### Previous Updates
- Fixed feedback storage in Google Sheets
- Enhanced PDF report generation with student information
- Improved menu management interface
- Removed local database dependency

## Testing Credentials

### Test Staff Account
- **ID**: (From Staff sheet)
- **Password**: Pass@0001

### Test Student Account
- Available after registration

## Known Limitations & Notes

- Development server runs in debug mode (Flask development only)
- All data persists in Google Sheets (no local cache)
- PDF generation may take a few seconds for large order lists
- AI responses depend on external API availability
- Sheet updates propagate in real-time to the application

## Future Enhancements

Potential improvements for future releases:
- Mobile app version
- Payment gateway integration
- Advanced analytics dashboard
- Email notifications
- SMS alerts
- Dietary restrictions tracking
- Allergy management system
- Reservation system
- Multi-language UI

## Support & Documentation

All routes and endpoints are documented in the `/api/help` endpoint. The system includes comprehensive error handling and logging for troubleshooting.
