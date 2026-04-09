"""
Personal Finance Tracker.
Rocky can answer questions about spending from a user's CSV expense file.
Default path: ~/Documents/expenses.csv

Expected CSV format (flexible column names):
  Date, Description, Category, Amount
"""

import os
import csv
import logging
from datetime import datetime, timedelta
from collections import defaultdict

DEFAULT_CSV = os.path.join(os.path.expanduser("~"), "Documents", "expenses.csv")

# Flexible column name aliases
_DATE_COLS    = {"date", "day", "transaction date", "time"}
_DESC_COLS    = {"description", "desc", "item", "merchant", "note", "name"}
_AMOUNT_COLS  = {"amount", "cost", "price", "total", "debit", "value"}
_CAT_COLS     = {"category", "cat", "type", "tag"}


def _load_csv(path: str = DEFAULT_CSV) -> list[dict]:
    """Load and normalize the expense CSV."""
    if not os.path.exists(path):
        return []
    
    rows = []
    try:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return []
            
            # Map actual column names to canonical names
            col_map = {}
            for col in reader.fieldnames:
                low = col.strip().lower()
                if low in _DATE_COLS:    col_map['date']        = col
                if low in _DESC_COLS:   col_map['description'] = col
                if low in _AMOUNT_COLS: col_map['amount']      = col
                if low in _CAT_COLS:    col_map['category']    = col

            for row in reader:
                entry = {}
                try:
                    if 'date' in col_map:
                        entry['date'] = row.get(col_map['date'], '').strip()
                    if 'description' in col_map:
                        entry['description'] = row.get(col_map['description'], '').strip()
                    if 'amount' in col_map:
                        raw = row.get(col_map['amount'], '0').replace('$', '').replace(',', '').strip()
                        entry['amount'] = float(raw) if raw else 0.0
                    if 'category' in col_map:
                        entry['category'] = row.get(col_map['category'], '').strip().lower()
                    rows.append(entry)
                except (ValueError, KeyError):
                    pass
    except Exception as e:
        logging.error(f"Finance CSV error: {e}")
    return rows


def query_finance(user_input: str, path: str = DEFAULT_CSV) -> str:
    """Answer finance questions from the CSV in natural language."""
    rows = _load_csv(path)
    if not rows:
        return (
            f"No expense file found at {path}. "
            "Create a CSV with columns: Date, Description, Category, Amount — and I will track it for you."
        )

    low = user_input.lower()
    now = datetime.now()

    # ── Time filtering ────────────────────────────────────────────────────────
    if "today" in low:
        cutoff = now.replace(hour=0, minute=0, second=0)
        label = "today"
    elif "this week" in low or "week" in low:
        cutoff = now - timedelta(days=7)
        label = "this week"
    elif "this month" in low or "month" in low:
        cutoff = now.replace(day=1, hour=0, minute=0, second=0)
        label = "this month"
    elif "this year" in low or "year" in low:
        cutoff = now.replace(month=1, day=1, hour=0, minute=0, second=0)
        label = "this year"
    else:
        cutoff = None
        label = "all time"

    def _within(row):
        if cutoff is None:
            return True
        date_str = row.get('date', '')
        if not date_str:
            return True
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt) >= cutoff
            except ValueError:
                pass
        return True

    filtered = [r for r in rows if _within(r)]

    # ── Query type detection ──────────────────────────────────────────────────
    if "total" in low or "how much" in low or "spend" in low or "spent" in low:
        # Category-specific?
        categories = {"food", "coffee", "groceries", "rent", "transport", "entertainment", "gym", "shopping", "utilities"}
        cat_hit = next((c for c in categories if c in low), None)
        
        if cat_hit:
            cat_rows = [r for r in filtered if cat_hit in r.get('category', '')]
            total = sum(r.get('amount', 0) for r in cat_rows)
            return f"You spent ₹{total:.2f} on {cat_hit} {label}. That is {len(cat_rows)} transactions."
        else:
            total = sum(r.get('amount', 0) for r in filtered)
            return f"Total spending {label}: ₹{total:.2f} across {len(filtered)} transactions."

    elif "most" in low or "biggest" in low or "largest" in low:
        if not filtered:
            return f"No transactions found for {label}."
        biggest = max(filtered, key=lambda r: r.get('amount', 0))
        return (
            f"Largest expense {label}: {biggest.get('description', 'Unknown')} "
            f"at ₹{biggest.get('amount', 0):.2f} "
            f"on {biggest.get('date', 'unknown date')}."
        )

    elif "breakdown" in low or "category" in low or "categor" in low:
        by_cat = defaultdict(float)
        for r in filtered:
            cat = r.get('category', 'Uncategorized') or 'Uncategorized'
            by_cat[cat] += r.get('amount', 0)
        sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)[:5]
        parts = [f"{cat}: ₹{amt:.2f}" for cat, amt in sorted_cats]
        return f"Spending breakdown {label}: " + ", ".join(parts) + "."

    else:
        total = sum(r.get('amount', 0) for r in filtered)
        return f"You have {len(filtered)} transactions totalling ₹{total:.2f} for {label}."
