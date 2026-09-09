import os
import sys
import json
import socket
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

env_path = Path("/home/ubuntu/Clipmaker/.env")
load_dotenv(dotenv_path=env_path)

supabase_url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxY2R4bG56cmZ4cW1mdHNlbWVrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxODMzODQsImV4cCI6MjA4NDc1OTM4NH0.ecn8NmvsE9mIYbhTmhs2sX8K5mmQTnjbmL8jY5kiddE"

print("==========================================")
print("     DETAILED SUPABASE CONNECTIVITY       ")
print("==========================================")

print(f"1. Configuration Check:")
print(f"   - Supabase URL: {supabase_url}")
print(f"   - Service Role Key: {service_key[:25]}... (length: {len(service_key)})")
print(f"   - Anon Key: {anon_key[:25]}... (length: {len(anon_key)})")
print(f"   - JWT Secret: {jwt_secret[:15]}... (length: {len(jwt_secret)})")

# DNS
print(f"\n2. DNS & Network:")
hostname = supabase_url.replace("https://", "").replace("http://", "").split("/")[0]
try:
    ip = socket.gethostbyname(hostname)
    print(f"   ✅ DNS resolution OK: {hostname} -> {ip}")
except Exception as e:
    print(f"   ❌ DNS resolution failed: {e}")

# JWT Signature verification
print(f"\n3. JWT Verification against Secret:")
import jwt
for key_name, token in [("SERVICE_ROLE_KEY", service_key), ("ANON_KEY", anon_key)]:
    try:
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
        jwt.decode(token, jwt_secret, algorithms=[header.get("alg", "HS256")], options={"verify_aud": False})
        print(f"   ✅ {key_name}: Signature valid! Role={payload.get('role')}, Ref={payload.get('ref')}, Exp={payload.get('exp')}")
    except Exception as e:
        print(f"   ❌ {key_name}: Verification failed: {e}")

# Direct API Requests
print(f"\n4. HTTP API Endpoints Check:")

def check_endpoint(name, url, token):
    headers = {"apikey": token, "Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8')
            print(f"   ✅ [{name}] {resp.status} OK: {data[:80]}...")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"   ❌ [{name}] HTTP {e.code}: {body}")
        return False
    except Exception as e:
        print(f"   ❌ [{name}] Error: {e}")
        return False

check_endpoint("Auth Health", f"{supabase_url}/auth/v1/health", anon_key)
check_endpoint("PostgREST Schema with Anon", f"{supabase_url}/rest/v1/", anon_key)
check_endpoint("PostgREST Schema with Service Role", f"{supabase_url}/rest/v1/", service_key)

# Python Client Tests
print(f"\n5. Supabase Python Client (Backend Service Role):")
from supabase import create_client
client = create_client(supabase_url, service_key)

# Admin Auth check
try:
    users_resp = client.auth.admin.list_users()
    users = getattr(users_resp, 'users', users_resp) if not isinstance(users_resp, list) else users_resp
    print(f"   ✅ Auth Admin: Successfully queried auth.users ({len(users)} users registered)")
except Exception as e:
    print(f"   ❌ Auth Admin: {e}")

# Database tables
tables = ["profiles", "user_credits", "subscriptions", "user_projects"]
for tbl in tables:
    try:
        res = client.table(tbl).select("*", count="exact").limit(3).execute()
        count = res.count if hasattr(res, 'count') and res.count is not None else len(res.data)
        print(f"   ✅ Table '{tbl}': Accessible! Total rows={count}")
    except Exception as e:
        print(f"   ❌ Table '{tbl}': {e}")

# Storage buckets
try:
    buckets = client.storage.list_buckets()
    print(f"   ✅ Storage: Accessible! Found {len(buckets)} buckets.")
except Exception as e:
    print(f"   ❌ Storage: {e}")

# Python Client Test with Anon Key
print(f"\n6. Supabase Python Client (Frontend Anon Key):")
try:
    anon_client = create_client(supabase_url, anon_key)
    # Anon query on public table (RLS should apply)
    res = anon_client.table("profiles").select("id").limit(1).execute()
    print(f"   ✅ Anon Client: Query to profiles succeeded (RLS active, returned {len(res.data)} public rows)")
except Exception as e:
    print(f"   ❌ Anon Client query failed: {e}")

print("==========================================")
print("               CHECK COMPLETE             ")
print("==========================================")
