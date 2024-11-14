import asyncio
from core.nodepay_client import NodePayClient
from core.captcha import CaptchaService
from core.utils.logger import setup_logger

# Setup logger (assuming this function is defined in core.utils.logger)
setup_logger()

# Konfigurasi email, password, dan user agent
EMAIL = "email@example.com"
PASSWORD = "your_password"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

# Fungsi utama yang menjalankan program
async def main():
    # Inisialisasi CaptchaService dan NodePayClient
    captcha_service = CaptchaService()  # Menggunakan core.captcha
    async with NodePayClient(email=EMAIL, password=PASSWORD, user_agent=USER_AGENT) as client:
        try:
            # Mendapatkan token autentikasi
            uid, token = await client.get_auth_token(captcha_service)
            print(f"Logged in with UID: {uid}")

            # Melakukan ping dan mendapatkan informasi
            total_earning = await client.ping(uid, token)
            print(f"Total Earning: {total_earning}")

        except Exception as e:
            print(f"An error occurred: {e}")

# Menjalankan event loop untuk async main function
if __name__ == "__main__":
    asyncio.run(main())
