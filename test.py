import requests
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

response1 = response.json()["data"]
for model in response1:
    print("Model:",model["id"]," Context window:", model["context_window"]/1000,"K ", " Max completion tokens:", model["max_completion_tokens"]/1000,"K")