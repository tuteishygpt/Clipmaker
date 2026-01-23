"""User Cabinet API routes."""
from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Body

from ..core.auth import AuthenticatedUser, require_auth
from ..services.billing_service import billing_service
from ..clients.supabase_client import get_supabase
from ..schemas.cabinet import (
    AccountStatus,
    CreditBalance,
    TransactionHistory,
    SubscriptionStatus,
    CreditAddRequest,
    CreditDeductResponse,
    ProfileUpdate,
    UserProfile
)
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cabinet", tags=["cabinet"])


@router.get("/status", response_model=AccountStatus)
async def get_account_status(
    user: AuthenticatedUser = Depends(require_auth)
) -> AccountStatus:
    """Get complete account status for dashboard."""
    # Get billing status
    subscription_status = await billing_service.get_subscription_status(user.id)
    credits = await billing_service.get_credit_balance(user.id)
    
    # Get profile
    supabase = get_supabase()
    profile_data = None
    if supabase:
        resp = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        if resp.data:
            profile_data = UserProfile(**resp.data)
    
    return AccountStatus(
        user_id=user.id,
        email=user.email,
        profile=profile_data,
        credits=credits,
        subscription=subscription_status,
        can_generate=subscription_status.can_generate,
        generation_block_reason=subscription_status.block_reason
    )


@router.get("/credits", response_model=CreditBalance)
async def get_credits(
    user: AuthenticatedUser = Depends(require_auth)
) -> CreditBalance:
    """Get current credit balance."""
    balance = await billing_service.get_credit_balance(user.id)
    return CreditBalance(user_id=user.id, balance=balance)


@router.get("/transactions", response_model=List[dict])
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    user: AuthenticatedUser = Depends(require_auth)
) -> List[dict]:
    """Get transaction history."""
    return await billing_service.get_transaction_history(user.id, limit, offset)


@router.get("/subscription", response_model=SubscriptionStatus)
async def get_subscription(
    user: AuthenticatedUser = Depends(require_auth)
) -> SubscriptionStatus:
    """Get current subscription status."""
    return await billing_service.get_subscription_status(user.id)


@router.post("/profile", response_model=UserProfile)
async def update_profile(
    update: ProfileUpdate,
    user: AuthenticatedUser = Depends(require_auth)
) -> UserProfile:
    """Update user profile."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    # Filter out None values
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if not update_data:
        # Return existing profile if no updates
        resp = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        return UserProfile(**resp.data)
    
    update_data["updated_at"] = "now()"
    
    try:
        resp = supabase.table("profiles") \
            .update(update_data) \
            .eq("id", user.id) \
            .select() \
            .single() \
            .execute()
        
        return UserProfile(**resp.data)
    except Exception as e:
        logger.error(f"Failed to update profile for {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/projects", response_model=List[dict])
async def get_projects(
    user: AuthenticatedUser = Depends(require_auth)
) -> List[dict]:
    """Get user's projects."""
    return await billing_service.get_user_projects(user.id)


# ==================== Dev/Simulated Endpoints ====================

@router.post("/credits/purchase_simulated", response_model=CreditDeductResponse)
async def simulate_purchase(
    request: CreditAddRequest,
    user: AuthenticatedUser = Depends(require_auth)
) -> CreditDeductResponse:
    """
    Simulate a credit purchase (Dev only).
    In production, this would be a webhook from Stripe.
    """
    # Verify allowed amount or permissions here if needed
    
    return await billing_service.add_credits(
        user_id=user.id,
        amount=request.amount,
        description=request.description or "Simulated purchase",
        transaction_type="credit_purchase"
    )

