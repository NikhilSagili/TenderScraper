import time
import pandas as pd
import re
import random
import logging
from datetime import datetime
from utils.driver_setup import setup_driver, retry
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException
)

# Configure logging
logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay=2, backoff=2):
    """Decorator for retrying a function with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Max retries ({max_retries}) reached. Last error: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {retries} failed: {str(e)}. Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                    
                    # Add some randomness to the delay to avoid patterns
                    current_delay = current_delay * (0.9 + 0.2 * random.random())
        return wrapper
    return decorator

class GemBidScraper:
    def __init__(self):
        self.driver = setup_driver()
        self.url = "https://bidplus.gem.gov.in/advance-search"

    @retry_on_failure(max_retries=3, delay=2)
    def load_page(self):
        """Loads the advanced search page with retry logic."""
        try:
            logger.info(f"Loading page: {self.url}")
            time.sleep(random.uniform(2, 5)) # Add random delay
            self.driver.get(self.url)
            
            # Wait for either the nav-tabs or a timeout
            WebDriverWait(self.driver, 45).until(
                EC.presence_of_element_located((By.CLASS_NAME, "nav-tabs"))
            )
            logger.info("Page loaded successfully")
            
        except TimeoutException:
            logger.error("Timeout while waiting for page to load")
            # Take a screenshot for debugging
            try:
                self.driver.save_screenshot('page_load_timeout.png')
                logger.info("Screenshot saved as 'page_load_timeout.png'")
            except Exception as e:
                logger.error(f"Failed to take screenshot: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Error loading page: {str(e)}")
            raise

    @retry_on_failure(max_retries=3, delay=3)
    def apply_filters_and_search(self, state):
        """Applies filters on the advanced search page and clicks search with retry logic."""
        try:
            logger.info(f"Applying filters for state: {state}")
            
            # Wait for and click the consignee tab
            consignee_tab = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.ID, "location-tab"))
            )
            # Scroll into view and click using JavaScript
            self.driver.execute_script("arguments[0].scrollIntoView(true);", consignee_tab)
            time.sleep(1)  # Small delay for any animations
            self.driver.execute_script("arguments[0].click();", consignee_tab)
            
            # Wait for state dropdown to be visible and select the state
            state_dropdown = WebDriverWait(self.driver, 30).until(
                EC.visibility_of_element_located((By.ID, "state_name_con"))
            )
            select = Select(state_dropdown)
            select.select_by_visible_text(state)
            logger.info(f"Selected state: {state}")
            
            # Add a small random delay before clicking search
            time.sleep(1 + random.random())
            
            # Click search using JavaScript
            self.driver.execute_script("searchBid('con');")
            logger.info("Search initiated")
            
            # Wait for results to load with a longer timeout
            WebDriverWait(self.driver, 60).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, ".card")) > 0 or \
                         d.find_elements(By.CLASS_NAME, "no-records")
            )
            
            # Check for no records message
            no_records = self.driver.find_elements(By.CLASS_NAME, "no-records")
            if no_records:
                logger.warning("No records found for the selected criteria")
                return False
                
            logger.info("Search completed successfully")
            return True
            
        except TimeoutException:
            logger.error("Timeout while waiting for search results")
            self.driver.save_screenshot('search_timeout.png')
            raise
            
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
            self.driver.save_screenshot('filter_error.png')
            raise

    def scrape_bids(self, stop_date=None):
        """Scrapes bid information from all pages, collecting only bids newer than stop_date."""
        all_bids = []
        page_num = 1

        while True:  # Loop indefinitely until the last page is reached
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card"))
                )
                bid_blocks = self.driver.find_elements(By.CSS_SELECTOR, ".card")
            except Exception:
                break # No bid blocks found, likely end of results

            if not bid_blocks:
                break

            for bid in bid_blocks:
                try:
                    start_date_str = bid.find_element(By.CLASS_NAME, "start_date").text
                    if stop_date:
                        bid_start_date = datetime.strptime(start_date_str, '%d-%m-%Y %I:%M %p')
                        if bid_start_date < stop_date:
                            continue
                except Exception:
                    continue

                bid_no = "Not Found"
                bid_url = "#"
                try:
                    bid_link_element = bid.find_element(By.CSS_SELECTOR, "a.bid_no_hover")
                    bid_no = bid_link_element.text
                    href = bid_link_element.get_attribute('href')
                    if href:
                        bid_url = f"https://bidplus.gem.gov.in{href}" if href.startswith('/') else href
                except Exception:
                    pass # Keep default values

                try:
                    items = bid.find_element(By.XPATH, ".//strong[contains(text(), 'Items:')]/following-sibling::a").text.strip()
                except Exception:
                    items = "Not Found"

                try:
                    quantity_text = bid.find_element(By.XPATH, ".//strong[contains(text(), 'Quantity:')]/..").text
                    quantity = quantity_text.split(':')[-1].strip()
                except Exception:
                    quantity = "Not Found"

                try:
                    department = bid.find_element(By.XPATH, ".//strong[contains(text(), 'Department Name And Address:')]/../following-sibling::div").text.strip()
                except Exception:
                    department = "Not Found"

                try:
                    end_date = bid.find_element(By.CLASS_NAME, "end_date").text
                except Exception:
                    end_date = "Not Found"

                bid_data = {
                    "bid_number": bid_no,
                    "bid_url": bid_url,
                    "items": items,
                    "quantity": quantity,
                    "department": department,
                    "start_date": start_date_str,
                    "end_date": end_date,
                }
                all_bids.append(bid_data)

            # Pagination
            try:
                next_page_button = self.driver.find_element(By.CSS_SELECTOR, "#light-pagination a.next")
                self.driver.execute_script("arguments[0].click();", next_page_button)
                page_num += 1
            except Exception:
                break  # Exit the while loop

        if not all_bids:
            return pd.DataFrame()

        bids_df = pd.DataFrame(all_bids)
        return bids_df

    def close_driver(self):
        """Closes the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")
