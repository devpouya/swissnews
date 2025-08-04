#!/usr/bin/env python3
"""
Unit tests for Wikipedia Swiss News Outlets Scraper

Tests the core functionality of the Wikipedia scraping system.
"""

import unittest
import tempfile
import csv
import os
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

# Add the scraper directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/scraper'))

from wikipedia_scraper import SwissNewsWikipediaScraper

class TestSwissNewsWikipediaScraper(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.scraper = SwissNewsWikipediaScraper()
        
    def test_clean_text(self):
        """Test text cleaning functionality."""
        # Test citation removal
        text_with_citations = "Neue Zürcher Zeitung[1][2]"
        cleaned = self.scraper.clean_text(text_with_citations)
        self.assertEqual(cleaned, "Neue Zürcher Zeitung")
        
        # Test whitespace normalization
        text_with_spaces = "  Multiple   spaces  "
        cleaned = self.scraper.clean_text(text_with_spaces)
        self.assertEqual(cleaned, "Multiple spaces")
        
        # Test special character removal
        text_with_symbols = "Outlet†‡"
        cleaned = self.scraper.clean_text(text_with_symbols)
        self.assertEqual(cleaned, "Outlet")

    def test_parse_table_basic(self):
        """Test basic table parsing functionality."""
        # Create a mock table with sample data
        html_table = """
        <table class="wikitable">
            <tr>
                <th>Name</th>
                <th>Owner</th>
                <th>City</th>
                <th>Canton</th>
                <th>Occurrence</th>
            </tr>
            <tr>
                <td>Test Zeitung</td>
                <td>Test Publisher</td>
                <td>Zurich</td>
                <td>Zurich</td>
                <td>Daily</td>
            </tr>
        </table>
        """
        
        soup = BeautifulSoup(html_table, 'html.parser')
        table = soup.find('table')
        
        outlets = self.scraper.parse_table(table, 'German')
        
        self.assertEqual(len(outlets), 1)
        outlet = outlets[0]
        self.assertEqual(outlet['news_website'], 'Test Zeitung')
        self.assertEqual(outlet['owner'], 'Test Publisher')
        self.assertEqual(outlet['city'], 'Zurich')
        self.assertEqual(outlet['canton'], 'Zurich')
        self.assertEqual(outlet['occurrence'], 'Daily')
        self.assertEqual(outlet['original_language'], 'German')

    def test_parse_table_empty(self):
        """Test parsing of empty table."""
        html_table = "<table class='wikitable'></table>"
        soup = BeautifulSoup(html_table, 'html.parser')
        table = soup.find('table')
        
        outlets = self.scraper.parse_table(table, 'German')
        self.assertEqual(len(outlets), 0)

    def test_parse_table_missing_columns(self):
        """Test parsing table with missing columns."""
        html_table = """
        <table class="wikitable">
            <tr>
                <th>Name</th>
                <th>City</th>
            </tr>
            <tr>
                <td>Test Outlet</td>
                <td>Basel</td>
            </tr>
        </table>
        """
        
        soup = BeautifulSoup(html_table, 'html.parser')
        table = soup.find('table')
        
        outlets = self.scraper.parse_table(table, 'French')
        
        self.assertEqual(len(outlets), 1)
        outlet = outlets[0]
        self.assertEqual(outlet['news_website'], 'Test Outlet')
        self.assertEqual(outlet['city'], 'Basel')
        self.assertEqual(outlet['original_language'], 'French')
        # Missing fields should be empty
        self.assertEqual(outlet['owner'], '')
        self.assertEqual(outlet['canton'], '')

    @patch('wikipedia_scraper.requests.Session.get')
    def test_fetch_page_success(self, mock_get):
        """Test successful page fetching."""
        mock_response = Mock()
        mock_response.content = b"<html><body>Test content</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        soup = self.scraper.fetch_page()
        
        self.assertIsInstance(soup, BeautifulSoup)
        mock_get.assert_called_once()

    @patch('wikipedia_scraper.requests.Session.get')
    def test_fetch_page_failure(self, mock_get):
        """Test page fetching failure."""
        mock_get.side_effect = Exception("Network error")
        
        with self.assertRaises(Exception):
            self.scraper.fetch_page()

    def test_save_to_csv(self):
        """Test CSV saving functionality."""
        # Set up test data
        self.scraper.outlets = [
            {
                'news_website': 'Test Outlet 1',
                'url': 'https://test1.ch',
                'original_language': 'German',
                'owner': 'Publisher 1',
                'city': 'Zurich',
                'canton': 'Zurich',
                'occurrence': 'Daily',
                'status': 'current'
            },
            {
                'news_website': 'Test Outlet 2',
                'url': 'https://test2.ch',
                'original_language': 'French',
                'owner': 'Publisher 2',
                'city': 'Geneva',
                'canton': 'Geneva',
                'occurrence': 'Weekly',
                'status': 'current'
            }
        ]
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_filename = temp_file.name
        
        try:
            # Save to CSV
            self.scraper.save_to_csv(temp_filename)
            
            # Verify file contents
            with open(temp_filename, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                rows = list(reader)
                
            self.assertEqual(len(rows), 2)
            
            # Check first row
            self.assertEqual(rows[0]['news_website'], 'Test Outlet 1')
            self.assertEqual(rows[0]['url'], 'https://test1.ch')
            self.assertEqual(rows[0]['original_language'], 'German')
            
            # Check second row
            self.assertEqual(rows[1]['news_website'], 'Test Outlet 2')
            self.assertEqual(rows[1]['original_language'], 'French')
            
        finally:
            # Clean up
            os.unlink(temp_filename)

    def test_save_to_csv_empty(self):
        """Test CSV saving with no outlets."""
        self.scraper.outlets = []
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_filename = temp_file.name
        
        try:
            # Should not raise exception
            self.scraper.save_to_csv(temp_filename)
            
            # File should exist but be empty (except for header)
            self.assertTrue(os.path.exists(temp_filename))
            
        finally:
            os.unlink(temp_filename)

    @patch.object(SwissNewsWikipediaScraper, 'fetch_page')
    def test_scrape_all_languages_integration(self, mock_fetch_page):
        """Test full scraping integration with mock data."""
        # Create mock HTML with multiple tables
        mock_html = """
        <html>
            <body>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>German Outlet</td><td>German Publisher</td><td>Zurich</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>French Outlet</td><td>French Publisher</td><td>Geneva</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Italian Outlet</td><td>Italian Publisher</td><td>Lugano</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Romansch Outlet</td><td>Romansch Publisher</td><td>Chur</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Other Outlet</td><td>Other Publisher</td><td>Bern</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Defunct German</td><td>Old Publisher</td><td>Basel</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Defunct French</td><td>Old French Pub</td><td>Lausanne</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Defunct Italian</td><td>Old Italian Pub</td><td>Bellinzona</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Defunct Romansch</td><td>Old Romansch Pub</td><td>St. Moritz</td></tr>
                </table>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Defunct Other</td><td>Old Other Pub</td><td>Lucerne</td></tr>
                </table>
            </body>
        </html>
        """
        
        mock_soup = BeautifulSoup(mock_html, 'html.parser')
        mock_fetch_page.return_value = mock_soup
        
        outlets = self.scraper.scrape_all_languages()
        
        # Should have scraped from all tables
        self.assertEqual(len(outlets), 10)
        
        # Check language distribution
        languages = [outlet['original_language'] for outlet in outlets]
        self.assertIn('German', languages)
        self.assertIn('French', languages)
        self.assertIn('Italian', languages)
        self.assertIn('Romansch', languages)
        self.assertIn('Other', languages)
        
        # Check status distribution
        statuses = [outlet['status'] for outlet in outlets]
        self.assertIn('current', statuses)
        self.assertIn('defunct', statuses)

if __name__ == '__main__':
    unittest.main()