# Perenual Scraper

## Project Overview
`perenual_scapper` is a Python-based web scraping tool designed to extract plant species data from the Perenual database (`perenual.com`). It utilizes `playwright` for asynchronous web navigation and extraction, and `pandas` for data structuring and storage.

The project operates in two stages:
1.  **Scraping**: Iterates through species pages, extracts details (scientific name, plant attributes), and saves individual CSV files.
2.  **Merging**: Aggregates all individual CSV files into a comprehensive dataset (`perenual_data.csv`).

## Key Files

### Source Code
-   **`main.py`**: The core scraper script.
    -   Uses `async_playwright` to launch a Chromium browser.
    -   Iterates through a range of pages (controlled by `start_page` and `end_page` globals).
    -   Extracts scientific names and key-value pairs from the plant info block.
    -   Saves each page's data to `data/species_raw/page_{i}.csv`.
-   **`merge_data.py`**: A utility script to consolidate data.
    -   Reads all CSVs from `data/species_raw/`.
    -   Standardizes columns (union of all found schemas).
    -   Appends data to `data/perenual_data.csv`.

### Configuration
-   **`pyproject.toml`**: Python project configuration. Managed by `uv`.
-   **`uv.lock`**: Lock file for exact dependency versions.

### Data
-   **`data/species_raw/`**: Directory containing raw, per-page CSV files.
-   **`data/perenual_data.csv`**: The final merged dataset.

## Building and Running

### Prerequisites
-   Python 3.11+
-   `uv` package manager (recommended) or standard `pip`.

### Setup
If using `uv`:
```bash
uv sync
```
*Note: If dependencies are missing in `pyproject.toml`, you may need to install them manually: `uv add playwright pandas tqdm` followed by `uv run playwright install`.*

### Usage

1.  **Run the Scraper:**
    Modify `start_page` and `end_page` in `main.py` to set the scraping range.
    ```bash
    uv run main.py
    ```

2.  **Merge Data:**
    After scraping is complete, combine the raw files:
    ```bash
    uv run merge_data.py
    ```

## Development Conventions

-   **Asynchronous I/O**: The scraper uses `asyncio` and `playwright`'s async API for efficiency.
-   **Error Handling**: Individual page failures are caught and logged, preventing the entire batch from crashing.
-   **Data Storage**: Data is saved incrementally (per page) to avoid data loss during long scraping sessions.
-   **Logging**: Basic `logging` configuration is used to track progress and errors.
