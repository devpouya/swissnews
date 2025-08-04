#!/usr/bin/env python3
"""
Debug script to examine Wikipedia page structure
"""

import requests
from bs4 import BeautifulSoup


def debug_wikipedia_structure():
    """Debug the actual structure of the Wikipedia page."""
    url = "https://en.wikipedia.org/wiki/List_of_newspapers_in_Switzerland"

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    print("=== ALL SPAN ELEMENTS WITH IDs ===")
    spans_with_ids = soup.find_all("span", {"id": True})
    for span in spans_with_ids:
        print(f"ID: '{span.get('id')}' - Text: '{span.get_text().strip()}'")

    print("\n=== ALL H2/H3 HEADERS ===")
    headers = soup.find_all(["h2", "h3"])
    for header in headers:
        span = header.find("span", {"id": True})
        if span:
            print(
                f"Header: {header.name} - ID: '{span.get('id')}' - Text: '{span.get_text().strip()}'"
            )

    print("\n=== ALL TABLES WITH CONTEXT ===")
    tables = soup.find_all("table")
    for i, table in enumerate(tables):
        if "wikitable" in table.get("class", []):
            print(f"\nTable {i}: wikitable found")

            # Get table headers to understand content
            header_row = table.find("tr")
            if header_row:
                headers = [
                    th.get_text().strip() for th in header_row.find_all(["th", "td"])
                ]
                print(f"  Headers: {headers}")

            # Look for preceding text/headers
            prev_element = table
            context_elements = []
            for j in range(10):  # Look at previous 10 elements
                prev_element = prev_element.previous_sibling
                if not prev_element:
                    break
                if prev_element.name:
                    if prev_element.name in ["h2", "h3", "h4"]:
                        text = prev_element.get_text().strip()
                        if text:
                            context_elements.append(f"{prev_element.name}: {text}")
                    elif prev_element.name == "p":
                        text = prev_element.get_text().strip()
                        if text and len(text) < 200:  # Short paragraphs only
                            context_elements.append(f"p: {text}")

            if context_elements:
                print(f"  Preceding context:")
                for elem in reversed(
                    context_elements[-3:]
                ):  # Show last 3 context elements
                    print(f"    {elem}")

            # Show first few data rows
            data_rows = table.find_all("tr")[1:3]  # Skip header, get first 2 data rows
            for row_idx, row in enumerate(data_rows):
                cells = [td.get_text().strip() for td in row.find_all(["td", "th"])]
                if cells and any(cell for cell in cells):  # Only show non-empty rows
                    print(
                        f"  Sample row {row_idx + 1}: {cells[:3]}..."
                    )  # First 3 columns


if __name__ == "__main__":
    debug_wikipedia_structure()
