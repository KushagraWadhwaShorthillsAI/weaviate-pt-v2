# 🚀 Parallel Collection Testing

Test performance by sending **9 simultaneous HTTP requests** (one per collection) instead of a single GraphQL query with 9 sub-queries.

---

## 🎯 Purpose

**Hypothesis:** Parallel execution should be faster because the bottleneck becomes the slowest collection, not the sum of all collections.

### Comparison

| Approach | Method | Expected Time |
|----------|--------|---------------|
| **Multi-Collection** | 1 GraphQL query with 9 sub-queries | Sequential or internal processing |
| **Parallel (This)** | 9 simultaneous HTTP requests | max(slowest_collection) + overhead |

---

## 📂 Structure

```
parallel_testing/
├── generate_parallel_report.py    # Report generator
├── run_parallel_tests.sh           # Run all 5 tests
├── locustfile_vector.py            # Vector search (9 parallel)
├── locustfile_bm25.py              # BM25 search (9 parallel)
├── locustfile_hybrid_01.py         # Hybrid α=0.1 (9 parallel)
├── locustfile_hybrid_09.py         # Hybrid α=0.9 (9 parallel)
├── locustfile_mixed.py             # Mixed types (9 parallel)
├── queries/                        # Query files (40 sets × 9 queries each)
├── results_YYYYMMDD_HHMMSS/        # Test results (timestamped)
└── README.md                       # This file
```

---

## 🚀 Quick Start

### 1. Generate Query Files

```bash
cd performance_testing/parallel_testing
python generate_parallel_queries.py --search-types all --limits 10 50 100 150 200
```

**Output:** 25 query files in `queries/` folder

### 2. Run Tests

```bash
# Run all 5 tests (Vector, BM25, Hybrid 0.1, Hybrid 0.9, Mixed)
./run_parallel_tests.sh
```

**Default Settings:**
- Users: 100 concurrent
- Spawn Rate: 5 users/sec  
- Run Time: 5 minutes per test
- Result Limit: 200 per collection

**Customize:**
```bash
USERS=200 SPAWN_RATE=10 RUN_TIME=10m ./run_parallel_tests.sh
```

### 3. Generate Report

```bash
# Auto-detect latest results folder
python generate_parallel_report.py

# Or specify folder
python generate_parallel_report.py results_20251025_103726
```

**Output:** `parallel_collection_report.html`

---

## 📊 How It Works

### Parallel Execution Flow

```python
# 1. Pick random query set (40 options, each with 9 queries)
query_set = random.choice(QUERIES)

# 2. Spawn 9 greenlets for parallel execution (gevent)
greenlets = []
for query in query_set["queries"]:  # 9 iterations
    g = gevent.spawn(execute_request, query)
    greenlets.append(g)

# 3. Wait for ALL 9 to complete (30s timeout)
gevent.joinall(greenlets, timeout=30)

# 4. Total time = max(all response times)
total_time = max(response_times)

# 5. Report to Locust
if all_9_succeeded:
    report_success(total_time)
elif some_succeeded:
    report_partial(successful_count)
else:
    report_failure()
```

### Why Gevent?

- **Async I/O:** True parallel HTTP requests without threads
- **Lightweight:** Much more efficient than OS threads
- **Non-blocking:** Doesn't block on network I/O
- **Locust Compatible:** Built-in support

---

## 🎯 Run Individual Tests

### Vector Search Only

```bash
cd performance_testing/parallel_testing
locust -f locustfile_vector.py \
    --users 100 --spawn-rate 5 --run-time 5m --headless \
    --html results/vector_report.html \
    --csv results/vector
```

### BM25 Search Only

```bash
locust -f locustfile_bm25.py \
    --users 100 --spawn-rate 5 --run-time 5m --headless \
    --html results/bm25_report.html \
    --csv results/bm25
```

### Interactive Mode (Web UI)

```bash
locust -f locustfile_vector.py
# Open http://localhost:8089 in browser
```

---

## 📈 Results

### Files Generated

After running tests:
```
results_YYYYMMDD_HHMMSS/
├── 1_Vector_limit200_report.html
├── 1_Vector_limit200_stats.csv
├── 1_Vector_limit200_stats_history.csv
├── 1_Vector_limit200_failures.csv
├── 1_Vector_limit200.log
├── 2_BM25_limit200_*
├── 3_Hybrid_01_limit200_*
├── 4_Hybrid_09_limit200_*
└── 5_Mixed_limit200_*
```

### Generate Combined Report

```bash
python generate_parallel_report.py results_YYYYMMDD_HHMMSS
```

**Report includes:**
- Response time comparisons
- Throughput (RPS) charts
- Percentile distributions
- Failure rate analysis
- Best/worst performer insights

---

## 🔍 Key Metrics Tracked

### Overall Metrics
- **Total Requests:** Number of parallel batches executed
- **Failures:** Failed parallel batches (≥1 collection failed)
- **Avg Response Time:** Average time for 9 parallel requests
- **Median Response Time:** 50th percentile
- **95th/99th Percentile:** High percentile response times
- **RPS:** Parallel batches per second

### Per-Collection Tracking
- Individual response times for each collection
- Failure rates per collection
- Identify slow collections

### Success Criteria
- **Full Success:** All 9 collections succeeded
- **Partial Success:** Some collections succeeded (e.g., 7/9)
- **Total Failure:** All 9 collections failed

---

## 🎯 Expected Results

### If Parallel is FASTER:
✅ Parallel time ≈ Time of slowest collection (~800ms for 1M collection)  
✅ Significant improvement over multi-collection  
✅ Better resource utilization on Weaviate

### If Multi-Collection is FASTER:
❌ Too much HTTP overhead from 9 requests  
❌ Weaviate already parallelizes internally  
❌ Network latency dominates

### Example Comparison

| Test Type | Multi-Collection | Parallel | Winner |
|-----------|------------------|----------|--------|
| Vector | 2500ms | 800ms | Parallel 🏆 |
| BM25 | 1200ms | 400ms | Parallel 🏆 |
| Hybrid 0.1 | 2800ms | 900ms | Parallel 🏆 |

---

## 🔧 Configuration

### Test Parameters

Edit `run_parallel_tests.sh`:
```bash
USERS=100           # Concurrent users
SPAWN_RATE=5        # Users spawned per second
RUN_TIME=5m         # Test duration
LIMIT=200           # Results per collection
```

### Query Limits

Generate queries for different limits:
```bash
# Only limit 100
python generate_parallel_queries.py --limits 100

# Multiple limits
python generate_parallel_queries.py --limits 50 100 150
```

Then edit locustfiles to load the correct query file (e.g., `queries_vector_100.json`).

---

## 🚨 Error Handling

### Automatic Features

1. **Timeout Protection**
   - 30s timeout per parallel batch
   - Prevents hanging requests

2. **Partial Success Tracking**
   - If 7/9 collections succeed, recorded as partial success
   - Detailed per-collection metrics

3. **Failure Categories**
   - HTTP errors
   - GraphQL errors
   - Timeouts
   - Connection errors

4. **Resource Cleanup**
   - Greenlets properly disposed
   - No memory leaks

---

## 🐛 Troubleshooting

### Issue: "No query files found"

```bash
# Solution: Generate queries first
python generate_parallel_queries.py --search-types all
```

### Issue: "All requests timing out"

**Check Weaviate:**
```bash
curl http://20.161.96.75/v1/.well-known/ready
```

**Solutions:**
- Reduce users: `--users 10`
- Increase timeout in locustfile (line ~75)
- Check network connectivity

### Issue: "Partial failures on large collections"

This is expected! Some collections are slower.
- Check which collections fail consistently
- Consider optimizing those collections
- Review Weaviate logs

### Issue: "Import error: gevent"

```bash
# Solution: Install gevent
pip install gevent>=23.9.0
```

---

## 📊 Comparing with Multi-Collection

### Side-by-Side Test

```bash
# 1. Run multi-collection test
cd ../multi_collection
locust -f locustfile_vector.py --users 100 --run-time 5m --headless --html multi_vector.html

# 2. Run parallel test
cd ../parallel_testing
locust -f locustfile_vector.py --users 100 --run-time 5m --headless --html parallel_vector.html

# 3. Compare reports
open multi_vector.html parallel_vector.html
```

### Key Comparisons

| Metric | What to Compare |
|--------|----------------|
| **Avg Response Time** | Which is faster? |
| **95th Percentile** | Consistency comparison |
| **Throughput (RPS)** | Which handles more load? |
| **Failure Rate** | Reliability comparison |

---

## 💡 Tips

### Quick Validation

Start with a short test:
```bash
locust -f locustfile_vector.py --users 10 --run-time 30s --headless
```

### Monitor Server

Watch Weaviate during tests:
```bash
# CPU/Memory usage
kubectl top pods

# Logs
kubectl logs -f <weaviate-pod>
```

### Analyze Failures

Check failures CSV:
```bash
cat results_*/1_Vector_limit200_failures.csv
```

### Best Practices

1. **Start small:** 10 users, 30 seconds
2. **Ramp up gradually:** 50 → 100 → 200 users
3. **Monitor resources:** Check Weaviate isn't overwhelmed
4. **Compare fairly:** Same users, same duration
5. **Run multiple times:** Average results for accuracy

---

## 📝 Notes

### Query Structure

Each query file contains:
- **40 query sets** (same search terms as multi-collection)
- **9 queries per set** (one per collection)
- **Total:** 360 individual queries per file

### Collections Tested

1. SongLyrics (1,000,000 objects) - Slowest
2. SongLyrics_400k (400,000)
3. SongLyrics_200k (200,000)
4. SongLyrics_50k (50,000)
5. SongLyrics_30k (30,000)
6. SongLyrics_20k (20,000)
7. SongLyrics_15k (15,000)
8. SongLyrics_12k (12,000)
9. SongLyrics_10k (10,000) - Fastest

**Parallel time should ≈ SongLyrics response time (largest collection)**

---

## 🎯 Success Criteria

Parallel testing is **successful** if:
- ✅ ≥30% faster than multi-collection
- ✅ Error rates comparable (≤1% difference)
- ✅ Higher throughput (RPS)
- ✅ Acceptable resource usage

Needs **optimization** if:
- ❌ Slower due to HTTP overhead
- ❌ High error rates (network issues)
- ❌ Client-side resource exhaustion

---

## 🔗 Related Files

- **Query Generator:** `generate_parallel_queries.py`
- **Test Runner:** `run_parallel_tests.sh`
- **Report Generator:** `generate_parallel_report.py`
- **Parent README:** `../README.md`

---

**Happy Testing! 🚀**
