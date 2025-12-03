"""
Optimized CSV processing script with batch reading, parallel embedding, and Weaviate indexing.
Supports resume capability and comprehensive error handling.
"""


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import json
import logging
import os
import sys
import gc
import signal
from typing import List, Dict, Any, Optional
from datetime import datetime

import pandas as pd
from tqdm import tqdm
import aiohttp

import config
from openai_client import create_async_openai_client
from weaviate_client import create_weaviate_client, batch_insert_objects
from resource_manager import (
    setup_signal_handlers, 
    setup_atexit_handler,
    register_cleanup,
    force_cleanup
)
from error_tracker import ErrorTracker


# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoint state for resume capability"""
    
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.state = self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load checkpoint from file"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}. Starting fresh.")
        return {"last_processed_row": 0, "total_processed": 0, "total_errors": 0}
    
    def save(self):
        """Save checkpoint to file"""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save checkpoint: {e}")
    
    def update(self, rows_processed: int, errors: int = 0):
        """Update checkpoint state"""
        self.state["last_processed_row"] += rows_processed
        self.state["total_processed"] += rows_processed
        self.state["total_errors"] += errors
        self.state["last_updated"] = datetime.now().isoformat()
        self.save()
    
    def get_last_row(self) -> int:
        """Get the last processed row number"""
        return self.state.get("last_processed_row", 0)


class LyricsProcessor:
    """Main processor for lyrics data with embedding and indexing"""
    
    def __init__(self):
        # Initialize OpenAI client using centralized module
        self.openai_client, self.embedding_model = create_async_openai_client()
        
        self.weaviate_client = None
        self.checkpoint = CheckpointManager(config.CHECKPOINT_FILE)
        self.error_tracker = ErrorTracker()  # Track all failures
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_EMBEDDINGS)
        
    def initialize_weaviate(self):
        """Initialize Weaviate client using centralized module"""
        try:
            # Use centralized client creation
            self.weaviate_client = create_weaviate_client()
            logger.info(f"Connected to Weaviate collection: {config.WEAVIATE_CLASS_NAME}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {e}")
            raise
    
    def clean_and_validate_row(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """Clean and validate a single row of data"""
        try:
            # Convert row to dict
            data = row.to_dict()
            song_id = str(data.get('id', 'unknown'))
            
            # Validate required fields
            if pd.isna(data.get('lyrics')) or str(data.get('lyrics')).strip() == '':
                logger.warning(f"Skipping row with empty lyrics: ID={song_id}")
                # Log to error tracker
                self.error_tracker.log_validation_error(
                    song_id=song_id,
                    reason="Empty or missing lyrics field",
                    row_data={
                        "title": str(data.get('title', '')),
                        "artist": str(data.get('artist', '')),
                        "lyrics": ""
                    }
                )
                return None
            
            # Clean and convert data types
            cleaned_data = {
                'title': str(data.get('title', '')),
                'tag': str(data.get('tag', '')),
                'artist': str(data.get('artist', '')),
                'year': int(data.get('year', 0)) if pd.notna(data.get('year')) else 0,
                'views': int(data.get('views', 0)) if pd.notna(data.get('views')) else 0,
                'features': str(data.get('features', '')),
                'lyrics': str(data.get('lyrics', '')),
                'song_id': song_id,
                'language_cld3': str(data.get('language_cld3', '')),
                'language_ft': str(data.get('language_ft', '')),
                'language': str(data.get('language', ''))
            }
            
            return cleaned_data
            
        except Exception as e:
            song_id = str(row.get('id', 'unknown'))
            logger.error(f"Error cleaning row: {e}, Row ID: {song_id}")
            # Log to error tracker
            self.error_tracker.log_error(
                error_type="DATA_CLEANING_ERROR",
                song_id=song_id,
                reason=str(e),
                additional_data={"raw_data": str(row.to_dict())[:200]}
            )
            return None
    
    async def get_embedding(self, text: str, retry_count: int = 0) -> Optional[List[float]]:
        """Get embedding for text using OpenAI API with retry logic"""
        async with self.semaphore:  # Limit concurrent requests
            try:
                # Truncate text if too long (simple approach without chunking)
                max_chars = 8000 * 4  # ~8000 tokens
                if len(text) > max_chars:
                    logger.warning(f"Text too long ({len(text)} chars), truncating to {max_chars}")
                    text = text[:max_chars]
                
                response = await self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text,
                    timeout=config.OPENAI_TIMEOUT
                )
                return response.data[0].embedding
                
            except Exception as e:
                if retry_count < config.OPENAI_MAX_RETRIES:
                    logger.warning(f"Embedding request failed (attempt {retry_count + 1}): {e}. Retrying...")
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    return await self.get_embedding(text, retry_count + 1)
                else:
                    logger.error(f"Embedding request failed after {config.OPENAI_MAX_RETRIES} retries: {e}")
                    return None
    
    async def process_batch_embeddings(self, batch_data: List[Dict[str, Any]]) -> List[tuple]:
        """
        Process embeddings for a batch of rows concurrently.
        Long lyrics are truncated (no chunking).
        """
        # Create tasks for all embeddings in the batch
        tasks = []
        for data in batch_data:
            task = self.get_embedding(data['lyrics'])
            tasks.append(task)
        
        # Wait for all embeddings to complete
        embeddings = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Pair data with embeddings
        results = []
        for data, embedding in zip(batch_data, embeddings):
            if isinstance(embedding, Exception):
                logger.error(f"Exception getting embedding for ID {data['song_id']}: {embedding}")
                # Log to error tracker
                self.error_tracker.log_embedding_error(
                    song_id=data['song_id'],
                    reason=str(embedding),
                    row_data=data
                )
                results.append((data, None))
            elif embedding is None:
                logger.error(f"Failed to get embedding for ID {data['song_id']}")
                results.append((data, None))
            else:
                # Normal case: single embedding for lyrics
                results.append((data, embedding))
        
        return results
    
    async def index_to_weaviate(self, batch_results: List[tuple]) -> tuple[int, int]:
        """Index a batch of data to Weaviate using centralized batch insert (async to not block)"""
        success_count = 0
        error_count = 0
        
        try:
            # Prepare batch data
            objects_to_insert = []
            
            for data, embedding in batch_results:
                if embedding is None:
                    logger.warning(f"Skipping indexing for ID {data['song_id']} due to missing embedding")
                    # Log to error tracker
                    self.error_tracker.log_indexing_error(
                        song_id=data['song_id'],
                        reason="Missing embedding (previous step failed)",
                        row_data={"title": data['title'], "artist": data['artist'], "has_embedding": False}
                    )
                    error_count += 1
                    continue
                
                try:
                    # Prepare object
                    obj = {
                        "properties": {
                            "title": data['title'],
                            "tag": data['tag'],
                            "artist": data['artist'],
                            "year": data['year'],
                            "views": data['views'],
                            "features": data['features'],
                            "lyrics": data['lyrics'],
                            "song_id": data['song_id'],
                            "language_cld3": data['language_cld3'],
                            "language_ft": data['language_ft'],
                            "language": data['language']
                        },
                        "vector": embedding
                    }
                    objects_to_insert.append(obj)
                    
                except Exception as e:
                    logger.error(f"Error preparing data for Weaviate ID {data['song_id']}: {e}")
                    error_count += 1
            
            # Batch insert using centralized function - run in thread pool to not block event loop
            if objects_to_insert:
                try:
                    # Run sync batch insert in thread pool
                    success, errors = await asyncio.to_thread(
                        batch_insert_objects,
                        objects_to_insert
                    )
                    success_count += success
                    error_count += errors
                    
                    logger.info(f"Indexed batch: {success_count} successful, {error_count} errors")
                    
                except Exception as e:
                    logger.error(f"Error during batch indexing: {e}")
                    error_count = len(objects_to_insert)
            
        except Exception as e:
            logger.error(f"Error during batch preparation: {e}")
            error_count = len(batch_results)
        
        return success_count, error_count
    
    async def process_chunk(self, chunk_df: pd.DataFrame, chunk_number: int):
        """Process a single chunk of data (10k rows) with pipelined embedding + indexing"""
        total_rows = len(chunk_df)
        logger.info(f"Processing chunk {chunk_number} with {total_rows} rows")
        
        chunk_success = 0
        chunk_errors = 0
        
        # Prepare all batches first
        batches = []
        for batch_start in range(0, total_rows, config.BATCH_SIZE):
            batch_end = min(batch_start + config.BATCH_SIZE, total_rows)
            batch_df = chunk_df.iloc[batch_start:batch_end]
            
            # Clean and validate data
            batch_data = []
            for _, row in batch_df.iterrows():
                cleaned = self.clean_and_validate_row(row)
                if cleaned:
                    batch_data.append(cleaned)
            
            if batch_data:
                batches.append((batch_start, batch_df, batch_data))
        
        if not batches:
            logger.warning(f"No valid data in chunk {chunk_number}")
            return 0, 0
        
        # Process batches with pipelining: embed batch N while indexing batch N-1
        # This allows embeddings and indexing to run concurrently for maximum throughput
        indexing_task = None
        last_batch_df = None
        
        with tqdm(total=len(batches), desc=f"Chunk {chunk_number}", unit="batch") as pbar:
            for i, (batch_start, batch_df, batch_data) in enumerate(batches):
                # Start embedding current batch immediately (non-blocking)
                embedding_task = asyncio.create_task(self.process_batch_embeddings(batch_data))
                
                # If we have a previous batch being indexed, wait for it NOW
                # This creates overlap: while we wait, the current batch is embedding
                if indexing_task is not None:
                    success, errors = await indexing_task
                    chunk_success += success
                    chunk_errors += errors
                    # Update checkpoint for the previous batch
                    if last_batch_df is not None:
                        self.checkpoint.update(rows_processed=len(last_batch_df), errors=errors)
                    
                    # Add small delay to prevent server overload
                    if hasattr(config, 'BATCH_INSERT_DELAY') and config.BATCH_INSERT_DELAY > 0:
                        await asyncio.sleep(config.BATCH_INSERT_DELAY)
                
                # Wait for current batch embeddings to complete
                batch_results = await embedding_task
                
                # Start indexing current batch immediately (will run while next batch embeds)
                indexing_task = asyncio.create_task(self.index_to_weaviate(batch_results))
                last_batch_df = batch_df
                
                pbar.update(1)
            
            # Wait for the last indexing task to complete
            if indexing_task is not None:
                success, errors = await indexing_task
                chunk_success += success
                chunk_errors += errors
                if last_batch_df is not None:
                    self.checkpoint.update(rows_processed=len(last_batch_df), errors=errors)
        
        logger.info(f"Chunk {chunk_number} complete: {chunk_success} indexed, {chunk_errors} errors")
        return chunk_success, chunk_errors
    
    async def process_csv(self):
        """Main processing function with proper file handle management"""
        logger.info("Starting CSV processing...")
        logger.info(f"Resuming from row: {self.checkpoint.get_last_row()}")
        
        # Initialize Weaviate
        self.initialize_weaviate()
        
        # Resolve CSV path from current location
        csv_path = config.CSV_FILE_PATH
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), '..', csv_path)
        
        total_success = 0
        total_errors = 0
        chunk_number = 0
        skip_rows = self.checkpoint.get_last_row()
        chunk_iterator = None
        
        try:
            # Get total rows for progress tracking
            with open(csv_path, 'r') as f:
                total_rows = sum(1 for _ in f) - 1  # -1 for header
            logger.info(f"Total rows in CSV: {total_rows}")
            
            # Check if MAX_ROWS_TO_PROCESS is set
            max_rows = config.MAX_ROWS_TO_PROCESS
            if max_rows is not None:
                remaining_rows = max_rows - skip_rows
                if remaining_rows <= 0:
                    logger.info(f"MAX_ROWS_TO_PROCESS ({max_rows}) already reached. Nothing to process.")
                    return
                rows_to_process = min(remaining_rows, total_rows - skip_rows)
                logger.info(f"MAX_ROWS_TO_PROCESS: {max_rows}")
                logger.info(f"Rows to process: {rows_to_process} (limit: {max_rows})")
            else:
                rows_to_process = total_rows - skip_rows
                logger.info(f"Rows to process: {rows_to_process} (no limit)")
            
            # Read and process CSV in chunks
            chunk_iterator = pd.read_csv(
                csv_path,
                chunksize=config.CHUNK_SIZE,
                skiprows=range(1, skip_rows + 1) if skip_rows > 0 else None
            )
            
            for chunk_df in chunk_iterator:
                chunk_number += 1
                
                # Check if we've reached the max rows limit
                if max_rows is not None:
                    current_row = skip_rows + (chunk_number - 1) * config.CHUNK_SIZE
                    if current_row >= max_rows:
                        logger.info(f"Reached MAX_ROWS_TO_PROCESS limit ({max_rows}). Stopping.")
                        break
                    
                    # If this chunk would exceed the limit, truncate it
                    rows_remaining = max_rows - self.checkpoint.get_last_row()
                    if len(chunk_df) > rows_remaining:
                        logger.info(f"Truncating final chunk to {rows_remaining} rows to reach limit")
                        chunk_df = chunk_df.iloc[:rows_remaining]
                
                success, errors = await self.process_chunk(chunk_df, chunk_number)
                total_success += success
                total_errors += errors
                
                # Check again after processing this chunk
                if max_rows is not None and self.checkpoint.get_last_row() >= max_rows:
                    logger.info(f"Reached MAX_ROWS_TO_PROCESS limit ({max_rows}). Stopping.")
                    break
            
            logger.info("=" * 80)
            if max_rows is not None and self.checkpoint.get_last_row() >= max_rows:
                logger.info(f"Processing stopped at MAX_ROWS_TO_PROCESS limit: {max_rows}")
            else:
                logger.info("Processing complete!")
            logger.info(f"Total records processed: {total_success}")
            logger.info(f"Total errors: {total_errors}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Fatal error during processing: {e}")
            logger.error("Checkpoint has been saved - you can resume from this point")
            raise
        finally:
            # Cleanup: Close chunk iterator if it exists
            if chunk_iterator is not None:
                try:
                    chunk_iterator.close()
                    logger.info("✓ CSV chunk iterator closed")
                except:
                    pass
            
            # Close Weaviate client
            if self.weaviate_client:
                try:
                    self.weaviate_client.close()
                    logger.info("✓ Weaviate connection closed")
                except Exception as e:
                    logger.error(f"Error closing Weaviate: {e}")
            
            # Force garbage collection of dataframes
            gc.collect()
            logger.info("✓ Memory cleaned up")
    
    async def close(self):
        """Cleanup resources with proper error handling"""
        logger.info("Starting resource cleanup...")
        
        # Close Weaviate client
        if self.weaviate_client:
            try:
                logger.info("Closing Weaviate connection...")
                self.weaviate_client.close()
                logger.info("✓ Weaviate connection closed")
            except Exception as e:
                logger.error(f"Error closing Weaviate: {e}")
            finally:
                self.weaviate_client = None
        
        # Close OpenAI client
        if self.openai_client:
            try:
                logger.info("Closing OpenAI client...")
                await self.openai_client.close()
                logger.info("✓ OpenAI client closed")
            except Exception as e:
                logger.error(f"Error closing OpenAI client: {e}")
            finally:
                self.openai_client = None
        
        # Force garbage collection
        logger.info("Running garbage collection...")
        collected = gc.collect()
        logger.info(f"✓ Garbage collection complete: {collected} objects collected")
        
        logger.info("✓ All resources cleaned up")


async def main():
    """Main entry point with proper resource management"""
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    setup_atexit_handler()
    
    processor = None
    
    try:
        processor = LyricsProcessor()
        
        # Register cleanup for Weaviate connection
        if processor.weaviate_client:
            register_cleanup(
                lambda: processor.weaviate_client.close() if processor.weaviate_client else None,
                "Weaviate connection"
            )
        
        await processor.process_csv()
        
    except KeyboardInterrupt:
        logger.warning("\n" + "=" * 70)
        logger.warning("Processing interrupted by user (Ctrl+C)")
        logger.warning("=" * 70)
        logger.info("Progress has been saved to checkpoint file")
        logger.info("Run the script again to resume from where you left off")
        
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"Fatal error occurred: {e}")
        logger.error("=" * 70)
        import traceback
        traceback.print_exc()
        logger.error("Initiating emergency cleanup...")
        
    finally:
        # Always cleanup resources
        if processor:
            try:
                await processor.close()
            except Exception as e:
                logger.error(f"Error during processor cleanup: {e}")
        
        # Force garbage collection
        logger.info("Final garbage collection...")
        for i in range(2):
            collected = gc.collect()
            logger.info(f"  GC pass {i+1}: {collected} objects collected")
        
        logger.info("All resources released")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

