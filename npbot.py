import threading
import time
import uuid
import cloudscraper
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent

# Inisialisasi fake_useragent
try:
    user_agent = UserAgent()
    session_user_agent = user_agent.random  # Ambil satu User-Agent untuk sesi ini
except Exception:
    session_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  # Fallback

# Constants
PING_INTERVAL = 60
RETRIES = 200

DOMAIN_API_ENDPOINTS = {
    "SESSION": [
        "http://api.nodepay.ai/api/auth/session"
    ],
    "PING": [
        "http://13.215.134.222/api/network/ping",
        "http://18.139.20.49/api/network/ping",
        "http://52.74.35.173/api/network/ping",
        "http://52.77.10.116/api/network/ping"
    ]
}

CONNECTION_STATES = {
    "CONNECTED": 1,
    "DISCONNECTED": 2,
    "NONE_CONNECTION": 3
}

status_connect = CONNECTION_STATES["NONE_CONNECTION"]
browser_id = None
account_info = {}
last_ping_time = {}
ping_index = 0  # To track the current ping API

# Logger Configuration
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO")

def uuidv4():
    return str(uuid.uuid4())

def valid_resp(resp):
    if not resp or "code" not in resp or resp["code"] < 0:
        raise ValueError("Invalid response")
    return resp

def get_next_ping_api():
    global ping_index
    ping_api = DOMAIN_API_ENDPOINTS["PING"][ping_index]
    ping_index = (ping_index + 1) % len(DOMAIN_API_ENDPOINTS["PING"])  # Cycle through endpoints
    return ping_api

def call_api(url, data, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": session_user_agent,  # Menggunakan User-Agent dari sesi
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://app.nodepay.ai",
    }

    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.post(url, json=data, headers=headers, timeout=30)

        response.raise_for_status()
        return valid_resp(response.json())
    except Exception:
        raise ValueError(f"Failed API call to {url}")

def start_ping(token):
    global last_ping_time, RETRIES, status_connect

    while True:
        current_time = time.time()

        try:
            ping_url = get_next_ping_api()  # Get the next ping API
            data = {
                "id": account_info.get("uid"),
                "browser_id": browser_id,
                "timestamp": int(time.time())
            }

            response = call_api(ping_url, data, token)
            if response["code"] == 0:
                logger.info(f"Ping sent successfully to {ping_url}: {response}")
                RETRIES = 0
                status_connect = CONNECTION_STATES["CONNECTED"]
            else:
                handle_ping_fail(response)
        except Exception:
            handle_ping_fail(None)

        time.sleep(PING_INTERVAL)

def handle_ping_fail(response):
    global RETRIES, status_connect

    RETRIES += 1
    status_connect = CONNECTION_STATES["DISCONNECTED"]

def render_profile_info(token):
    global browser_id, account_info

    try:
        browser_id = uuidv4()
        response = call_api(DOMAIN_API_ENDPOINTS["SESSION"][0], {}, token)
        valid_resp(response)
        account_info = response["data"]
        if account_info.get("uid"):
            start_ping(token)
    except Exception:
        pass  # Suppress errors to focus only on ping messages

def load_tokens(token_file):
    try:
        with open(token_file, 'r') as file:
            tokens = [line.strip() for line in file if line.strip()]
        return tokens
    except Exception as e:
        logger.error(f"Failed to load tokens: {e}")
        raise SystemExit("Exiting due to failure in loading tokens")

def run_for_token(token):
    try:
        render_profile_info(token)
    except Exception:
        pass  # Suppress errors to focus only on ping messages

def main():
    tokens = load_tokens('tokens.txt')

    threads = []
    for token in tokens:
        thread = threading.Thread(target=run_for_token, args=(token,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    main()
