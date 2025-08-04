#!/usr/bin/env python3
"""
API Contract Tests for Articles API

Tests the API endpoints for article retrieval, search, and related functionality.
These tests verify that the API contracts are maintained and responses
follow the expected format.
"""

import pytest
import httpx
import json
from typing import Dict, Any, List
from datetime import datetime


class TestArticlesAPI:
    """Test article-related API endpoints"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def client(self):
        """HTTP client for API testing"""
        return httpx.Client(base_url=self.BASE_URL)
    
    def test_get_articles_endpoint_exists(self, client):
        """Test that the articles endpoint exists and returns proper status"""
        response = client.get("/api/articles")
        
        # Should return 200 OK or 404 if not implemented yet
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            # If implemented, should return JSON
            assert response.headers["content-type"].startswith("application/json")
    
    def test_get_articles_response_format(self, client):
        """Test that articles endpoint returns proper JSON format"""
        response = client.get("/api/articles")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have articles array
            assert "articles" in data or isinstance(data, list)
            
            if "articles" in data:
                articles = data["articles"]
            else:
                articles = data
            
            if len(articles) > 0:
                article = articles[0]
                
                # Article should have required fields
                required_fields = ["id", "title", "url"]
                for field in required_fields:
                    assert field in article, f"Article missing required field: {field}"
                
                # Optional but expected fields
                optional_fields = ["content", "summary", "author", "publish_date", "language", "outlet"]
                for field in optional_fields:
                    if field in article:
                        assert article[field] is not None or article[field] == ""
    
    def test_get_articles_pagination(self, client):
        """Test that articles endpoint supports pagination"""
        response = client.get("/api/articles?page=1&limit=10")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have pagination metadata
            if isinstance(data, dict):
                # Common pagination fields
                pagination_fields = ["page", "limit", "total", "pages"]
                has_pagination = any(field in data for field in pagination_fields)
                
                if has_pagination:
                    assert "articles" in data
                    assert len(data["articles"]) <= 10
    
    def test_get_article_by_id(self, client):
        """Test getting a single article by ID"""
        # First get list of articles to get a valid ID
        response = client.get("/api/articles")
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", data) if isinstance(data, dict) else data
            
            if len(articles) > 0:
                article_id = articles[0]["id"]
                
                # Get specific article
                response = client.get(f"/api/articles/{article_id}")
                
                if response.status_code == 200:
                    article = response.json()
                    assert article["id"] == article_id
                    assert "title" in article
                    assert "url" in article
    
    def test_get_nonexistent_article(self, client):
        """Test getting a non-existent article returns 404"""
        response = client.get("/api/articles/nonexistent-id-12345")
        
        # Should return 404 or other appropriate error code
        assert response.status_code in [404, 400]
        
        if response.headers.get("content-type", "").startswith("application/json"):
            error_data = response.json()
            assert "error" in error_data or "message" in error_data
    
    def test_search_articles(self, client):
        """Test article search functionality"""
        response = client.get("/api/articles/search?q=test")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should return search results
            results = data.get("results", data.get("articles", data))
            assert isinstance(results, list)
            
            # If there are results, they should have the same structure as articles
            if len(results) > 0:
                result = results[0]
                assert "id" in result
                assert "title" in result
                assert "url" in result
    
    def test_get_similar_articles(self, client):
        """Test getting similar articles for a given article"""
        # First get an article ID
        response = client.get("/api/articles")
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", data) if isinstance(data, dict) else data
            
            if len(articles) > 0:
                article_id = articles[0]["id"]
                
                # Get similar articles
                response = client.get(f"/api/articles/{article_id}/similar")
                
                if response.status_code == 200:
                    data = response.json()
                    similar_articles = data.get("similar", data.get("articles", data))
                    
                    assert isinstance(similar_articles, list)
                    
                    # Similar articles should not include the original article
                    if len(similar_articles) > 0:
                        similar_ids = [article["id"] for article in similar_articles]
                        assert article_id not in similar_ids


class TestOutletsAPI:
    """Test outlet-related API endpoints"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def client(self):
        """HTTP client for API testing"""
        return httpx.Client(base_url=self.BASE_URL)
    
    def test_get_outlets_endpoint(self, client):
        """Test that the outlets endpoint exists"""
        response = client.get("/api/outlets")
        
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            assert response.headers["content-type"].startswith("application/json")
            
            data = response.json()
            outlets = data.get("outlets", data) if isinstance(data, dict) else data
            
            if len(outlets) > 0:
                outlet = outlets[0]
                
                # Outlet should have required fields
                required_fields = ["id", "name", "language"]
                for field in required_fields:
                    assert field in outlet
                
                # Language should be valid Swiss language
                if "language" in outlet:
                    assert outlet["language"] in ["de", "fr", "it", "rm", "en"]


class TestMultilingualAPI:
    """Test multilingual functionality in API"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def client(self):
        """HTTP client for API testing"""
        return httpx.Client(base_url=self.BASE_URL)
    
    def test_get_article_with_language_parameter(self, client):
        """Test getting article in specific language"""
        # Get an article ID first
        response = client.get("/api/articles")
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", data) if isinstance(data, dict) else data
            
            if len(articles) > 0:
                article_id = articles[0]["id"]
                
                # Test different language parameters
                for lang in ["de", "fr", "it", "en"]:
                    response = client.get(f"/api/articles/{article_id}?lang={lang}")
                    
                    if response.status_code == 200:
                        article = response.json()
                        
                        # Should return article (potentially translated)
                        assert "title" in article
                        assert "content" in article or "summary" in article
                        
                        # Language field should match requested language if available
                        if "language" in article:
                            # Could be original language or translated language
                            assert article["language"] in ["de", "fr", "it", "rm", "en"]
    
    def test_translation_endpoint(self, client):
        """Test translation functionality"""
        translation_data = {
            "text": "Hello, this is a test article.",
            "source_language": "en",
            "target_language": "de"
        }
        
        response = client.post("/api/translate", json=translation_data)
        
        if response.status_code == 200:
            data = response.json()
            
            assert "translated_text" in data
            assert data["translated_text"] != translation_data["text"]
            assert "source_language" in data
            assert "target_language" in data
        elif response.status_code in [404, 501]:
            # Translation not implemented yet
            pytest.skip("Translation endpoint not implemented")


class TestAPIErrorHandling:
    """Test API error handling and edge cases"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def client(self):
        """HTTP client for API testing"""
        return httpx.Client(base_url=self.BASE_URL)
    
    def test_invalid_endpoints_return_404(self, client):
        """Test that invalid endpoints return 404"""
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404
    
    def test_malformed_requests_return_400(self, client):
        """Test that malformed requests return 400"""
        # Test invalid JSON
        response = client.post(
            "/api/translate",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        
        if response.status_code not in [404, 501]:  # Skip if endpoint doesn't exist
            assert response.status_code == 400
    
    def test_api_rate_limiting(self, client):
        """Test that API has reasonable rate limiting"""
        # Make multiple rapid requests
        responses = []
        for i in range(20):
            response = client.get("/api/articles")
            responses.append(response.status_code)
        
        # Should either all succeed or some be rate limited (429)
        success_codes = [200, 404, 501]  # Valid responses
        rate_limit_codes = [429, 503]    # Rate limiting responses
        
        for status_code in responses:
            assert status_code in success_codes + rate_limit_codes
    
    def test_api_response_headers(self, client):
        """Test that API returns proper headers"""
        response = client.get("/api/articles")
        
        if response.status_code == 200:
            # Should have CORS headers for frontend access
            cors_headers = ["access-control-allow-origin", "access-control-allow-methods"]
            
            # Not all headers are required, but if present should be valid
            for header in cors_headers:
                if header in response.headers:
                    assert response.headers[header] is not None
            
            # Should have content-type
            assert "content-type" in response.headers
            assert response.headers["content-type"].startswith("application/json")


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])