# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a gas mileage tracking tool that uses YNAB (You Need A Budget) transactions as the source of truth and correlates them with gas pump and odometer photos using Immich's CLIP-based smart search. The system generates comprehensive fuel tracking reports with extracted gallon amounts from pump displays.

## Architecture

**YNAB-First Design**: The application (`go.py`) follows a transaction-driven approach:
- Fetches gas transactions from YNAB API using specified budget and category
- Uses Immich's smart search API with both semantic ("odometer", "gas pump") and amount-based queries
- Extracts actual gallon amounts from gas pump displays using CLIP search
- Matches photos to transactions within a 72-hour window
- Outputs formatted table with comprehensive fill-up data

**Key Integration Points**:
- YNAB API: Retrieves gas transactions from specified budget/category
- Immich API endpoint: `IMMICH_URL/api/search/smart` for CLIP-based photo search
- Authentication via API keys from environment variables
- SQLite database for persistent storage of matches

## Configuration

**Environment Setup**:
```bash
source setup_env.sh  # Sets all required environment variables
source .venv/bin/activate  # Python virtual environment
python go.py
```

**Required Environment Variables** (set in `setup_env.sh`):
- `IMMICH_API_KEY`: Immich server authentication
- `YNAB_API_KEY`: YNAB API access token
- `YNAB_BUDGET_ID`: Target YNAB budget UUID
- `YNAB_GAS_CATEGORY_ID`: Gas category UUID for filtering transactions

**Key Configuration Values** (in `go.py`):
- `DAYS_BACK`: Search window (90 days for comprehensive history)
- `MATCH_WINDOW_HOURS`: Max time difference for photo matching (72 hours)
- `DB_PATH`: SQLite database file location

## Core Algorithms

**Enhanced Search Flow**:
1. Fetch gas transactions from YNAB for specified time period
2. Query Immich for "odometer" and "gas pump" photos within date range
3. Perform amount-based searches using transaction amounts (e.g., "34.99")
4. Match transactions to photos within 72-hour window using timestamp correlation
5. Extract actual gallon amounts from pump displays using CLIP semantic search
6. Generate formatted table output with provider recognition

**Gallon Extraction Logic**:
- Calculates likely gallon amounts based on transaction amount and current gas prices
- Uses CLIP search to find specific gallon values in pump display images
- Only extracts from photos > $10 transactions to focus on main fill-ups
- Returns actual values when found, blank when not extractable (no estimates)

**Provider Recognition**:
- Maps YNAB payee names to standardized gas station brands
- Handles common variations (BP, Shell, Costco Gas, Marathon, etc.)

## Output Format

The system generates a comprehensive table showing:
- **Date**: Transaction date from YNAB
- **Provider**: Recognized gas station brand
- **Amount**: Transaction amount in dollars
- **Gallons**: Extracted from pump displays (blank if not found)
- **Odometer**: Reading from odometer photos (placeholder)
- **Photos**: Count of matched pump/odometer images

## Development Notes

- Dependencies: `requests`, `ynab` Python SDK, SQLite
- Virtual environment setup with `uv`
- No estimates - only shows actual extracted gallon values
- Comprehensive logging of extraction attempts and matches
- SQLite database stores transaction history and photo matches