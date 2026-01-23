"""Supabase client initialization for backend operations."""
from __future__ import annotations

from typing import Optional
from supabase import create_client, Client

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# Global Supabase client (using service role key for backend)
_supabase_client: Client | None = None


def get_supabase() -> Client | None:
    """Get or create Supabase client instance."""
    global _supabase_client
    
    if not settings.supabase_configured:
        return None
    
    if _supabase_client is None:
        try:
            _supabase_client = create_client(
                settings.supabase_url, # type: ignore
                settings.supabase_key # type: ignore
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None
    
    return _supabase_client


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured."""
    return settings.supabase_configured
