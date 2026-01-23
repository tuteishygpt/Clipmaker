"""Pydantic schemas for user cabinet operations."""
from __future__ import annotations

from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== Credits ====================

class CreditBalance(BaseModel):
    """User's current credit balance."""
    user_id: str
    balance: int
    updated_at: Optional[datetime] = None


class CreditDeductRequest(BaseModel):
    """Request to deduct credits."""
    amount: int = Field(default=1, ge=1, description="Amount of credits to deduct")
    description: str = Field(default="Image generation", description="Description of the deduction")
    reference_id: Optional[str] = Field(default=None, description="External reference (e.g., project ID)")


class CreditDeductResponse(BaseModel):
    """Response from credit deduction."""
    success: bool
    transaction_id: Optional[str] = None
    previous_balance: Optional[int] = None
    new_balance: Optional[int] = None
    error: Optional[str] = None


class CreditAddRequest(BaseModel):
    """Request to add credits (purchase, refund, bonus)."""
    amount: int = Field(ge=1, description="Amount of credits to add")
    description: str
    transaction_type: str = Field(default="credit_purchase", description="Type of credit addition")
    reference_id: Optional[str] = None


class Transaction(BaseModel):
    """Credit transaction record."""
    id: str
    user_id: str
    amount: int
    type: str
    description: str
    balance_after: int
    reference_id: Optional[str] = None
    created_at: datetime


class TransactionHistory(BaseModel):
    """List of transactions."""
    transactions: List[Transaction]
    total_count: int


# ==================== Subscriptions ====================

class SubscriptionPlan(BaseModel):
    """Subscription plan details."""
    id: str
    name: str
    price: float
    credits_per_month: int
    features: List[str]


class Subscription(BaseModel):
    """User subscription record."""
    id: str
    user_id: str
    plan_id: str
    status: str  # active, canceled, past_due, expired
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    stripe_subscription_id: Optional[str] = None


class SubscriptionStatus(BaseModel):
    """Current subscription status for a user."""
    has_subscription: bool
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    status: Optional[str] = None
    credits_per_month: int = 0
    renewal_date: Optional[datetime] = None
    days_until_renewal: Optional[int] = None
    can_generate: bool = False
    block_reason: Optional[str] = None


# ==================== User Profile ====================

class UserProfile(BaseModel):
    """User profile data."""
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProfileUpdate(BaseModel):
    """Update user profile request."""
    full_name: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None


# ==================== User Projects ====================

class UserProject(BaseModel):
    """User's project record (links to local Clipmaker project)."""
    id: str
    user_id: str
    project_id: str  # Local Clipmaker project ID
    title: str
    thumbnail_url: Optional[str] = None
    status: str = "draft"  # draft, processing, completed, error
    settings: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class UserProjectCreate(BaseModel):
    """Create a user project link."""
    project_id: str
    title: str
    settings: dict = Field(default_factory=dict)


class UserProjectUpdate(BaseModel):
    """Update a user project."""
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[dict] = None
    metadata: Optional[dict] = None


class UserProjectList(BaseModel):
    """List of user projects."""
    projects: List[UserProject]
    total_count: int


# ==================== Generation History ====================

class GenerationRecord(BaseModel):
    """Record of a generation."""
    id: str
    user_id: str
    project_id: Optional[str] = None
    transaction_id: Optional[str] = None
    generation_type: str  # image, video, analysis
    status: str  # pending, processing, completed, failed
    credits_used: int = 1
    input_data: dict = Field(default_factory=dict)
    output_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class GenerationStart(BaseModel):
    """Start a new generation (with credit check)."""
    project_id: str
    generation_type: str = "image"
    input_data: dict = Field(default_factory=dict)


class GenerationResult(BaseModel):
    """Result of starting a generation."""
    success: bool
    generation_id: Optional[str] = None
    transaction_id: Optional[str] = None
    credits_remaining: Optional[int] = None
    error: Optional[str] = None


# ==================== Account Status ====================

class AccountStatus(BaseModel):
    """Complete account status for dashboard."""
    user_id: str
    email: Optional[str] = None
    profile: Optional[UserProfile] = None
    credits: int = 0
    subscription: Optional[SubscriptionStatus] = None
    can_generate: bool = False
    generation_block_reason: Optional[str] = None
    total_generations: int = 0
    projects_count: int = 0
