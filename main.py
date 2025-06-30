import os
from scrapers.gem_scraper import GemBidScraper
from utils.driver_setup import get_webdriver

def main():
    """Main function to run the scraper."""
    print("Starting the GeM bid scraper...")
    
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
        
    driver = None
    try:
        driver = get_webdriver()
        scraper = GemBidScraper(driver)
        scraper.load_page()
        scraper.apply_filters_and_search(state="ANDHRA PRADESH")
        
        # Scrape the first 2 pages of results
        bids_df = scraper.scrape_bids(num_pages=2)
        
        if not bids_df.empty:
            output_path = "data/gem_bids.csv"
            bids_df.to_csv(output_path, index=False, encoding='utf-8')
            print(f"Scraped {len(bids_df)} bids and saved to {output_path}")
        else:
            print("No bids were scraped.")
            
        print("\nScraping complete. Press Enter to close the browser.")
        input()

    except Exception as e:
        print(f"An error occurred: {e}")
        print("\nThe browser will remain open for inspection. Press Enter to close.")
        input()
    finally:
        if driver:
            scraper.close_driver()
            print("WebDriver closed.")

if __name__ == "__main__":
    main()
