#!/usr/bin/env python3
"""
Wikipedia Swiss News Outlets Scraper

Scrapes the Wikipedia page for Swiss newspapers to extract outlet information
across German, French, Italian, and Romansch language sections.

Issue: https://github.com/devpouya/swissnews/issues/1
"""

import csv
import logging
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SwissNewsWikipediaScraper:
    def __init__(self):
        self.base_url = (
            "https://en.wikipedia.org/wiki/List_of_newspapers_in_Switzerland"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Swiss News Aggregator Research Bot (https://github.com/devpouya/swissnews)"
            }
        )
        self.outlets = []

    def fetch_page(self) -> BeautifulSoup:
        """Fetch and parse the Wikipedia page."""
        logger.info(f"Fetching Wikipedia page: {self.base_url}")

        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            logger.info("Successfully fetched Wikipedia page")
            return soup
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Wikipedia page: {e}")
            raise

    def parse_table(self, table, language: str) -> List[Dict]:
        """Parse a Wikipedia table to extract outlet information."""
        outlets = []
        rows = table.find_all("tr")

        if not rows:
            return outlets

        # Get header row to understand column structure
        header_row = rows[0]
        headers = [
            th.get_text().strip().lower() for th in header_row.find_all(["th", "td"])
        ]

        # Map common header variations to standard fields
        header_mapping = {
            "name": ["name", "newspaper", "publication"],
            "established": ["established", "founded", "year"],
            "owner": ["owner", "publisher"],
            "city": ["city", "location"],
            "canton": ["canton", "state"],
            "occurrence": ["occurrence", "frequency", "type"],
        }

        # Create column index mapping
        column_map = {}
        for std_field, variations in header_mapping.items():
            for i, header in enumerate(headers):
                if any(var in header for var in variations):
                    column_map[std_field] = i
                    break

        # Parse data rows
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:  # Skip rows with insufficient data
                continue

            outlet = {
                "news_website": "",
                "url": "",
                "original_language": language,
                "owner": "",
                "city": "",
                "canton": "",
                "occurrence": "",
            }

            # Extract name (always in first column typically)
            if cells:
                name_cell = cells[0]
                outlet["news_website"] = self.clean_text(name_cell.get_text())

            # Extract other fields based on column mapping
            for field, col_index in column_map.items():
                if col_index < len(cells) and field != "name":
                    if field == "owner":
                        outlet["owner"] = self.clean_text(cells[col_index].get_text())
                    elif field == "city":
                        outlet["city"] = self.clean_text(cells[col_index].get_text())
                    elif field == "canton":
                        outlet["canton"] = self.clean_text(cells[col_index].get_text())
                    elif field == "occurrence":
                        outlet["occurrence"] = self.clean_text(
                            cells[col_index].get_text()
                        )

            # Skip if no meaningful name
            if outlet["news_website"] and len(outlet["news_website"]) > 1:
                outlets.append(outlet)

        return outlets

    def clean_text(self, text: str) -> str:
        """Clean and normalize text extracted from Wikipedia."""
        if not text:
            return ""

        # Remove citations like [1], [2], etc.
        text = re.sub(r"\[\d+\]", "", text)

        # Remove extra whitespace
        text = " ".join(text.split())

        # Remove common Wikipedia artifacts
        text = text.replace("†", "").replace("‡", "")

        return text.strip()

    def scrape_all_languages(self) -> List[Dict]:
        """Scrape outlets from all language sections."""
        logger.info("Starting comprehensive scraping of all language sections")

        soup = self.fetch_page()
        all_outlets = []

        # Based on the actual Wikipedia structure, tables are organized as:
        # Table 0: German current, Table 1: French current, Table 2: Italian current,
        # Table 3: Romansch current, Table 4: Other languages current
        # Table 5: German defunct, Table 6: French defunct, Table 7: Italian defunct,
        # Table 8: Romansch defunct, Table 9: Other languages defunct

        tables = soup.find_all("table", {"class": "wikitable"})

        table_language_map = [
            (0, "German", "current"),
            (1, "French", "current"),
            (2, "Italian", "current"),
            (3, "Romansch", "current"),
            (4, "Other", "current"),
            (5, "German", "defunct"),
            (6, "French", "defunct"),
            (7, "Italian", "defunct"),
            (8, "Romansch", "defunct"),
            (9, "Other", "defunct"),
        ]

        for table_idx, language, status in table_language_map:
            if table_idx < len(tables):
                try:
                    logger.info(
                        f"Processing table {table_idx}: {language} {status} outlets"
                    )
                    outlets = self.parse_table(tables[table_idx], language)

                    # Add status information to each outlet
                    for outlet in outlets:
                        outlet["status"] = status

                    all_outlets.extend(outlets)

                    logger.info(f"Found {len(outlets)} {language} {status} outlets")

                except Exception as e:
                    logger.error(
                        f"Error processing table {table_idx} ({language} {status}): {e}"
                    )
                    continue
            else:
                logger.warning(
                    f"Table {table_idx} not found (expected {language} {status})"
                )

        logger.info(f"Total outlets scraped: {len(all_outlets)}")
        self.outlets = all_outlets
        return all_outlets

    def save_to_csv(self, filename: str) -> None:
        """Save scraped outlets to CSV file."""
        logger.info(f"Saving {len(self.outlets)} outlets to {filename}")

        if not self.outlets:
            logger.warning("No outlets to save")
            return

        fieldnames = [
            "news_website",
            "url",
            "original_language",
            "owner",
            "city",
            "canton",
            "occurrence",
            "status",
        ]

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.outlets)

        logger.info(f"Successfully saved outlets to {filename}")

    def print_summary(self) -> None:
        """Print a summary of scraped data."""
        if not self.outlets:
            print("No outlets scraped")
            return

        print(f"\n=== SCRAPING SUMMARY ===")
        print(f"Total outlets: {len(self.outlets)}")

        # Language breakdown
        language_counts = {}
        for outlet in self.outlets:
            lang = outlet["original_language"]
            language_counts[lang] = language_counts.get(lang, 0) + 1

        print("\nBy language:")
        for lang, count in sorted(language_counts.items()):
            print(f"  {lang}: {count}")

        print("\nSample outlets:")
        for i, outlet in enumerate(self.outlets[:5]):
            print(f"  {i+1}. {outlet['news_website']} ({outlet['original_language']})")
            if outlet["city"]:
                print(f"     Location: {outlet['city']}")
            if outlet["owner"]:
                print(f"     Owner: {outlet['owner']}")


def main():
    """Main execution function."""
    scraper = SwissNewsWikipediaScraper()

    try:
        # Scrape all outlets
        outlets = scraper.scrape_all_languages()

        # Save to CSV
        output_file = "../../data/raw/swiss_news_outlets_raw.csv"
        scraper.save_to_csv(output_file)

        # Print summary
        scraper.print_summary()

        print(f"\n✅ Scraping completed successfully!")
        print(f"📁 Raw data saved to: {output_file}")
        print(f"📊 Next step: Research actual website URLs for each outlet")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print(f"❌ Scraping failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
