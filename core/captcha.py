import asyncio
from capmonster_python import TurnstileTask
from twocaptcha import TwoCaptcha

# Constants for CAPTCHA parameters
CAPTCHA_PARAMS = {
    'website_key': '0x4AAAAAAAx1CyDNL8zOEPe7',  # Website Key
    'website_url': 'https://app.nodepay.ai/login'  # Website URL
}

# Directly set API key for Capmonster
class ServiceCapmonster:
    def __init__(self):
        # Directly set your Capmonster API key here
        api_key = "your_capmonster_api_key_here"  # Replace with your actual API key
        self.capmonster = TurnstileTask(api_key)

    def get_captcha_token(self):
        task_id = self.capmonster.create_task(
            **CAPTCHA_PARAMS
        )
        return self.capmonster.join_task_result(task_id).get("token")

    async def get_captcha_token_async(self):
        return await asyncio.to_thread(self.get_captcha_token)

    # Add alias for compatibility
    async def solve_captcha(self):
        return await self.get_captcha_token_async()


# Directly set API key for Anticaptcha
from anticaptchaofficial.turnstileproxyless import turnstileProxyless

class ServiceAnticaptcha:
    def __init__(self):
        # Directly set your Anticaptcha API key here
        api_key = "your_anticaptcha_api_key_here"  # Replace with your actual API key
        self.solver = turnstileProxyless()
        self.solver.set_verbose(1)
        self.solver.set_key(api_key)
        self.solver.set_website_url(CAPTCHA_PARAMS['website_url'])
        self.solver.set_website_key(CAPTCHA_PARAMS['website_key'])
        self.solver.set_action("login")

    def get_captcha_token(self):
        captcha_token = self.solver.solve_and_return_solution()
        return captcha_token

    async def get_captcha_token_async(self):
        return await asyncio.to_thread(self.get_captcha_token)

    # Add alias for compatibility
    async def solve_captcha(self):
        return await self.get_captcha_token_async()


# Directly set API key for 2Captcha
class Service2Captcha:
    def __init__(self):
        # Directly set your 2Captcha API key here
        api_key = "your_2captcha_api_key_here"  # Replace with your actual API key
        self.solver = TwoCaptcha(api_key)

    def get_captcha_token(self):
        captcha_token = self.solver.turnstile(sitekey=CAPTCHA_PARAMS['website_key'], url=CAPTCHA_PARAMS['website_url'])
        return captcha_token

    async def get_captcha_token_async(self):
        return await asyncio.to_thread(self.get_captcha_token)

    # Add alias for compatibility
    async def solve_captcha(self):
        return await self.get_captcha_token_async()
