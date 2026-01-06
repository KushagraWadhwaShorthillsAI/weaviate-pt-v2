import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

"""
Quick script to check processing progress
"""

import json
import os
from datetime import datetime
import config

def format_time_ago(iso_timestamp):
    """Format timestamp as time ago"""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day(s) ago"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600} hour(s) ago"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60} minute(s) ago"
        else:
            return f"{diff.seconds} second(s) ago"
    except:
        return "Unknown"

def main():
    checkpoint_file = config.CHECKPOINT_FILE
    
    if not os.path.exists(checkpoint_file):
        print("No checkpoint file found. Processing hasn't started yet.")
        print(f"Run: python process_lyrics.py")
        return
    
    try:
        with open(checkpoint_file, 'r') as f:
            state = json.load(f)
        
        # Resolve CSV path from utilities/ folder
        csv_path = config.CSV_FILE_PATH
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), '..', csv_path)
        
        # Get total rows
        total_rows = sum(1 for _ in open(csv_path)) - 1
        
        last_row = state.get('last_processed_row', 0)
        total_processed = state.get('total_processed', 0)
        total_errors = state.get('total_errors', 0)
        last_updated = state.get('last_updated', 'Never')
        
        percentage = (last_row / total_rows * 100) if total_rows > 0 else 0
        remaining = total_rows - last_row
        success_rate = ((total_processed - total_errors) / total_processed * 100) if total_processed > 0 else 0
        
        print("=" * 60)
        print("PROCESSING PROGRESS")
        print("=" * 60)
        print(f"Last Processed Row:  {last_row:,} / {total_rows:,}")
        print(f"Progress:            {percentage:.2f}%")
        print(f"Remaining:           {remaining:,} rows")
        print()
        print(f"Total Processed:     {total_processed:,}")
        print(f"Successful:          {total_processed - total_errors:,}")
        print(f"Errors:              {total_errors:,}")
        print(f"Success Rate:        {success_rate:.2f}%")
        print()
        print(f"Last Updated:        {last_updated}")
        print(f"                     ({format_time_ago(last_updated)})")
        print("=" * 60)
        
        # Progress bar
        bar_length = 50
        filled = int(bar_length * percentage / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"[{bar}] {percentage:.1f}%")
        print("=" * 60)
        
        if last_row < total_rows:
            print(f"\n💡 To continue processing: python process_lyrics.py")
        else:
            print(f"\n✅ Processing complete!")
        
    except Exception as e:
        print(f"Error reading checkpoint: {e}")

if __name__ == "__main__":
    main()

