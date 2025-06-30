# GeM Bid Scraper - Full Stack Application

This project is a full-stack web application for scraping bid information from the GeM (Government e-Marketplace) website. It consists of a Python backend that performs the scraping and a React frontend that provides a user-friendly interface.

## Project Structure

- `/backend`: Contains the Python Flask API, the Selenium scraper logic, and all related Python files.
- `/frontend`: Contains the React user interface.
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
