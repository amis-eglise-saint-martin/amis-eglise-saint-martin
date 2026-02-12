#!/usr/bin/env python3
"""
Visitor counter using Simple Analytics API.

Fetches visitor count from Simple Analytics and adds it to the base count
from the old website (23785 visitors).

Usage:
    python count_visitors.py              # Update visitor count
    python count_visitors.py --status     # Show current count
    python count_visitors.py --domain X   # Use specific domain
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Base count from old website before migration
BASE_COUNT = 23785

# Domain must be provided via env or CLI (no hardcoded default)

# Data file location - check Docker mount first, then project path
DOCKER_DATA_FILE = Path("/data/visitor_count.json")
PROJECT_DATA_FILE = PROJECT_ROOT / "docker" / "visitor_count.json"
DATA_FILE = DOCKER_DATA_FILE if DOCKER_DATA_FILE.parent.exists() else PROJECT_DATA_FILE


def fetch_sa_visitors(domain: str) -> int:
    """Fetch total visitor count from Simple Analytics API."""
    url = f"https://simpleanalytics.com/{domain}.json?version=6&fields=visitors"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
            return data.get('visitors', 0)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        if e.code == 401:
            print("Site might be private - API key required")
        return 0
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return 0
    except json.JSONDecodeError:
        print("Failed to parse JSON response")
        return 0


def load_data() -> dict:
    """Load existing visitor data."""
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {'count': BASE_COUNT}


def save_data(data: dict) -> None:
    """Save visitor data to JSON file."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Visitor counter using Simple Analytics')
    parser.add_argument('--status', action='store_true', help='Show current count')
    parser.add_argument('--domain', type=str, help='Simple Analytics domain')
    args = parser.parse_args()

    # Get domain from args or env (required)
    domain = args.domain or os.environ.get('SA_DOMAIN') or os.environ.get('DOMAIN')
    if not domain:
        print("Error: No domain specified. Use --domain, SA_DOMAIN, or DOMAIN env var.")
        sys.exit(1)

    if args.status:
        data = load_data()
        print(f"Current visitor count: {data.get('count', 0):,}")
        print(f"Base count (old site): {data.get('base_count', BASE_COUNT):,}")
        print(f"SA visitors: {data.get('sa_visitors', 0):,}")
        print(f"Last updated: {data.get('last_updated', 'Never')}")
        return

    # Fetch from Simple Analytics
    print(f"Fetching visitors from Simple Analytics ({domain})...")
    sa_visitors = fetch_sa_visitors(domain)

    if sa_visitors == 0:
        print("Warning: Got 0 visitors - keeping previous count")
        data = load_data()
        if data.get('count', 0) > BASE_COUNT:
            print(f"Keeping previous count: {data['count']:,}")
            return

    # Calculate total
    total = BASE_COUNT + sa_visitors

    # Save data
    data = {
        'count': total,
        'base_count': BASE_COUNT,
        'sa_visitors': sa_visitors,
        'domain': domain,
        'last_updated': datetime.now().isoformat()
    }
    save_data(data)

    print(f"Total: {total:,} visitors")
    print(f"  - Base (old site): {BASE_COUNT:,}")
    print(f"  - Simple Analytics: {sa_visitors:,}")


if __name__ == '__main__':
    main()
