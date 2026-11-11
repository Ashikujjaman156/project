"""Check that your AI key works. Run: python check_ai.py  (never prints the key)"""
import requests
from config import Config

key, base, model = Config.OPENAI_API_KEY, Config.OPENAI_BASE_URL.rstrip("/"), Config.OPENAI_MODEL
print(f"Address : {base}\nModel   : {model}")
if not key:
    raise SystemExit("Key     : NOT FOUND. Put OPENAI_API_KEY=... in the .env file.")
print(f"Key     : found ({key[:3]}..., {len(key)} characters)")
if key != key.strip() or key.startswith(('"', "'")):
    print("WARNING : the key has a space or quote around it. Remove it in .env")

try:
    r = requests.post(f"{base}/chat/completions", timeout=60,
                      headers={"Authorization": f"Bearer {key}", "User-Agent": "UPS-Placement-System/1.0"},
                      json={"model": model, "messages": [{"role": "user", "content": "Say hello in 5 words."}],
                            "max_tokens": 300})
except requests.RequestException as e:
    raise SystemExit(f"RESULT  : could not reach the server ({type(e).__name__}). Check your internet.")

print(f"HTTP    : {r.status_code}")
if r.status_code == 200:
    try:
        print("Reply   :", r.json()["choices"][0]["message"]["content"].strip())
    except Exception:
        print("Reply   : (200 OK but unexpected format)", r.text[:200])
    print("RESULT  : WORKS. Start the site; the assistant will use it.")
else:
    print("Provider says:", r.text[:300].replace(key, "***"))
    hint = {401: "Key rejected or this provider doesn't allow your app.",
            403: "Blocked. Key not allowed here or provider firewall.",
            404: "Model name not found. Fix OPENAI_MODEL (try without the 'models/' prefix).",
            429: "Out of free quota or too many requests. Wait a bit.",
            400: "Request not accepted. Often a wrong model name."}.get(r.status_code, "Unexpected error.")
    print("RESULT  : DOES NOT WORK.", hint)
