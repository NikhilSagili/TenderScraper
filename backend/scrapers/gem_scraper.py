import logging
import time
import pandas as pd
import re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

class GemBidScraper:
    def __init__(self, driver, logger):
        self.driver = driver
        self.url = "https://bidplus.gem.gov.in/advance-search"
        self.logger = logger

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
            self.logger.info(f"Applying filters. State: {state}")
            if state and state.strip():
                try:
                    self.logger.info("Opening consignee location filter section...")
                    consignee_tab = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.ID, "location-tab"))
                    )
                    self.driver.execute_script("arguments[0].click();", consignee_tab)
                    
                    self.logger.info(f"Attempting to select state: {state}")
                    state_dropdown_elem = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.ID, "state_name_con"))
                    )
                    state_dropdown = Select(state_dropdown_elem)
                    state_dropdown.select_by_visible_text(state)
                    self.logger.info(f"Successfully selected state: {state}")
                    time.sleep(1)  # Brief pause for any JS to trigger
                except Exception as e:
                    self.logger.error(f"Could not select state '{state}'. It might not be available or the filter section failed to open. Error: {e}")
                    raise Exception(f"Failed to select state: {state}")

            # More robustly click the search button
            try:
                self.logger.info("Locating and clicking search button...")
                search_button = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, \"searchBid('con')\")] | //button[contains(@onclick, \"searchBid('con')\")]"))
                )
                self.driver.execute_script("arguments[0].click();", search_button)
                self.logger.info("Clicked search button successfully.")
            except Exception as e:
                self.logger.error(f"Could not find or click search button. Falling back to JS execution. Error: {e}")
                self.driver.execute_script("searchBid('con');")

            self.logger.info("Waiting for search results or an error message...")
            WebDriverWait(self.driver, 40).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#bidCard .alert.alert-danger"))
                )
            )

            try:
                error_element = self.driver.find_element(By.CSS_SELECTOR, "#bidCard .alert.alert-danger")
                if "Something went wrong" in error_element.text:
                    self.logger.error("Detected server-side error message on GeM portal.")
                    raise Exception("The GeM portal returned an error: 'Something went wrong, please try again after some time'. This is an issue with the website, not the scraper.")
            except NoSuchElementException:
                self.logger.info("Bid results loaded successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during filter application: {e}")
            self.driver.save_screenshot('debug_screenshot_filters.png')
            raise

    def scrape_bids(self, start_date=None, end_date=None):
        """Scrapes bid information from all pages, collecting only bids newer than stop_date."""
        all_bids = []
        page_num = 1
        self.logger.info(f"Starting scrape with Start Date: {start_date} and End Date: {end_date}")
        while True:  # Loop indefinitely until the last page is reached
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card"))
                )
                bid_blocks = self.driver.find_elements(By.CSS_SELECTOR, ".card")
            except Exception:
                self.logger.info("No bid cards found on page, ending scrape.")
                break # No bid blocks found, likely end of results

            if not bid_blocks:
                self.logger.info(f"No bid blocks found for the given criteria, ending scrape.")
                break

            for bid in bid_blocks:
                try:
                    start_date_str = bid.find_element(By.CLASS_NAME, "start_date").text.split('\n')[0]
                    bid_start_date = datetime.strptime(start_date_str, '%d-%m-%Y %I:%M %p')
                except Exception as e:
                    raw_text = "not found"
                    try:
                        raw_text = bid.find_element(By.CLASS_NAME, "start_date").text
                    except:
                        pass
                    self.logger.error(f"Could not parse start date. Raw text: '{raw_text}'. Error: {e}")
                    continue

                # Only process the bid if it's within the specified date range
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
                    scraped_end_date_str = bid.find_element(By.CLASS_NAME, "end_date").text
                except Exception:
                    scraped_end_date_str = "Not Found"

                bid_url = ""
                try:
                    bid_link_element = bid.find_element(By.CSS_SELECTOR, "a.bid_no_hover")
                    href = bid_link_element.get_attribute('href')
                    if href:
                        bid_url = f"https://bidplus.gem.gov.in{href}"
                except Exception:
                    bid_url = "Not Found"

                bid_data = {
                    "bid_number": bid_no,
                    "bid_url": bid_url,
                    "items": items,
                    "quantity": quantity,
                    "department": department,
                    "start_date": start_date_str,
                    "end_date": scraped_end_date_str,
                }
                all_bids.append(bid_data)


            # Pagination
            try:
                # Find the 'next' button to see if another page exists
                next_page_button = self.driver.find_element(By.CSS_SELECTOR, "#light-pagination a.next")
                self.driver.execute_script("arguments[0].click();", next_page_button)
                page_num += 1
                self.logger.info(f"Navigating to page {page_num}...")

                # Wait for the next page's content OR an error message to appear
                WebDriverWait(self.driver, 40).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".card")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#bidCard .alert.alert-danger"))
                    )
                )

                # After waiting, check if the error message is present
                try:
                    error_element = self.driver.find_element(By.CSS_SELECTOR, "#bidCard .alert.alert-danger")
                    if "Something went wrong" in error_element.text:
                        error_msg = f"The GeM portal returned an error on page {page_num}: 'Something went wrong'."
                        self.logger.error(error_msg)
                        raise Exception(error_msg)
                except NoSuchElementException:
                    # No error found, page loaded successfully
                    self.logger.info(f"Page {page_num} loaded successfully.")

            except NoSuchElementException:
                # This is the normal exit condition: no 'next' button was found.
                self.logger.info("No more pages found. Finalizing scrape.")
                break
            except Exception as e:
                # This will catch the explicit raise from our error check, or a TimeoutException if neither bids nor error appeared.
                self.logger.error(f"Failed to navigate to page {page_num}. Error: {e}")
                raise e # Re-raise to be handled by app.py

        if not all_bids:
            self.logger.info("Scraping completed. No bids matched the date criteria.")
            return pd.DataFrame()

        self.logger.info(f"Scraping completed. Found {len(all_bids)} bids.")
        bids_df = pd.DataFrame(all_bids)
        return bids_df

    def close_driver(self):
        """Closes the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.logger.info("WebDriver closed.")