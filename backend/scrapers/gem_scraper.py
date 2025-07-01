import time
import pandas as pd
import re
from datetime import datetime
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
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "nav-tabs"))
            )
        except Exception as e:
            # Optionally log this error to a file
            raise

    def apply_filters_and_search(self, state):
        """Applies filters on the advanced search page and clicks search."""
        try:
            consignee_tab = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "location-tab"))
            )
            self.driver.execute_script("arguments[0].click();", consignee_tab)
            state_dropdown = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "state_name_con"))
            )
            select = Select(state_dropdown)
            select.select_by_visible_text(state)

            # More robustly click the search button instead of just executing script
            try:
                print("Locating and clicking search button...")
                search_button = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, \"searchBid('con')\")] | //button[contains(@onclick, \"searchBid('con')\")]"))
                )
                self.driver.execute_script("arguments[0].click();", search_button)
                print("Clicked search button successfully.")
            except Exception as e:
                print(f"Could not find or click search button. Falling back to JS execution. Error: {e}")
                self.driver.execute_script("searchBid('con');")

            time.sleep(3)  # Allow time for AJAX request to be sent and processed

            print("Waiting for bid results to load...")
            WebDriverWait(self.driver, 40).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".card"))
            )
            print("Bid results loaded.")
        except Exception as e:
            screenshot_path = 'debug_screenshot_filters.png'
            self.driver.save_screenshot(screenshot_path)
            # Optionally log errors to a file
            raise

    def scrape_bids(self, start_date=None, end_date=None):
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
                    start_date_str = bid.find_element(By.CLASS_NAME, "start_date").text.split('\n')[0]
                    bid_start_date = datetime.strptime(start_date_str, '%d-%m-%Y')
                except Exception:
                    continue

                # Only append the bid if it's within the specified date range
                if start_date and end_date:
                    if not (start_date <= bid_start_date <= end_date):
                        continue # Skip this bid

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
                    end_date = bid.find_element(By.CLASS_NAME, "end_date").text
                except Exception:
                    end_date = "Not Found"

                bid_data = {
                    "bid_number": bid_no,
                    "items": items,
                    "quantity": quantity,
                    "department": department,
                    "start_date": start_date_str,
                    "end_date": end_date,
                }


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