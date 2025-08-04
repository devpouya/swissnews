#!/usr/bin/env python3
"""
Quick URL Research for Major Swiss News Outlets

Focus on major current outlets with known URLs first.
"""

import csv
import logging
from typing import Dict

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def quick_url_research():
    """Research URLs for major Swiss outlets quickly."""

    # Major Swiss outlets with their known URLs
    known_urls = {
        "20 minuten": "https://www.20min.ch",
        "blick": "https://www.blick.ch",
        "neue zürcher zeitung": "https://www.nzz.ch",
        "tages-anzeiger": "https://www.tagesanzeiger.ch",
        "basler zeitung (baz)": "https://www.bazonline.ch",
        "aargauer zeitung": "https://www.aargauerzeitung.ch",
        "berner zeitung": "https://www.bernerzeitung.ch",
        "der bund": "https://www.derbund.ch",
        "luzerner zeitung": "https://www.luzernerzeitung.ch",
        "st. galler tagblatt": "https://www.tagblatt.ch",
        "thurgauer zeitung": "https://www.thurgauerzeitung.ch",
        "südostschweiz": "https://www.suedostschweiz.ch",
        "handelszeitung": "https://www.handelszeitung.ch",
        "finanz und wirtschaft [de]": "https://www.fuw.ch",
        "limmattaler zeitung": "https://www.limmattalerzeitung.ch",
        "nidwaldner zeitung": "https://www.nidwaldnerzeitung.ch",
        "obwaldner zeitung": "https://www.obwaldnerzeitung.ch",
        "schwyzer zeitung": "https://www.schwyzerzeitung.ch",
        "urner zeitung": "https://www.urnerzeitung.ch",
        "walliser bote": "https://www.walliserbote.ch",
        "zuger zeitung": "https://www.zugerzeitung.ch",
        "zürichsee-zeitung": "https://www.zsz.ch",
        # French outlets
        "le temps": "https://www.letemps.ch",
        "24 heures": "https://www.24heures.ch",
        "la tribune de genève": "https://www.tdg.ch",
        "le matin": "https://www.lematin.ch",
        "le nouvelliste": "https://www.lenouvelliste.ch",
        "l'essentiel": "https://www.lessentiel.lu",
        "l'express": "https://www.lexpress.ch",
        "l'impartial": "https://www.limpartial.ch",
        "journal du jura": "https://www.journaldujura.ch",
        "quotidien jurassien": "https://www.qj.ch",
        # Italian outlets
        "corriere del ticino": "https://www.cdt.ch",
        "la regione": "https://www.laregione.ch",
        "giornale del popolo": "https://www.gdp.ch",
        # Romansch outlets
        "la quotidiana": "https://www.laquotidiana.ch",
        # Other common variations
        "basellandschaftliche zeitung (bz)": "https://www.bzbasel.ch",
        "appenzeller zeitung [de]": "https://www.appenzellerzeitung.ch",
        "bieler tagblatt": "https://www.bielertagblatt.ch",
        "freiburger nachrichten [de]": "https://www.freiburger-nachrichten.ch",
    }

    input_file = "../../data/raw/swiss_news_outlets_raw.csv"
    output_file = "../../data/processed/swiss_news_outlets_with_urls.csv"

    logger.info("Loading outlets from CSV")
    outlets = []
    with open(input_file, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        outlets = list(reader)

    current_outlets = [o for o in outlets if o["status"] == "current"]
    logger.info(f"Found {len(current_outlets)} current outlets")

    # Match outlets with known URLs
    found_count = 0
    for outlet in current_outlets:
        name = outlet["news_website"].lower().strip()

        if name in known_urls:
            outlet["url"] = known_urls[name]
            found_count += 1
            logger.info(f"✅ Matched: {outlet['news_website']} -> {known_urls[name]}")
        else:
            logger.debug(f"❌ No match for: {outlet['news_website']}")

    # Save results
    logger.info(f"Saving results to {output_file}")
    with open(output_file, "w", newline="", encoding="utf-8") as file:
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
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(outlets)

    logger.info(
        f"✅ Quick research completed: {found_count}/{len(current_outlets)} URLs found"
    )

    # Show summary by language
    print(f"\n=== QUICK URL RESEARCH SUMMARY ===")
    print(f"Total current outlets: {len(current_outlets)}")
    print(f"URLs found: {found_count}")
    print(f"Success rate: {found_count/len(current_outlets)*100:.1f}%")

    # Show found URLs by language
    print(f"\nFound URLs by language:")
    for lang in ["German", "French", "Italian", "Romansch"]:
        lang_outlets = [o for o in current_outlets if o["original_language"] == lang]
        lang_found = [o for o in lang_outlets if o["url"]]
        if lang_outlets:
            print(f"  {lang}: {len(lang_found)}/{len(lang_outlets)} outlets")

    print(f"\nSample found outlets:")
    found_outlets = [o for o in current_outlets if o["url"]][:10]
    for outlet in found_outlets:
        print(f"  {outlet['news_website']}: {outlet['url']}")

    return found_count, len(current_outlets)


if __name__ == "__main__":
    try:
        found, total = quick_url_research()
        print(f"\n🎯 Quick research completed: {found}/{total} URLs found")
    except Exception as e:
        logger.error(f"Research failed: {e}")
        print(f"❌ Research failed: {e}")
