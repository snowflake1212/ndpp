import asyncio
import aiohttp
import time
import uuid
from loguru import logger
import sys
from fake_useragent import UserAgent

# Inisialisasi fake_useragent
user_agent = UserAgent()

# Customize loguru to use color for different log levels
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>", colorize=True)

PING_INTERVAL = 180
DOMAIN_API = {
    "SESSION": "http://api.nodepay.ai/api/auth/session",
    "PING": "http://18.139.20.49/api/network/ping"
}

def uuidv4():
    return str(uuid.uuid4())

def valid_resp(resp):
    if not resp or "code" not in resp or resp["code"] < 0:
        raise ValueError("Invalid response")
    return resp

async def call_api(url, data, token, user_agent, max_retries=3):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": user_agent,  # User-Agent khusus untuk token ini
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for attempt in range(max_retries):
            try:
                async with session.post(url, json=data, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    resp_json = await response.json()
                    return valid_resp(resp_json)
            except Exception as e:
                logger.warning(f"Error on attempt {attempt + 1} for {url}: {e}")
                await asyncio.sleep(2 ** attempt)
    return None

async def render_profile_info(token, user_agent):
    browser_id = uuidv4()
    account_info = {}

    try:
        logger.info("Fetching session data...")
        response = await call_api(DOMAIN_API["SESSION"], {}, token, user_agent)
        if response:
            account_info = response.get("data", {})
            logger.info(f"Session established for browser_id={browser_id}, account_info={account_info}")
            await start_ping(token, browser_id, account_info, user_agent)
        else:
            logger.warning("Failed to fetch session data.")
    except Exception as e:
        logger.error(f"Error in render_profile_info: {e}")

async def start_ping(token, browser_id, account_info, user_agent):
    last_ping_time = None
    try:
        while True:
            await ping(token, browser_id, account_info, last_ping_time, user_agent)
            await asyncio.sleep(PING_INTERVAL)
    except asyncio.CancelledError:
        logger.info("Ping task was cancelled.")
    except Exception as e:
        logger.error(f"Error in start_ping: {e}")

async def ping(token, browser_id, account_info, last_ping_time, user_agent):
    current_time = time.time()
    if last_ping_time and (current_time - last_ping_time) < PING_INTERVAL:
        return

    try:
        data = {
            "id": account_info.get("uid"),
            "browser_id": browser_id,
            "timestamp": int(current_time),
            "version": '2.2.7'
        }
        response = await call_api(DOMAIN_API["PING"], data, token, user_agent)
        if response and response.get("code") == 0:
            logger.info(f"Ping successful: {response}")
        else:
            logger.warning(f"Ping failed: {response}")
    except Exception as e:
        logger.error(f"Error in ping: {e}")

async def run_with_token(token, user_agent):
    logger.info(f"Starting session for token: {token} with User-Agent: {user_agent}")
    await render_profile_info(token, user_agent)
    logger.info(f"Session completed for token: {token}")

async def main():
    # Baca token dari file tokens.txt
    try:
        with open("tokens.txt", "r") as file:
            tokens = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logger.error("File 'tokens.txt' tidak ditemukan.")
        return

    # Buat User-Agent unik untuk setiap token
    user_agents = {token: user_agent.random for token in tokens}

    # Buat tasks untuk setiap token dengan User-Agent masing-masing
    tasks = [run_with_token(token, user_agents[token]) for token in tokens]

    # Jalankan semua tasks secara paralel
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
