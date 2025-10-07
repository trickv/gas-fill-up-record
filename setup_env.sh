#!/bin/bash

# Load secrets from .env if it exists
if [ -f .env ]; then
    source .env
fi

# YNAB Environment Variables for Gas Tracking
export YNAB_BUDGET_ID="0b50ea42-4da0-429d-b457-e3b4978e7331"
export YNAB_GAS_CATEGORY_ID="cbde5035-6472-4cb2-9785-9eb213ff7cbc"  # "Gas for car"
export YNAB_API_KEY="A0J2vqduFKLBNh4fkBieDzqavRw4S6WaMMHGDGRxWwk"

# Google Sheets Configuration
export GOOGLE_SHEETS_CREDS_FILE="service_account.json"
export GOOGLE_SHEET_ID="1CjsRari_xvY-28jgVTxeLHWmoZtAeaZv8hldYs2b_QU"
export GOOGLE_SHEET_TAB_NAME="Samantha"

# Home Assistant Configuration
export HA_URL="https://hass.vanstaveren.us"
# HA_TOKEN is loaded from .env file
export HA_NOTIFY_SERVICE="notify.mobile_app_trickyiphone16v2"

echo "✅ Environment variables set for Gas Tracker"
echo "YNAB Budget: USA Money 2022"
echo "YNAB Category: Gas for car"
echo "Google Sheet: Samantha tab"
echo "HA Notify: mobile_app_trickyiphone16v2"