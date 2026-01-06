import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

"""
Analyze actual token/word/character distribution in your lyrics CSV file.
Provides real statistics instead of estimates.
"""

import pandas as pd
import numpy as np
import config
from tqdm import tqdm


def estimate_tokens(text):
    """Estimate token count (1 token ≈ 4 characters)"""
    return len(str(text)) // 4


def analyze_lyrics_distribution(sample_size=100000):
    """
    Analyze lyrics size distribution from CSV.
    
    Args:
        sample_size: Number of rows to sample (None for all rows)
    """

    # Resolve CSV path from current location
    csv_path = config.CSV_FILE_PATH
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), '..', csv_path)
    

    print("=" * 70)
    print("LYRICS SIZE ANALYSIS")
    print("=" * 70)
    print(f"\nAnalyzing: {config.CSV_FILE_PATH}")
    
    # Read CSV
    print(f"\n📖 Reading CSV (sample_size={sample_size if sample_size else 'ALL'})...")
    
    try:
        if sample_size:
            df = pd.read_csv(csv_path, nrows=sample_size)
        else:
            df = pd.read_csv(csv_path)
        
        print(f"✓ Loaded {len(df):,} rows")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    print("\n📊 Analyzing lyrics sizes...")
    
    # Calculate sizes
    stats = {
        'char_lengths': [],
        'word_counts': [],
        'estimated_tokens': []
    }
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        lyrics = str(row.get('lyrics', ''))
        
        if lyrics and lyrics != 'nan':
            chars = len(lyrics)
            words = len(lyrics.split())
            tokens = estimate_tokens(lyrics)
            
            stats['char_lengths'].append(chars)
            stats['word_counts'].append(words)
            stats['estimated_tokens'].append(tokens)
    
    # Convert to numpy arrays for statistics
    chars = np.array(stats['char_lengths'])
    words = np.array(stats['word_counts'])
    tokens = np.array(stats['estimated_tokens'])
    
    # Calculate statistics
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print(f"\n📊 Sample Size: {len(chars):,} songs with lyrics")
    
    # Character statistics
    print(f"\n📝 CHARACTER COUNT:")
    print(f"   Mean:       {np.mean(chars):>10,.1f} characters")
    print(f"   Median:     {np.median(chars):>10,.1f} characters")
    print(f"   Std Dev:    {np.std(chars):>10,.1f}")
    print(f"   Min:        {np.min(chars):>10,} characters")
    print(f"   Max:        {np.max(chars):>10,} characters")
    print(f"   25th %:     {np.percentile(chars, 25):>10,.1f} characters")
    print(f"   50th %:     {np.percentile(chars, 50):>10,.1f} characters")
    print(f"   75th %:     {np.percentile(chars, 75):>10,.1f} characters")
    print(f"   95th %:     {np.percentile(chars, 95):>10,.1f} characters")
    print(f"   99th %:     {np.percentile(chars, 99):>10,.1f} characters")
    
    # Word statistics
    print(f"\n📖 WORD COUNT:")
    print(f"   Mean:       {np.mean(words):>10,.1f} words")
    print(f"   Median:     {np.median(words):>10,.1f} words")
    print(f"   Std Dev:    {np.std(words):>10,.1f}")
    print(f"   Min:        {np.min(words):>10,} words")
    print(f"   Max:        {np.max(words):>10,} words")
    print(f"   25th %:     {np.percentile(words, 25):>10,.1f} words")
    print(f"   75th %:     {np.percentile(words, 75):>10,.1f} words")
    print(f"   95th %:     {np.percentile(words, 95):>10,.1f} words")
    print(f"   99th %:     {np.percentile(words, 99):>10,.1f} words")
    
    # Token statistics (estimated)
    print(f"\n🔢 ESTIMATED TOKENS (1 token ≈ 4 chars):")
    print(f"   Mean:       {np.mean(tokens):>10,.1f} tokens")
    print(f"   Median:     {np.median(tokens):>10,.1f} tokens")
    print(f"   Std Dev:    {np.std(tokens):>10,.1f}")
    print(f"   Min:        {np.min(tokens):>10,} tokens")
    print(f"   Max:        {np.max(tokens):>10,} tokens")
    print(f"   25th %:     {np.percentile(tokens, 25):>10,.1f} tokens")
    print(f"   75th %:     {np.percentile(tokens, 75):>10,.1f} tokens")
    print(f"   95th %:     {np.percentile(tokens, 95):>10,.1f} tokens")
    print(f"   99th %:     {np.percentile(tokens, 99):>10,.1f} tokens")
    
    # Chunking analysis
    print(f"\n✂️  CHUNKING ANALYSIS (8,000 token threshold):")
    songs_needing_chunking = np.sum(tokens > 8000)
    percentage_chunking = (songs_needing_chunking / len(tokens)) * 100
    
    print(f"   Songs > 8,000 tokens:  {songs_needing_chunking:>10,} ({percentage_chunking:.2f}%)")
    print(f"   Songs ≤ 8,000 tokens:  {len(tokens) - songs_needing_chunking:>10,} ({100-percentage_chunking:.2f}%)")
    
    if songs_needing_chunking > 0:
        chunked_tokens = tokens[tokens > 8000]
        avg_chunks = np.mean(chunked_tokens) / 8000
        print(f"   Avg chunks needed:     {avg_chunks:>10.2f} chunks per long song")
        estimated_extra_chunks = int(songs_needing_chunking * (avg_chunks - 1))
        print(f"   Extra objects:         {estimated_extra_chunks:>10,} (due to chunking)")
    
    # Distribution
    print(f"\n📊 DISTRIBUTION:")
    bins = [0, 1000, 2000, 4000, 6000, 8000, 10000, 15000, 999999]
    labels = ['<1k', '1k-2k', '2k-4k', '4k-6k', '6k-8k', '8k-10k', '10k-15k', '>15k']
    
    for i, label in enumerate(labels):
        if i < len(bins) - 1:
            count = np.sum((tokens >= bins[i]) & (tokens < bins[i+1]))
            percentage = (count / len(tokens)) * 100
            print(f"   {label:10} tokens: {count:>10,} songs ({percentage:>5.2f}%)")
    
    # Storage estimate
    print(f"\n💾 STORAGE ESTIMATE (for full dataset):")
    total_rows = df.shape[0] if sample_size is None else 3000000  # Approximate total
    
    avg_text_size = np.mean(chars)
    avg_vector_size = 3072 * 4  # 3072 dimensions × 4 bytes
    avg_metadata_size = 1024  # ~1 KB for metadata
    avg_per_song = (avg_text_size + avg_vector_size + avg_metadata_size) / 1024  # In KB
    
    total_storage_gb = (total_rows * avg_per_song) / (1024 * 1024)  # Convert to GB
    
    print(f"   Avg text size:         {avg_text_size:>10,.0f} bytes")
    print(f"   Avg vector size:       {avg_vector_size:>10,} bytes")
    print(f"   Avg total per song:    {avg_per_song:>10,.1f} KB")
    print(f"   Estimated total:       {total_storage_gb:>10,.1f} GB (for {total_rows:,} songs)")
    
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)
    
    if sample_size and sample_size < total_rows:
        print(f"\n💡 Note: This analysis is based on {sample_size:,} sample rows.")
        print(f"   For complete analysis, run without sample limit (will take longer).")


if __name__ == "__main__":
    import sys
    
    # Check for sample size argument
    if len(sys.argv) > 1:
        try:
            sample = int(sys.argv[1])
            analyze_lyrics_distribution(sample_size=sample)
        except ValueError:
            print("Usage: python analyze_lyrics_size.py [sample_size]")
            print("Example: python analyze_lyrics_size.py 100000")
            sys.exit(1)
    else:
        # Default: analyze 100k samples for speed
        print("Analyzing 100,000 sample rows (for full analysis, pass sample size)")
        print("Example: python analyze_lyrics_size.py 1000000")
        print("")
        analyze_lyrics_distribution(sample_size=100000)

