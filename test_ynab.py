#!/usr/bin/env python3

import ynab
from datetime import datetime, timedelta
from secrets import ynab_api_key

# Configuration
API_KEY = ynab_api_key
DAYS_BACK = 30

def test_ynab_connection():
    """Test YNAB API connection and list budgets"""
    print("🔗 Testing YNAB API connection...")

    configuration = ynab.Configuration(access_token=API_KEY)

    try:
        with ynab.ApiClient(configuration) as api_client:
            # Test budgets endpoint
            budgets_api = ynab.BudgetsApi(api_client)
            budgets_response = budgets_api.get_budgets()

            print(f"✅ Connected successfully!")
            print(f"📊 Found {len(budgets_response.data.budgets)} budget(s):")

            for budget in budgets_response.data.budgets:
                print(f"   • {budget.name} (ID: {budget.id})")

            return budgets_response.data.budgets

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def test_categories(budget_id):
    """List categories for a budget to find gas category"""
    print(f"\n📁 Listing categories for budget {budget_id}...")

    configuration = ynab.Configuration(access_token=API_KEY)

    try:
        with ynab.ApiClient(configuration) as api_client:
            categories_api = ynab.CategoriesApi(api_client)
            categories_response = categories_api.get_categories(budget_id=budget_id)

            gas_categories = []
            print("📂 Available categories:")

            for category_group in categories_response.data.category_groups:
                print(f"\n🗂️  {category_group.name}:")
                for category in category_group.categories:
                    print(f"   • {category.name} (ID: {category.id})")

                    # Look for gas-related categories
                    if any(term in category.name.lower() for term in ['gas', 'fuel', 'car', 'auto']):
                        gas_categories.append((category.name, category.id))

            if gas_categories:
                print(f"\n⛽ Found potential gas categories:")
                for name, cat_id in gas_categories:
                    print(f"   • {name} (ID: {cat_id})")

            return gas_categories

    except Exception as e:
        print(f"❌ Failed to get categories: {e}")
        return []

def test_transactions(budget_id, category_id=None):
    """Test fetching recent transactions"""
    print(f"\n💳 Fetching recent transactions...")

    configuration = ynab.Configuration(access_token=API_KEY)

    try:
        with ynab.ApiClient(configuration) as api_client:
            transactions_api = ynab.TransactionsApi(api_client)

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=DAYS_BACK)

            # Get transactions
            transactions_response = transactions_api.get_transactions(
                budget_id=budget_id,
                since_date=start_date.strftime('%Y-%m-%d')
            )

            all_transactions = transactions_response.data.transactions
            print(f"📝 Found {len(all_transactions)} total transactions in last {DAYS_BACK} days")

            # Filter by category if specified
            if category_id:
                filtered_transactions = [t for t in all_transactions if t.category_id == category_id]
                print(f"⛽ Found {len(filtered_transactions)} gas transactions")
                transactions_to_show = filtered_transactions
            else:
                transactions_to_show = all_transactions[:10]  # Show first 10

            # Display sample transactions
            print(f"\n📋 Sample transactions:")
            for i, transaction in enumerate(transactions_to_show[:5]):
                print(f"\n{i+1}. {transaction.payee_name or 'Unknown Payee'}")
                print(f"   📅 Date: {transaction.date.strftime('%Y-%m-%d') if hasattr(transaction.date, 'strftime') else transaction.date}")
                print(f"   💵 Amount: ${abs(transaction.amount) / 1000:.2f}")
                print(f"   📁 Category ID: {transaction.category_id}")
                print(f"   🆔 Transaction ID: {transaction.id}")
                if transaction.memo:
                    print(f"   📝 Memo: {transaction.memo}")

            return transactions_to_show

    except Exception as e:
        print(f"❌ Failed to get transactions: {e}")
        return []

if __name__ == "__main__":
    print("🧪 YNAB API Test Script")
    print("=" * 40)

    # Test connection and get budgets
    budgets = test_ynab_connection()
    if not budgets:
        exit(1)

    # Find the "USA Money 2022" budget
    usa_budget = None
    for budget in budgets:
        if "USA Money 2022" in budget.name:
            usa_budget = budget
            break

    if not usa_budget:
        print("❌ Could not find 'USA Money 2022' budget")
        exit(1)

    print(f"🎯 Using budget: {usa_budget.name}")
    budget_id = usa_budget.id

    # Test categories
    gas_categories = test_categories(budget_id)

    # Test transactions (without category filter first)
    print(f"\n🔍 Testing transaction retrieval...")
    transactions = test_transactions(budget_id)

    # If we found gas categories, test with category filter
    if gas_categories:
        # Look for "Gas for car" specifically
        gas_for_car_id = None
        for name, cat_id in gas_categories:
            if "Gas for car" in name:
                gas_for_car_id = cat_id
                break

        if gas_for_car_id:
            print(f"\n⛽ Testing with 'Gas for car' category filter...")
            gas_transactions = test_transactions(budget_id, gas_for_car_id)
        else:
            print(f"\n⛽ Testing with gas category filter ({gas_categories[0][0]})...")
            gas_transactions = test_transactions(budget_id, gas_categories[0][1])

    print(f"\n✅ Test completed successfully!")
    print(f"\n📋 Next steps:")
    print(f"   1. Set YNAB_BUDGET_ID={budget_id}")
    if gas_categories:
        print(f"   2. Set YNAB_GAS_CATEGORY_ID={gas_categories[0][1]}")
    print(f"   3. Run the main go.py script")