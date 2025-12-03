"""
Centralized OpenAI client creation.
All scripts use this module for consistent OpenAI operations.
"""

import logging
from openai import AsyncOpenAI, AsyncAzureOpenAI, OpenAI, AzureOpenAI

import config

logger = logging.getLogger(__name__)


def create_async_openai_client():
    """
    Create async OpenAI client (Azure or regular OpenAI).
    
    Returns:
        Tuple of (client, model_name)
    """
    if config.USE_AZURE_OPENAI:
        client = AsyncAzureOpenAI(
            api_key=config.AZURE_OPENAI_API_KEY,
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_version=config.AZURE_OPENAI_API_VERSION
        )
        model = config.AZURE_OPENAI_DEPLOYMENT_NAME
        logger.info(f"Using Azure OpenAI with deployment: {model}")
    else:
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        model = config.OPENAI_MODEL
        logger.info(f"Using OpenAI with model: {model}")
    
    return client, model


def create_sync_openai_client():
    """
    Create sync OpenAI client (Azure or regular OpenAI).
    Used for testing and verification.
    
    Returns:
        Tuple of (client, model_name)
    """
    if config.USE_AZURE_OPENAI:
        client = AzureOpenAI(
            api_key=config.AZURE_OPENAI_API_KEY,
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_version=config.AZURE_OPENAI_API_VERSION
        )
        model = config.AZURE_OPENAI_DEPLOYMENT_NAME
        logger.info(f"Using Azure OpenAI with deployment: {model}")
    else:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        model = config.OPENAI_MODEL
        logger.info(f"Using OpenAI with model: {model}")
    
    return client, model

