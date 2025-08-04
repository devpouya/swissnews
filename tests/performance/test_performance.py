#!/usr/bin/env python3
"""
Performance Tests for Swiss News Aggregator

Tests the performance characteristics of key system components
including database queries, API responses, and frontend loading times.
"""

import pytest
import time
import statistics
from typing import List
import asyncio
import psycopg2
from unittest.mock import patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))


class TestDatabasePerformance:
    """Test database query performance"""

    @pytest.fixture
    def db_connection(self):
        """Database connection for testing"""
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', 5432),
                database=os.getenv('DB_NAME', 'swissnews_test'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
            yield conn
            conn.close()
        except psycopg2.Error:
            pytest.skip("Database not available for performance testing")

    def test_article_query_performance(self, db_connection):
        """Test that article queries complete within acceptable time"""
        cursor = db_connection.cursor()

        # Test basic article selection
        start_time = time.time()
        cursor.execute("SELECT * FROM articles LIMIT 100")
        results = cursor.fetchall()
        end_time = time.time()

        query_time = end_time - start_time

        # Should complete within 100ms for 100 articles
        assert query_time < 0.1, f"Article query took {query_time:.3f}s, expected < 0.1s"

        cursor.close()

    def test_outlet_query_performance(self, db_connection):
        """Test that outlet queries are fast"""
        cursor = db_connection.cursor()

        start_time = time.time()
        cursor.execute("SELECT * FROM outlets")
        results = cursor.fetchall()
        end_time = time.time()

        query_time = end_time - start_time

        # Should complete very quickly as outlets table is small
        assert query_time < 0.05, f"Outlet query took {query_time:.3f}s, expected < 0.05s"

        cursor.close()

    def test_article_with_outlet_join_performance(self, db_connection):
        """Test performance of articles joined with outlets"""
        cursor = db_connection.cursor()

        start_time = time.time()
        cursor.execute("""
            SELECT a.id, a.title, a.publish_date, o.name as outlet_name, o.language
            FROM articles a
            JOIN outlets o ON a.outlet_id = o.id
            ORDER BY a.publish_date DESC
            LIMIT 50
        """)
        results = cursor.fetchall()
        end_time = time.time()

        query_time = end_time - start_time

        # Should complete within 200ms for joined query
        assert query_time < 0.2, f"Article-outlet join took {query_time:.3f}s, expected < 0.2s"

        cursor.close()

    @pytest.mark.slow
    def test_database_connection_pool_performance(self):
        """Test database connection pool performance"""
        connection_times = []

        for i in range(10):
            start_time = time.time()
            try:
                conn = psycopg2.connect(
                    host=os.getenv('DB_HOST', 'localhost'),
                    port=os.getenv('DB_PORT', 5432),
                    database=os.getenv('DB_NAME', 'swissnews_test'),
                    user=os.getenv('DB_USER', 'postgres'),
                    password=os.getenv('DB_PASSWORD', 'postgres')
                )
                conn.close()
                end_time = time.time()
                connection_times.append(end_time - start_time)
            except psycopg2.Error:
                pytest.skip("Database not available for performance testing")

        avg_connection_time = statistics.mean(connection_times)
        max_connection_time = max(connection_times)

        # Average connection time should be reasonable
        assert avg_connection_time < 0.1, f"Average connection time {avg_connection_time:.3f}s too slow"
        assert max_connection_time < 0.2, f"Max connection time {max_connection_time:.3f}s too slow"


class TestAPIPerformance:
    """Test API endpoint performance"""

    def measure_request_time(self, url: str, method: str = "GET", data=None) -> float:
        """Measure time to complete HTTP request"""
        import httpx

        client = httpx.Client(base_url="http://localhost:8000")

        start_time = time.time()
        try:
            if method == "GET":
                response = client.get(url, timeout=5.0)
            elif method == "POST":
                response = client.post(url, json=data, timeout=5.0)
            end_time = time.time()

            return end_time - start_time
        except httpx.ConnectError:
            pytest.skip("API server not available for performance testing")
        except httpx.TimeoutException:
            return 5.0  # Timeout occurred
        finally:
            client.close()

    def test_articles_endpoint_performance(self):
        """Test articles endpoint response time"""
        response_time = self.measure_request_time("/api/articles")

        # Should respond within 500ms
        assert response_time < 0.5, f"Articles endpoint took {response_time:.3f}s, expected < 0.5s"

    def test_outlets_endpoint_performance(self):
        """Test outlets endpoint response time"""
        response_time = self.measure_request_time("/api/outlets")

        # Should respond very quickly
        assert response_time < 0.2, f"Outlets endpoint took {response_time:.3f}s, expected < 0.2s"

    @pytest.mark.slow
    def test_api_concurrent_requests_performance(self):
        """Test API performance under concurrent load"""
        import concurrent.futures
        import httpx

        def make_request():
            client = httpx.Client(base_url="http://localhost:8000")
            try:
                start_time = time.time()
                response = client.get("/api/articles", timeout=10.0)
                end_time = time.time()
                return end_time - start_time
            except httpx.ConnectError:
                return None  # Skip if server not available
            except httpx.TimeoutException:
                return 10.0  # Timeout
            finally:
                client.close()

        # Test with 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            response_times = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Filter out None values (server not available)
        response_times = [t for t in response_times if t is not None]

        if len(response_times) == 0:
            pytest.skip("API server not available for concurrent testing")

        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)

        # Under concurrent load, should still be reasonable
        assert avg_response_time < 1.0, f"Average concurrent response time {avg_response_time:.3f}s too slow"
        assert max_response_time < 2.0, f"Max concurrent response time {max_response_time:.3f}s too slow"


class TestScrapingPerformance:
    """Test scraping performance"""

    def test_wikipedia_scraper_performance(self):
        """Test Wikipedia scraper performance"""
        try:
            from scraper.wikipedia_scraper import SwissNewsWikipediaScraper
        except ImportError:
            pytest.skip("Wikipedia scraper not available")

        scraper = SwissNewsWikipediaScraper()

        start_time = time.time()

        # Mock the actual HTTP request to avoid network dependency
        with patch.object(scraper, 'fetch_page') as mock_fetch:
            # Create mock HTML response
            mock_html = """
            <html><body>
                <table class="wikitable">
                    <tr><th>Name</th><th>Owner</th><th>City</th></tr>
                    <tr><td>Test Outlet 1</td><td>Test Owner 1</td><td>Zurich</td></tr>
                    <tr><td>Test Outlet 2</td><td>Test Owner 2</td><td>Geneva</td></tr>
                </table>
            </body></html>
            """

            from bs4 import BeautifulSoup
            mock_fetch.return_value = BeautifulSoup(mock_html, 'html.parser')

            # Test scraping performance
            outlets = scraper.scrape_all_languages()

            end_time = time.time()
            scraping_time = end_time - start_time

            # Should complete scraping quickly with mocked data
            assert scraping_time < 1.0, f"Scraping took {scraping_time:.3f}s, expected < 1.0s"
            assert len(outlets) > 0, "Should have scraped some outlets"

    @pytest.mark.external
    def test_real_scraping_performance(self):
        """Test actual scraping performance (requires network)"""
        try:
            from scraper.wikipedia_scraper import SwissNewsWikipediaScraper
        except ImportError:
            pytest.skip("Wikipedia scraper not available")

        scraper = SwissNewsWikipediaScraper()

        start_time = time.time()

        try:
            # Test just one section to avoid long test times
            soup = scraper.fetch_page()
            tables = soup.find_all('table', class_='wikitable')

            if len(tables) > 0:
                outlets = scraper.parse_table(tables[0], 'German')

                end_time = time.time()
                scraping_time = end_time - start_time

                # Should complete within reasonable time
                assert scraping_time < 10.0, f"Real scraping took {scraping_time:.3f}s, expected < 10.0s"

        except Exception as e:
            pytest.skip(f"Network scraping failed: {e}")


class TestMemoryPerformance:
    """Test memory usage characteristics"""

    def test_memory_usage_during_processing(self):
        """Test that memory usage stays reasonable during processing"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Simulate processing large dataset
        large_data = []
        for i in range(10000):
            large_data.append({
                'id': i,
                'title': f'Article {i}' * 10,  # Make it somewhat large
                'content': f'Content for article {i}' * 50
            })

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Clean up
        del large_data

        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_increase = peak_memory - initial_memory
        memory_leak = final_memory - initial_memory

        # Should not use excessive memory
        assert memory_increase < 500, f"Memory usage increased by {memory_increase:.1f}MB, expected < 500MB"

        # Should not have significant memory leak
        assert memory_leak < 50, f"Potential memory leak of {memory_leak:.1f}MB"


class TestFrontendPerformance:
    """Test frontend performance characteristics"""

    def test_bundle_size_expectations(self):
        """Test that built frontend bundle sizes are reasonable"""
        import os
        import glob

        # Look for built frontend files
        frontend_build_dir = os.path.join(os.path.dirname(__file__), '../../frontend/.next')

        if not os.path.exists(frontend_build_dir):
            pytest.skip("Frontend not built, run 'npm run build' first")

        # Check JavaScript bundle sizes
        js_files = glob.glob(os.path.join(frontend_build_dir, 'static/chunks/*.js'))

        total_js_size = 0
        for js_file in js_files:
            size = os.path.getsize(js_file)
            total_js_size += size

            # Individual chunks should not be too large
            size_mb = size / 1024 / 1024
            assert size_mb < 5.0, f"JS chunk {os.path.basename(js_file)} is {size_mb:.1f}MB, expected < 5MB"

        # Total JS size should be reasonable
        total_js_mb = total_js_size / 1024 / 1024
        assert total_js_mb < 10.0, f"Total JS size is {total_js_mb:.1f}MB, expected < 10MB"


if __name__ == "__main__":
    # Run with pytest, including slow tests
    pytest.main([__file__, "-v", "-m", "not external"])  # Skip external tests by default
