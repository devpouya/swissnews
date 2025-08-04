#!/usr/bin/env python3
"""
Swiss News Outlets URL Researcher

Researches and validates website URLs for Swiss news outlets extracted from Wikipedia.
Focuses on current outlets first for the comprehensive database.

Issue: https://github.com/devpouya/swissnews/issues/1
"""

import csv
import requests
import time
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin
import re
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Outlet:
    name: str
    language: str
    owner: str
    city: str
    canton: str
    occurrence: str
    status: str
    url: str = ""
    url_status: str = "pending"  # pending, found, not_found, invalid

class SwissNewsURLResearcher:
    def __init__(self, input_csv: str):
        self.input_csv = input_csv
        self.outlets: List[Outlet] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Swiss News Aggregator Research Bot https://github.com/devpouya/swissnews'
        })
        # Common URL patterns for Swiss news outlets
        self.common_domains = [
            '.ch', '.li'  # Swiss and Liechtenstein domains
        ]
        
    def load_outlets(self) -> None:
        """Load outlets from the CSV file."""
        logger.info(f"Loading outlets from {self.input_csv}")
        
        with open(self.input_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                outlet = Outlet(
                    name=row['news_website'].strip(),
                    language=row['original_language'].strip(),
                    owner=row['owner'].strip(),
                    city=row['city'].strip(),
                    canton=row['canton'].strip(),
                    occurrence=row['occurrence'].strip(),
                    status=row['status'].strip(),
                    url=row.get('url', '').strip()
                )
                self.outlets.append(outlet)
                
        logger.info(f"Loaded {len(self.outlets)} outlets")
        
        # Show breakdown
        current_outlets = [o for o in self.outlets if o.status == 'current']
        logger.info(f"Current outlets: {len(current_outlets)}")
        
        lang_breakdown = {}
        for outlet in current_outlets:
            lang_breakdown[outlet.language] = lang_breakdown.get(outlet.language, 0) + 1
        
        for lang, count in sorted(lang_breakdown.items()):
            logger.info(f"  {lang}: {count} current outlets")

    def generate_url_candidates(self, outlet: Outlet) -> List[str]:
        """Generate potential URL candidates for an outlet."""
        candidates = []
        name = outlet.name.lower()
        
        # Clean the name for URL generation
        # Remove common patterns
        name = re.sub(r'\[.*?\]', '', name)  # Remove [de], [fr] etc.
        name = re.sub(r'\(.*?\)', '', name)  # Remove (bz), (BaZ) etc.
        name = name.strip()
        
        # Replace spaces and special characters
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        clean_name = re.sub(r'\s+', '', clean_name)
        
        # Generate domain candidates
        domain_bases = [
            clean_name.lower(),
            clean_name.lower().replace(' ', ''),
            clean_name.lower().replace(' ', '-'),
            ''.join([word[0] for word in clean_name.split()]),  # Acronym
        ]
        
        # Remove duplicates and empty strings
        domain_bases = list(set([d for d in domain_bases if d and len(d) > 1]))
        
        # Generate full URLs
        for base in domain_bases:
            candidates.extend([
                f"https://www.{base}.ch",
                f"https://{base}.ch",
                f"https://www.{base}.li",  # Some Swiss outlets use .li
                f"https://{base}.li"
            ])
            
        # Known major Swiss outlets (manual additions for high-priority outlets)
        known_mappings = {
            '20 minuten': 'https://www.20min.ch',
            'blick': 'https://www.blick.ch',
            'neue zürcher zeitung': 'https://www.nzz.ch',
            'tages-anzeiger': 'https://www.tagesanzeiger.ch',
            'basler zeitung': 'https://www.bazonline.ch',
            'aargauer zeitung': 'https://www.aargauerzeitung.ch',
            'berner zeitung': 'https://www.bernerzeitung.ch',
            'le temps': 'https://www.letemps.ch',
            '24 heures': 'https://www.24heures.ch',
            'la tribune de genève': 'https://www.tdg.ch',
            'corriere del ticino': 'https://www.cdt.ch',
            'la quotidiana': 'https://www.laquotidiana.ch'
        }
        
        outlet_name_lower = outlet.name.lower().strip()
        if outlet_name_lower in known_mappings:
            candidates.insert(0, known_mappings[outlet_name_lower])
            
        return candidates[:10]  # Limit to top 10 candidates

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate if a URL is accessible and appears to be a news website."""
        try:
            logger.debug(f"Validating URL: {url}")
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                # Basic checks for news website content
                content = response.text.lower()
                news_indicators = [
                    'news', 'artikel', 'article', 'nachrichten', 'actualités',
                    'notizie', 'journal', 'zeitung', 'gazette', 'times',
                    'media', 'press', 'newspaper'
                ]
                
                if any(indicator in content for indicator in news_indicators):
                    final_url = response.url
                    logger.info(f"✅ Valid URL found: {final_url}")
                    return True, final_url
                else:
                    logger.debug(f"❌ URL exists but doesn't appear to be news site: {url}")
                    return False, "Not a news website"
            else:
                logger.debug(f"❌ URL returned status {response.status_code}: {url}")
                return False, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            logger.debug(f"⏰ Timeout for URL: {url}")
            return False, "Timeout"
        except requests.exceptions.ConnectionError:
            logger.debug(f"🔌 Connection error for URL: {url}")
            return False, "Connection error"
        except Exception as e:
            logger.debug(f"❌ Error validating URL {url}: {str(e)}")
            return False, f"Error: {str(e)}"

    def research_outlet_url(self, outlet: Outlet) -> bool:
        """Research and find a valid URL for a specific outlet."""
        logger.info(f"Researching URL for: {outlet.name} ({outlet.language})")
        
        candidates = self.generate_url_candidates(outlet)
        logger.debug(f"Generated {len(candidates)} URL candidates")
        
        for i, candidate in enumerate(candidates):
            is_valid, result = self.validate_url(candidate)
            
            if is_valid:
                outlet.url = result
                outlet.url_status = "found"
                logger.info(f"🎉 Found URL for {outlet.name}: {result}")
                return True
                
            # Be respectful with delays
            if i < len(candidates) - 1:
                time.sleep(1)
        
        outlet.url_status = "not_found"
        logger.warning(f"❌ Could not find URL for: {outlet.name}")
        return False

    def research_all_current_outlets(self) -> None:
        """Research URLs for all current outlets."""
        current_outlets = [o for o in self.outlets if o.status == 'current']
        logger.info(f"Starting URL research for {len(current_outlets)} current outlets")
        
        found_count = 0
        
        for i, outlet in enumerate(current_outlets):
            logger.info(f"Progress: {i+1}/{len(current_outlets)}")
            
            if self.research_outlet_url(outlet):
                found_count += 1
                
            # Respectful delay between outlets
            time.sleep(2)
            
            # Progress checkpoint every 10 outlets
            if (i + 1) % 10 == 0:
                logger.info(f"Checkpoint: Found URLs for {found_count}/{i+1} outlets")
                
        logger.info(f"🎯 URL research completed: {found_count}/{len(current_outlets)} URLs found")

    def save_results(self, output_csv: str) -> None:
        """Save the research results to a new CSV file."""
        logger.info(f"Saving results to {output_csv}")
        
        fieldnames = ['news_website', 'url', 'original_language', 'owner', 'city', 'canton', 'occurrence', 'status', 'url_status']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            
            for outlet in self.outlets:
                writer.writerow({
                    'news_website': outlet.name,
                    'url': outlet.url,
                    'original_language': outlet.language,
                    'owner': outlet.owner,
                    'city': outlet.city,
                    'canton': outlet.canton,
                    'occurrence': outlet.occurrence,
                    'status': outlet.status,
                    'url_status': outlet.url_status
                })
                
        logger.info(f"Results saved to {output_csv}")

    def print_summary(self) -> None:
        """Print a summary of the URL research results."""
        current_outlets = [o for o in self.outlets if o.status == 'current']
        found_urls = [o for o in current_outlets if o.url_status == 'found']
        
        print(f"\n=== URL RESEARCH SUMMARY ===")
        print(f"Total current outlets: {len(current_outlets)}")
        print(f"URLs found: {len(found_urls)}")
        print(f"Success rate: {len(found_urls)/len(current_outlets)*100:.1f}%")
        
        print(f"\nBy language:")
        for lang in ['German', 'French', 'Italian', 'Romansch']:
            lang_outlets = [o for o in current_outlets if o.language == lang]
            lang_found = [o for o in lang_outlets if o.url_status == 'found']
            if lang_outlets:
                print(f"  {lang}: {len(lang_found)}/{len(lang_outlets)} ({len(lang_found)/len(lang_outlets)*100:.1f}%)")
                
        print(f"\nSample found URLs:")
        for outlet in found_urls[:10]:
            print(f"  {outlet.name}: {outlet.url}")


def main():
    """Main execution function."""
    input_file = "../../data/raw/swiss_news_outlets_raw.csv"
    output_file = "../../data/processed/swiss_news_outlets_with_urls.csv"
    
    researcher = SwissNewsURLResearcher(input_file)
    
    try:
        # Load the scraped outlets
        researcher.load_outlets()
        
        # Research URLs for current outlets
        researcher.research_all_current_outlets()
        
        # Save results
        researcher.save_results(output_file)
        
        # Print summary
        researcher.print_summary()
        
        print(f"\n✅ URL research completed!")
        print(f"📁 Results saved to: {output_file}")
        print(f"📊 Next step: Create final swiss_news_outlets.csv with proper schema")
        
    except Exception as e:
        logger.error(f"URL research failed: {e}")
        print(f"❌ URL research failed: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())