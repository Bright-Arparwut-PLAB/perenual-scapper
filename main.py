import logging
import asyncio
import argparse
import random
from playwright.async_api import async_playwright
import os
import tqdm
import pandas as pd

logging.basicConfig(level=logging.INFO)

async def extract_scientific_name(page) -> str:
    # Extract scientific name using the specific h2 classes
    try:
        scientific_name = await page.locator("h2.italic.main-t-c.my-2").inner_text()
        return scientific_name.strip()
    except Exception as e:
        logging.error(f"Error extraction scientific name: {e}")
        return ""

async def extract_plant_info(page) -> dict:
    info_data = {}
    info_block = page.locator("div.flex.gap-1.capitalize")   
    count = await info_block.count()
    
    for j in range(count):
        block = info_block.nth(j)
        try:
            label = await block.locator("h3").inner_text()
            value = await block.locator("p").inner_text()
            
            clean_label = label.replace(":", "").strip()
            clean_label = clean_label.replace(" ", "_").strip().lower()

            clean_value = value.replace("\n", "").strip()
            clean_value = clean_value.replace(" ", "_").strip().lower()
            
            info_data[clean_label] = clean_value
            # logging.info(f"{clean_label}: {clean_value}")
        except Exception as e:
            logging.error(f"Error extracting info block {j}: {e}")
            
    return info_data

async def extract_care_description(page) -> dict:
    """
    Extracts care description labels and values from the plant species page.

    Returns a dict with keys like 'watering', 'sunlight', 'pruning' and their
    corresponding description text as values.
    """
    care_data = {}
    try:
        # Each care block is contained in a rounded shadow div
        care_blocks = page.locator("div.rounded-md.shadow.p-3")
        count = await care_blocks.count()

        for i in range(count):
            block = care_blocks.nth(i)
            try:
                # Extract the label (h3 inside the flex container)
                label = await block.locator("div.flex.items-center.gap-2.capitalize.mb-2 > h3").inner_text()

                # Extract the value (p with the description text)
                value = await block.locator("p.line-clamp-2.whitespace-pre-wrap.break-words").inner_text()

                # Clean and normalize
                clean_label = label.strip().lower()
                clean_value = value.strip()

                care_data[clean_label] = clean_value
            except Exception as e:
                logging.warning(f"Could not extract care block {i}: {e}")
                continue

        return care_data
    except Exception as e:
        logging.error(f"Error extracting care description: {e}")
        return {}

async def main(start_page: int, end_page: int, min_delay: float = 2.0, max_delay: float = 5.0):
    """
    Main scraping function.

    Args:
        start_page: Starting species ID to scrape
        end_page: Ending species ID to scrape (exclusive)
        min_delay: Minimum delay between requests in seconds
        max_delay: Maximum delay between requests in seconds
    """
    output_dir = "data/species_raw"
    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        for i in tqdm.tqdm(range(start_page, end_page)):
            try:
                # Check if this page was already scraped (skip duplicates)
                file_path = f"{output_dir}/page_{i}.csv"
                if os.path.exists(file_path):
                    logging.info(f"Page {i} already scraped, skipping...")
                    continue

                data = pd.DataFrame()
                # data = pd.DataFrame(index=[i]) # Let's stick to their logic but maybe init with index to allow loc[i] assignment

                page = await context.new_page()
                await page.goto(f"https://perenual.com/plant-species-database-search-finder/species/{i}")
                logging.info(f"Page {i} opened")

                # Set the species ID
                data.loc[i, "id"] = str(i)

                # Extraction
                sci_name = await extract_scientific_name(page)
                data.loc[i, "scientific_name"] = sci_name
                logging.info(f"Scientific Name: {sci_name}")

                plant_info = await extract_plant_info(page)
                for k, v in plant_info.items():
                    data.loc[i, k] = v

                care_info = await extract_care_description(page)
                for k, v in care_info.items():
                    data.loc[i,k] = v

                # Save individually
                data.to_csv(file_path, index=False)
                logging.info(f"Saved page {i} to {file_path}")

                await page.close()

                # Random delay between requests to avoid IP blocking
                # This mimics human behavior - humans don't click at exact intervals
                delay = random.uniform(min_delay, max_delay)
                logging.info(f"Waiting {delay:.2f} seconds before next request...")
                await asyncio.sleep(delay)

            except Exception as e:
                logging.error(f"Failed to process page {i}: {e}")

        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape plant species data from Perenual.com",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Starting species ID to scrape"
    )
    parser.add_argument(
        "--end",
        type=int,
        required=True,
        help="Ending species ID to scrape (exclusive)"
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=2.0,
        help="Minimum delay between requests in seconds (for anti-blocking)"
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=5.0,
        help="Maximum delay between requests in seconds (for anti-blocking)"
    )

    args = parser.parse_args()

    if args.start >= args.end:
        logging.error("Error: --start must be less than --end")
        exit(1)

    if args.min_delay < 0 or args.max_delay < 0:
        logging.error("Error: delays must be non-negative")
        exit(1)

    if args.min_delay > args.max_delay:
        logging.error("Error: --min-delay must be less than or equal to --max-delay")
        exit(1)

    logging.info(f"Scraping species {args.start} to {args.end - 1}")
    logging.info(f"Random delays: {args.min_delay}-{args.max_delay} seconds between requests")

    asyncio.run(main(args.start, args.end, args.min_delay, args.max_delay))
