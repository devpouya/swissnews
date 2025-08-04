# Scratchpad: Issue #3 - Implement Base Selenium Scraper Framework

**Issue Link:** https://github.com/devpouya/swissnews/issues/3

## Objective
Create a robust Selenium-based web scraping framework for Swiss news outlets that can handle different HTML structures, provide configurable selectors, and include comprehensive error handling.

## Current State Analysis

### Existing Infrastructure
- ✅ Selenium 4.15.2 already in requirements.txt
- ✅ Existing scraper directory: `backend/scraper/`
- ✅ Wikipedia scraper implemented (`wikipedia_scraper.py`)
- ✅ Configuration system using Pydantic BaseSettings
- ✅ Database schema with outlets table
- ✅ Logging infrastructure using loguru
- ✅ Testing framework with pytest

### Current Scraper Capabilities
- Wikipedia outlet discovery and metadata extraction
- CSV export functionality
- Comprehensive logging and error handling
- Multi-language support (German, French, Italian, Romansch)

## Implementation Plan

### 1. Core Framework Components

#### BaseScraper Class (`backend/scraper/base.py`)
```python
class BaseScraper:
    def __init__(self, outlet_config: Dict)
    def setup_driver(self) -> WebDriver
    def scrape_article_list(self) -> List[str]
    def scrape_article_content(self, url: str) -> Dict
    def cleanup(self) -> None
```

**Key Features:**
- Headless Chrome WebDriver configuration
- Configurable timeouts and retry logic
- Resource cleanup and error handling
- Logging integration with existing loguru setup
- Base methods for outlet-specific inheritance

#### OutletScraper Class
```python
class OutletScraper(BaseScraper):
    # Outlet-specific implementations
    # Will use configuration from outlets.yaml
```

### 2. Configuration System

#### Outlet Configuration (`backend/scraper/config/outlets.yaml`)
```yaml
outlets:
  nzz:
    url: "https://www.nzz.ch"
    selectors:
      article_links: ".teaser__link"
      title: "h1.headline"
      content: ".article__body"
      author: ".author__name"
      date: ".article__date"
    timeouts:
      page_load: 30
      element_wait: 10
    retry:
      max_attempts: 3
      delay: 2
```

### 3. Utility Functions (`backend/scraper/utils.py`)
- WebDriver setup and configuration
- Retry decorators
- Text cleaning and normalization
- URL validation and normalization
- Common selector helpers

### 4. Integration Points

#### Database Integration
- Use existing outlets table from database schema
- Store scraped articles in articles table
- Track scraping status and metadata

#### Settings Integration
- Extend existing `config/settings.py` with Selenium-specific settings
- Use existing USER_AGENT and timeout configurations
- Integrate with existing logging configuration

#### Error Handling Strategy
- Graceful degradation when outlets are unavailable
- Comprehensive logging of failures and retries
- Circuit breaker pattern for repeatedly failing outlets
- Resource cleanup in all error scenarios

## Technical Decisions

### WebDriver Configuration
- **Choice:** Headless Chrome
- **Rationale:** Best balance of performance, compatibility, and debugging capability
- **Configuration:**
  - Headless mode for production
  - Configurable window size for mobile/desktop testing
  - Custom user agent matching existing scraping infrastructure

### Configuration Format
- **Choice:** YAML over JSON
- **Rationale:** More readable for complex nested configurations, supports comments
- **Structure:** Hierarchical with outlet-specific settings

### Error Handling Strategy
- **Retry Logic:** Exponential backoff with configurable max attempts
- **Circuit Breaker:** Temporarily disable failing outlets
- **Fallback:** Continue with other outlets when one fails

## Implementation Steps

1. ✅ **Research Phase** - Understand existing codebase structure
2. 🔄 **Planning Phase** - Create this scratchpad and plan
3. **Setup Phase** - Create branch and basic structure
4. **Core Implementation** - BaseScraper class with WebDriver setup
5. **Configuration** - outlets.yaml and configuration loading
6. **Utilities** - Helper functions and decorators
7. **Testing** - Unit tests and integration tests
8. **Integration** - Connect with existing database and settings
9. **Documentation** - Update README and add usage examples
10. **PR Creation** - Submit for review

## Testing Strategy

### Unit Tests
- BaseScraper class methods
- Configuration loading and validation
- Utility functions
- Error handling scenarios

### Integration Tests
- End-to-end scraping with test outlets
- Database integration
- Configuration file parsing

### Performance Tests
- Memory usage with WebDriver lifecycle
- Concurrent scraping performance
- Resource cleanup verification

## Success Criteria
- [ ] Scraper works with headless Chrome
- [ ] Configurable per outlet via YAML
- [ ] Robust error handling with retries
- [ ] Proper resource cleanup
- [ ] Comprehensive logging
- [ ] All tests passing
- [ ] Integration with existing database schema
- [ ] Documentation and examples

## Risks and Mitigations

### Risk: WebDriver Resource Leaks
**Mitigation:** Comprehensive cleanup in finally blocks, context managers

### Risk: Anti-bot Detection
**Mitigation:** Configurable delays, realistic user agents, rotating IP support

### Risk: Site Structure Changes
**Mitigation:** Flexible selector configuration, graceful failure handling

### Risk: Performance Impact
**Mitigation:** Headless mode, connection pooling, configurable concurrency

## Future Enhancements
- Proxy rotation support
- JavaScript rendering optimization
- Mobile user agent testing
- Screenshot capture for debugging
- Performance monitoring and metrics
