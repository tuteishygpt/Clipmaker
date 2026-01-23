"""Billing dependencies for generation endpoints.

This module provides FastAPI dependencies that enforce billing entitlements
on the backend, preventing bypass of credit checks.
"""
from __future__ import annotations

from typing import Optional
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status

from .auth import AuthenticatedUser, require_auth, get_optional_user
from ..services.billing_service import billing_service
from ..clients.supabase_client import is_supabase_configured
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class BillingContext:
    """Billing context for a generation request."""
    user: Optional[AuthenticatedUser]
    credits: int
    can_generate: bool
    block_reason: Optional[str]
    bypass_billing: bool  # True when Supabase is not configured
    
    def require_credits(self, amount: int = 1) -> None:
        """Raise HTTPException if insufficient credits."""
        if self.bypass_billing:
            return
        
        if not self.can_generate:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=self.block_reason or "Cannot generate: billing issue"
            )
        
        if self.credits < amount:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits: need {amount}, have {self.credits}"
            )


async def get_billing_context(
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
) -> BillingContext:
    """
    Get billing context for the current request.
    Returns context that allows generation if Supabase is not configured (dev mode).
    """
    # If Supabase is not configured, bypass billing (local dev mode)
    if not is_supabase_configured():
        return BillingContext(
            user=None,
            credits=999999,  # Unlimited in dev mode
            can_generate=True,
            block_reason=None,
            bypass_billing=True
        )
    
    # If user is not authenticated
    if not user:
        return BillingContext(
            user=None,
            credits=0,
            can_generate=False,
            block_reason="Authentication required for generation",
            bypass_billing=False
        )
    
    # Get billing status from service
    try:
        subscription_status = await billing_service.get_subscription_status(user.id)
        credits = await billing_service.get_credit_balance(user.id)
        
        return BillingContext(
            user=user,
            credits=credits,
            can_generate=subscription_status.can_generate,
            block_reason=subscription_status.block_reason,
            bypass_billing=False
        )
    except Exception as e:
        logger.error(f"Failed to get billing context for {user.id}: {e}")
        return BillingContext(
            user=user,
            credits=0,
            can_generate=False,
            block_reason="Failed to verify billing status",
            bypass_billing=False
        )


async def require_generation_credits(
    amount: int = 1
):
    """
    Factory for a dependency that requires a specific credit amount.
    Usage: Depends(require_generation_credits(5))
    """
    async def _dependency(
        billing: BillingContext = Depends(get_billing_context)
    ) -> BillingContext:
        billing.require_credits(amount)
        return billing
    
    return _dependency


async def require_can_generate(
    billing: BillingContext = Depends(get_billing_context)
) -> BillingContext:
    """
    Dependency that requires the user can generate (has subscription + credits).
    Use this on generation endpoints.
    """
    billing.require_credits(1)
    return billing


async def deduct_generation_credits(
    billing: BillingContext,
    amount: int = 1,
    description: str = "Image generation",
    reference_id: Optional[str] = None
) -> Optional[str]:
    """
    Deduct credits for a generation.
    Returns the transaction ID, or None if billing is bypassed.
    """
    if billing.bypass_billing or not billing.user:
        return None
    
    result = await billing_service.deduct_credits(
        user_id=billing.user.id,
        amount=amount,
        description=description,
        reference_id=reference_id
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=result.error or "Failed to deduct credits"
        )
    
    return result.transaction_id


async def refund_generation_credits(
    billing: BillingContext,
    amount: int,
    transaction_id: str,
    reason: str = "Generation failed - refund"
) -> bool:
    """
    Refund credits for a failed generation.
    Returns True if successful, False otherwise.
    """
    if billing.bypass_billing or not billing.user or not transaction_id:
        return True
    
    result = await billing_service.refund_credits(
        user_id=billing.user.id,
        amount=amount,
        original_transaction_id=transaction_id,
        reason=reason
    )
    
    if not result.success:
        logger.error(f"Failed to refund {amount} credits: {result.error}")
        return False
    
    return True
