# Backup & Restore - Complete Guide

Fast and reliable backup/restore using Weaviate v4 REST API.

---

## 🚀 Quick Start

### Step 1: Create Schemas (if needed)

```bash
cd backup_restore
python create_all_schemas.py
```

**Options:**
- Enter `1` - Create one collection
- Enter `all` - Create all 9 collections
- Enter `1 2 3` - Create multiple

---

### Step 2: Backup Collections

```bash
python backup_v4.py
```

**Options:**
- Enter `1` - Backup only one collection
- Enter `all` - Backup all collections
- Enter `1 2` - Backup multiple collections

**What happens:**
- Fetches objects in batches of 10,000
- Saves to local JSON files temporarily
- Uploads to Azure Blob Storage
- Deletes local files (no disk usage)
- Memory-optimized with GC

---

### Step 3: Restore Collections

#### Restore All Files:

```bash
python restore_v4.py
```

#### Restore Specific File Range:

```bash
# Restore files 1-10
python restore_v4.py --start 1 --end 10

# Restore from file 5 onwards
python restore_v4.py --start 5

# Restore up to file 10
python restore_v4.py --end 10
```

**What happens:**
- Lists backed up collections
- Select collection and backup run
- Downloads JSON files from Azure
- Batch inserts via REST API (FAST!)
- Shows progress with memory cleanup

---

## 📂 Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| **backup_v4.py** | Backup collections | `python backup_v4.py` |
| **restore_v4.py** | Restore collections | `python restore_v4.py --start 1 --end 10` |
| **create_all_schemas.py** | Create collection schemas | `python create_all_schemas.py` |
| **check_blob_backups.py** | List available backups | `python check_blob_backups.py` |

---

## 🔧 Features

### backup_v4.py

- ✅ Weaviate v4 compatible
- ✅ REST API (no gRPC needed)
- ✅ Auto-detects schema properties
- ✅ Collection selection (single/multiple/all)
- ✅ Batch size: 10,000 objects
- ✅ Cursor-based pagination
- ✅ Memory-optimized (aggressive GC)
- ✅ Progress tracking
- ✅ Error handling

### restore_v4.py

- ✅ Weaviate v4 compatible
- ✅ REST batch API (FAST!)
- ✅ File range selection (--start --end)
- ✅ Auto-creates schema if missing
- ✅ Backup selection
- ✅ Memory-optimized (aggressive GC)
- ✅ Progress bars
- ✅ Error handling
- ✅ 10-30x faster than old method

### create_all_schemas.py

- ✅ Hardcoded schema (no dependency on SongLyrics)
- ✅ Collection selection
- ✅ Complete schema (12 properties)
- ✅ All configuration included

### delete_collection.py

**Purpose:** Safely delete Weaviate collections

**Features:**
- Lists all collections with object counts
- Number-based selection
- Double confirmation (prevents accidents)
- Shows what will be deleted

**Usage:**
```bash
python delete_collection.py
```

**Workflow:**
1. Lists collections with counts
2. Enter number to delete
3. Shows preview
4. Type exact collection name to confirm
5. Deletes collection

---

## 💡 Usage Examples

### Backup SongLyrics_10k:

```bash
cd backup_restore
python backup_v4.py
# Enter: 11
# Confirm: yes
```

**Output:**
```
Backing up: SongLyrics_10k
Fetching batch 1... Got 2000 objects
   Saving... 35.2 MB
   ✅ Uploaded
   ✅ Cleaned up local file
   
✅ Backup complete: 2,000 objects
```

---

### Restore SongLyrics_10k (All Files):

```bash
python restore_v4.py
# Select collection
# Select backup
```

---

### Restore in Batches (Parallel):

**Terminal 1:**
```bash
python restore_v4.py --start 1 --end 10
```

**Terminal 2:**
```bash
python restore_v4.py --start 11 --end 20
```

**Benefit:** 2x faster!

---

## 🔑 Configuration

Edit `../config.py`:

```python
# Azure Blob Storage
AZURE_BLOB_CONNECTION_STRING = "DefaultEndpointsProtocol=https;..."
AZURE_BLOB_CONTAINER_NAME = "weaviate-backups"

# Weaviate
WEAVIATE_URL = "http://your-url:8080"
WEAVIATE_API_KEY = "your-key"
```

---

## 🗂️ Backup Structure

```
Azure Container: weaviate-backups/
├── SongLyrics/
│   └── backup_20251025_120000/
│       ├── SongLyrics_backup_20251025_120000_1.json
│       ├── SongLyrics_backup_20251025_120000_2.json
│       └── ...
├── SongLyrics_10k/
│   └── backup_20251025_150000/
│       ├── SongLyrics_10k_backup_20251025_150000_1.json
│       └── ...
```

---

### Complete Backup/Restore Cycle:

```bash
# 1. Create schema (if needed)
python create_all_schemas.py
# Enter: 1

# 2. Backup
python backup_v4.py
# Enter: 1
# Confirm: yes

# 3. Verify backup
python check_blob_backups.py

# 4. Restore (if needed)
python restore_v4.py
# Or: python restore_v4.py --start 1 --end 10
```

---
