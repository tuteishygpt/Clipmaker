# User Cabinet Module - Setup Guide

## Overview

The User Cabinet is a complete user account system for the Clipmaker application, featuring:

- **Authentication**: Email/password and OAuth (Google, GitHub) via Supabase Auth.
- **Mock Mode**: Fully functional "Dev Mode" for local development without Supabase.
- **User Profile**: Personal information and settings management with Supabase.
- **Credits System**: Atomic balance tracking with transaction history.
- **Subscription Management**: Plan selection and billing logic.

## 🚀 Dev Mode (Local Testing)

The application is designed to be fully functional immediately, even without a Supabase project:

1.  **Mock Authentication**: If `SUPABASE_URL` is missing from `.env`, internal routes will automatically provide a **Mock User** ("Developer Proxy").
2.  **Infinite Credits**: In Dev Mode, `BillingService` provides a balance of **999,999** credits.
3.  **Pro Subscription**: Users automatically get a **Pro (Dev Mode)** status, allowing all generation features.

To enable full production features, follow the setup below.

## Setup Instructions

### 1. Install Dependencies

Ensure you have the required Supabase client library:

```bash
pip install supabase
# or
pip install -r requirements.txt
```

### 2. Create a Supabase Project

1.  Go to [supabase.com](https://supabase.com) and create a new project.
2.  Navigate to **Project Settings** → **API**.
3.  Copy the `URL` and the `service_role` secret key.

### 3. Configure Environment Variables

Update your `.env` file in the project root:

```env
# Supabase Configuration
SUPABASE_URL=https://aqcdxlnzrfxqmftsemek.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-from-settings
```

*Note: The backend uses the `service_role` key to bypass RLS for administrative tasks like credit deduction.*

### 4. Set Up Database Schema

1.  Go to your Supabase dashboard → **SQL Editor**.
2.  Create a "New Query" and paste the contents of `supabase_schema.sql` (located in the project root).
3.  Run the query. This creates:
    *   `profiles`, `user_credits`, `subscriptions`, etc.
    *   Atomic RPC functions: `deduct_credits()` and `add_credits()`.

## Credit System

### How It Works

1.  **Lazy Initialization**: The Supabase client in the backend is initialized only when needed. If the connection fails or isn't configured, it gracefully falls back to Dev Mode.
2.  **Atomic Operations**: Credits are deducted via a database-side function (`RPC`) which uses row locking. This prevents "double-spending" even if multiple requests arrive simultaneously.
3.  **Refund Logic**: If the AI generation pipeline fails, the system automatically triggers a refund to the user's balance.

### Transaction Types

- `credit_purchase`: Manual or Stripe purchases.
- `subscription_credit`: Monthly recurrent credits.
- `generation_deduct`: Subtracted for creating images/videos.
- `refund`: Returned after a failed generation.

## Troubleshooting

### `ModuleNotFoundError: No module named 'supabase'`
This occurs if the Supabase SDK is not installed in your active environment. 
**Fix:**
```bash
pip install supabase==2.10.0
```
If you are using a virtual environment, ensure it is activated before running the server.

### "Authentication service not configured"
This means you are accessing a protected route but `SUPABASE_URL` is not set. Wait for the "Mock User" fallback or check your `.env`.

### Credits not deducting in Production
1.  Check that the `service_role` key is used, not the `anon` key in the backend.
2.  Verify the `deduct_credits` function was created in the SQL Editor.
3.  Check the `logs/app.log` for database error messages.

## UX Design Principles

1.  **Transparency**: Always show credit balance in the header.
2.  **Resilience**: Allow viewing and editing projects even if billing is down.
3.  **Clarity**: Provide human-readable reasons (e.g., "Insufficient credits") instead of raw error codes.
