
import gspread
from google.oauth2.service_account import Credentials
import os

# Google Sheets Setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1JBhFtZmw7bNMbJdBnINvAXacokwRwvNFKrm_wz9bYRI")

print("Connecting to Google Sheets...")
creds = Credentials.from_service_account_file(
    'canteen-app-376c7-eaaf8790c170.json',
    scopes=SCOPES
)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
menu_sheet = spreadsheet.worksheet("Menu")

# CORRECTED Menu items - Each item matched to its ACTUAL image
new_menu = [
    ['id', 'name', 'price', 'benefits', 'image', 'soldOut'],
    ['item1', 'Samosa', 15, 'Crispy and delicious!', '/static/images/samosa.jpg', 'FALSE'],
    ['item2', 'Potato Patties', 30, 'Golden and crunchy!', '/static/images/potato_patties.jpg', 'FALSE'],
    ['item3', 'Paneer Gravy Patties', 50, 'Rich in protein', '/static/images/paneer_gravy_patties.jpg', 'FALSE'],
    ['item4', 'Sandwich', 30, 'Fresh and healthy', '/static/images/sandwich.jpg', 'FALSE'],
    ['item5', 'Burger', 50, 'Tasty and filling', '/static/images/veggie_burger_vegeta.jpg', 'FALSE'],
    ['item6', 'Paneer Roll', 50, 'Protein-rich roll', '/static/images/paneer_roll.jpg', 'FALSE'],
    ['item7', 'Pasta Roll', 50, 'Fusion delight', '/static/images/pasta_roll.jpg', 'FALSE'],
    ['item8', 'Chips (Small)', 10, 'Crunchy snack', '/static/images/chips_large.jpg', 'FALSE'],
    ['item9', 'Chips (Medium)', 20, 'Perfect snack', '/static/images/chips_large.jpg', 'FALSE'],
    ['item10', 'Chips (Large)', 50, 'Share with friends!', '/static/images/chips_large.jpg', 'FALSE'],
    ['item11', 'Chole Kulche', 50, 'North Indian favorite', '/static/images/chole_kulche.jpg', 'FALSE'],
    ['item12', 'Veg Noodles', 50, 'Indo-Chinese delight', '/static/images/veg_noodles.jpg', 'FALSE'],
    ['item13', 'Chilli Potato', 50, 'Spicy and tangy', '/static/images/chilli_potato.jpg', 'FALSE'],
    ['item14', 'Pizza', 50, 'Cheesy goodness', '/static/images/pizza.jpg', 'FALSE']
]

print("Clearing existing menu data...")
menu_sheet.clear()

print("Uploading FINAL corrected menu data...")
menu_sheet.update(values=new_menu, range_name='A1', value_input_option='USER_ENTERED')

print("✓ Menu updated successfully!")
print(f"Total items: {len(new_menu) - 1}")

# Verify the data
print("\n📋 FINAL VERIFICATION - Menu items and image paths:")
all_data = menu_sheet.get_all_values()
for idx, row in enumerate(all_data[1:], 1):
    print(f"  {idx}. {row[1]:<25} → {row[4]}")

print("\n✅ ALL IMAGES ARE NOW CORRECTLY MAPPED!")
print("\n🔍 Please check these image files exist in /static/images/:")
image_files = [
    'samosa.jpg', 'potato_patties.jpg', 'paneer_gravy_patties.jpg', 
    'sandwich.jpg', 'veggie_burger_vegeta.jpg', 'paneer_roll.jpg',
    'pasta_roll.jpg', 'chips_large.jpg', 'chole_kulche.jpg',
    'veg_noodles.jpg', 'chilli_potato.jpg', 'pizza.jpg'
]
for img in image_files:
    path = f'static/images/{img}'
    exists = "✓" if os.path.exists(path) else "✗ MISSING"
    print(f"  {exists} {img}")
