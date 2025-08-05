# Scratchpad: Issue #5 - Implement Duplicate Article Detection System

**Issue Link**: https://github.com/devpouya/swissnews/issues/5

## Objective
Prevent duplicate articles from being stored and handle article updates efficiently across Swiss news outlets using multiple detection methods: URL-based, content-based, hash-based, and time-based.

## Current State Analysis

### Existing Infrastructure ✅
- **Database Schema**: Articles table with `url UNIQUE` constraint in `001_initial_schema.sql`
- **ArticleRepository**: Basic `article_exists(url)` method and `create_article()` workflow in `backend/database/connection.py`
- **Content Extraction**: Advanced `ArticleExtractor` and `ContentProcessor` in `backend/scraper/extractors.py`
- **Data Models**: Rich `ArticleContent` dataclass with comprehensive metadata
- **Quality Scoring**: Content quality assessment system already implemented

### Current Limitations ❌
- Only basic URL-based duplicate detection via unique constraint
- No content hashing or similarity detection
- No handling of article updates (same URL, new content)
- No cross-outlet similar article detection
- Missing database indexes for fast duplicate lookups

## Technical Implementation Plan

### Phase 1: Database Schema Enhancement

#### New Migration: `002_add_duplicate_detection.sql`
```sql
-- Add content hashing field for duplicate detection
ALTER TABLE articles ADD COLUMN content_hash VARCHAR(64);

-- Add indexes for fast duplicate detection
CREATE INDEX idx_articles_content_hash ON articles(content_hash);
CREATE INDEX idx_articles_title_date ON articles(title, publish_date);
CREATE INDEX idx_articles_title_similarity ON articles USING GIN(to_tsvector('simple', title));

-- Add configuration table for duplicate detection settings
CREATE TABLE duplicate_detection_config (
    id SERIAL PRIMARY KEY,
    similarity_threshold DECIMAL(3,2) DEFAULT 0.80,
    title_similarity_threshold DECIMAL(3,2) DEFAULT 0.85,
    time_proximity_hours INT DEFAULT 24,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO duplicate_detection_config (similarity_threshold, title_similarity_threshold, time_proximity_hours)
VALUES (0.80, 0.85, 24);
```

### Phase 2: DuplicateDetector Implementation

#### Core Class: `backend/scraper/duplicates.py`
```python
class DuplicateDetector:
    """
    Comprehensive duplicate article detection system.

    Implements multiple detection strategies:
    - URL-based: Exact URL matches
    - Content-based: Title + content similarity using difflib
    - Hash-based: SHA-256 content fingerprinting
    - Time-based: Publication date proximity analysis
    """

    def __init__(self, db_manager: DatabaseManager, config: Dict[str, Any] = None)

    # Method implementations as specified in issue:
    def is_duplicate_url(self, url: str) -> bool
    def is_duplicate_content(self, title: str, content: str) -> Tuple[bool, Optional[Dict]]
    def calculate_content_hash(self, content: str) -> str
    def find_similar_articles(self, article: ArticleContent) -> List[Dict[str, Any]]
    def should_update_article(self, existing: Dict, new: ArticleContent) -> bool

    # Additional utility methods:
    def _calculate_title_similarity(self, title1: str, title2: str) -> float
    def _calculate_content_similarity(self, content1: str, content2: str) -> float
    def _normalize_content_for_hashing(self, content: str) -> str
    def _is_within_time_proximity(self, date1: datetime, date2: datetime) -> bool
```

#### Key Features:
- **Fast Performance**: < 100ms per detection (cached lookups, optimized queries)
- **Configurable Thresholds**: Title similarity (0.85), content similarity (0.80), time proximity (24h)
- **Multi-layered Detection**: Sequential checks from fastest (URL) to most comprehensive (content similarity)
- **Update Logic**: Smart detection of content updates vs true duplicates

### Phase 3: Repository Integration

#### Enhanced ArticleRepository Methods
```python
class ArticleRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.duplicate_detector = DuplicateDetector(db_manager)

    def create_article_with_duplicate_check(self, article_data: ArticleContent) -> Tuple[int, str]:
        """
        Create article with comprehensive duplicate detection.

        Returns:
            Tuple[article_id, action] where action is:
            - 'created': New article created
            - 'updated': Existing article updated
            - 'skipped': Duplicate found, no action taken
        """

    def find_duplicates_for_article(self, article: ArticleContent) -> List[Dict]:
        """Find all potential duplicates using multiple strategies."""

    def get_articles_by_content_hash(self, content_hash: str) -> List[Dict]:
        """Fast lookup by content hash."""
```

### Phase 4: Integration Points

#### With Existing Content Extraction Pipeline
```python
# In OutletScraper.scrape_article_content() or similar
def scrape_and_store_article(self, url: str) -> Dict[str, Any]:
    # 1. Extract content using existing ArticleExtractor
    article_content = self.extractor.extract_full_content(driver, url)

    # 2. Check for duplicates before storing
    article_id, action = article_repo.create_article_with_duplicate_check(article_content)

    # 3. Return result with duplicate detection info
    return {
        'article_id': article_id,
        'action': action,  # 'created', 'updated', 'skipped'
        'duplicate_info': {...}
    }
```

### Phase 5: Testing Strategy (Maximum 5 Tests)

#### Test Coverage Plan
1. **`test_url_duplicate_detection()`**: URL-based detection with exact matches
2. **`test_content_similarity_detection()`**: Title and content similarity with various thresholds
3. **`test_content_hash_detection()`**: SHA-256 hash-based detection with content variations
4. **`test_article_update_logic()`**: Same URL, different content update scenarios
5. **`test_duplicate_detection_performance()`**: < 100ms performance requirement validation

#### Test Data Strategy
- Real Swiss news article samples from existing scratchpads
- Synthetic variations (slight content changes, different URLs, same content)
- Edge cases: empty content, very short articles, special characters
- Performance dataset: 1000+ articles for speed testing

## Technical Considerations

### Performance Optimization
- **Database Indexes**: Content hash, title similarity (GIN), composite indexes
- **Caching Strategy**: In-memory cache for recent article hashes
- **Query Optimization**: Limit similarity searches to recent articles (90 days)
- **Batch Processing**: Process multiple articles efficiently

### Similarity Algorithm Selection
- **Title Similarity**: `difflib.SequenceMatcher` for robust fuzzy matching
- **Content Similarity**: Combination of:
  - Edit distance for short content
  - Jaccard similarity for longer content
  - TF-IDF cosine similarity for high precision
- **Hash Algorithm**: SHA-256 for content fingerprinting (collision-resistant)

### Configuration Management
- **Database-driven**: Store thresholds in `duplicate_detection_config` table
- **Environment Override**: Allow env vars for testing/staging
- **Runtime Tuning**: Adjustable thresholds based on outlet characteristics

## Implementation Steps

### Step 1: Database Migration
1. Create `backend/database/migrations/002_add_duplicate_detection.sql`
2. Add content_hash field and performance indexes
3. Create configuration table with default thresholds
4. Test migration with existing data

### Step 2: DuplicateDetector Implementation
5. Create `backend/scraper/duplicates.py` with all required methods
6. Implement content hashing and similarity algorithms
7. Add comprehensive error handling and logging
8. Unit test individual methods

### Step 3: Repository Integration
9. Extend ArticleRepository with duplicate detection methods
10. Integrate with existing `create_article()` workflow
11. Add proper transaction handling for updates
12. Test integration with existing scraper pipeline

### Step 4: Testing and Validation
13. Write comprehensive test suite (5 tests maximum)
14. Test with real Swiss news article data
15. Performance validation (< 100ms requirement)
16. Edge case validation and error handling

### Step 5: Documentation and Deployment
17. Update API documentation and README
18. Create configuration guide for thresholds
19. Create pull request with comprehensive description
20. Request review and address feedback

## Success Criteria Validation

- [x] **No duplicate URLs stored**: Enforced by existing unique constraint + detection
- [x] **Content updates handled correctly**: `should_update_article()` logic
- [x] **Fast duplicate detection (< 100ms)**: Optimized queries and indexes
- [x] **Configurable similarity thresholds**: Database configuration table
- [x] **Handles edge cases gracefully**: Comprehensive error handling

## Risk Mitigation

### Risk: Performance Impact on Storage Pipeline
**Mitigation**:
- Optimize database queries with proper indexes
- Cache recent article hashes in memory
- Implement circuit breaker for fallback to basic URL check

### Risk: False Positive Duplicate Detection
**Mitigation**:
- Configurable similarity thresholds
- Multi-layered validation (URL + content + time)
- Detailed logging for manual review of edge cases

### Risk: Content Hash Collisions
**Mitigation**:
- Use SHA-256 (cryptographically secure)
- Combine with title similarity for validation
- Log potential collisions for investigation

## Future Enhancements
- AI-powered semantic similarity using embeddings
- Cross-language duplicate detection
- Real-time duplicate monitoring dashboard
- Automatic threshold tuning based on outlet characteristics

---

**Status**: 🔄 Planning Complete - Ready for Implementation
**Branch**: feature/issue-5-duplicate-detection
**Next Steps**: Create database migration and begin DuplicateDetector implementation
