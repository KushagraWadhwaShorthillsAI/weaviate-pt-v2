# Indexing Module

Data ingestion, schema creation, and collection management.

---

## 📂 Scripts

### create_weaviate_schema.py

**Purpose:** Create Weaviate collection schema

**Schema Configuration:**
- 11 properties (title, lyrics, artist, year, views, etc.)
- Vector index: Cosine distance
- Sharding: 3 shards
- Replication: Factor 1
- BlockMaxWAND: Disabled
- BM25: b=0.75, k1=1.2

**Properties:**
- **Searchable** (word tokenization): title, lyrics
- **Filterable** (field tokenization): tag, artist, features, song_id, languages
- **Numeric** (range filters): year, views

**Usage:**
```bash
python create_weaviate_schema.py
```

**Note:** Deletes existing collection if confirmed

---

### process_lyrics.py

**Purpose:** Process CSV and index to Weaviate with embeddings

**Features:**
- Reads CSV in chunks (10k rows)
- Generates embeddings via Azure OpenAI (3072-dim)
- Batch inserts (50 objects per batch)
- Checkpoint-based (can resume on failure)
- Memory-optimized (GC after each chunk)
- Long lyrics truncated (no chunking)

**Usage:**
```bash
python process_lyrics.py
```

**Configuration (`config.py`):**
```python
CSV_FILE_PATH = "song_lyrics.csv"
CHUNK_SIZE = 10000  # Rows per chunk
BATCH_SIZE = 50  # Objects per Weaviate batch
MAX_CONCURRENT_EMBEDDINGS = 10
```

**Progress:**
- Saves checkpoint: `processing_checkpoint.json`
- Can resume from last processed row

---

### create_multiple_collections.py

**Purpose:** Create collection variants by copying data

**Creates:**
- SongLyrics_400k (400k objects)
- SongLyrics_200k (200k objects)
- SongLyrics_50k, 30k, 20k, 15k, 12k, 10k

**Method:**
- Copies data from SongLyrics (parent collection)
- Uses cursor-based pagination (handles >100k objects)
- Creates schema for each collection
- Memory-optimized

**Usage:**
```bash
python create_multiple_collections.py
```

**Time:** ~10-30 minutes depending on size

---

### copy_collection.py

**Purpose:** Copy collection using cursor-based pagination

**Features:**
- Handles collections > 100k objects
- UUID cursor pagination (no offset limit)
- Batch processing
- Progress tracking

**Usage:**
```bash
python copy_collection.py
```

**Note:** Weaviate limits offset-based pagination to ~100k objects. This script uses cursors.

---

### count_objects.py

**Purpose:** Count objects in all collections

**Usage:**
```bash
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

## 🔧 Configuration

All scripts use `../config.py`:

```python
# CSV file
CSV_FILE_PATH = "song_lyrics.csv"

# Weaviate
WEAVIATE_URL = "http://ip:port"
WEAVIATE_CLASS_NAME = "SongLyrics"

# Azure OpenAI
AZURE_OPENAI_API_KEY = "key"
AZURE_OPENAI_ENDPOINT = "https://endpoint.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT = "text-embedding-3-large"

# Processing
CHUNK_SIZE = 10000
BATCH_SIZE = 50
MAX_CONCURRENT_EMBEDDINGS = 10
```

---

## 📊 Data Pipeline

```
song_lyrics.csv (8.4GB)
    ↓
Read in chunks (10k rows)
    ↓
Generate embeddings (Azure OpenAI)
    ↓
Batch insert (50 objects)
    ↓
Weaviate collection
```

---

## ⚠️ Important Notes

### CSV File

- Must be in project root
- Expected columns: title, artist, lyrics, year, views, etc.
- Size: ~8.4GB for 1M records

### Embeddings

- Uses Azure OpenAI (not OpenAI directly)
- Model: text-embedding-3-large (3072 dimensions)
- Long lyrics (>32k chars) are truncated
- No chunking

### Memory

- Process uses checkpoints for resume capability
- GC runs after each chunk
- Can handle millions of objects

### Pagination

- Offset-based limited to ~100k objects
- Use cursor-based (UUID) for larger collections
- `copy_collection.py` implements cursor pagination

---

## 🔄 Typical Workflow

```bash
# 1. Create schema
python create_weaviate_schema.py

# 2. Index data
python process_lyrics.py
# (Can take 10-20 hours for 1M objects)

# 3. Verify
python count_objects.py

# 4. Create variants
python create_multiple_collections.py

# 5. Backup
cd ../backup_restore
python backup_v4.py
```

---
