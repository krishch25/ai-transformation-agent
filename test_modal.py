import os
from openai import OpenAI

base_url = os.environ.get("MODAL_LLM_URL")
if not base_url:
    print("MODAL_LLM_URL not set")
    exit(1)

client = OpenAI(
    base_url=base_url,
    api_key=os.environ.get("MODAL_LLM_TOKEN", "EMPTY")
)

print(f"Testing Modal Endpoint: {base_url}")
try:
    response = client.chat.completions.create(
        model="modal-model",
        messages=[{"role": "user", "content": "Hello, are you there?"}],
        timeout=120
    )
    print("Success:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
