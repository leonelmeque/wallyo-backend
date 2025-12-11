"""Supabase client initialization with service role key."""

from typing import Optional
from supabase import create_client, Client
from app.core.config import get_settings

# Lazy-initialized Supabase client
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create the Supabase client with service role key.

    This client is used for server-side operations that require elevated privileges.
    The client is lazily initialized to avoid import-time errors.

    Returns:
        Supabase Client instance
    """
    global _supabase_client
    if _supabase_client is None:
        s = get_settings()
        _supabase_client = create_client(
            s.supabase_url, s.supabase_service_role_key
        )
    return _supabase_client


# For backward compatibility, provide module-level access
# Accessing this will lazily initialize the client
def _get_supabase() -> Client:
    """Get Supabase client (internal function)."""
    return get_supabase_client()


# Create a module-level attribute that lazily initializes
class _LazySupabase:
    """Lazy wrapper for Supabase client."""

    def __getattr__(self, name: str) -> any:
        """Delegate attribute access to the actual Supabase client."""
        return getattr(get_supabase_client(), name)


# Module-level supabase object that lazily initializes
supabase = _LazySupabase()
