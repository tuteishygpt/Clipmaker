import jwt
import os
import base64

# Values from .env and frontend-react/.env

SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxY2R4bG56cmZ4cW1mdHNlbWVrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTE4MzM4NCwiZXhwIjoyMDg0NzU5Mzg0fQ.8Rz7HVlFimiJSBKchfvD9P_Ddo11KMn1d37cbEYNIKo"
VITE_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxY2R4bG56cmZ4cW1mdHNlbWVrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxODMzODQsImV4cCI6MjA4NDc1OTM4NH0.ecn8NmvsE9mIYbhTmhs2sX8K5mmQTnjbmL8jY5kiddE"

SUPABASE_JWT_SECRET_RAW = "1L/jbUD/sm+WSFpBi+vdDtCsZd7h5/asTtbIyLhbuN/xQwqWjuPc9kozyssSKaIWQATH6dL4XnsUTZw8vXx2Xg=="

print(f"Testing with Secret Raw: {SUPABASE_JWT_SECRET_RAW[:10]}...")

def test_key(name, token, secret, is_base64=False):
    try:
        if is_base64:
            secret = base64.b64decode(secret)
        
        jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
        print(f"SUCCESS: {name} verified with {'BASE64' if is_base64 else 'RAW'} secret.")
        return True
    except Exception as e:
        print(f"FAIL: {name} verification failed ({'BASE64' if is_base64 else 'RAW'}): {e}")
        return False

# Test Service Role Key
test_key("Service Role (Raw)", SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET_RAW, False)
test_key("Service Role (B64)", SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET_RAW, True)

# Test Anon Key
test_key("Anon Key (Raw)", VITE_SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET_RAW, False)
test_key("Anon Key (B64)", VITE_SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET_RAW, True)
