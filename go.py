import os
from datetime import datetime, timedelta
import ynab
import gspread
from google.oauth2.service_account import Credentials
import requests

# ==== CONFIG ====
YNAB_API_KEY = os.getenv("YNAB_API_KEY")
YNAB_BUDGET_ID = os.getenv("YNAB_BUDGET_ID")
YNAB_GAS_CATEGORY_ID = os.getenv("YNAB_GAS_CATEGORY_ID")
GOOGLE_SHEETS_CREDS_FILE = os.getenv("GOOGLE_SHEETS_CREDS_FILE", "service_account.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEET_TAB_NAME = os.getenv("GOOGLE_SHEET_TAB_NAME", "Samantha")
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_NOTIFY_SERVICE = os.getenv("HA_NOTIFY_SERVICE", "notify.mobile_app_trickyiphone16v2")
DAYS_BACK = 90

# ==== SHEET COLUMN INDICES (0-based) ====
COL_YNAB_ID = 0
COL_DATE = 1
COL_PROVIDER = 2
COL_AMOUNT = 3
COL_GALLONS = 4
COL_ODOMETER = 5
COL_CAR = 6
COL_MPG = 7
COL_NOTES = 8

# ==== CAR NAMES ====
CAR_PRIMARY = "samantha"
CAR_SECONDARY = "mkz"
CAR_SKIP = "skip"

# Validate required environment variables
if not YNAB_API_KEY:
    raise EnvironmentError("YNAB_API_KEY environment variable not set")
if not YNAB_BUDGET_ID:
    raise EnvironmentError("YNAB_BUDGET_ID environment variable not set")
if not GOOGLE_SHEET_ID:
    raise EnvironmentError("GOOGLE_SHEET_ID environment variable not set")
if not HA_URL:
    raise EnvironmentError("HA_URL environment variable not set")
if not HA_TOKEN:
    raise EnvironmentError("HA_TOKEN environment variable not set")


# ==== GOOGLE SHEETS INTEGRATION ====
def get_google_sheet():
    """Connect to Google Sheet and return the worksheet"""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDS_FILE, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

    # Try to get existing worksheet, create if doesn't exist
    try:
        worksheet = spreadsheet.worksheet(GOOGLE_SHEET_TAB_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=GOOGLE_SHEET_TAB_NAME, rows=1000, cols=6)
        # Add header row
        worksheet.append_row(['ynab_transaction_id', 'date', 'provider', 'amount', 'gallons', 'notes'])

    return worksheet


def get_existing_transaction_ids(worksheet):
    """Get all existing YNAB transaction IDs from the sheet"""
    try:
        # Get all values from first column (transaction IDs)
        all_values = worksheet.col_values(1)
        # Skip header row
        if len(all_values) > 1:
            return set(all_values[1:])
        return set()
    except Exception as e:
        print(f"⚠️  Error reading existing transactions: {e}")
        return set()


def append_transactions_to_sheet(worksheet, transactions):
    """Append new transactions to the Google Sheet"""
    if not transactions:
        return 0

    rows = []
    for transaction in transactions:
        # Parse date as datetime object for Google Sheets
        if hasattr(transaction.var_date, 'strftime'):
            # Already a date/datetime object
            date_obj = transaction.var_date
        else:
            # Parse string to datetime
            from datetime import datetime as dt
            date_obj = dt.strptime(str(transaction.var_date), '%Y-%m-%d')

        provider = extract_provider_from_payee(transaction.payee_name)
        amount = abs(transaction.amount) / 1000

        rows.append([
            transaction.id,
            date_obj.strftime('%Y-%m-%d'),  # Convert datetime to string for JSON serialization
            provider,
            amount,  # Plain float, no dollar sign
            "",  # Empty gallons column
            "",  # Empty odometer column
            "",  # Empty car column (Samantha or MKZ)
            "",  # Empty MPG column
            ""   # Empty notes column
        ])

    if rows:
        worksheet.append_rows(rows)

    return len(rows)


def count_missing_data(worksheet):
    """Count rows where car column is empty (need user input)"""
    try:
        # Get all rows (to count total data rows)
        all_rows = worksheet.get_all_values()
        # Skip header row
        data_rows = all_rows[1:] if len(all_rows) > 1 else []

        missing_count = 0
        for row in data_rows:
            # Count if car column is empty (user hasn't filled in data yet)
            car_value = row[COL_CAR].strip() if len(row) > COL_CAR else ""
            if not car_value:
                missing_count += 1

        return missing_count
    except Exception as e:
        print(f"⚠️  Error counting missing data: {e}")
        return 0


def update_mpg_calculations(worksheet):
    """Update MPG formulas for rows where current and previous both have gallons + odometer for Samantha"""
    try:
        # Get all rows
        all_rows = worksheet.get_all_values()
        if len(all_rows) <= 2:  # Need at least header + 2 data rows
            return 0

        updated_count = 0
        suspicious_count = 0

        # Start from row 3 (index 2, since we need a previous row)
        for i in range(2, len(all_rows)):
            current_row = all_rows[i]
            previous_row = all_rows[i - 1]

            # Check if current row is for Samantha (primary car)
            current_car = current_row[COL_CAR].strip().lower() if len(current_row) > COL_CAR else ""
            if current_car != CAR_PRIMARY:
                continue

            # Check if both rows have gallons and odometer
            current_has_data = (
                len(current_row) > COL_ODOMETER and
                current_row[COL_GALLONS].strip() and
                current_row[COL_ODOMETER].strip()
            )
            previous_has_data = (
                len(previous_row) > COL_ODOMETER and
                previous_row[COL_GALLONS].strip() and
                previous_row[COL_ODOMETER].strip()
            )

            # Check if previous row is also Samantha
            previous_car = previous_row[COL_CAR].strip().lower() if len(previous_row) > COL_CAR else ""
            previous_is_samantha = previous_car == CAR_PRIMARY

            if current_has_data and previous_has_data and previous_is_samantha:
                # Row numbers are 1-indexed in Google Sheets
                sheet_row_num = i + 1

                # Calculate MPG to check if it's suspicious
                try:
                    current_odometer = float(current_row[COL_ODOMETER])
                    previous_odometer = float(previous_row[COL_ODOMETER])
                    current_gallons = float(current_row[COL_GALLONS])
                    calculated_mpg = (current_odometer - previous_odometer) / current_gallons

                    # Check if MPG > 35 (likely missing transaction)
                    if calculated_mpg > 35:
                        # Clear the cell and highlight yellow
                        worksheet.update_cell(sheet_row_num, COL_MPG + 1, "")
                        # Format cell with yellow background
                        worksheet.format(f"{chr(65+COL_MPG)}{sheet_row_num}", {
                            "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.0}
                        })
                        suspicious_count += 1
                        continue
                except (ValueError, ZeroDivisionError):
                    # If we can't calculate, skip this row
                    continue

                # Create formula: =(odometer_current - odometer_previous) / gallons_current
                # Using A1 notation for the formula
                mpg_formula = f"=({chr(65+COL_ODOMETER)}{sheet_row_num}-{chr(65+COL_ODOMETER)}{sheet_row_num-1})/{chr(65+COL_GALLONS)}{sheet_row_num}"

                # Check if MPG cell needs updating (is empty or not a formula)
                current_mpg = current_row[COL_MPG] if len(current_row) > COL_MPG else ""
                if not current_mpg.startswith("="):
                    # Update the MPG cell
                    worksheet.update_cell(sheet_row_num, COL_MPG + 1, mpg_formula)
                    updated_count += 1

        if suspicious_count > 0:
            print(f"⚠️  Found {suspicious_count} suspicious MPG value(s) > 35 (highlighted yellow)")

        return updated_count
    except Exception as e:
        print(f"⚠️  Error updating MPG calculations: {e}")
        return 0


# ==== YNAB INTEGRATION ====
def fetch_gas_transactions():
    """Fetch gas transactions from YNAB"""
    configuration = ynab.Configuration(access_token=YNAB_API_KEY)

    with ynab.ApiClient(configuration) as api_client:
        transactions_api = ynab.TransactionsApi(api_client)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=DAYS_BACK)

        try:
            # Get all transactions for the budget (we'll filter by category)
            transactions_response = transactions_api.get_transactions(
                budget_id=YNAB_BUDGET_ID,
                since_date=start_date.strftime('%Y-%m-%d')
            )

            gas_transactions = []
            for transaction in transactions_response.data.transactions:
                # Filter by gas category if specified
                if YNAB_GAS_CATEGORY_ID and transaction.category_id != YNAB_GAS_CATEGORY_ID:
                    continue
                # Skip pending transactions
                if transaction.cleared == 'uncleared':
                    continue

                gas_transactions.append(transaction)

            return gas_transactions

        except Exception as e:
            print(f"❌ Error fetching YNAB transactions: {e}")
            return []


def extract_provider_from_payee(payee_name):
    """Extract gas station provider from payee name"""
    if not payee_name:
        return "Unknown"

    # Common gas station mappings
    providers = {
        'BP': 'BP',
        'SHELL': 'Shell',
        'MOBIL': 'Mobil',
        'EXXON': 'ExxonMobil',
        'CHEVRON': 'Chevron',
        'CITGO': 'Citgo',
        'SPEEDWAY': 'Speedway',
        'MARATHON': 'Marathon',
        'PHILLIPS': 'Phillips 66',
        'SINCLAIR': 'Sinclair',
        'VALERO': 'Valero',
        'COSTCO': 'Costco Gas',
        'SAMS': "Sam's Club Gas",
        'KWIK': 'Kwik Trip'
    }

    payee_upper = payee_name.upper()
    for key, value in providers.items():
        if key in payee_upper:
            return value

    return payee_name


# ==== HOME ASSISTANT NOTIFICATION ====
def send_ha_notification(missing_count, sheet_url):
    """Send notification to Home Assistant"""
    if missing_count == 0:
        print("✅ No action needed - all transactions have been processed")
        return

    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }

    message = f"You have {missing_count} gas fill-up{'s' if missing_count != 1 else ''} that need data entry"

    payload = {
        "message": message,
        "title": "Gas Tracker: Action Needed",
        "data": {
            "url": sheet_url,
            "clickAction": sheet_url
        }
    }

    # Call the notify service
    service_path = HA_NOTIFY_SERVICE.replace(".", "/")
    url = f"{HA_URL}/api/services/{service_path}"

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"📱 Sent Home Assistant notification: {missing_count} transaction(s) need gallon data")
        print(f"   Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️  Failed to send Home Assistant notification: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.status_code} - {e.response.text}")


# ==== MAIN ====
if __name__ == "__main__":
    print("🚀 Gas Tracker - YNAB to Google Sheets Sync")
    print("=" * 60)

    # Fetch YNAB transactions
    print("💰 Fetching gas transactions from YNAB...")
    gas_transactions = fetch_gas_transactions()
    print(f"💳 Found {len(gas_transactions)} gas transactions in last {DAYS_BACK} days")

    # Connect to Google Sheet
    print(f"\n📊 Connecting to Google Sheet '{GOOGLE_SHEET_TAB_NAME}'...")
    worksheet = get_google_sheet()

    # Get existing transaction IDs
    existing_ids = get_existing_transaction_ids(worksheet)
    print(f"📋 Found {len(existing_ids)} existing transactions in sheet")

    # Filter for new transactions only
    new_transactions = [t for t in gas_transactions if t.id not in existing_ids]
    print(f"🆕 Found {len(new_transactions)} new transactions to add")

    # Append new transactions
    if new_transactions:
        added_count = append_transactions_to_sheet(worksheet, new_transactions)
        print(f"✅ Added {added_count} new transactions to sheet")

    # Count rows needing user input
    missing_count = count_missing_data(worksheet)
    print(f"\n📝 Transactions needing data entry: {missing_count}")

    # Update MPG calculations
    print("\n📐 Updating MPG calculations...")
    mpg_updated = update_mpg_calculations(worksheet)
    if mpg_updated > 0:
        print(f"✅ Updated {mpg_updated} MPG formula(s)")
    else:
        print("✅ All MPG formulas up to date")

    # Send Home Assistant notification
    sheet_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit#gid={worksheet.id}"
    send_ha_notification(missing_count, sheet_url)

    print("\n" + "=" * 60)
    print("✅ Sync complete!")
    print(f"📊 Google Sheet: {sheet_url}")
