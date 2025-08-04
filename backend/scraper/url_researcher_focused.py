#!/usr/bin/env python3
"""
Focused URL Researcher for Current Swiss News Outlets

Researches website URLs for current Swiss outlets and updates the CSV file.
Focus on major outlets first, then expand to smaller ones.
"""

import csv
import requests
import time
import logging
from typing import List, Dict, Optional, Tuple
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FocusedURLResearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Swiss News Research) AppleWebKit/537.36'
        })
        
        # Known major Swiss outlets (manually curated for accuracy)
        self.known_outlets = {
            '20 minuten': 'https://www.20min.ch',
            'blick': 'https://www.blick.ch', 
            'neue zürcher zeitung': 'https://www.nzz.ch',
            'tages-anzeiger': 'https://www.tagesanzeiger.ch',
            'basler zeitung': 'https://www.bazonline.ch',
            'aargauer zeitung': 'https://www.aargauerzeitung.ch',
            'berner zeitung': 'https://www.bernerzeitung.ch',
            'bieler tagblatt': 'https://www.bielertagblatt.ch',
            'südostschweiz': 'https://www.suedostschweiz.ch',
            'st. galler tagblatt': 'https://www.tagblatt.ch',
            'thurgauer zeitung': 'https://www.thurgauerzeitung.ch',
            'luzerner zeitung': 'https://www.luzernerzeitung.ch',
            'walliser bote': 'https://www.walliserbote.ch',
            'le temps': 'https://www.letemps.ch',
            '24 heures': 'https://www.24heures.ch',
            'la tribune de genève': 'https://www.tdg.ch',
            'le matin': 'https://www.lematin.ch',
            'corriere del ticino': 'https://www.cdt.ch',
            'la regione': 'https://www.laregione.ch',
            'giornale del popolo': 'https://www.gdp.ch',
            'la quotidiana': 'https://www.laquotidiana.ch',
            # Common alternative names
            'baz': 'https://www.bazonline.ch',
            'nzz': 'https://www.nzz.ch',
            'tagi': 'https://www.tagesanzeiger.ch',
            'az': 'https://www.aargauerzeitung.ch',
            'bz': 'https://www.bernerzeitung.ch',
            'tdg': 'https://www.tdg.ch',
            'cdt': 'https://www.cdt.ch'
        }

    def normalize_name(self, name: str) -> str:
        """Normalize outlet name for matching."""
        name = name.lower().strip()
        # Remove common patterns
        name = re.sub(r'\[.*?\]', '', name)  # Remove [de], [fr] etc.
        name = re.sub(r'\(.*?\)', '', name)  # Remove (bz), (BaZ) etc.
        name = name.strip()
        return name

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate if URL is accessible and appears to be news website."""
        try:
            response = self.session.get(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return True, response.url
            return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def generate_url_candidates(self, name: str) -> List[str]:
        """Generate potential URLs for an outlet."""
        clean_name = self.normalize_name(name)
        
        # Check known outlets first
        if clean_name in self.known_outlets:
            return [self.known_outlets[clean_name]]
            
        candidates = []
        
        # Clean for domain generation
        domain_name = re.sub(r'[^a-zA-Z0-9\s]', '', clean_name)
        domain_name = re.sub(r'\s+', '', domain_name)
        
        if len(domain_name) > 2:
            candidates.extend([
                f"https://www.{domain_name}.ch",
                f"https://{domain_name}.ch",
                f"https://www.{domain_name.replace(' ', '')}.ch",
                f"https://www.{domain_name.replace(' ', '-')}.ch"
            ])
            
        return candidates[:5]  # Limit candidates

    def research_urls(self, input_csv: str, output_csv: str):
        """Research URLs for all current outlets."""
        logger.info("Starting URL research for current outlets")
        
        outlets = []
        with open(input_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            outlets = list(reader)
            
        current_outlets = [o for o in outlets if o['status'] == 'current']
        logger.info(f"Found {len(current_outlets)} current outlets to research")
        
        found_count = 0
        
        for i, outlet in enumerate(current_outlets):
            name = outlet['news_website']
            logger.info(f"[{i+1}/{len(current_outlets)}] Researching: {name}")
            
            candidates = self.generate_url_candidates(name)
            
            url_found = False
            for candidate in candidates:
                is_valid, result = self.validate_url(candidate)
                if is_valid:
                    outlet['url'] = result
                    logger.info(f"✅ Found: {result}")
                    found_count += 1
                    url_found = True
                    break
                time.sleep(0.5)  # Small delay between attempts
                
            if not url_found:
                logger.warning(f"❌ No URL found for: {name}")
                
            # Respectful delay between outlets
            time.sleep(1)
            
            # Progress update every 10 outlets
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {found_count}/{i+1} URLs found")
        
        # Save updated results
        logger.info(f"Saving results to {output_csv}")
        with open(output_csv, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['news_website', 'url', 'original_language', 'owner', 'city', 'canton', 'occurrence', 'status']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(outlets)
            
        logger.info(f"✅ URL research completed: {found_count}/{len(current_outlets)} URLs found")
        return found_count, len(current_outlets)


if __name__ == "__main__":
    researcher = FocusedURLResearcher()
    
    input_file = "../../data/raw/swiss_news_outlets_raw.csv"  
    output_file = "../../data/processed/swiss_news_outlets_with_urls.csv"
    
    try:
        found, total = researcher.research_urls(input_file, output_file)
        print(f"\n🎯 Results: Found {found}/{total} URLs ({found/total*100:.1f}% success rate)")
        print(f"📁 Updated data saved to: {output_file}")
    except Exception as e:
        logger.error(f"Research failed: {e}")
        print(f"❌ Research failed: {e}")