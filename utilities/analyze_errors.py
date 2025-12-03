import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

"""
Analyze failed records from error log.
Shows which IDs failed, why, and provides statistics.
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
import os


def load_errors(error_log_file="processing_errors.jsonl"):
    """Load all errors from the error log file"""
    errors = []
    
    if not os.path.exists(error_log_file):
        return errors
    
    try:
        with open(error_log_file, 'r') as f:
            for line in f:
                if line.strip():
                    errors.append(json.loads(line))
        return errors
    except Exception as e:
        print(f"❌ Error loading error log: {e}")
        return []


def analyze_errors(errors):
    """Analyze errors and return statistics"""
    if not errors:
        return None
    
    # Count by error type
    error_types = Counter(e['error_type'] for e in errors)
    
    # Group by session
    sessions = defaultdict(list)
    for e in errors:
        sessions[e['session_start']].append(e)
    
    # Recent errors (last 10)
    recent = sorted(errors, key=lambda x: x['timestamp'], reverse=True)[:10]
    
    # Unique failed IDs
    failed_ids = set(e['song_id'] for e in errors)
    
    return {
        'total_errors': len(errors),
        'error_types': error_types,
        'sessions': len(sessions),
        'recent_errors': recent,
        'failed_ids': failed_ids,
        'latest_session': max(sessions.keys()) if sessions else None
    }


def print_error_summary(stats):
    """Print formatted error summary"""
    print("=" * 70)
    print("ERROR ANALYSIS SUMMARY")
    print("=" * 70)
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Total errors logged: {stats['total_errors']:,}")
    print(f"   Unique failed IDs: {len(stats['failed_ids']):,}")
    print(f"   Processing sessions: {stats['sessions']}")
    
    print(f"\n📋 Error Types:")
    for error_type, count in stats['error_types'].most_common():
        percentage = (count / stats['total_errors']) * 100
        print(f"   {error_type:25} {count:6,} ({percentage:5.2f}%)")
    
    print(f"\n🔍 Recent Errors (Last 10):")
    print("-" * 70)
    for i, error in enumerate(stats['recent_errors'], 1):
        timestamp = error['timestamp'].split('T')[1][:8]  # Just time
        song_id = error['song_id']
        error_type = error['error_type']
        reason = error['reason'][:50]  # Truncate long reasons
        
        print(f"{i:2}. [{timestamp}] ID: {song_id}")
        print(f"    Type: {error_type}")
        print(f"    Reason: {reason}")
        
        # Show additional data if available
        add_data = error.get('additional_data', {})
        if add_data.get('title'):
            print(f"    Title: {add_data['title'][:40]}")
        if add_data.get('artist'):
            print(f"    Artist: {add_data['artist'][:30]}")
        print()


def export_failed_ids(errors, output_file="failed_ids.txt"):
    """Export list of failed IDs to a text file"""
    failed_ids = sorted(set(e['song_id'] for e in errors))
    
    try:
        with open(output_file, 'w') as f:
            for song_id in failed_ids:
                f.write(f"{song_id}\n")
        
        print(f"✅ Exported {len(failed_ids):,} failed IDs to: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Error exporting IDs: {e}")
        return False


def search_errors_by_id(errors, song_id):
    """Find all errors for a specific song ID"""
    matches = [e for e in errors if e['song_id'] == song_id]
    
    if not matches:
        print(f"\n❌ No errors found for ID: {song_id}")
        return
    
    print(f"\n🔍 Errors for ID: {song_id}")
    print("=" * 70)
    
    for i, error in enumerate(matches, 1):
        print(f"\nError #{i}:")
        print(f"  Timestamp: {error['timestamp']}")
        print(f"  Error Type: {error['error_type']}")
        print(f"  Reason: {error['reason']}")
        
        add_data = error.get('additional_data', {})
        if add_data:
            print(f"  Additional Data:")
            for key, value in add_data.items():
                print(f"    - {key}: {value}")


def search_errors_by_type(errors, error_type):
    """Find all errors of a specific type"""
    matches = [e for e in errors if e['error_type'] == error_type]
    
    if not matches:
        print(f"\n❌ No errors found of type: {error_type}")
        return
    
    print(f"\n🔍 Errors of type: {error_type}")
    print(f"   Total: {len(matches):,} errors")
    print("=" * 70)
    
    # Show first 20
    for i, error in enumerate(matches[:20], 1):
        song_id = error['song_id']
        reason = error['reason'][:60]
        title = error.get('additional_data', {}).get('title', 'N/A')[:30]
        
        print(f"{i:3}. ID: {song_id:15} | {title:30} | {reason}")
    
    if len(matches) > 20:
        print(f"\n   ... and {len(matches) - 20:,} more errors of this type")


def main():
    """Main function"""
    error_log_file = "processing_errors.jsonl"
    
    print("=" * 70)
    print("ERROR ANALYSIS TOOL")
    print("=" * 70)
    
    # Check if error log exists
    if not os.path.exists(error_log_file):
        print(f"\n✅ No error log found!")
        print(f"   File: {error_log_file}")
        print(f"\n   This means:")
        print(f"   • No errors occurred yet, OR")
        print(f"   • Processing hasn't started")
        print("\n   Error tracking will begin when process_lyrics.py runs.")
        return 0
    
    # Load errors
    print(f"\n📂 Loading errors from: {error_log_file}")
    errors = load_errors(error_log_file)
    
    if not errors:
        print("\n✅ Error log is empty - no failures recorded!")
        return 0
    
    # Analyze errors
    stats = analyze_errors(errors)
    
    # Print summary
    print_error_summary(stats)
    
    # Interactive menu
    while True:
        print("\n" + "=" * 70)
        print("OPTIONS:")
        print("=" * 70)
        print("1. Export failed IDs to file")
        print("2. Search errors by song ID")
        print("3. Search errors by type")
        print("4. Show all error types")
        print("5. Exit")
        print("=" * 70)
        
        try:
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                export_failed_ids(errors)
            
            elif choice == '2':
                song_id = input("Enter song ID: ").strip()
                search_errors_by_id(errors, song_id)
            
            elif choice == '3':
                print("\nAvailable error types:")
                for i, (error_type, count) in enumerate(stats['error_types'].most_common(), 1):
                    print(f"  {i}. {error_type} ({count:,} errors)")
                
                error_type = input("\nEnter error type: ").strip()
                search_errors_by_type(errors, error_type)
            
            elif choice == '4':
                print("\n📋 All Error Types:")
                for error_type, count in stats['error_types'].most_common():
                    print(f"   {error_type:30} {count:8,} errors")
            
            elif choice == '5':
                print("\n✅ Exiting...")
                break
            
            else:
                print("\n❌ Invalid choice. Please enter 1-5.")
        
        except KeyboardInterrupt:
            print("\n\n✅ Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

