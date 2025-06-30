import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_webdriver(max_retries=3, retry_delay=5):
    """
    Sets up and returns a Selenium Chrome WebDriver instance with retry logic.
    
    Args:
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
        
    Returns:
        WebDriver: Configured Chrome WebDriver instance
    """
    attempt = 0
    last_exception = None
    
    while attempt < max_retries:
        try:
            chrome_options = Options()
            
            # Basic options
            chrome_options.add_argument("--headless")
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Performance optimizations
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            
            # Make Selenium look more like a regular browser
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            chrome_options.add_argument(f'user-agent={user_agent}')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Configure timeouts
            service = ChromeService(executable_path=ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set page load and script timeouts
            driver.set_page_load_timeout(120)  # 2 minutes
            driver.set_script_timeout(120)     # 2 minutes
            
            # Additional capabilities to prevent detection
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("WebDriver initialized successfully")
            return driver
            
        except WebDriverException as e:
            last_exception = e
            attempt += 1
            logger.warning(f"WebDriver initialization attempt {attempt} failed: {str(e)}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    
    logger.error(f"Failed to initialize WebDriver after {max_retries} attempts")
    raise RuntimeError(f"Failed to initialize WebDriver: {str(last_exception)}")

def safe_quit(driver):
    """Safely quit the WebDriver instance."""
    if driver:
        try:
            driver.quit()
            logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error while closing WebDriver: {str(e)}")
