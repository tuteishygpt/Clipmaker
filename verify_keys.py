import jwt
import sys
import base64

# Configuration from your files
SUPABASE_JWT_SECRET = "1L/jbUD/sm+WSFpBi+vdDtCsZd7h5/asTtbIyLhbuN/xQwqWjuPc9kozyssSKaIWQATH6dL4XnsUTZw8vXx2Xg=="
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxY2R4bG56cmZ4cW1mdHNlbWVrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTE4MzM4NCwiZXhwIjoyMDg0NzU5Mzg0fQ.8Rz7HVlFimiJSBKchfvD9P_Ddo11KMn1d37cbEYNIKo"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxY2R4bG56cmZ4cW1mdHNlbWVrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTE4MzM4NCwiZXhwIjoyMDg0NzU5Mzg0fQ.ecn8NmvsE9mIYbhTmhs2sX8K5mmQTnjbmL8jY5kiddE"

def analyze_token(name, token, secret):
    print(f"\n--- Analyzing {name} ---")
    try:
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
        print(f"Audience found: '{payload.get('aud')}'")
    except Exception as e:
        print(f"Error decoding: {e}")
        return

    # Try validating with Strict Audience Check
    try:
        jwt.decode(token, secret, algorithms=[header.get('alg', 'HS256')], audience="authenticated")
        print("✅ SUCCESS: Signature Verified AND Audience is 'authenticated'")
    except jwt.InvalidAudienceError:
        print(f"❌ FAILED: Audience mismatch. Expected 'authenticated', got '{payload.get('aud')}'")
    except jwt.InvalidSignatureError:
        print("❌ FAILED: Signature mismatch (Raw Secret)")
    except Exception as e:
        print(f"❌ ERROR: {e}")

print("=== JWT AUDIENCE CHECK ===")
analyze_token("SERVICE_ROLE_KEY", SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET)
analyze_token("ANON_KEY", ANON_KEY, SUPABASE_JWT_SECRET)
