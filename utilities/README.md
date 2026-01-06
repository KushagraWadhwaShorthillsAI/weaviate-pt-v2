# Utilities Module

Helper scripts for testing, verification, and analysis.

---

## 📂 Scripts

### verify_setup.py

**Purpose:** Verify all connections and configuration

**Tests:**
- Azure OpenAI connection
- Weaviate connection
- CSV file accessibility
- Collection existence

**Usage:**
```bash
python verify_setup.py
```

**Output:**
```
✅ OpenAI: PASS
✅ Weaviate: PASS (SongLyrics exists)
✅ CSV File: PASS
```

---

### count_objects.py

**Purpose:** Count objects in all Weaviate collections

**Usage:**
```bash
cd ../indexing  # Must run from indexing folder
python count_objects.py
```

**Output:**
```
SongLyrics: 1,000,416 objects
SongLyrics_400k: 400,000 objects
...
Total: 1,737,416 objects
```

---

### check_test_data.py

**Purpose:** Verify performance test results exist

**Checks:**
- `single_collection_reports/reports_*/`
- `multi_collection_reports/reports_*/`
- Shows missing test types/limits

**Usage:**
```bash
python check_test_data.py
```

---

### check_all_collections.py

**Purpose:** Check status of all collections

**Shows:**
- Expected vs actual object counts
- Collection status (complete/partial/empty)
- Total objects across all collections

**Usage:**
```bash
python check_all_collections.py
```

---

### analyze_lyrics_size.py

**Purpose:** Analyze lyrics data distribution

**Analyzes:**
- Character count distribution
- Word count distribution
- Statistics (mean, median, percentiles)

**Usage:**
```bash
python analyze_lyrics_size.py
# Or with sample size:
python analyze_lyrics_size.py 100000
```

---

### check_progress.py

**Purpose:** Check indexing progress from checkpoint

**Shows:**
- Last processed row
- Total processed
- Progress percentage
- Estimated remaining time
- Error count

**Usage:**
```bash
python check_progress.py
```

---

### analyze_errors.py

**Purpose:** Analyze errors from processing logs

**Analyzes:**
- Error types and frequencies
- Failed song IDs
- Error patterns

**Usage:**
```bash
python analyze_errors.py
```

---

## 🔧 Configuration

All scripts read from `../config.py`:

```python
WEAVIATE_URL = "http://ip:port"
WEAVIATE_API_KEY = "key"
CSV_FILE_PATH = "song_lyrics.csv"
```

**Note:** Scripts handle relative paths from utilities/ folder automatically.

---

## 📝 Common Usage

### Before Indexing:
```bash
python verify_setup.py  # Verify all connections
```

### During Indexing:
```bash
python check_progress.py  # Check progress
```

### After Indexing:
```bash
python count_objects.py  # Verify counts
python check_all_collections.py  # Check status
```

### For Testing:
```bash
python check_test_data.py  # Verify PT results
```

### For Cleanup:
```bash
python delete_collection.py  # Delete collections safely
```

---
