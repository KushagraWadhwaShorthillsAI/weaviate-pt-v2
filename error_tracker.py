"""
Error tracking system for failed records during processing.
Logs all failures with IDs and reasons for later analysis.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class ErrorTracker:
    """Tracks and logs all processing errors with details"""
    
    def __init__(self, error_log_file: str = "processing_errors.jsonl"):
        self.error_log_file = error_log_file
        self.session_start = datetime.now().isoformat()
        self.error_count = 0
        
        # Create or append to error log
        if not os.path.exists(self.error_log_file):
            logger.info(f"Created new error log: {self.error_log_file}")
        else:
            logger.info(f"Appending to existing error log: {self.error_log_file}")
    
    def log_error(self, 
                  error_type: str,
                  song_id: str,
                  reason: str,
                  additional_data: Optional[Dict[str, Any]] = None):
        """
        Log an error with full details.
        
        Args:
            error_type: Type of error (e.g., 'EMPTY_LYRICS', 'EMBEDDING_FAILED', 'INDEXING_FAILED')
            song_id: The song ID that failed
            reason: Human-readable reason for failure
            additional_data: Any additional context (title, artist, etc.)
        """
        try:
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "session_start": self.session_start,
                "error_type": error_type,
                "song_id": song_id,
                "reason": reason,
                "additional_data": additional_data or {}
            }
            
            # Append to JSONL file (one JSON object per line)
            with open(self.error_log_file, 'a') as f:
                f.write(json.dumps(error_record) + '\n')
            
            self.error_count += 1
            
        except Exception as e:
            logger.error(f"Failed to log error for ID {song_id}: {e}")
    
    def log_validation_error(self, song_id: str, reason: str, row_data: Optional[Dict] = None):
        """Log data validation errors (empty lyrics, invalid data, etc.)"""
        additional = {}
        if row_data:
            additional = {
                "title": row_data.get("title", ""),
                "artist": row_data.get("artist", ""),
                "has_lyrics": bool(row_data.get("lyrics"))
            }
        
        self.log_error("VALIDATION_ERROR", song_id, reason, additional)
    
    def log_embedding_error(self, song_id: str, reason: str, row_data: Optional[Dict] = None):
        """Log embedding generation errors"""
        additional = {}
        if row_data:
            additional = {
                "title": row_data.get("title", ""),
                "artist": row_data.get("artist", ""),
                "lyrics_length": len(str(row_data.get("lyrics", "")))
            }
        
        self.log_error("EMBEDDING_FAILED", song_id, reason, additional)
    
    def log_indexing_error(self, song_id: str, reason: str, row_data: Optional[Dict] = None):
        """Log Weaviate indexing errors"""
        additional = {}
        if row_data:
            additional = {
                "title": row_data.get("title", ""),
                "artist": row_data.get("artist", ""),
                "has_embedding": row_data.get("has_embedding", False)
            }
        
        self.log_error("INDEXING_FAILED", song_id, reason, additional)
    
    def get_stats(self) -> Dict[str, int]:
        """Get error statistics for current session"""
        return {
            "total_errors": self.error_count,
            "session_start": self.session_start
        }

