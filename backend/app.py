import os
import time
import logging
from functools import wraps
from datetime import datetime, timedelta
from concurrent.futures import TimeoutError

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import pandas as pd
from pebble import concurrent

from scrapers.gem_scraper import GemBidScraper
from utils.driver_setup import get_webdriver, safe_quit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max payload

# Configure CORS with additional headers for long-running requests
CORS(app, resources={
    r"/*": {
        "origins": ["https://nikhilsagili.github.io", "http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-Requested-With"],
        "expose_headers": ["X-Progress", "X-Status"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# Request hooks
@app.before_request
def before_request():
    """Set up request context."""
    g.start_time = time.time()
    g.request_id = os.urandom(8).hex()
    logger.info(f"Request started: {request.method} {request.path} [{g.request_id}]")

@app.after_request
def after_request(response):
    """Clean up after request and log completion."""
    # Calculate request duration
    duration = time.time() - g.start_time
    
    # Add response headers for CORS and timeouts
    response.headers['X-Request-Duration'] = f"{duration:.2f}s"
    response.headers['X-Request-ID'] = getattr(g, 'request_id', '')
    response.headers['Keep-Alive'] = 'timeout=300, max=1000'
    
    logger.info(
        f"Request completed: {request.method} {request.path} "
        f"[{g.request_id}] - {response.status_code} ({duration:.2f}s)"
    )
    return response

# Error handlers

@app.errorhandler(500)
def handle_server_error(e):
    logger.error(f"Server error: {str(e)}", exc_info=True)
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

# API endpoints
@app.route('/', methods=['GET'])
def index():
    """Root endpoint that provides basic API information."""
    return jsonify({
        "name": "GeM Bid Scraper API",
        "version": "1.0.0",
        "status": "operational",
        "timeout": "1800s",
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
    """
    API endpoint to trigger the scraper with progress tracking and timeout handling.
    This endpoint can take a long time to complete (up to 30 minutes).
    """
    # Initialize request data and validate input
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        target_url = data.get('url')
        start_date_str = data.get('startDate')
        end_date_str = data.get('endDate')
        state = data.get('state', 'ANDHRA PRADESH') # Default to AP if not provided

        # Input validation
        if not target_url:
            return jsonify({"error": "URL is required"}), 400
            
        start_date = validate_date(start_date_str)
        end_date = validate_date(end_date_str)
        
        if not start_date or not end_date:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
            
        if start_date > end_date:
            return jsonify({"error": "Start date cannot be after end date"}), 400
            
        # Convert string date to datetime object
        try:
            stop_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD"}), 400
            
        # Log the start of scraping
        logger.info(f"Starting scrape for {target_url} from {start_date_str} to {end_date_str}")
        
    except Exception as e:
        logger.error(f"Error in input validation: {str(e)}", exc_info=True)
        return jsonify({"error": f"Invalid request: {str(e)}"}), 400

    try:
        # Use pebble to run the scraping task with a timeout
        future = run_scraping_task_with_timeout(stop_date=stop_date, state=state)
        result = future.result()  # Blocks until complete or timeout
        return jsonify(result)
    
    except TimeoutError:
        logger.error("Scraping task timed out after 30 minutes.")
        return jsonify({"error": "Request timed out", "details": "The scraping process took too long to complete."}), 504
    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@concurrent.process(timeout=1800)  # 30-minute timeout
def run_scraping_task_with_timeout(stop_date, state):
    """Runs the entire scraping process in a separate process with a timeout."""
    driver = None
    try:
        logger.info("Worker process: Initializing WebDriver...")
        driver = get_webdriver()
        driver.set_page_load_timeout(300)
        driver.set_script_timeout(300)
        
        scraper = GemBidScraper(driver)
        
        logger.info("Worker process: Loading page...")
        scraper.load_page()
        
        logger.info(f"Worker process: Applying filters for state: {state}...")
        if not scraper.apply_filters_and_search(state=state):
            return {"message": "No results found for the selected criteria", "data": []}
        
        logger.info(f"Worker process: Starting scrape until {stop_date}...")
        start_time = time.time()
        bids_df = scraper.scrape_bids(stop_date=stop_date, max_pages=50)
        duration = time.time() - start_time
        
        if bids_df.empty:
            return {"message": "No bids found for the given criteria", "data": []}
        
        logger.info(f"Worker process: Scraping completed in {duration:.1f}s. Found {len(bids_df)} bids.")
        result_data = bids_df.to_dict(orient="records")
        return {
            "message": "Success",
            "data": result_data,
            "stats": {
                "total_bids": len(result_data),
                "duration_seconds": round(duration, 2),
            }
        }
    except Exception as e:
        logger.error(f"Error within scraping worker process: {str(e)}", exc_info=True)
        # Re-raise to ensure the main thread catches it as a task failure
        raise
    finally:
        if driver:
            logger.info("Worker process: Cleaning up WebDriver...")
            driver.quit()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
