#!/usr/bin/env python3
"""
Visitor counter using Simple Analytics API.

Incrementally counts visitors by fetching daily totals from Simple Analytics
and adding them to a cumulative total. Keeps a daily history for analytics.

Strategy:
  - Each run: finalize any completed days, then fetch today's live count
  - Total = cumulative + today_visitors
  - Finalized days are stored in daily_history for trend analysis

Commands:
    python count_visitors.py              # Update visitor count
    python count_visitors.py --status     # Show current count and recent stats
    python count_visitors.py --export     # Export monthly CSV snapshot
    python count_visitors.py --domain X   # Use specific domain
"""

import argparse
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Initial cumulative total baked into the first run.
# Includes all visitors before the incremental counter was deployed.
INITIAL_CUMULATIVE = 23869
DEPLOY_DATE = "2026-02-08"

# Data file location - check Docker mount first, then project path
DOCKER_DATA_DIR = Path("/data")
PROJECT_DATA_DIR = PROJECT_ROOT / "docker"
DATA_DIR = DOCKER_DATA_DIR if DOCKER_DATA_DIR.exists() else PROJECT_DATA_DIR
DATA_FILE = DATA_DIR / "visitor_count.json"
EXPORTS_DIR = DATA_DIR / "exports"


def fetch_sa_visitors_for_date(domain: str, day: str) -> int:
    """Fetch visitor count from Simple Analytics for a specific date (YYYY-MM-DD)."""
    url = f"https://simpleanalytics.com/{domain}.json?version=6&fields=visitors&info=false&start={day}&end={day}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
            return data.get('visitors', 0)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"Error fetching {day}: {e}")
        return -1  # -1 = error, distinct from 0 visitors


def load_data() -> dict:
    """Load existing visitor data."""
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_data(data: dict) -> None:
    """Save visitor data to JSON file."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def compute_stats(daily_history: dict) -> dict:
    """Compute average daily visitors for various periods."""
    if not daily_history:
        return {}

    today = date.today()
    sorted_days = sorted(daily_history.keys())

    def avg_for_period(days_back):
        cutoff = (today - timedelta(days=days_back)).isoformat()
        values = [v for k, v in daily_history.items() if k >= cutoff and k < today.isoformat()]
        if not values:
            return None
        return round(sum(values) / len(values), 1)

    stats = {
        'avg_7d': avg_for_period(7),
        'avg_30d': avg_for_period(30),
        'first_date': sorted_days[0],
        'last_date': sorted_days[-1],
        'total_days_tracked': len(sorted_days),
    }

    all_values = list(daily_history.values())
    if all_values:
        stats['avg_all_time'] = round(sum(all_values) / len(all_values), 1)
        stats['max_day'] = max(all_values)
        stats['min_day'] = min(all_values)

    return stats


def export_csv(data: dict) -> Path:
    """Export visitor data as a CSV snapshot."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m')
    filepath = EXPORTS_DIR / f"visitors-{timestamp}.csv"

    daily_history = data.get('daily_history', {})
    sorted_days = sorted(daily_history.keys())

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'visitors'])
        for day in sorted_days:
            writer.writerow([day, daily_history[day]])

    return filepath


def cmd_status(data: dict) -> None:
    """Display current count and statistics."""
    print(f"Total visitor count: {data.get('count', INITIAL_CUMULATIVE):,}")
    print(f"  Cumulative:        {data.get('cumulative', 0):,}")
    print(f"  Today (live):      {data.get('today_visitors', 0):,}")
    print(f"  Last counted date: {data.get('last_counted_date', 'None')}")
    print(f"  Last updated:      {data.get('last_updated', 'Never')}")

    daily_history = data.get('daily_history', {})
    if daily_history:
        stats = compute_stats(daily_history)
        print(f"\nDaily statistics ({stats['total_days_tracked']} days tracked):")
        if stats.get('avg_7d') is not None:
            print(f"  Avg last 7 days:   {stats['avg_7d']}")
        if stats.get('avg_30d') is not None:
            print(f"  Avg last 30 days:  {stats['avg_30d']}")
        if stats.get('avg_all_time') is not None:
            print(f"  Avg all time:      {stats['avg_all_time']}")
        print(f"  Best day:          {stats.get('max_day', 'N/A')}")
        print(f"  Tracking since:    {stats.get('first_date', 'N/A')}")


def cmd_export(data: dict) -> None:
    """Export monthly CSV snapshot."""
    filepath = export_csv(data)
    daily_history = data.get('daily_history', {})
    print(f"Exported {len(daily_history)} days to {filepath}")


def cmd_update(domain: str) -> None:
    """Main update: finalize completed days, fetch today's live count."""
    prev = load_data()
    today = date.today()
    today_str = today.isoformat()
    cumulative = prev.get('cumulative', 0)
    last_counted = prev.get('last_counted_date')
    daily_history = prev.get('daily_history', {})

    # First run or migration from old format
    if last_counted is None:
        # Use the higher of INITIAL_CUMULATIVE or previously displayed count
        # so the counter never goes backwards during migration
        prev_count = prev.get('count', 0)
        cumulative = max(INITIAL_CUMULATIVE, prev_count)
        last_counted = today_str
        print(f"Initialized cumulative to {cumulative:,}")

    # Finalize completed days since last_counted_date
    last_date = date.fromisoformat(last_counted)
    finalized_days = 0

    if last_date < today:
        d = last_date + timedelta(days=1)
        while d < today:
            day_str = d.isoformat()
            visitors = fetch_sa_visitors_for_date(domain, day_str)
            if visitors < 0:
                print(f"API error on {day_str}, will retry next run")
                break
            cumulative += visitors
            daily_history[day_str] = visitors
            finalized_days += 1
            print(f"  {day_str}: +{visitors} visitors")
            d += timedelta(days=1)
        else:
            # All days finalized, update last_counted to yesterday
            last_counted = (today - timedelta(days=1)).isoformat()

    if finalized_days > 0:
        print(f"Finalized {finalized_days} day(s), cumulative now: {cumulative:,}")

    # Fetch today's live count (will be finalized tomorrow)
    today_visitors = fetch_sa_visitors_for_date(domain, today_str)
    if today_visitors < 0:
        today_visitors = prev.get('today_visitors', 0)
        print(f"API error for today, keeping previous: {today_visitors}")

    # Total = cumulative (includes old site + all finalized days) + today's live count
    total = cumulative + today_visitors

    data = {
        'count': total,
        'cumulative': cumulative,
        'today_visitors': today_visitors,
        'last_counted_date': last_counted,
        'domain': domain,
        'last_updated': datetime.now().isoformat(),
        'daily_history': daily_history,
    }
    save_data(data)

    print(f"Total: {total:,} visitors (cumul:{cumulative:,} + today:{today_visitors:,})")


def main():
    parser = argparse.ArgumentParser(description='Visitor counter using Simple Analytics')
    parser.add_argument('--status', action='store_true', help='Show current count and stats')
    parser.add_argument('--export', action='store_true', help='Export monthly CSV snapshot')
    parser.add_argument('--domain', type=str, help='Simple Analytics domain')
    args = parser.parse_args()

    # Get domain from args or env (required for update, optional for status/export)
    domain = args.domain or os.environ.get('SA_DOMAIN') or os.environ.get('DOMAIN')

    if args.status:
        data = load_data()
        cmd_status(data)
        return

    if args.export:
        data = load_data()
        cmd_export(data)
        return

    if not domain:
        print("Error: No domain specified. Use --domain, SA_DOMAIN, or DOMAIN env var.")
        sys.exit(1)

    cmd_update(domain)


if __name__ == '__main__':
    main()
