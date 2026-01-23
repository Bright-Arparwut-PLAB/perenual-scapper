import logging
import asyncio
import argparse
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import os
import tqdm
import pandas as pd

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    level=logging.INFO)

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
    info_block =  page.locator("div.flex.gap-1.capitalize")   
    count = await info_block.count()
    
    for j in range(count):
        block = info_block.nth(j)
        try:
            label = await block.locator("h3").inner_text()
            value = await block.locator("p").inner_text()
            
            clean_label = str(label).replace(":", "").strip()
            clean_label = str(clean_label).replace(" ", "_").strip().lower()

            clean_value = str(value).replace("\n", "").strip()
            clean_value = str(clean_value).replace(" ", "_").strip().lower()
            
            info_data[clean_label] = clean_value
            logging.info(f"{clean_label}: {clean_value}")
        except Exception as e:
            logging.error(f"Error extracting info block {j}: {e}")
            
    return info_data

async def extract_care_description(page) -> dict:
    """
    Extracts care description labels and values from the plant species page.

    Returns a dict with keys like 'watering', 'sunlight', 'pruning' and their
    corresponding description text as values.

    Improved version:
    - More robust by finding parent containers first
    - Validates label-value pairing
    - Better error handling for individual blocks
    - Prevents misalignment if DOM structure changes
    """
    care_data = {}
    try:
        # Find parent containers that hold both label and value together
        # This is more robust than selecting labels and values separately
        label_block = page.locator("div.col-span-3.flex.flex-col.space-y-4").locator("h3.font-bold.text-xl.capitalize")
        value_block = page.locator("div.col-span-3.flex.flex-col.space-y-4").locator("p.line-clamp-2.whitespace-pre-wrap.break-words")
        
        if await label_block.count() != await value_block.count():
            logging.info("No care description sections found")
            return care_data
        
        logging.info(f"Found {await label_block.count()} care description blocks")
    
        for i in range(await label_block.count()):
            try:
                label = await label_block.nth(i).inner_text()
                value = await value_block.nth(i).inner_text()
                
                clean_label = str(label).strip().lower().replace(":", "")
                clean_value = str(value).strip().replace("\n", " ").strip().lower()
                
                if clean_label and clean_value:
                    care_data[clean_label] = clean_value
                    logging.info(f"Extracted: {clean_label}: {clean_value}")
                else:
                    logging.warning(f"Empty label or value for section {i}")
        
            except Exception as e:
                logging.warning(f"Failed to extract care description block {i}: {e}")
                # Continue with next block instead of failing entire function
                continue
        
        return care_data
    except Exception as e:
        logging.error(f"Error in extract_care_description: {e}")
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

    async with Stealth().use_async(async_playwright()) as p:
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
                try:
                    sci_name = await extract_scientific_name(page)
                    data.loc[i, "scientific_name"] = sci_name
                    logging.info(f"Scientific Name: {sci_name}")
                except Exception as e:
                    logging.error(f"Error extracting scientific name: {e}")

                try:
                    plant_info = await extract_plant_info(page)
                    for k, v in plant_info.items():
                        data.loc[i, k] = v
                except Exception as e:
                    logging.error(f"Error extracting plant info: {e}")

                try:
                    care_info = await extract_care_description(page)
                    for k, v in care_info.items():
                        data.loc[i,k] = v
                except Exception as e:
                    logging.error(f"Error extracting care info: {e}")

                # Save individually
                data.to_csv(file_path, index=False, encoding="utf-8")
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
