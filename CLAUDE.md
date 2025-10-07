# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a gas mileage tracking tool that uses YNAB (You Need A Budget) transactions as the source of truth, syncs them to a Google Sheet for manual data entry, and sends Home Assistant notifications when action is needed.

## Project Goal

**Daily automated workflow (via cron):**
1. Fetch gas transactions from YNAB API (last 90 days)
2. Sync new transactions to Google Sheet (using `ynab_transaction_id` as unique key)
3. Count rows with missing gallon data
4. Send Home Assistant notification with:
   - Count of transactions needing gallon data
   - Clickable link to open the Google Sheet

**No local database** - Google Sheet is the master record of state.

## Architecture

**Data Flow:**
```
YNAB API → Python Script → Google Sheet
                ↓
         Home Assistant Notification
```

**Google Sheet Structure:**
- Columns: `ynab_transaction_id`, `date`, `provider`, `amount`, `gallons`, `notes`
- `ynab_transaction_id` is the unique key to differentiate new vs existing transactions
- User manually fills in `gallons` column after receiving notification

**Integration Points:**
1. **YNAB API**: Source of truth for gas transactions
2. **Google Sheets API**: Persistent storage and manual data entry interface
3. **Home Assistant REST API**: User notifications with actionable links

## Configuration

**Environment Setup:**
```bash
source setup_env.sh  # Sets all required environment variables
python go.py
```

**Required Files:**
- `service_account.json`: Google Cloud service account credentials (gitignored)
- `.env`: Contains `HA_TOKEN` (Home Assistant long-lived access token) (gitignored)

**Environment Variables** (set in `setup_env.sh` and `.env`):
- `YNAB_API_KEY`: YNAB API access token
- `YNAB_BUDGET_ID`: Target YNAB budget UUID (0b50ea42-4da0-429d-b457-e3b4978e7331)
- `YNAB_GAS_CATEGORY_ID`: Gas category UUID (cbde5035-6472-4cb2-9785-9eb213ff7cbc - "Gas for car")
- `GOOGLE_SHEETS_CREDS_FILE`: Path to Google service account JSON (default: service_account.json)
- `GOOGLE_SHEET_ID`: Google Sheet ID (1CjsRari_xvY-28jgVTxeLHWmoZtAeaZv8hldYs2b_QU)
- `GOOGLE_SHEET_TAB_NAME`: Worksheet name (Samantha)
- `HA_URL`: Home Assistant instance URL (https://hass.vanstaveren.us)
- `HA_TOKEN`: Home Assistant long-lived access token (from .env)
- `HA_NOTIFY_SERVICE`: HA notification service (notify.mobile_app_trickyiphone16v2)

**Key Configuration Values** (in `go.py`):
- `DAYS_BACK`: Search window (90 days for comprehensive history)

## Core Logic

**Sync Flow:**
1. Fetch gas transactions from YNAB for last 90 days
2. Read existing transactions from Google Sheet (get all `ynab_transaction_id` values)
3. Identify new transactions not yet in sheet
4. Append new rows to Google Sheet with: transaction ID, date, provider, amount, empty gallons, empty notes
5. Count total rows where `gallons` column is empty
6. Send Home Assistant notification if count > 0

**Provider Recognition:**
- Maps YNAB payee names to standardized gas station brands
- Handles common variations (BP, Shell, Costco Gas, Marathon, etc.)

## Output

**Google Sheet Format:**
| ynab_transaction_id | date       | provider    | amount  | gallons | notes |
|---------------------|------------|-------------|---------|---------|-------|
| abc123...           | 2025-10-01 | Shell       | $42.50  |         |       |
| def456...           | 2025-10-05 | Costco Gas  | $38.99  | 12.5    | OK    |

**Home Assistant Notification:**
- Title: "Gas Tracker: Action Needed"
- Message: "You have 3 gas fill-ups that need gallon data"
- Action: Clickable link to Google Sheet URL

## Setup Instructions

1. **Google Service Account Setup:**
   - Service account email: `hg-390@net-power-meter-data.iam.gserviceaccount.com`
   - Must have Editor access to the Google Sheet
   - Credentials stored in `service_account.json` (gitignored)

2. **Google Sheet Setup:**
   - Sheet URL: https://docs.google.com/spreadsheets/d/1CjsRari_xvY-28jgVTxeLHWmoZtAeaZv8hldYs2b_QU
   - Tab name: "Samantha"
   - Header row must exist: `ynab_transaction_id`, `date`, `provider`, `amount`, `gallons`, `notes`

3. **Home Assistant Setup:**
   - Create long-lived access token in HA
   - Add to `.env` file as `HA_TOKEN`
   - Notification service: `notify.mobile_app_trickyiphone16v2`
   - Notifications include clickable URL to open the Google Sheet

4. **Installation:**
   ```bash
   uv pip install -r requirements.txt
   source setup_env.sh
   python go.py
   ```

## Development Notes

- Dependencies: `ynab` Python SDK, `gspread`, `google-auth`, `requests`
- Virtual environment managed with `uv`
- Designed to run as a daily cron job
- Idempotent: safe to run multiple times (won't create duplicates)
- Google Sheet serves as both storage and UI for manual data entry
- Script only sends notifications when there are missing gallon entries
