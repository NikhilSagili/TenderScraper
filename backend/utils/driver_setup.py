import os
import logging
from functools import wraps
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from selenium.common.exceptions import (WebDriverException, TimeoutException, 
                                        NoSuchElementException, StaleElementReferenceException)

logger = logging.getLogger(__name__)

def retry(attempts=3, delay=5):
    """Decorator for retrying a function on WebDriver-related exceptions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except (WebDriverException, TimeoutException, 
                        NoSuchElementException, StaleElementReferenceException) as e:
                    logger.warning(f"Attempt {attempt}/{attempts} failed for {func.__name__}: {e}")
                    if attempt == attempts:
                        logger.error(f"Max retries ({attempts}) reached. Last error: {e}")
                        raise
                    if hasattr(args[0], 'driver'):
                        args[0].driver.implicitly_wait(delay)
        return wrapper
    return decorator

def setup_driver():
    """Initializes and returns a Selenium WebDriver instance with advanced anti-detection."""
    logger.info("Setting up Chrome WebDriver with advanced anti-detection...")
    try:
        ua = UserAgent()
        user_agent = ua.random

        chrome_options = webdriver.ChromeOptions()

        # More aggressive anti-detection options
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--password-store=basic")
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process,SitePerProcess")
        chrome_options.add_argument(f"--lang=en-US,en;q=0.9")

        # Headless and environment-specific options
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Further anti-detection measures
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_page_load_timeout(300)
        driver.set_script_timeout(300)

        logger.info("WebDriver setup complete.")
        return driver
    except Exception as e:
        logger.error(f"Error setting up WebDriver: {e}")
        raise

def safe_quit(driver):
    """Safely quit the WebDriver instance."""
    if driver:
        try:
            driver.quit()
            logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error while closing WebDriver: {str(e)}")
