#!/usr/bin/env python3
"""
Test script to manually enqueue Open Meteo fetch jobs with custom timestamps.

Usage:
    python test_fetch_open_meteo.py                    # Yesterday's time
    python test_fetch_open_meteo.py 2026-05-20T14:00   # Specific datetime
    python test_fetch_open_meteo.py --hours-ago 48     # 48 hours ago
"""
import sys
import os
from datetime import datetime, timezone, timedelta
import argparse

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.tasks import fetch_open_meteo_data
from logger.logging_config import setup_logging_colored

logger = setup_logging_colored("test-open-meteo", level="INFO")


def main():
    parser = argparse.ArgumentParser(
        description="Enqueue Open Meteo fetch job with custom timestamp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enqueue job for yesterday (tests historical retry behavior)
  python test_fetch_open_meteo.py

  # Enqueue for specific datetime (ISO format)
  python test_fetch_open_meteo.py 2026-05-20T14:30:00

  # Enqueue for 48 hours ago
  python test_fetch_open_meteo.py --hours-ago 48

  # Enqueue for specific date at noon
  python test_fetch_open_meteo.py --date 2026-05-22 --hour 12
        """
    )
    
    parser.add_argument(
        "datetime",
        nargs="?",
        help="ISO format datetime (e.g., 2026-05-20T14:30:00)"
    )
    parser.add_argument(
        "--hours-ago",
        type=int,
        help="Fetch data from N hours ago"
    )
    parser.add_argument(
        "--date",
        help="Date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=12,
        help="Hour of day (0-23, default: 12)"
    )
    
    args = parser.parse_args()
    
    # Determine target datetime
    now = datetime.now(timezone.utc)
    
    if args.hours_ago:
        target_dt = now - timedelta(hours=args.hours_ago)
        logger.info(f"Using time from {args.hours_ago} hours ago")
    elif args.date:
        try:
            date_obj = datetime.strptime(args.date, "%Y-%m-%d").replace(
                hour=args.hour,
                tzinfo=timezone.utc
            )
            target_dt = date_obj
            logger.info(f"Using specified date: {args.date} at {args.hour}:00 UTC")
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            sys.exit(1)
    elif args.datetime:
        try:
            # Try to parse ISO format
            if 'T' not in args.datetime:
                args.datetime += "T00:00:00"
            target_dt = datetime.fromisoformat(args.datetime.replace('Z', '+00:00'))
            if target_dt.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=timezone.utc)
            logger.info(f"Using specified datetime: {target_dt.isoformat()}")
        except ValueError as e:
            logger.error(f"Invalid datetime format: {e}")
            sys.exit(1)
    else:
        # Default: yesterday
        target_dt = now - timedelta(days=1)
        logger.info("Using yesterday's time (default)")
    
    result_time = target_dt.isoformat()
    logger.info(f"Enqueuing job for: {result_time}")
    
    # Send the task
    try:
        fetch_open_meteo_data.send(result_time)
        logger.info(f"✓ Job enqueued successfully with result_time={result_time}")
        logger.info("Watch logs to see historical data fetch in action")
    except Exception as e:
        logger.error(f"Failed to enqueue job: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
