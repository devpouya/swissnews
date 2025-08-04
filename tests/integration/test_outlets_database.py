#!/usr/bin/env python3
"""
Integration tests for Swiss News Outlets Database

Tests the complete workflow from Wikipedia scraping to final CSV creation.
"""

import unittest
import os
import csv
from pathlib import Path

class TestSwissOutletsDatabase(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / 'data'
        self.final_csv = self.data_dir / 'swiss_news_outlets.csv'
        
    def test_final_csv_exists(self):
        """Test that the final CSV file exists."""
        self.assertTrue(self.final_csv.exists(), 
                       f"Final CSV file does not exist at {self.final_csv}")
    
    def test_csv_schema(self):
        """Test that the CSV has the correct schema."""
        expected_headers = [
            'news_website', 'url', 'original_language', 
            'owner', 'city', 'canton', 'occurrence'
        ]
        
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)
            
        self.assertEqual(headers, expected_headers,
                        f"CSV headers {headers} don't match expected {expected_headers}")
    
    def test_minimum_outlets(self):
        """Test that we have minimum 20+ outlets as required."""
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            outlets = list(reader)
            
        self.assertGreaterEqual(len(outlets), 20,
                               f"Need minimum 20 outlets, found {len(outlets)}")
    
    def test_all_languages_represented(self):
        """Test that all 4 Swiss languages are represented."""
        expected_languages = {'German', 'French', 'Italian', 'Romansch'}
        
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            languages = {row['original_language'] for row in reader}
            
        missing_languages = expected_languages - languages
        self.assertEqual(len(missing_languages), 0,
                        f"Missing languages: {missing_languages}")
    
    def test_all_outlets_have_urls(self):
        """Test that all outlets have valid URLs."""
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for i, row in enumerate(reader):
                url = row['url']
                self.assertTrue(url.startswith(('http://', 'https://')),
                               f"Row {i+1}: Invalid URL format: {url}")
                self.assertTrue(url.strip(), 
                               f"Row {i+1}: Empty URL for outlet {row['news_website']}")
    
    def test_no_empty_outlet_names(self):
        """Test that all outlets have names."""
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for i, row in enumerate(reader):
                name = row['news_website']
                self.assertTrue(name.strip(),
                               f"Row {i+1}: Empty outlet name")
                self.assertGreater(len(name.strip()), 2,
                                  f"Row {i+1}: Outlet name too short: '{name}'")
    
    def test_swiss_domains(self):
        """Test that most URLs use Swiss domains (.ch) or are legitimate news sites."""
        swiss_domains = ['.ch', '.li']  # Swiss and Liechtenstein
        legitimate_exceptions = ['blick.ch']  # Known legitimate non-.ch Swiss outlets
        
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            non_swiss_urls = []
            
            for row in reader:
                url = row['url']
                is_swiss_domain = any(domain in url for domain in swiss_domains)
                is_legitimate = any(exception in url for exception in legitimate_exceptions)
                
                if not (is_swiss_domain or is_legitimate):
                    non_swiss_urls.append((row['news_website'], url))
        
        # Allow some non-.ch domains but flag for review
        self.assertLess(len(non_swiss_urls), 5,
                       f"Too many non-Swiss domains: {non_swiss_urls}")
    
    def test_major_outlets_included(self):
        """Test that major Swiss outlets are included."""
        major_outlets = {
            '20 Minuten', 'Blick', 'Neue Zürcher Zeitung', 'Tages-Anzeiger',
            'Le Temps', '24 heures', 'Corriere del Ticino'
        }
        
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            outlet_names = {row['news_website'] for row in reader}
        
        missing_major = major_outlets - outlet_names
        # Allow some flexibility - not all major outlets may have been found
        self.assertLess(len(missing_major), 3,
                       f"Too many major outlets missing: {missing_major}")
    
    def test_data_quality(self):
        """Test general data quality."""
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            occurrence_values = set()
            
            for i, row in enumerate(reader):
                # Test that required fields are not empty
                self.assertTrue(row['news_website'].strip(),
                               f"Row {i+1}: Empty news_website")
                self.assertTrue(row['url'].strip(),
                               f"Row {i+1}: Empty url")
                self.assertTrue(row['original_language'].strip(),
                               f"Row {i+1}: Empty original_language")
                
                # Collect occurrence values for validation
                if row['occurrence'].strip():
                    occurrence_values.add(row['occurrence'])
        
        # Check that occurrence values make sense
        valid_occurrences = {'Daily', 'Weekly', 'Monthly', 'Bi-weekly', 'Quarterly'}
        invalid_occurrences = occurrence_values - valid_occurrences
        
        # Allow some flexibility in naming
        self.assertLess(len(invalid_occurrences), len(occurrence_values) * 0.3,
                       f"Too many invalid occurrence values: {invalid_occurrences}")
    
    def test_language_distribution(self):
        """Test that language distribution makes sense for Switzerland."""
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            language_counts = {}
            
            for row in reader:
                lang = row['original_language']
                language_counts[lang] = language_counts.get(lang, 0) + 1
        
        total_outlets = sum(language_counts.values())
        
        # German should be the largest group (roughly 60-70% of Swiss outlets)
        german_percentage = language_counts.get('German', 0) / total_outlets
        self.assertGreater(german_percentage, 0.5,
                          f"German outlets should be majority, got {german_percentage:.1%}")
        
        # French should be second largest (roughly 20-30%)
        french_percentage = language_counts.get('French', 0) / total_outlets
        self.assertGreater(french_percentage, 0.1,
                          f"French outlets should be significant minority, got {french_percentage:.1%}")
        
        # Italian and Romansch should be smaller but present
        self.assertGreater(language_counts.get('Italian', 0), 0,
                          "Should have at least one Italian outlet")
        self.assertGreater(language_counts.get('Romansch', 0), 0,
                          "Should have at least one Romansch outlet")
    
    def test_csv_formatting(self):
        """Test CSV formatting and encoding."""
        # Test that file can be read without encoding errors
        try:
            with open(self.final_csv, 'r', encoding='utf-8') as file:
                content = file.read()
                self.assertGreater(len(content), 100,
                                  "CSV file seems too small")
        except UnicodeDecodeError:
            self.fail("CSV file has encoding issues")
        
        # Test CSV structure
        with open(self.final_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            row_count = 0
            
            for row in reader:
                row_count += 1
                # Test that each row has all required fields
                self.assertEqual(len(row), 7,
                               f"Row {row_count} has wrong number of fields")
        
        self.assertGreater(row_count, 0, "CSV file appears to be empty")

if __name__ == '__main__':
    unittest.main()