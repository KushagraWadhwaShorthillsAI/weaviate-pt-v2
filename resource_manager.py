"""
Resource manager for proper cleanup of connections, files, and memory.
Ensures cleanup happens even on crashes, interruptions, or network failures.
"""


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import logging
import signal
import gc
import sys
import atexit
from typing import Optional, List, Any

logger = logging.getLogger(__name__)

# Global registry of resources to cleanup
_cleanup_handlers = []
_shutdown_initiated = False


def register_cleanup(handler, description: str = "Resource"):
    """
    Register a cleanup handler to be called on shutdown.
    
    Args:
        handler: Callable to execute on cleanup
        description: Description of what's being cleaned up
    """
    _cleanup_handlers.append((handler, description))
    logger.debug(f"Registered cleanup handler: {description}")


def cleanup_all_resources():
    """
    Execute all registered cleanup handlers.
    Called automatically on:
    - Normal exit
    - Ctrl+C (SIGINT)
    - Kill signal (SIGTERM)
    - Uncaught exceptions
    """
    global _shutdown_initiated
    
    if _shutdown_initiated:
        return  # Already cleaning up, avoid duplicate cleanup
    
    _shutdown_initiated = True
    
    logger.info("=" * 70)
    logger.info("Initiating cleanup of all resources...")
    logger.info("=" * 70)
    
    # Execute cleanup handlers in reverse order (LIFO)
    for handler, description in reversed(_cleanup_handlers):
        try:
            logger.info(f"Cleaning up: {description}")
            handler()
            logger.info(f"✓ {description} cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up {description}: {e}")
    
    # Force garbage collection
    logger.info("Running garbage collection...")
    collected = gc.collect()
    logger.info(f"✓ Garbage collection complete: {collected} objects collected")
    
    logger.info("=" * 70)
    logger.info("Cleanup complete")
    logger.info("=" * 70)


def signal_handler(signum, frame):
    """Handle signals (SIGINT, SIGTERM) for graceful shutdown"""
    signal_name = signal.Signals(signum).name
    logger.warning(f"\nReceived {signal_name} signal. Initiating graceful shutdown...")
    cleanup_all_resources()
    sys.exit(0)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Kill signal
    logger.info("Signal handlers registered for graceful shutdown")


def setup_atexit_handler():
    """Setup atexit handler for cleanup on normal exit"""
    atexit.register(cleanup_all_resources)
    logger.info("Atexit handler registered for resource cleanup")


class ResourceManager:
    """
    Context manager for automatic resource cleanup.
    Ensures cleanup happens even on exceptions.
    """
    
    def __init__(self, name: str = "ResourceManager"):
        self.name = name
        self.resources: List[Any] = []
        self.cleanup_functions: List[tuple] = []
    
    def __enter__(self):
        logger.debug(f"{self.name}: Entered context")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources on context exit (even on exceptions)"""
        if exc_type is not None:
            logger.error(f"{self.name}: Exiting due to exception: {exc_type.__name__}: {exc_val}")
        else:
            logger.debug(f"{self.name}: Normal exit")
        
        # Execute cleanup functions
        for cleanup_func, description in reversed(self.cleanup_functions):
            try:
                logger.debug(f"{self.name}: Cleaning up {description}")
                cleanup_func()
            except Exception as e:
                logger.error(f"{self.name}: Error during cleanup of {description}: {e}")
        
        # Clear resources list
        self.resources.clear()
        self.cleanup_functions.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Don't suppress exceptions
        return False
    
    def add_resource(self, resource: Any, cleanup_func, description: str):
        """Add a resource with its cleanup function"""
        self.resources.append(resource)
        self.cleanup_functions.append((cleanup_func, description))
        logger.debug(f"{self.name}: Added resource: {description}")
    
    def add_cleanup(self, cleanup_func, description: str):
        """Add a cleanup function without a resource object"""
        self.cleanup_functions.append((cleanup_func, description))
        logger.debug(f"{self.name}: Added cleanup function: {description}")


class WeaviateConnectionManager:
    """Context manager specifically for Weaviate connections"""
    
    def __init__(self, client):
        self.client = client
    
    def __enter__(self):
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close Weaviate connection on exit"""
        if self.client:
            try:
                logger.info("Closing Weaviate connection...")
                self.client.close()
                logger.info("✓ Weaviate connection closed")
            except Exception as e:
                logger.error(f"Error closing Weaviate connection: {e}")
        
        # Force cleanup
        self.client = None
        gc.collect()
        
        return False


class OpenAIClientManager:
    """Context manager specifically for OpenAI clients"""
    
    def __init__(self, client):
        self.client = client
    
    def __enter__(self):
        return self.client
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync exit - for sync clients"""
        if self.client:
            try:
                logger.info("Closing OpenAI client...")
                # Sync client doesn't have close method typically
                logger.info("✓ OpenAI client cleanup complete")
            except Exception as e:
                logger.error(f"Error closing OpenAI client: {e}")
        
        self.client = None
        gc.collect()
        return False
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit - for async clients"""
        if self.client:
            try:
                logger.info("Closing async OpenAI client...")
                await self.client.close()
                logger.info("✓ Async OpenAI client closed")
            except Exception as e:
                logger.error(f"Error closing async OpenAI client: {e}")
        
        self.client = None
        gc.collect()
        return False


def force_cleanup():
    """
    Force cleanup of all resources and garbage collection.
    Use this in emergency situations or after errors.
    """
    logger.warning("Forcing cleanup of all resources...")
    
    # Run all cleanup handlers
    cleanup_all_resources()
    
    # Aggressive garbage collection
    logger.info("Running aggressive garbage collection...")
    for i in range(3):
        collected = gc.collect(generation=2)  # Full collection
        logger.info(f"  GC pass {i+1}: {collected} objects collected")
    
    logger.info("✓ Force cleanup complete")

