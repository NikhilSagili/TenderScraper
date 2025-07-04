import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from scrapers.gem_scraper import GemBidScraper
from utils.driver_setup import get_webdriver
from datetime import datetime, timedelta
import pandas as pd
from pyngrok import ngrok

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        return jsonify({"error": f"Invalid request: {str(e)}"}), 400 

    if not target_url or not start_date_str or not end_date_str:
        return jsonify({"error": "URL, start date, and end date are required"}), 400

    try:
        # Convert string dates from frontend to datetime objects
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
        # Set end_date to the end of the day to include all bids on that day
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD"}), 400

    driver = None
    try:
        app.logger.info("Initializing webdriver...")
        driver = get_webdriver()
        app.logger.info("Webdriver initialized successfully")
        
        app.logger.info("Initializing scraper...")
        scraper = GemBidScraper(driver, app.logger)
        app.logger.info("Scraper initialized successfully")
        
        try:
            app.logger.info("Loading page...")
            scraper.load_page()
            app.logger.info("Page loaded successfully")
            
            app.logger.info("Applying filters and searching...")
            state = data.get("state")  # Get state from request payload
            app.logger.info(f"Received state filter: {state}")
            scraper.apply_filters_and_search(state=state)
            app.logger.info("Filters applied successfully")
            
            app.logger.info(f"Starting to scrape bids from {start_date_str} to {end_date_str}...")
            bids_df = scraper.scrape_bids(start_date=start_date_obj, end_date=end_date_obj)
            app.logger.info(f"Scraping completed. Found {len(bids_df)} bids")
            
            if bids_df.empty:
                app.logger.info("No bids found for the given criteria")
                return jsonify({"message": "No bids found for the given criteria", "data": []}), 200

            # Convert DataFrame to list of dicts for JSON serialization
            app.logger.info("Converting results to JSON...")
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
    # app.run(debug=True, port=5001)
    port = 5001
    try:
        # It's recommended to set your ngrok authtoken in your environment variables
        # for a more stable experience.
        public_url_obj = ngrok.connect(port, "http")
        app.logger.info("***********************************************************************************")
        app.logger.info(f"* Backend is running on: http://127.0.0.1:{port}")
        app.logger.info(f"* ngrok tunnel is active. Public URL: {public_url_obj.public_url}")
        app.logger.info("* Copy this Public URL and paste it into the frontend's 'Backend URL' field.")
        app.logger.info("***********************************************************************************")
    except Exception as e:
        app.logger.error("***********************************************************************************")
        app.logger.error(f"* Could not start ngrok tunnel: {e}")
        app.logger.error(f"* Backend is running locally. Use http://localhost:{port} for the frontend.")
        app.logger.error("***********************************************************************************")

    # Start the Flask app. use_reloader=False is recommended with ngrok
    # to prevent creating multiple tunnels when in debug mode.
    app.run(debug=True, port=port, use_reloader=False)