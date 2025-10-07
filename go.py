import os
import sqlite3
from datetime import datetime, timedelta
import ynab

# ==== CONFIG ====
YNAB_API_KEY = os.getenv("YNAB_API_KEY")
YNAB_BUDGET_ID = os.getenv("YNAB_BUDGET_ID")
YNAB_GAS_CATEGORY_ID = os.getenv("YNAB_GAS_CATEGORY_ID")
DAYS_BACK = 90
DB_PATH = "gas_tracking.db"

if not YNAB_API_KEY:
    raise EnvironmentError("YNAB_API_KEY environment variable not set")
if not YNAB_BUDGET_ID:
    raise EnvironmentError("YNAB_BUDGET_ID environment variable not set")


# ==== DATABASE SETUP ====
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gas_transactions (
            ynab_transaction_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            amount INTEGER NOT NULL,
            payee_name TEXT,
            memo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ==== YNAB INTEGRATION ====
def fetch_gas_transactions():
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
            print(f"Error fetching YNAB transactions: {e}")
            return []


def store_gas_transactions(transactions):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for transaction in transactions:
        cursor.execute('''
            INSERT OR REPLACE INTO gas_transactions
            (ynab_transaction_id, date, amount, payee_name, memo)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            transaction.id,
            transaction.var_date.strftime('%Y-%m-%d') if hasattr(transaction.var_date, 'strftime') else str(transaction.var_date),
            transaction.amount,
            transaction.payee_name or '',
            transaction.memo or ''
        ))

    conn.commit()
    conn.close()
    return len(transactions)


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


# ==== MAIN ====
if __name__ == "__main__":
    print("🚀 Gas Tracker - YNAB Integration")
    print("=" * 40)

    # Initialize database
    print("📊 Setting up database...")
    init_database()

    # Fetch YNAB transactions
    print("💰 Fetching gas transactions from YNAB...")
    gas_transactions = fetch_gas_transactions()
    print(f"💳 Found {len(gas_transactions)} gas transactions")

    if gas_transactions:
        stored_count = store_gas_transactions(gas_transactions)
        print(f"💾 Stored {stored_count} transactions in database")

    # Create output table
    print(f"\n📊 Gas Fill-Up Summary (Last {DAYS_BACK} days)")
    print("=" * 80)
    print(f"{'Date':<12} {'Provider':<20} {'Amount':<10}")
    print("-" * 80)

    for transaction in gas_transactions:
        # Extract data for table
        date = transaction.var_date.strftime('%Y-%m-%d') if hasattr(transaction.var_date, 'strftime') else str(transaction.var_date)
        provider = extract_provider_from_payee(transaction.payee_name)
        amount = abs(transaction.amount) / 1000

        # Display table row
        print(f"{date:<12} {provider:<20} ${amount:<9.2f}")

    print("-" * 80)
    print(f"\n📈 Summary:")
    print(f"💳 Total fill-ups: {len(gas_transactions)}")
    print(f"💾 Database: {DB_PATH}")

    if gas_transactions:
        total_spent = sum(abs(t.amount) / 1000 for t in gas_transactions)
        print(f"💰 Total spent: ${total_spent:.2f}")
