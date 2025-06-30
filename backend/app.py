from flask import Flask, request, jsonify
from flask_cors import CORS
from scrapers.gem_scraper import GemBidScraper
from utils.driver_setup import get_webdriver
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)
CORS(app)  # Allow requests from the React frontend

@app.route('/scrape', methods=['POST'])
def scrape():
    """API endpoint to trigger the scraper."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    target_url = data.get('url')
    start_date_str = data.get('startDate')
    end_date_str = data.get('endDate') # Note: end_date is not used in the current scraper logic, but we get it for future use.

    if not target_url or not start_date_str:
        return jsonify({"error": "URL and start date are required"}), 400

    try:
        # Convert string date from frontend to datetime object
        stop_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD"}), 400

    driver = None
    try:
        driver = get_webdriver()
        scraper = GemBidScraper(driver)
        
        # The scraper's load_page method uses a hardcoded URL.
        # For this app, we can either modify the scraper or just acknowledge it.
        # For now, we'll assume the URL from the frontend is for confirmation, 
        # and the scraper will use its own configured URL.
        scraper.load_page()
        
        # The state is also hardcoded. This could be another parameter in the future.
        scraper.apply_filters_and_search(state="ANDHRA PRADESH")
        
        bids_df = scraper.scrape_bids(stop_date=stop_date)
        
        if bids_df.empty:
            return jsonify([])

        # Convert DataFrame to JSON
        result = bids_df.to_json(orient="records")
        return result

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
