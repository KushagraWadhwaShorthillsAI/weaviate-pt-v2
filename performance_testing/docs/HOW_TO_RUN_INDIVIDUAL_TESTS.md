# How to Run Individual Performance Tests

This guide shows how to run specific tests instead of the full suite.

---

## 🚀 Quick Start - Run Everything

```bash
./run_all_pt_tests.sh
```

Runs all tests (~4.5 hours):
- Multi-collection (25 tests)
- Single-collection (25 tests)
- Generates all reports

---

## 🎯 Run Specific Test Scenarios

### Option 1: Only Multi-Collection Tests

```bash
# Generate queries first
python generate_all_queries.py --type multi

# Run all multi-collection tests
cd multi_collection
./run_multi_collection_all_limits.sh
```

### Option 2: Only Single-Collection Tests

```bash
# Generate queries first
python generate_all_queries.py --type single

# Run all single-collection tests
cd single_collection
python run_automated_tests.py
```

---

## 🔍 Run Specific Search Type (e.g., Only BM25)

### For Multi-Collection (BM25 only, all limits):

```bash
# 1. Generate BM25 queries only
python generate_all_queries.py --type multi --search-types bm25

# 2. Run for each limit manually
cd multi_collection

for LIMIT in 10 50 100 150 200; do
    # Update locustfile
    sed -i.bak "s/queries_bm25_[0-9]*\.json/queries_bm25_${LIMIT}.json/" locustfile_bm25.py
    
    # Run test
    locust -f locustfile_bm25.py \
        --users 100 --spawn-rate 5 --run-time 5m --headless \
        --html ../../multi_collection_reports/reports_${LIMIT}/bm25_report.html \
        --csv ../../multi_collection_reports/reports_${LIMIT}/bm25
    
    echo "✅ BM25 limit $LIMIT complete"
done
```

### For Single-Collection (BM25 only, all limits):

```bash
# 1. Generate BM25 queries
python generate_all_queries.py --type single --search-types bm25

# 2. Edit run_automated_tests.py to only include BM25:
cd single_collection
# Comment out other tests in run_automated_tests.py, keep only BM25

# 3. Run
python run_automated_tests.py
```

---

## 📊 Run Specific Limit (e.g., Only Limit 200)

### For All Search Types but Only Limit 200:

```bash
# 1. Generate queries for limit 200 only
python generate_all_queries.py --type multi --limits 200

# 2. Edit run_multi_collection_all_limits.sh:
#    Change: LIMITS=(10 50 100 150 200)
#    To:     LIMITS=(200)

cd multi_collection
./run_multi_collection_all_limits.sh
```

---

## 🎯 Run ONE Specific Test (e.g., BM25 at Limit 50)

### Multi-Collection:

```bash
# 1. Generate queries
python generate_all_queries.py --type multi --search-types bm25 --limits 50

# 2. Run single test
cd multi_collection

# Update locustfile to use queries_bm25_50.json
sed -i.bak 's/queries_bm25_.*\.json/queries_bm25_50.json/' locustfile_bm25.py

# Run test
locust -f locustfile_bm25.py \
    --users 100 --spawn-rate 5 --run-time 5m --headless \
    --html ../../multi_collection_reports/reports_50/bm25_report.html \
    --csv ../../multi_collection_reports/reports_50/bm25
```

---

## 📋 Search Type Reference

| Search Type | Description | Query File |
|-------------|-------------|------------|
| **bm25** | Keyword-only search | queries_bm25_{limit}.json |
| **hybrid_01** | Hybrid α=0.1 (keyword-focused) | queries_hybrid_01_{limit}.json |
| **hybrid_09** | Hybrid α=0.9 (vector-focused) | queries_hybrid_09_{limit}.json |
| **vector** | Pure semantic search | queries_vector_{limit}.json |
| **mixed** | Mix of all types | queries_mixed_{limit}.json |

---

## 🔧 Query Generation Options

### Generate Only Specific Search Types:

```bash
# Only BM25
python generate_all_queries.py --type multi --search-types bm25

# Only Hybrid
python generate_all_queries.py --type multi --search-types hybrid_01 hybrid_09

# Only Vector
python generate_all_queries.py --type multi --search-types vector
```

### Generate Only Specific Limits:

```bash
# Only limits 10 and 200
python generate_all_queries.py --type multi --limits 10 200

# Only limit 100
python generate_all_queries.py --type single --limits 100
```

### Combine Options:

```bash
# BM25 + Hybrid 0.1, only limits 50 and 100
python generate_all_queries.py --type multi \
    --search-types bm25 hybrid_01 \
    --limits 50 100
```

---

## 📂 File Organization

### Multi-Collection Files:
```
multi_collection/
├── locustfile_bm25.py
├── locustfile_hybrid_01.py
├── locustfile_hybrid_09.py
├── locustfile_vector.py
├── locustfile_mixed.py
├── run_multi_collection_all_limits.sh  (runs all)
└── queries_*.json  (generated)
```

### Single-Collection Files:
```
single_collection/
├── locustfile_single_vector.py
├── run_automated_tests.py  (runs all)
└── queries_*.json  (generated)
```

---

## ⚡ Quick Examples

### Example 1: Test BM25 Performance Across All Limits
```bash
python generate_all_queries.py --type multi --search-types bm25
cd multi_collection
# Edit run_multi_collection_all_limits.sh to only run BM25 test
./run_multi_collection_all_limits.sh
```

### Example 2: Quick Test with Limit 10 Only
```bash
python generate_all_queries.py --type single --limits 10
cd single_collection
# Edit run_automated_tests.py: LIMITS = [10]
python run_automated_tests.py
```

### Example 3: Compare Hybrid 0.1 vs 0.9
```bash
python generate_all_queries.py --type multi --search-types hybrid_01 hybrid_09
cd multi_collection
# Edit runner to only test hybrid_01 and hybrid_09
./run_multi_collection_all_limits.sh
```

---

## 📝 Note

1. **Always generate queries first** before running tests
2. **Edit runner scripts** to skip unwanted tests (comment out sections)
3. **Use specific limits** to save time during development
4. **Start with limit 10** for quick validation

---

**See `README.md` for full documentation**

