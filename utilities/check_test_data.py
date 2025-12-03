import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import os

print("=" * 70)
print("CHECKING TEST DATA - What Exists & What's Missing")
print("=" * 70)

# Check single_collection_reports
print("\n📂 Folder 1: single_collection_reports/ (Single Collection - SongLyrics)")
print("-" * 70)

single_data = {}
for limit in [10, 50, 100, 150, 200]:
    folder = os.path.join(os.path.dirname(__file__), '..', f"single_collection_reports/reports_{limit}")
    if os.path.exists(folder):
        files = [f for f in os.listdir(folder) if f.endswith('_stats.csv')]
        search_types = [f.replace('_stats.csv', '') for f in files]
        single_data[limit] = search_types
        print(f"Limit {limit:3}: {', '.join(search_types) if search_types else 'EMPTY'}")
    else:
        print(f"Limit {limit:3}: FOLDER NOT FOUND")
        single_data[limit] = []

# Check multi_collection_reports
print("\n📂 Folder 2: multi_collection_reports/ (Multi-Collection - 9 Collections)")
print("-" * 70)

multi_data = {}
for limit in [10, 50, 100, 150, 200]:
    folder = os.path.join(os.path.dirname(__file__), '..', f"multi_collection_reports/reports_{limit}")
    if os.path.exists(folder):
        files = [f for f in os.listdir(folder) if f.endswith('_stats.csv')]
        search_types = [f.replace('_stats.csv', '') for f in files]
        multi_data[limit] = search_types
        print(f"Limit {limit:3}: {', '.join(search_types) if search_types else 'EMPTY'}")
    else:
        print(f"Limit {limit:3}: FOLDER NOT FOUND")
        multi_data[limit] = []

# Expected search types
expected = ['bm25', 'hybrid_01', 'hybrid_09', 'vector', 'mixed']

# Check what's missing
print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)

print("\nSingle Collection (single_collection_reports/):")
single_missing = []
for limit in [10, 50, 100, 150, 200]:
    missing = [st for st in expected if st not in single_data.get(limit, [])]
    if missing:
        single_missing.append((limit, missing))
        print(f"  Limit {limit:3}: Missing {', '.join(missing)}")
    else:
        print(f"  Limit {limit:3}: ✅ Complete")

print("\nMulti-Collection (multi_collection_reports/):")
multi_missing = []
for limit in [10, 50, 100, 150, 200]:
    missing = [st for st in expected if st not in multi_data.get(limit, [])]
    if missing:
        multi_missing.append((limit, missing))
        print(f"  Limit {limit:3}: Missing {', '.join(missing)}")
    else:
        print(f"  Limit {limit:3}: ✅ Complete")

# Final recommendation
print("\n" + "=" * 70)
print("🎯 RECOMMENDATION")
print("=" * 70)

if single_missing:
    print("\n⚠️  Single Collection Missing Data:")
    for limit, missing in single_missing:
        print(f"   Limit {limit}: {', '.join(missing)}")
    print("\n   To fix: Run the missing tests")

if multi_missing:
    print("\n⚠️  Multi-Collection Missing Data:")
    for limit, missing in multi_missing:
        print(f"   Limit {limit}: {', '.join(missing)}")
    print("\n   To fix: Run the missing tests")

if not single_missing and not multi_missing:
    print("\n✅ ALL DATA COMPLETE!")
    print("   Ready to generate reports")

print("\n" + "=" * 70)
