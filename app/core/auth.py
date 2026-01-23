"""Authentication dependencies for FastAPI routes."""
from __future__ import annotations

from typing import Optional, Any
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.config import settings
from ..core.logging import get_logger
from ..clients.supabase_client import get_supabase, is_supabase_configured

logger = get_logger(__name__)

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    """Authenticated user data extracted from JWT."""
    id: str
    email: str
    role: str = "authenticated"
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def verify_jwt(token: str) -> Optional[dict]:
    """Verify and decode a Supabase JWT token supporting both HS256 and ES256."""
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
    except Exception as e:
        logger.warning(f"Failed to parse JWT header: {e}")
        return None

    # Determine which key to use and whether we can verify
    key = None
    if alg == "ES256":
        key = settings.supabase_jwt_public_key
    else:
        key = settings.supabase_jwt_secret
        
    # Debug logging
    if not key:
        logger.error("No JWT Secret configured!")
    else:
        # Log first 5 chars to verify it's loaded
        pass 
        # logger.info(f"Verifying with key prefix: {key[:5]}...")

    # If no key configured for the detected algorithm, try unverified (Dev Mode fallback)
    if not key:
        logger.warning(f"No key configured for algorithm {alg}, attempting unverified decode")
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None
    
    try:
        # Decode and verify
        # NOTE: We allow audience mismatch for now to debug, or handle via options
        payload = jwt.decode(
            token,
            key,
            algorithms=[alg],
            leeway=60, # Allow 60 seconds of clock skew
            # Allow any audience or specific one. 
            # If tokens don't have 'aud', we must NOT require it.
            # We set verify_aud=False to test signature FIRST.
            options={"verify_aud": False} 
        )
        
        # Manual Audience Check (optional)
        # aud = payload.get("aud")
        # if aud and aud != "authenticated":
        #    logger.warning(f"Audience mismatch: {aud}")
            
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except Exception as e:
        logger.error(f"JWT Verification Failed. Key: {key[:10]}... Alg: {alg} Error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[AuthenticatedUser]:
    """
    Extract and validate user from JWT token.
    Returns None if no token provided (for optional auth).
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = verify_jwt(token)
    
    if not payload:
        return None
    
    # Extract user info from Supabase JWT
    user_id = payload.get("sub")
    email = payload.get("email", "")
    role = payload.get("role", "authenticated")
    user_metadata = payload.get("user_metadata", {})
    
    if not user_id:
        return None
    
    return AuthenticatedUser(
        id=user_id,
        email=email,
        role=role,
        metadata=user_metadata
    )


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthenticatedUser:
    """
    Require authenticated user. Raises 401 if not authenticated.
    In dev mode (Supabase not configured), returns a mock user.
    """
    if not is_supabase_configured():
        logger.info("Supabase not configured, providing mock user for auth")
        return AuthenticatedUser(
            id="dev_user_123",
            email="dev@example.com",
            role="authenticated",
            metadata={"full_name": "Developer Proxy"}
        )
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = await get_current_user(credentials)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[AuthenticatedUser]:
    """
    Get user if authenticated, None otherwise.
    Use this for routes that work with or without auth.
    """
    if not is_supabase_configured():
        return None
    
    return await get_current_user(credentials)
