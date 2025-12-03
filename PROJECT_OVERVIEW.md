# Weaviate Performance Testing & Scaling Project

**Complete Overview - Data to Deployment**

---

## 🎯 Project Purpose

**Objective:** Build and test a scalable Weaviate vector database system for song lyrics search.

**Goals:**
1. Index 1M+ song lyrics with embeddings
2. Test search performance across different strategies
3. Find performance bottlenecks and scaling limits
4. Establish baseline metrics for infrastructure decisions

---

## 🏗️ Infrastructure

### Server Details

```
PT server Host: ssh xyz@xx.xx.xxx.xxx
PT server Password: abc@abc
Weaviate URL: http://xx.xxx.xx.xx 
```

**Current Setup:**
- Single node
- Single pod 
- Azure-hosted

---

## 📊 Complete Workflow

### Phase 1: Data Acquisition & Preparation

**Source:** Kaggle Dataset
```
Dataset: genius-song-lyrics-with-language-information
Size: 8.4 GB CSV
Records: 1M+ song lyrics
Fields: title, artist, lyrics, year, views, language, etc.
```

**File:** `song_lyrics.csv` (in project root)

---

### Phase 2: Data Indexing

**Step 1: Schema Creation**
```bash
cd indexing
python create_weaviate_schema.py
```

**Creates:**
- Collection: SongLyrics (and variants)
- 11 properties (title, lyrics, artist, year, etc.)
- Vector index (cosine distance)
- BM25 configuration
- Sharding: 3 shards, Replication: 1, BlockMaxWand: False
- No chunking (lyrics truncated if > 32k chars)

**Step 2: Data Processing & Indexing**
```bash
python process_lyrics.py
```

**What happens:**
1. Reads CSV in chunks (10k rows at a time)
2. Generates embeddings via Azure OpenAI (3072-dim)
3. Batch inserts to Weaviate (50 objects/batch)
4. Resumes on failure (checkpoint-based)
5. Memory-optimized (GC after each chunk)


**Step 3: Create Collection Variants**
```bash
python create_multiple_collections.py
```

**Creates:**
- SongLyrics (1M objects)
- SongLyrics_400k, 200k, 50k, 30k, 20k, 15k, 12k, 10k
- Total: 9 collections for different scale testing

---

### Phase 3: Backup to Azure Blob

**Purpose:** Disaster recovery & quick restore after infrastructure changes

```bash
cd backup_restore
python backup_v4.py
```

**Backup Strategy:**
- Batch size: 10,000 objects per file
- Format: Plain JSON
- Storage: Azure Blob Storage
- Structure: `<collection>/backup_YYYYMMDD_HHMMSS/batch_*.json`

**Example:**
```
weaviate-backups/
├── SongLyrics/backup_20251025_120000/
│   ├── SongLyrics_backup_20251025_120000_1.json (10k objects)
│   ├── SongLyrics_backup_20251025_120000_2.json (10k objects)
│   └── ... (100 files for 1M objects)
```

---

### Phase 4: Performance Testing

**Goal:** Find bottlenecks and optimal search strategy

**Test Scenarios:**

**A. Multi-Collection Search (9 collections simultaneously)**
- Tests searching across multiple collections in one graphql query
- Simulates production workload

**B. Single-Collection Search (SongLyrics 1M only)**
- Tests single collection in one graphql query
- Isolates performance characteristics

**Search Types Tested:**
1. **BM25** - Keyword-only (baseline)
2. **Hybrid α=0.1** - Keyword-focused (90% keyword, 10% vector)
3. **Hybrid α=0.9** - Vector-focused (10% keyword, 90% vector)
4. **Vector (nearVector)** - Pure semantic search
5. **Mixed** - All 4 types rotating (realistic workload)

**Result Limits:**
- 10, 50, 100, 150, 200 results per collection

**Total Tests:** 5 types × 5 limits × 2 scenarios = **50 tests**

**Load:**
- Users: 100 concurrent
- Duration: 5 minutes per test
- Ramp-up: 5 users/sec


**Quick Test Available:**
```bash
cd performance_testing
./quick_test.sh  # 2 users, 20 seconds - For verification
```

---

## 🔍 Sample GraphQL Query

### Multi-Collection Search (All 9 collections in one query):

```graphql
{
  Get {
    SongLyrics(
      hybrid: {
        query: "love and heartbreak"
        alpha: 0.5
        vector: [0.123, 0.456, ..., 0.789]  # 3072-dim embedding
      }
      limit: 200
    ) {
      title
      artist
      lyrics
      year
      views
      _additional {
        score
        distance
      }
    }
    SongLyrics_400k(
      hybrid: { ... }
      limit: 200
    ) {
      title
      artist
      ...
    }
    # ... (7 more collections)
  }
}
```

**Returns:** Up to 1800 results (9 collections × 200 each)

---

## 📈 Project Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. DATA ACQUISITION                          │
│  Kaggle → song_lyrics.csv (8.4GB, 1M+ songs)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    2. DATA INDEXING                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ create_weaviate_schema.py                                │   │
│  │ Creates: SongLyrics collection                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ process_lyrics.py                                        │   │
│  │ • Read CSV chunks                                        │   │
│  │ • Generate embeddings (Azure OpenAI)                     │   │
│  │ • Batch insert to Weaviate                               │   │
│  │ Time: 10-20 hours                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ create_multiple_collections.py                           │   │
│  │ Creates: 8 collection variants (400k, 200k..., 10k)      │   │
│  │ Copy Parent Data to other 8 collections for cost saving  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    3. BACKUP TO AZURE                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ backup_v4.py                                             │   │
│  │ • 10k objects per file                                   │   │
│  │ • Plain JSON format                                      │   │
│  │ • Azure Blob Storage                                     │   │
│  │ • Enables quick restore                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 4. PERFORMANCE TESTING                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Multi-Collection Tests (5 types × 5 limits)              │   │
│  │ • BM25, Hybrid 0.1, Hybrid 0.9, Vector, Mixed            │   │
│  │ • 100 users, 5 minutes each                              │   │
│  │ • Results → multi_collection_report.html                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Single-Collection Tests (5 types × 5 limits)             │   │
│  │ • Same search types                                      │   │
│  │ • Results → single_collection_report.html                │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 5. ANALYSIS & INSIGHTS                          │
│  • Compare search types (which is fastest?)                     │
│  • Compare result limits (optimal size?)                        │
│  • Identify bottlenecks                                         │
│  • Recommend infrastructure changes                             │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Infrastructure Change Workflow

**Every time infrastructure changes:**

### Step 1: Backup (only if data changes otherwise restore old data only)
```bash
cd backup_restore
python backup_v4.py
# Select: all (or specific collections)
```

### Step 2: Change Infrastructure
- Modify Kubernetes config
- Scale pods/nodes
- Restart Weaviate

### Step 3: Create Schemas
```bash
cd backup_restore
python create_all_schemas.py
# Select: all
```

### Step 4: Restore Data
```bash
python restore_v4.py
# Can do parallel restore:
# Terminal 1: python restore_v4.py --start 1 --end 50
# Terminal 2: python restore_v4.py --start 51 --end 100
```

**Time:** ~1-2 hours for 1M objects (vs 10-20 hours to re-index!)

### Step 5: Run Performance Tests
```bash
cd performance_testing
./quick_test.sh  # Quick verification (20 min)
# Or
./run_all_pt_tests.sh  # Full test (4.5 hours)
```

### Step 6: Analyze Results
- Compare with previous configuration
- Check if performance improved
- Decide next scaling step

---

## 📊 Current Collections Info

### Collections Created:
```
SongLyrics:        1,000,416 objects ✅
SongLyrics_400k:     400,000 objects ✅
SongLyrics_200k:     200,000 objects ✅
SongLyrics_50k:       50,000 objects ✅
... (9 collections total)
Total: ~1.7M objects indexed
```

---

## 🛠️ Project Structure

```
nthScaling/
│
├── README.md                    Main project guide
├── PROJECT_OVERVIEW.md          This file - Complete overview
│
├── config.py                    Central configuration
├── requirements.txt             Dependencies
├── [6 shared modules]           weaviate_client, openai_client, etc.
│
├── indexing/                    Data indexing & schema
│   ├── README.md
│   ├── create_weaviate_schema.py
│   ├── process_lyrics.py
│   ├── create_multiple_collections.py
│   └── count_objects.py
│
├── backup_restore/              Azure Blob backup/restore
│   ├── README.md
│   ├── backup_v4.py             Backup (10k/batch, REST API)
│   ├── restore_v4.py            Restore (fast, file range support)
│   ├── create_all_schemas.py    Schema creator
│   ├── delete_collection.py     Safe collection deletion
│   └── check_blob_backups.py    List backups
│
├── performance_testing/         Load testing suite
│   ├── README.md
│   ├── generate_all_queries.py  Query generator (cached embeddings!)
│   ├── run_all_pt_tests.sh      Master runner (50 tests)
│   ├── quick_test.sh            Quick test (20 min)
│   ├── multi_collection/        9 collections tests
│   ├── single_collection/       1M single collection tests
│   └── report_generators/       HTML report creators
│
├── utilities/                   Helper scripts
│   ├── README.md
│   ├── verify_setup.py          Verify all connections
│   └── count_objects.py         Count objects in collections
│
└── Results/                     Generated reports
    ├── multi_collection_reports/
    ├── single_collection_reports/
    ├── multi_collection_report.html
    └── single_collection_report.html
```

---

## 📋 Key Technologies

**Vector Database:**
- Weaviate 1.32.7 (v4 client)

**Embeddings:**
- Azure OpenAI
- Model: text-embedding-3-large
- Dimensions: 3072

**Performance Testing:**
- Locust (load testing framework)
- 100 concurrent users for 5 min
- GraphQL queries

**Storage:**
- Azure Blob Storage
- Backup/restore capability
- ~10k objects per file

---

## 📖 Documentation Index

| Document | Purpose |
|----------|---------|
| **PROJECT_OVERVIEW.md** | This file - Complete project overview |
| **README.md** | Quick start & module navigation |
| **indexing/README.md** | Indexing module guide |
| **backup_restore/README.md** | Backup/restore guide |
| **performance_testing/README.md** | PT comprehensive guide |
| **utilities/README.md** | Utilities guide |
| **performance_testing/QUICK_ACCESS.txt** | Quick PT commands |

---

## 🚀 Quick Command Reference

```bash
# Verify setup
cd utilities && python verify_setup.py

# Index data
cd ../indexing && python process_lyrics.py

# Backup all
cd ../backup_restore && python backup_v4.py  # Enter: all

# Restore with parallel
python restore_v4.py --start 1 --end 50  # Terminal 1
python restore_v4.py --start 51 --end 100  # Terminal 2

# Run quick PT test
cd ../performance_testing && ./quick_test.sh

# Run full PT suite
./run_all_pt_tests.sh
```

---

