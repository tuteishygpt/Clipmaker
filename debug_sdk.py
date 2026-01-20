
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

try:
    client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
    print("Client created.")
    
    import inspect
    sig = inspect.signature(client.batches.create)
    print(f"Signature of batches.create: {sig}")
    
    # Also help on the method
    # print(help(client.batches.create))
    
except Exception as e:
    print(f"Error: {e}")
