
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GENAI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    print("List of models:")
    for m in client.models.list():
        print(f"Model: {m.name}")
        # print(f"Supported methods: {m.supported_generation_methods}") # Attribute might differ in this SDK
except Exception as e:
    print(f"Error listing models: {e}")

