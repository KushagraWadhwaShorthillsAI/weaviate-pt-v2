# Report Naming Conventions

This document defines the standardized naming conventions for all performance test reports.

## 📁 Directory Structure

```
performance_testing/reports/
├── multi_collection/          # Multi-collection test reports
│   ├── reports_RF{rf}_Users{users}_Limit{limit}/     # Regular multi-collection tests
│   ├── fastapi_async_RF{rf}_Users{users}_Limit{limit}/  # FastAPI async tests
│   ├── fastapi_sync_RF{rf}_Users{users}_Limit{limit}/   # FastAPI sync tests
│   └── fanout/                # Fanout test reports (moved from root)
├── single_collection/         # Single-collection test reports
│   └── reports_{limit}/       # Single collection tests (limit-based only)
├── parallel_testing/          # Parallel collection test reports
│   └── results_{timestamp}/   # Timestamped parallel test results
└── fanout/                    # Fanout test reports
```

## 📄 File Naming Standards

### 1. Test Result Folders

**Pattern:** `{test_type}_RF{rf}_Users{users}_Limit{limit}/`

**Examples:**
- `reports_RF3_Users100_Limit200/` - Regular multi-collection tests
- `fastapi_async_RF3_Users100_Limit200/` - FastAPI async tests
- `fastapi_sync_RF3_Users10_Limit200/` - FastAPI sync tests

**Rules:**
- Always include RF value (replication factor)
- Always include Users count
- Always include Limit value
- Use underscores to separate components

### 2. Individual Report Files (Inside Folders)

**Pattern:** `{search_type}_report.html` and `{search_type}_stats.csv`

**Examples:**
- `bm25_report.html`, `bm25_stats.csv`
- `bm25_async_report.html`, `bm25_async_stats.csv`
- `hybrid_09_sync_report.html`, `hybrid_09_sync_stats.csv`
- `hybrid_09_report.html`, `hybrid_09_stats.csv`

**Rules:**
- Search type prefix (bm25, hybrid_01, hybrid_09, vector, mixed)
- Add `_async` or `_sync` suffix for FastAPI tests to differentiate
- Always use `_report.html` for HTML reports
- Always use `_stats.csv` for CSV statistics

### 3. Combined Reports

**Pattern:** `{test_type}_combined_RF{rf}_Users{users}_Limit{limit}.html`

**Examples:**
- `multi_collection_combined_RF3_Users100.html` - Multi-collection (all limits)
- `fastapi_async_combined_RF3_Users100_Limit200.html` - Single user count
- `fastapi_async_combined_RF3_Users100-200-300_Limit200.html` - Multiple user counts
- `fastapi_sync_combined_RF3_Users10_Limit200.html` - Single user count
- `fanout_hybrid_09_RF3_Users100_Limit200.html` - Fanout test
- `parallel_collection_report_{timestamp}.html` - Parallel test (includes timestamp)

**Rules:**
- Always use `_combined` suffix for combined reports
- Always include RF value
- Always include Users count(s)
  - Single user: `Users100`
  - Multiple users: `Users100-200-300` (sorted, hyphen-separated)
- Include Limit when applicable
- For parallel tests, include timestamp folder name

### 4. Single Collection Reports

**Pattern:** `single_collection_report.html`

**Note:** Single collection reports don't vary RF/Users/Limit in the same way, so they use a simpler naming pattern.

### 5. Fanout Reports

**Pattern:** `fanout_hybrid_09_RF{rf}_Users{users}_Limit{limit}.html`

**Location:** `reports/fanout/` subdirectory

**Note:** Fanout reports are now organized in their own subdirectory for better organization.

## 🔄 Migration Notes

### Old Naming Patterns (Deprecated)

- ❌ `multi_collection_report_RF{rf}_Users{users}.html` → ✅ `multi_collection_combined_RF{rf}_Users{users}.html`
- ❌ `fastapi_async_combined_RF{rf}_Limit{limit}.html` (no Users) → ✅ `fastapi_async_combined_RF{rf}_Users{users}_Limit{limit}.html`
- ❌ `hybrid_09_fanout_*.html` in root → ✅ `fanout/hybrid_09_fanout_*.html`
- ❌ `reports_{limit}/` (no RF/Users) → ✅ `reports_RF{rf}_Users{users}_Limit{limit}/`

## ✅ Consistency Checklist

When creating or updating reports, ensure:

- [ ] Folder names include RF, Users, and Limit
- [ ] Combined reports use `_combined` suffix
- [ ] User counts are always included in combined report filenames
- [ ] Multiple user counts use hyphen-separated format: `Users100-200-300`
- [ ] Individual reports use `{search_type}_report.html` pattern
- [ ] FastAPI tests include `_async` or `_sync` in search type names
- [ ] Fanout reports are in `reports/fanout/` subdirectory
- [ ] All paths use forward slashes and relative paths from `performance_testing/`

## 📝 Examples

### Running Multi-Collection Tests
```bash
export PT_RF_VALUE=3 PT_USER_COUNT=100
./run_multi_collection_all_limits.sh
# Creates: reports/multi_collection/reports_RF3_Users100_Limit{10,50,100,150,200}/
# Creates: reports/multi_collection/multi_collection_combined_RF3_Users100.html
```

### Running FastAPI Async Tests
```bash
export PT_RF_VALUE=3 PT_LIMIT=200
USER_COUNTS=(100 200 300)
./run_fastapi_async_tests.sh
# Creates: reports/multi_collection/fastapi_async_RF3_Users{100,200,300}_Limit200/
# Creates: reports/multi_collection/fastapi_async_combined_RF3_Users100-200-300_Limit200.html
```

### Running FastAPI Sync Tests
```bash
export PT_RF_VALUE=3 PT_LIMIT=200
USER_COUNTS=(10)
./run_fastapi_sync_tests.sh
# Creates: reports/multi_collection/fastapi_sync_RF3_Users10_Limit200/
# Creates: reports/multi_collection/fastapi_sync_combined_RF3_Users10_Limit200.html
```

