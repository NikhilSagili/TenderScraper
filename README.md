# GeM Bid Scraper

This project scrapes bid information from the Government e-Marketplace (GeM) of India.

## Project Structure

- `main.py`: The main script to run the scraper.
- `scrapers/`: Contains the core scraping logic.
  - `gem_scraper.py`: Scraper for the GeM bid website.
- `utils/`: Contains utility functions.
  - `driver_setup.py`: Handles Selenium WebDriver setup.
- `data/`: Directory to store the scraped data (e.g., CSV files).
- `requirements.txt`: Lists the Python dependencies for the project.

## Setup

1.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

To start scraping, run the `main.py` script from the root of the project directory:

```bash
python main.py
```

The scraped data will be saved as `gem_bids.csv` in the `data/` directory. You can configure the number of pages to scrape in `main.py`.
