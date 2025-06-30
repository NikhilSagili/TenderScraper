import time
import pandas as pd
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

class GemBidScraper:
    def __init__(self, driver):
        self.driver = driver
        self.url = "https://bidplus.gem.gov.in/advance-search"

    def load_page(self):
        """Loads the advanced search page."""
        self.driver.get(self.url)
        print(f"Loading page: {self.url}")
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "nav-tabs"))
            )
            print("Advanced search page loaded.")
        except Exception as e:
            print("Error waiting for the main search interface to load.")
            raise

    def apply_filters_and_search(self, state):
        """Applies filters on the advanced search page and clicks search."""
        print(f"Applying filters for state: {state}")
        try:
            time.sleep(2)
            consignee_tab = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "location-tab"))
            )
            self.driver.execute_script("arguments[0].click();", consignee_tab)
            state_dropdown = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "state_name_con"))
            )
            select = Select(state_dropdown)
            select.select_by_visible_text(state)
            print(f"Selected state: {state}")
            print("Directly executing search JavaScript function...")
            self.driver.execute_script("searchBid('con');")
            print("JavaScript function executed.")
            WebDriverWait(self.driver, 40).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".card"))
            )
            print("Search results loaded.")
        except Exception as e:
            print(f"Error applying filters: {e}")
            screenshot_path = 'debug_screenshot_filters.png'
            self.driver.save_screenshot(screenshot_path)
            print(f"Saved a screenshot to {screenshot_path}")
            raise

    def scrape_bids(self, num_pages=1):
        """Scrapes bid information from the search results with robust error handling."""
        all_bids = []
        for page in range(num_pages):
            print(f"Scraping page {page + 1}...")
            time.sleep(3)
            bid_blocks = self.driver.find_elements(By.CSS_SELECTOR, ".card")
            print(f"Found {len(bid_blocks)} bid blocks on this page.")

            for bid in bid_blocks:
                try:
                    bid_no = bid.find_element(By.CSS_SELECTOR, "a.bid_no_hover").text
                except Exception:
                    bid_no = "Not Found"
                
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
                    start_date = bid.find_element(By.CLASS_NAME, "start_date").text
                except Exception:
                    start_date = "Not Found"
                
                try:
                    end_date = bid.find_element(By.CLASS_NAME, "end_date").text
                except Exception:
                    end_date = "Not Found"

                bid_data = {
                    "bid_number": bid_no,
                    "items": items,
                    "quantity": quantity,
                    "department": department,
                    "start_date": start_date,
                    "end_date": end_date,
                }
                all_bids.append(bid_data)
                print(f"Successfully scraped bid: {bid_no}")

            if page < num_pages - 1:
                try:
                    print("Trying to go to the next page...")
                    pagination = self.driver.find_element(By.CSS_SELECTOR, "ul.pagination")
                    next_page_button = pagination.find_element(By.LINK_TEXT, "›")
                    
                    if "disabled" in next_page_button.find_element(By.XPATH, "./..").get_attribute("class"):
                        print("Next page button is disabled. Reached the last page.")
                        break

                    self.driver.execute_script("arguments[0].click();", next_page_button)
                    print("Navigated to the next page.")
                    time.sleep(3) # Wait for new page to load
                except Exception as e:
                    print(f"Could not find or click the next page button. Stopping. Error: {e}")
                    break
        
        if not all_bids:
            print("No bids were scraped.")
            return pd.DataFrame()

        bids_df = pd.DataFrame(all_bids)
        return bids_df

    def close_driver(self):
        """Closes the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")
