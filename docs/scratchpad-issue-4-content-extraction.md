# Scratchpad: Issue #4 - Implement Full Article Content Extraction Logic

**Issue Link:** https://github.com/devpouya/swissnews/issues/4

## Objective
Implement comprehensive article content extraction logic that goes beyond the basic scraper framework to extract complete article content, metadata, and media from Swiss news outlets with advanced text processing and validation.

## Current State Analysis

### Existing Infrastructure
- ✅ Base Selenium scraper framework implemented (PR #21)
- ✅ BaseScraper and OutletScraper classes in `backend/scraper/base.py`
- ✅ Basic content extraction (title, content, author, date) in OutletScraper.scrape_article_content()
- ✅ Utility functions in `backend/scraper/utils.py` with text cleaning capabilities
- ✅ Configuration system with `backend/scraper/config/outlets.yaml`
- ✅ Swiss news outlet configurations for major outlets (NZZ, Tages-Anzeiger, etc.)

### Current Limitations
- Basic paragraph extraction without structure preservation
- Limited metadata extraction (missing tags, categories, images)
- Basic text cleaning (needs advanced ad removal, HTML artifact cleaning)
- No content validation mechanisms
- No multimedia content extraction
- No outlet-specific content handling variations

## Implementation Plan

### 1. Advanced Content Extraction System

#### ArticleExtractor Class (`backend/scraper/extractors.py`)
```python
class ArticleExtractor:
    """Advanced article content extraction with structure preservation"""
    def extract_full_content(self, driver, selectors) -> ArticleContent
    def extract_metadata(self, driver, selectors) -> ArticleMetadata
    def extract_multimedia(self, driver, selectors) -> MultimediaContent
    def validate_content(self, content) -> ContentValidation
```

**Key Features:**
- Hierarchical content extraction (title, subtitle, body paragraphs)
- Advanced metadata parsing (author, date, tags, categories)
- Image URL and caption extraction
- Content structure preservation
- Outlet-specific extraction strategies

#### ContentProcessor Class (`backend/scraper/extractors.py`)
```python
class ContentProcessor:
    """Process and enhance extracted content"""
    def clean_article_text(self, text) -> str
    def preserve_paragraph_structure(self, elements) -> List[str]
    def extract_quotes_and_highlights(self, elements) -> List[str]
    def remove_navigation_elements(self, content) -> str
```

### 2. Enhanced Text Processing (`backend/scraper/text_utils.py`)

#### Advanced Text Cleaning Functions
```python
def advanced_clean_text(text: str, outlet_config: Dict) -> str
def remove_ad_content(text: str, language: str) -> str
def clean_html_artifacts(text: str) -> str
def preserve_article_structure(elements: List) -> str
def extract_and_clean_quotes(text: str) -> List[str]
def handle_special_characters(text: str, encoding: str) -> str
```

#### Content Validation Functions
```python
def validate_article_content(content: ArticleContent) -> ValidationResult
def check_content_completeness(content: str) -> bool
def detect_content_quality(content: str) -> float
def validate_metadata_consistency(metadata: dict) -> bool
```

### 3. Enhanced Configuration System

#### Extended Outlet Configuration (`backend/scraper/config/outlets.yaml`)
```yaml
nzz:
  content_selectors:
    main_text: ".article__body p, .article__text > p"
    subtitle: ".article__subtitle, .headline__subtitle"
    author: ".author__name, .byline__author"
    date: ".article__date, .publish-date"
    tags: ".article__tags a, .topic-tags a"
    categories: ".breadcrumb a, .category-link"
    images: ".article__image img, .content-image img"
    image_captions: ".image-caption, .photo-caption"
    quotes: ".quote, blockquote"
    highlights: ".highlight, .callout"
  exclusion_selectors:
    ads: ".advertisement, .ad-container, .sponsored"
    navigation: ".navigation, .breadcrumb, .related-links"
    social: ".social-share, .share-buttons"
  text_processing:
    language: "de"
    remove_patterns: ["\\[Werbung\\]", "\\(Anzeige\\)"]
    preserve_formatting: true
```

### 4. Content Data Models

#### ArticleContent Structure
```python
@dataclass
class ArticleContent:
    url: str
    title: str
    subtitle: Optional[str]
    body_paragraphs: List[str]
    author: Optional[str]
    publication_date: Optional[datetime]
    tags: List[str]
    categories: List[str]
    images: List[ImageContent]
    quotes: List[str]
    highlights: List[str]
    language: Optional[str]
    word_count: int
    reading_time_minutes: int
    content_quality_score: float
    extraction_metadata: ExtractionMetadata
```

#### ImageContent Structure
```python
@dataclass
class ImageContent:
    url: str
    caption: Optional[str]
    alt_text: Optional[str]
    width: Optional[int]
    height: Optional[int]
```

### 5. Integration with Existing System

#### Extend OutletScraper Class
- Modify `scrape_article_content()` to use new ArticleExtractor
- Maintain backward compatibility with existing interface
- Add content validation before returning results
- Implement fallback to basic extraction if advanced fails

#### Database Schema Extensions
- Add fields for new metadata (tags, categories, images)
- Store content quality scores and extraction metadata
- Create indexes for efficient searching by tags/categories

## Implementation Steps

### Phase 1: Core Infrastructure
1. ✅ **Planning** - Create this scratchpad and detailed plan
2. **Create extractors.py** - ArticleExtractor and ContentProcessor classes
3. **Enhance text_utils.py** - Advanced text processing functions
4. **Update outlet configurations** - Add advanced selectors

### Phase 2: Content Extraction Logic
5. **Implement metadata extraction** - Tags, categories, author info
6. **Implement multimedia extraction** - Images and captions
7. **Implement structure preservation** - Paragraphs, quotes, highlights
8. **Add content validation** - Quality checks and completeness validation

### Phase 3: Integration and Testing
9. **Integrate with OutletScraper** - Update scrape_article_content method
10. **Write comprehensive tests** - Unit tests for all new functionality
11. **Test with real outlets** - Validate extraction quality
12. **Performance optimization** - Ensure extraction doesn't slow down scraping

### Phase 4: Quality Assurance
13. **Run full test suite** - Ensure no regressions
14. **Content quality validation** - Manual review of extracted content
15. **Documentation updates** - README and API documentation
16. **PR creation and review**

## Technical Implementation Details

### Content Extraction Strategy
1. **Primary Selectors**: Use configured selectors for each content type
2. **Fallback Strategy**: Try alternative selectors if primary fails
3. **Content Validation**: Validate extracted content meets quality thresholds
4. **Structure Preservation**: Maintain article hierarchy and formatting

### Text Processing Pipeline
1. **Raw Extraction**: Get text content from HTML elements
2. **HTML Cleaning**: Remove HTML artifacts and encoding issues
3. **Ad Removal**: Remove advertisement content using patterns
4. **Navigation Cleanup**: Remove navigation and UI elements
5. **Text Normalization**: Normalize whitespace and special characters
6. **Structure Preservation**: Maintain paragraph breaks and quotes

### Multimedia Handling
1. **Image Detection**: Find article images using CSS selectors
2. **Caption Extraction**: Extract captions and alt text
3. **URL Normalization**: Convert relative URLs to absolute
4. **Quality Filtering**: Filter out low-quality or UI images

### Content Validation
1. **Completeness Check**: Ensure all required fields are extracted
2. **Quality Assessment**: Calculate content quality score
3. **Consistency Check**: Validate metadata consistency
4. **Language Detection**: Confirm content language matches expected

## Testing Strategy

### Unit Tests (Maximum 5 tests as per issue requirement)
1. **ArticleExtractor.extract_full_content()** - Core extraction functionality
2. **ContentProcessor.clean_article_text()** - Text cleaning and processing
3. **validate_article_content()** - Content validation logic
4. **Image extraction functionality** - Multimedia content extraction
5. **Integration test** - End-to-end content extraction with real article

### Test Data Strategy
- Mock HTML content for each major Swiss news outlet
- Real article URLs for integration testing (with consent/robots.txt compliance)
- Edge cases: articles with missing content, special formatting, multimedia

## Success Criteria
- [ ] Extract complete article text with preserved paragraph structure
- [ ] Parse all required metadata (author, date, tags, categories)
- [ ] Handle different content structures across Swiss outlets
- [ ] Clean and normalize text content effectively
- [ ] Extract image URLs and captions
- [ ] Validate content quality and completeness
- [ ] Maintain backward compatibility with existing scraper
- [ ] All tests passing with comprehensive coverage
- [ ] Performance impact < 20% increase in scraping time

## Risk Mitigation

### Risk: Performance Impact
**Mitigation**: Profile extraction performance, implement caching, optimize selectors

### Risk: Outlet Structure Changes
**Mitigation**: Comprehensive fallback selectors, graceful degradation

### Risk: Content Quality Issues
**Mitigation**: Robust validation, manual spot-checking, quality scoring

### Risk: Complex Multimedia Handling
**Mitigation**: Start with basic image extraction, iterate based on results

## Future Enhancements
- Video content metadata extraction (separate issue as requested)
- AI-powered content quality assessment
- Automatic selector discovery for new outlets
- Real-time content validation dashboards
- Multi-language content translation pipeline

---

**Status**: 🔄 In Progress
**Branch**: feature/issue-4-content-extraction
**Next Steps**: Implement ArticleExtractor class and enhanced text processing functions
