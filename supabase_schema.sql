-- =====================================================
-- Clipmaker User Cabinet - Supabase Database Schema
-- =====================================================
-- Run this in your Supabase SQL Editor to set up the 
-- required tables and functions for the User Cabinet.
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- PROFILES TABLE
-- Extends Supabase auth.users with additional profile data
-- =====================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    full_name TEXT,
    avatar_url TEXT,
    company TEXT,
    website TEXT,
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Policies for profiles
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Trigger to create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, avatar_url)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url'
    );
    
    -- Also create initial credits record
    INSERT INTO public.user_credits (user_id, balance)
    VALUES (NEW.id, 10);  -- 10 free credits for new users
    
    -- Create initial free subscription
    INSERT INTO public.subscriptions (
        user_id, 
        plan_id, 
        status, 
        current_period_start, 
        current_period_end
    )
    VALUES (
        NEW.id, 
        'free', 
        'active', 
        now(), 
        now() + INTERVAL '100 years'
    );
    
    -- Log the welcome bonus transaction
    INSERT INTO public.credit_transactions (
        user_id, 
        amount, 
        type, 
        description, 
        balance_after
    )
    VALUES (
        NEW.id, 
        10, 
        'bonus', 
        'Welcome bonus - 10 free credits', 
        10
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- USER CREDITS TABLE
-- Stores current credit balance for each user
-- =====================================================
CREATE TABLE IF NOT EXISTS public.user_credits (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    balance INTEGER DEFAULT 0 NOT NULL CHECK (balance >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.user_credits ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own credits" ON public.user_credits
    FOR SELECT USING (auth.uid() = user_id);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON public.user_credits(user_id);

-- =====================================================
-- CREDIT TRANSACTIONS TABLE
-- Immutable audit log of all credit changes
-- =====================================================
CREATE TABLE IF NOT EXISTS public.credit_transactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    amount INTEGER NOT NULL,  -- Positive for credits added, negative for deducted
    type TEXT NOT NULL CHECK (type IN (
        'credit_purchase', 
        'subscription_credit', 
        'generation_deduct', 
        'refund', 
        'bonus', 
        'adjustment'
    )),
    description TEXT NOT NULL,
    balance_after INTEGER NOT NULL,  -- Balance after this transaction
    reference_id TEXT,  -- External reference (e.g., Stripe charge ID, project ID)
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own transactions" ON public.credit_transactions
    FOR SELECT USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON public.credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON public.credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON public.credit_transactions(type);

-- =====================================================
-- SUBSCRIPTIONS TABLE
-- Stores active subscriptions for users
-- =====================================================
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    plan_id TEXT NOT NULL CHECK (plan_id IN ('free', 'starter', 'pro', 'enterprise')),
    status TEXT NOT NULL CHECK (status IN ('active', 'canceled', 'past_due', 'expired')),
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT false,
    stripe_subscription_id TEXT,  -- External subscription ID from payment provider
    stripe_customer_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own subscriptions" ON public.subscriptions
    FOR SELECT USING (auth.uid() = user_id);

-- Index
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON public.subscriptions(status);

-- =====================================================
-- USER PROJECTS TABLE
-- Links Clipmaker projects to users with metadata
-- =====================================================
CREATE TABLE IF NOT EXISTS public.user_projects (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    project_id TEXT NOT NULL,  -- The local project ID from Clipmaker
    title TEXT NOT NULL,
    thumbnail_url TEXT,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'processing', 'completed', 'error')),
    settings JSONB DEFAULT '{}'::jsonb,  -- Project settings (visual style, format, etc.)
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id, project_id)
);

-- Enable RLS
ALTER TABLE public.user_projects ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own projects" ON public.user_projects
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own projects" ON public.user_projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own projects" ON public.user_projects
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own projects" ON public.user_projects
    FOR DELETE USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_projects_user_id ON public.user_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_updated_at ON public.user_projects(updated_at DESC);

-- =====================================================
-- GENERATION HISTORY TABLE
-- Records each generation with credits used
-- =====================================================
CREATE TABLE IF NOT EXISTS public.generation_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    project_id UUID REFERENCES public.user_projects(id) ON DELETE SET NULL,
    transaction_id UUID REFERENCES public.credit_transactions(id) ON DELETE SET NULL,
    generation_type TEXT NOT NULL CHECK (generation_type IN ('image', 'video', 'analysis')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    credits_used INTEGER DEFAULT 1 NOT NULL,
    input_data JSONB DEFAULT '{}'::jsonb,  -- Prompts, settings, etc.
    output_url TEXT,  -- URL to the generated asset (external hosting)
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Enable RLS
ALTER TABLE public.generation_history ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own generations" ON public.generation_history
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own generations" ON public.generation_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_generation_history_user_id ON public.generation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_history_project_id ON public.generation_history(project_id);
CREATE INDEX IF NOT EXISTS idx_generation_history_created_at ON public.generation_history(created_at DESC);

-- =====================================================
-- ATOMIC CREDIT DEDUCTION FUNCTION
-- Ensures credits are deducted exactly once using 
-- database-level locking and transactions
-- =====================================================
CREATE OR REPLACE FUNCTION public.deduct_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_description TEXT,
    p_transaction_type TEXT DEFAULT 'generation_deduct',
    p_reference_id TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
    v_transaction_id UUID;
    v_subscription_status TEXT;
BEGIN
    -- Check subscription status first
    SELECT status INTO v_subscription_status
    FROM public.subscriptions
    WHERE user_id = p_user_id AND status = 'active'
    ORDER BY created_at DESC
    LIMIT 1;
    
    IF v_subscription_status IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'No active subscription'
        );
    END IF;

    -- Lock the user's credit row to prevent race conditions
    SELECT balance INTO v_current_balance
    FROM public.user_credits
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Check if user has enough credits
    IF v_current_balance IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'User credits not found'
        );
    END IF;
    
    IF v_current_balance < p_amount THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Insufficient credits',
            'current_balance', v_current_balance,
            'required', p_amount
        );
    END IF;
    
    -- Calculate new balance
    v_new_balance := v_current_balance - p_amount;
    
    -- Update balance
    UPDATE public.user_credits
    SET 
        balance = v_new_balance,
        updated_at = now()
    WHERE user_id = p_user_id;
    
    -- Create transaction record
    INSERT INTO public.credit_transactions (
        user_id,
        amount,
        type,
        description,
        balance_after,
        reference_id,
        metadata
    )
    VALUES (
        p_user_id,
        -p_amount,  -- Negative for deduction
        p_transaction_type,
        p_description,
        v_new_balance,
        p_reference_id,
        p_metadata
    )
    RETURNING id INTO v_transaction_id;
    
    -- Return success with details
    RETURN jsonb_build_object(
        'success', true,
        'transaction_id', v_transaction_id,
        'previous_balance', v_current_balance,
        'new_balance', v_new_balance,
        'amount_deducted', p_amount
    );
END;
$$;

-- =====================================================
-- ATOMIC CREDIT ADDITION FUNCTION
-- For purchases, refunds, and subscription credits
-- =====================================================
CREATE OR REPLACE FUNCTION public.add_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_description TEXT,
    p_transaction_type TEXT DEFAULT 'credit_purchase',
    p_reference_id TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
    v_transaction_id UUID;
BEGIN
    -- Lock the user's credit row
    SELECT balance INTO v_current_balance
    FROM public.user_credits
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Create credits record if doesn't exist
    IF v_current_balance IS NULL THEN
        INSERT INTO public.user_credits (user_id, balance)
        VALUES (p_user_id, 0)
        RETURNING balance INTO v_current_balance;
    END IF;
    
    -- Calculate new balance
    v_new_balance := v_current_balance + p_amount;
    
    -- Update balance
    UPDATE public.user_credits
    SET 
        balance = v_new_balance,
        updated_at = now()
    WHERE user_id = p_user_id;
    
    -- Create transaction record
    INSERT INTO public.credit_transactions (
        user_id,
        amount,
        type,
        description,
        balance_after,
        reference_id,
        metadata
    )
    VALUES (
        p_user_id,
        p_amount,  -- Positive for addition
        p_transaction_type,
        p_description,
        v_new_balance,
        p_reference_id,
        p_metadata
    )
    RETURNING id INTO v_transaction_id;
    
    -- Return success with details
    RETURN jsonb_build_object(
        'success', true,
        'transaction_id', v_transaction_id,
        'previous_balance', v_current_balance,
        'new_balance', v_new_balance,
        'amount_added', p_amount
    );
END;
$$;

-- =====================================================
-- GRANT PERMISSIONS
-- Allow authenticated users to call these functions
-- =====================================================
GRANT EXECUTE ON FUNCTION public.deduct_credits TO authenticated;
GRANT EXECUTE ON FUNCTION public.add_credits TO authenticated;

-- =====================================================
-- AUTOMATIC updated_at TRIGGER
-- Updates the updated_at column on relevant tables
-- =====================================================
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_credits_updated_at ON public.user_credits;
CREATE TRIGGER update_user_credits_updated_at
    BEFORE UPDATE ON public.user_credits
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON public.subscriptions;
CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_projects_updated_at ON public.user_projects;
CREATE TRIGGER update_user_projects_updated_at
    BEFORE UPDATE ON public.user_projects
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE 'Clipmaker User Cabinet schema created successfully!';
    RAISE NOTICE 'Tables created: profiles, user_credits, credit_transactions, subscriptions, user_projects, generation_history';
    RAISE NOTICE 'Functions created: deduct_credits, add_credits';
END $$;
