from flask import Flask, request, jsonify
from flask_cors import CORS
from scrapers.gem_scraper import GemBidScraper
from utils.driver_setup import get_webdriver
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    """Root endpoint that provides basic API information."""
    return jsonify({
        "name": "GeM Bid Scraper API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health_check": "/health (GET)",
            "scrape": "/scrape (POST)"
        },
        "documentation": "https://github.com/NikhilSagili/TenderScraper"
    }), 200

# Allow requests from GitHub Pages and local development
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://nikhilsagili.github.io",  # GitHub Pages
            "http://localhost:3000"            # Local development
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render to monitor the service."""
    try:
        # Test database connection if you have one
        # Test external service connections if any
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "gem-bid-scraper"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

def validate_date(date_str):
    """Validate and parse date string."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None

@app.route('/scrape', methods=['POST'])
def scrape():
    """API endpoint to trigger the scraper."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        target_url = data.get('url')
        start_date_str = data.get('startDate')
        end_date_str = data.get('endDate')

        # Input validation
        if not target_url:
            return jsonify({"error": "URL is required"}), 400
            
        start_date = validate_date(start_date_str)
        end_date = validate_date(end_date_str)
        
        if not start_date or not end_date:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
            
        if start_date > end_date:
            return jsonify({"error": "Start date cannot be after end date"}), 400
            
        # Add rate limiting check if needed
        # if is_rate_limited():
        #     return jsonify({"error": "Too many requests. Please try again later."}), 429
            
    except Exception as e:
        app.logger.error(f"Error in input validation: {str(e)}")
        return jsonify({"error": f"Invalid request: {str(e)}"}), 400 # Note: end_date is not used in the current scraper logic, but we get it for future use.

    if not target_url or not start_date_str:
        return jsonify({"error": "URL and start date are required"}), 400

    try:
        # Convert string date from frontend to datetime object
        stop_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD"}), 400

    driver = None
    try:
        print("Initializing webdriver...")
        driver = get_webdriver()
        print("Webdriver initialized successfully")
        
        print("Initializing scraper...")
        scraper = GemBidScraper(driver)
        print("Scraper initialized successfully")
        
        try:
            print("Loading page...")
            scraper.load_page()
            print("Page loaded successfully")
            
            print("Applying filters and searching...")
            scraper.apply_filters_and_search(state="ANDHRA PRADESH")
            print("Filters applied successfully")
            
            print(f"Starting to scrape bids until {stop_date}...")
            bids_df = scraper.scrape_bids(stop_date=stop_date)
            print(f"Scraping completed. Found {len(bids_df)} bids")
            
            if bids_df.empty:
                print("No bids found for the given criteria")
                return jsonify({"message": "No bids found for the given criteria", "data": []}), 200

            # Convert DataFrame to list of dicts for JSON serialization
            print("Converting results to JSON...")
            result = bids_df.to_dict(orient="records")
            return jsonify({"message": "Success", "data": result}), 200
            
        except Exception as scrape_error:
            app.logger.error(f"Error during scraping: {str(scrape_error)}", exc_info=True)
            return jsonify({
                "error": "Scraping failed",
                "details": str(scrape_error)
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error initializing scraper: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Failed to initialize scraper",
            "details": str(e)
        }), 500
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
