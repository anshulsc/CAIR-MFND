import os
import sys
from pyngrok import ngrok, conf
import time

print("---  Tunnel Manager Started ---")
NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN")
if not NGROK_AUTHTOKEN:
    print("❌ ERROR: NGROK_AUTHTOKEN not found in environment.")
    sys.exit(1)

conf.get_default().auth_token = NGROK_AUTHTOKEN
streamlit_port = 8501

try:
    public_url = ngrok.connect(streamlit_port, "http").public_url
    print("===============================================================")
    print(f"✅ Streamlit UI is now public at: {public_url}")
    print("===============================================================")
    ngrok_process = ngrok.get_ngrok_process()
    ngrok_process.proc.wait()

except Exception as e:
    print(f"❌ An error occurred with ngrok: {e}")
    ngrok.kill()
