import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("INTERNAL_API_KEY")
res = requests.get(
    'http://localhost:8000/api/jobs/33041848-3473-45f5-8377-f59379022c02',
    headers={'Authorization': f'Bearer {api_key}'}
)
import json
print(json.dumps(res.json(), indent=2))
