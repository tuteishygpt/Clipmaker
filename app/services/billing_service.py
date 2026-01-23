"""Billing service for credits and subscription management."""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ..clients.supabase_client import get_supabase, is_supabase_configured
from ..core.logging import get_logger
from ..schemas.cabinet import (
    CreditBalance,
    CreditDeductResponse,
    Transaction,
    Subscription,
    SubscriptionStatus,
)

logger = get_logger(__name__)

# Subscription plans configuration (should match frontend)
SUBSCRIPTION_PLANS = {
    "free": {
        "id": "free",
        "name": "Free",
        "price": 0,
        "credits_per_month": 100,
        "features": ["100 credits/month", "Standard quality", "Community support"],
        "can_generate": True
    },
    "starter": {
        "id": "starter",
        "name": "Starter",
        "price": 9.99,
        "credits_per_month": 1000,
        "features": ["1000 credits/month", "HD quality", "Email support", "Priority queue"],
        "can_generate": True
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price": 29.99,
        "credits_per_month": 5000,
        "features": ["5000 credits  /month", "4K quality", "Priority support", "API access", "Custom styles"],
        "can_generate": True
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise",
        "price": 99.99,
        "credits_per_month": 20000,
        "features": ["20000 credits/month", "4K+ quality", "Dedicated support", "White label", "Custom integrations"],
        "can_generate": True
    }
}


class BillingService:
    """Service for managing user credits and subscriptions."""
    
    @property
    def is_configured(self) -> bool:
        """Check if billing is configured."""
        return is_supabase_configured()
    
    def _ensure_supabase(self):
        """Ensure Supabase is available."""
        client = get_supabase()
        if not client:
            raise RuntimeError("Supabase is not configured")
        return client
    
    # ==================== Credits ====================
    
    async def get_credit_balance(self, user_id: str) -> int:
        """Get user's current credit balance."""
        if not self.is_configured:
            return 999999
            
        supabase = self._ensure_supabase()
        
        try:
            response = supabase.table("user_credits") \
                .select("balance") \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            
            if response.data:
                return response.data.get("balance", 0)
            return 0
        except Exception as e:
            logger.error(f"Failed to get credit balance for {user_id}: {e}")
            return 0
    
    async def deduct_credits(
        self,
        user_id: str,
        amount: int = 1,
        description: str = "Image generation",
        reference_id: Optional[str] = None
    ) -> CreditDeductResponse:
        """
        Deduct credits atomically using database function.
        Returns success status with transaction details.
        """
        supabase = self._ensure_supabase()
        
        try:
            # Call the atomic deduct_credits function
            response = supabase.rpc("deduct_credits", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_description": description,
                "p_transaction_type": "generation_deduct",
                "p_reference_id": reference_id
            }).execute()
            
            result = response.data
            
            if not result:
                return CreditDeductResponse(
                    success=False,
                    error="No response from server"
                )
            
            if result.get("success"):
                return CreditDeductResponse(
                    success=True,
                    transaction_id=result.get("transaction_id"),
                    previous_balance=result.get("previous_balance"),
                    new_balance=result.get("new_balance")
                )
            else:
                return CreditDeductResponse(
                    success=False,
                    error=result.get("error", "Unknown error")
                )
                
        except Exception as e:
            logger.error(f"Credit deduction failed for {user_id}: {e}")
            return CreditDeductResponse(
                success=False,
                error=str(e)
            )
    
    async def add_credits(
        self,
        user_id: str,
        amount: int,
        description: str,
        transaction_type: str = "credit_purchase",
        reference_id: Optional[str] = None
    ) -> CreditDeductResponse:
        """
        Add credits atomically (for purchases, refunds, bonuses).
        """
        supabase = self._ensure_supabase()
        
        try:
            response = supabase.rpc("add_credits", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_description": description,
                "p_transaction_type": transaction_type,
                "p_reference_id": reference_id
            }).execute()
            
            result = response.data
            
            if result and result.get("success"):
                return CreditDeductResponse(
                    success=True,
                    transaction_id=result.get("transaction_id"),
                    previous_balance=result.get("previous_balance"),
                    new_balance=result.get("new_balance")
                )
            else:
                return CreditDeductResponse(
                    success=False,
                    error=result.get("error", "Unknown error") if result else "No response"
                )
                
        except Exception as e:
            logger.error(f"Credit addition failed for {user_id}: {e}")
            return CreditDeductResponse(
                success=False,
                error=str(e)
            )
    
    async def refund_credits(
        self,
        user_id: str,
        amount: int,
        original_transaction_id: str,
        reason: str = "Generation failed - refund"
    ) -> CreditDeductResponse:
        """Refund credits for a failed operation."""
        return await self.add_credits(
            user_id=user_id,
            amount=amount,
            description=reason,
            transaction_type="refund",
            reference_id=original_transaction_id
        )
    
    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's transaction history."""
        if not self.is_configured:
            return []
            
        supabase = self._ensure_supabase()
        
        try:
            response = supabase.table("credit_transactions") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()
            
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get transactions for {user_id}: {e}")
            return []
            
    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's projects with metadata."""
        if not self.is_configured:
            return []

        supabase = self._ensure_supabase()

        try:
            response = supabase.table("user_projects") \
                .select("*, generation_history(count)") \
                .eq("user_id", user_id) \
                .order("updated_at", desc=True) \
                .execute()
            
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get projects for {user_id}: {e}")
            return []

    async def link_user_project(self, user_id: str, project_id: str, title: str, settings: dict = {}) -> bool:
        """Link a project to a user."""
        if not self.is_configured:
            return True

        supabase = self._ensure_supabase()

        try:
            supabase.table("user_projects").insert({
                "user_id": user_id,
                "project_id": project_id,
                "title": title,
                "settings": settings,
                "status": "draft"
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to link project {project_id} to {user_id}: {e}")
            return False
    
    # ==================== Subscriptions ====================
    
    async def get_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's active subscription."""
        supabase = self._ensure_supabase()
        
        try:
            response = supabase.table("subscriptions") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("status", "active") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get subscription for {user_id}: {e}")
            return None
    
    async def get_subscription_status(self, user_id: str) -> SubscriptionStatus:
        """Get detailed subscription status with generation eligibility."""
        if not self.is_configured:
            return SubscriptionStatus(
                has_subscription=True,
                plan_id="pro",
                plan_name="Pro (Dev Mode)",
                status="active",
                credits_per_month=5000,
                can_generate=True,
                block_reason=None
            )

        subscription = await self.get_subscription(user_id)
        credits = await self.get_credit_balance(user_id)
        
        if not subscription:
            return SubscriptionStatus(
                has_subscription=False,
                can_generate=False,
                block_reason="No active subscription. Please subscribe to start generating."
            )
        
        plan_id = subscription.get("plan_id", "free")
        plan = SUBSCRIPTION_PLANS.get(plan_id, SUBSCRIPTION_PLANS["free"])
        
        # Check subscription status
        status = subscription.get("status", "inactive")
        if status != "active":
            return SubscriptionStatus(
                has_subscription=True,
                plan_id=plan_id,
                plan_name=plan["name"],
                status=status,
                credits_per_month=plan["credits_per_month"],
                can_generate=False,
                block_reason="Your subscription is not active. Please renew to continue."
            )
        
        # Check renewal date
        period_end_str = subscription.get("current_period_end")
        renewal_date = None
        days_until = None
        
        if period_end_str:
            try:
                if isinstance(period_end_str, str):
                    renewal_date = datetime.fromisoformat(period_end_str.replace("Z", "+00:00"))
                else:
                    renewal_date = period_end_str
                
                now = datetime.now(timezone.utc)
                days_until = (renewal_date - now).days
                
                if renewal_date < now:
                    return SubscriptionStatus(
                        has_subscription=True,
                        plan_id=plan_id,
                        plan_name=plan["name"],
                        status="expired",
                        credits_per_month=plan["credits_per_month"],
                        renewal_date=renewal_date,
                        days_until_renewal=0,
                        can_generate=False,
                        block_reason="Your subscription period has ended. Please renew to continue."
                    )
            except Exception as e:
                logger.warning(f"Failed to parse renewal date: {e}")
        
        # Check credits
        if credits <= 0:
            return SubscriptionStatus(
                has_subscription=True,
                plan_id=plan_id,
                plan_name=plan["name"],
                status=status,
                credits_per_month=plan["credits_per_month"],
                renewal_date=renewal_date,
                days_until_renewal=days_until,
                can_generate=False,
                block_reason="Insufficient credits. Please purchase more credits to continue."
            )
        
        # All checks passed
        return SubscriptionStatus(
            has_subscription=True,
            plan_id=plan_id,
            plan_name=plan["name"],
            status=status,
            credits_per_month=plan["credits_per_month"],
            renewal_date=renewal_date,
            days_until_renewal=days_until,
            can_generate=True,
            block_reason=None
        )
    
    async def check_can_generate(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Quick check if user can generate.
        Returns (can_generate, block_reason).
        """
        status = await self.get_subscription_status(user_id)
        return status.can_generate, status.block_reason


# Global service instance
billing_service = BillingService()
