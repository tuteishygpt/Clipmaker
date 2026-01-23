import jwt
import base64

SECRET = "1L/jbUD/sm+WSFpBi+vdDtCsZd7h5/asTtbIyLhbuN/xQwqWjuPc9kozyssSKaIWQATH6dL4XnsUTZw8vXx2Xg=="
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxY2R4bG56cmZ4cW1mdHNlbWVrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTE4MzM4NCwiZXhwIjoyMDg0NzU5Mzg0fQ.8Rz7HVlFimiJSBKchfvD9P_Ddo11KMn1d37cbEYNIKo"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxY2R4bG56cmZ4cW1mdHNlbWVrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxODMzODQsImV4cCI6MjA4NDc1OTM4NH0.ecn8NmvsE9mIYbhTmhs2sX8K5mmQTnjbmL8jY5kiddE"

def check(name, token):
    res = "FAIL"
    try:
        jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_aud": False})
        res = "OK-RAW"
    except:
        try:
             # Try base64
             jwt.decode(token, base64.b64decode(SECRET+"=="), algorithms=["HS256"], options={"verify_aud": False})
             res = "OK-B64"
        except:
             pass
    print(f"{name}: {res}")

check("SERVICE_ROLE", SERVICE_KEY)
check("ANON", ANON_KEY)
