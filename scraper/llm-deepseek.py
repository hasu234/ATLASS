import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()
llm_model = os.getenv("LLM_MODEL")

url = "http://10.10.10.104:11434/api/generate"
# payload = json.dumps({
#     "model": "deepseek-coder-v2",
#     "prompt": "Write a Python function to reverse a string.",
#     "stream": False
# })

system_prompt = "You are a helpful assistant that writes clean, idiomatic Python code."
user_prompt = "Write a Python function to reverse a string."

combined_prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}"

payload = json.dumps({
    "model": llm_model,
    "prompt": combined_prompt,
    "stream": False
})


headers = {'Content-Type': 'application/json'}

response = requests.post(url, data=payload, headers=headers)

print(response.json().get("response"))