# Canteen Management System - Complete & Operational ✅

## Overview

A beautiful, fully-functional canteen management system with neumorphic soft UI design featuring manual student registration and dual student/staff login capabilities. Students can register, browse food items, and place orders. Staff have a complete admin interface to manage orders and menu availability.

**Design Theme**: Modern neumorphic soft UI with blue-to-magenta gradients (#00A9E0 to #F000B8)

## User Preferences

- Button text: "STUDENT REGISTAR" (not "Register")
- Form field spacing: 6px gaps between fields
- Simple, everyday language communication style
- Staff credentials: s.18.20@slps.one / 12345678

## System Architecture

### Frontend
- **Flask templates** with Jinja2 rendering
- **Vanilla JavaScript** for interactivity with browser sessionStorage
- **CSS3** with neumorphic shadows, gradient accents, and smooth animations
- **Toast notifications** and real-time form validation
- **Responsive design** for all devices

### Backend
- **Python Flask** framework handling all routes and API endpoints
- **Replit Key-Value Store** for persistent data storage
- **Server-side session management** for secure authentication
- **RESTful API** endpoints (/api) for database operations

### Authentication System
- **Manual registration**: Email, name, admission ID, class, student ID, password
- **Manual login**: Student/Staff credentials stored securely
- **Session management**: Both server-side (Flask) and client-side (sessionStorage)
- **Google OAuth**: Completely removed (was causing 403 verification errors)

### Data Storage
- **Replit DB keys**: 
  - `user:{student_id}` - Student accounts
  - `staff:{email}` - Staff accounts
  - `food_items` - Menu items with images and prices
  - `orders_{order_id}` - Individual orders

## Features Implemented ✅

### Student Features
- Manual registration with 6 required fields
- Student login/logout
- View personal profile information
- Browse food menu with images and descriptions
- Select multiple food items for ordering
- Real-time order total calculation
- Place orders with automatic ID generation
- Order confirmation page
- Toast notifications for all actions

### Staff Features
- Staff login with credentials
- Orders Dashboard with:
  - Statistics cards (total, pending, delivered, unable)
  - Three-column order view (Pending, Delivered, Unable)
  - Search functionality that opens full-page table modal
  - Ability to mark orders as delivered or unable to deliver
  - Real-time order status updates
- Menu Management page
- Logout functionality

### UI/UX Features
- Neumorphic soft shadows and depth effects
- Blue-to-magenta gradient accents throughout
- Smooth animations and transitions
- Loading spinners on buttons during operations
- Error messages with inline validation
- Success toast notifications
- Responsive mobile-friendly design
- Smooth scrollbars with gradient styling
- Accessibility features (ARIA labels)
- Beautiful food item cards with images
- Color-coded status badges (orange pending, green delivered, red unable)

## Technology Stack

### Languages & Frameworks
- Python 3.11
- Flask web framework
- Vanilla JavaScript (ES6+)
- HTML5
- CSS3

### Libraries
- Flask
- Flask-Login
- oauthlib (installed but not used)
- replit (Replit DB integration)
- requests (installed but not used)

### Data & Storage
- Replit's built-in KV store (no external database needed)
- Browser sessionStorage for client state
- JSON serialization

## File Structure

```
app.py                              # Main Flask application
templates/
  ├── index.html                    # Home - login/register/staff options (neumorphic UI)
  ├── student_info_flask.html       # Student profile page
  ├── food_selection.html           # Food ordering page with cart
  ├── staff_view.html               # Staff portal main menu
  ├── staff_orders_dashboard.html   # Order management with search modal
  ├── staff_menu_management.html    # Menu item management
  └── thank_you.html                # Order confirmation page

static/
  ├── style2.css                    # Complete styling (neumorphic, responsive)
  ├── database.js                   # Database wrapper for Replit API
  └── images/
      ├── veggie_burger_vegeta.jpg
      ├── paneer_pizza_slice.jpg
      ├── fresh_fruit_salad_bo.jpg
      ├── chocolate_milkshake.jpg
      └── vegetable_spring_rol.jpg
```

## Key Implementation Details

### Critical Fixes Applied
1. **Staff Login Bug**: Fixed JSON serialization of Replit's ObservedDict objects
2. **Image Paths**: Corrected all image references to `/static/images/` paths
3. **Navigation**: Fixed all hardcoded `index.html` references to use Flask routes (`/`)
4. **Session Management**: Implemented dual server-side and client-side session storage
5. **Search Results**: Created beautiful full-page modal table for order search results

### Database Integration
- **Food items**: Auto-initialize with default items on first load
- **Orders**: Stored with complete details including student info and items
- **Users**: Manual registration stores all required fields
- **ObservedDict handling**: Converts to regular dicts before JSON serialization

### API Endpoints
- `POST /staff_login` - Staff authentication with session creation
- `GET /api?action=read&key=...` - Read from database
- `GET /api?action=save&key=...&value=...` - Save to database
- `GET /api?action=delete&key=...` - Delete from database
- `GET /api?action=get_keys&prefix=...` - List keys with prefix
- Flask routes: `/`, `/student_info`, `/food_selection`, `/staff_view`, `/staff_orders`, `/staff_menu`, `/thank_you`, `/logout`

## Design System

### Color Palette
- **Primary Blue**: #00A9E0
- **Primary Magenta**: #F000B8
- **Background**: #EFEDF5 (light purple-gray)
- **Text Primary**: #2D3748 (soft dark blue-gray)
- **Text Secondary**: #718096

### Neumorphic Shadows
- **Outer (relief)**: 10px 10px 20px #D1D9E6, -10px -10px 20px #FFFFFF
- **Inner (inset)**: 5px 5px 10px #D1D9E6, -5px -5px 10px #FFFFFF

### Typography
- **Font**: Montserrat (primary), Orbitron (accents)
- **Heading sizes**: 32px (h1), 24px (h2), 18px (h3)
- **Smooth transitions**: 0.3s ease-in-out

## Session & State Management

### Server-Side (Flask)
- Uses `session['currentUser']` to store JSON user data
- Middleware checks prevent unauthorized access to protected routes
- Session cleared on logout

### Client-Side (JavaScript)
- Uses `sessionStorage.setItem('currentUser', JSON.stringify(data))`
- Database wrapper checks session for authentication
- Modal open/close state managed with display property

## Known Working Flows

✅ Student Registration → Login → View Profile → Order Food → Receive Confirmation
✅ Staff Login → View Orders Dashboard → Search Orders → Manage Order Status
✅ Menu Management → View/Edit Food Items
✅ All redirects working correctly
✅ Image loading and display
✅ Session persistence across page navigation
✅ Toast notifications for user feedback
✅ Responsive design on mobile/tablet/desktop

## Deployment

The app is ready to deploy to production:
- No external APIs or services required
- All data persists in Replit DB
- No environment variables needed (but secrets are available if needed)
- Flask app runs on port 5000
- Static files properly served
- Database automatically initializes on first run

---

**Last Updated**: November 29, 2025
**Status**: ✅ COMPLETE AND TESTED
**Team**: Built with Replit Agent
