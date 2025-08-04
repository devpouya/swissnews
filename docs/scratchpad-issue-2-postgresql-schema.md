# Scratchpad: Issue #2 - Design PostgreSQL database schema for articles storage

**Issue Link**: https://github.com/devpouya/swissnews/issues/2

## Understanding the Problem

Issue #2 requires creating a PostgreSQL database schema for storing scraped articles and metadata. This builds upon the work from Issue #1, which created the Swiss news outlets database (CSV format). Now we need to design a proper relational database schema to support the news aggregation functionality.

### Requirements Analysis
- Store full article text and metadata
- Support multilingual content (German, French, Italian, Romansch)
- Track scraping timestamps for data freshness
- Enable efficient querying for the frontend
- Handle outlet relationships and metadata
- Support article categorization and tagging

### Existing Data Analysis
From Issue #1 work, we have outlets data with schema:
```csv
news_website,url,original_language,owner,city,canton,occurrence,status
```

Key observations from existing data:
- ~50+ Swiss outlets across 4 languages
- Some outlets have missing URLs or location data
- Standardized occurrence values (Daily, Weekly, etc.)
- Status field tracks outlet activity

## Technical Approach

### 1. Database Schema Design

The issue provides a solid foundation, but I'll refine it based on the existing data:

**Outlets Table** (refined):
```sql
CREATE TABLE outlets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500),  -- Allow NULL for outlets without websites
    language VARCHAR(5) NOT NULL,
    owner VARCHAR(255),
    city VARCHAR(100),
    canton VARCHAR(50),
    occurrence VARCHAR(50),  -- Daily, Weekly, etc.
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'current',  -- current, discontinued, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Articles Table** (as specified):
```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    url VARCHAR(1000) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    author VARCHAR(255),
    publish_date TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    language VARCHAR(5),
    outlet_id INT REFERENCES outlets(id),
    is_paywalled BOOLEAN DEFAULT FALSE,
    word_count INT,
    tags TEXT[]
);
```

### 2. Indexes for Performance
Critical indexes for common query patterns:
- Articles by outlet and date: `(outlet_id, publish_date DESC)`
- Articles by language: `(language, publish_date DESC)`
- URL uniqueness: `UNIQUE(url)`
- Scraping recency: `(scraped_at DESC)`
- Full-text search on title/content

### 3. Implementation Plan

**Phase 1: Schema Creation**
1. Create migration file `001_initial_schema.sql`
2. Define tables with proper constraints
3. Add performance indexes
4. Create database initialization script

**Phase 2: Data Population**
5. Create utility to populate outlets table from existing CSV
6. Add database connection utilities
7. Test schema with sample article data

**Phase 3: Testing and Validation**
8. Create/update integration tests
9. Validate foreign key relationships
10. Test query performance
11. Verify all constraints work properly

**Phase 4: Documentation and Delivery**
12. Update documentation
13. Create pull request
14. Request review

### 4. Deliverables
- `backend/database/migrations/001_initial_schema.sql` - Complete schema with indexes
- `backend/database/init.sql` - Database initialization script
- `backend/database/connection.py` - Database connection utilities
- Updated tests in `tests/integration/`
- Updated documentation

### 5. Success Criteria
- [  ] Schema supports all required fields from issue spec
- [  ] Proper indexes for common queries (articles by outlet, date, language)
- [  ] Foreign key relationships established between outlets and articles
- [  ] Migration scripts work correctly
- [  ] Existing outlets data can be imported
- [  ] Schema handles multilingual content properly
- [  ] All constraints and validations work
- [  ] Tests pass and validate schema functionality

## Technical Considerations

### Schema Refinements
Based on existing data analysis:
1. **Outlets.url**: Made nullable since some outlets don't have websites
2. **Outlets.status**: Added to track outlet lifecycle (matches existing CSV)
3. **Articles.language**: Should match outlet language in most cases
4. **Articles.tags**: Using PostgreSQL array type for flexibility
5. **Timestamps**: Consistent timezone handling (UTC)

### Performance Considerations
1. **Composite indexes**: For common query patterns (outlet + date)
2. **Partial indexes**: For active outlets only
3. **Full-text search**: Consider GIN indexes for content search
4. **Partitioning**: Future consideration for large article volumes

### Data Integrity
1. **Foreign keys**: Ensure articles reference valid outlets
2. **Check constraints**: Validate URL formats, language codes
3. **Unique constraints**: Prevent duplicate articles by URL
4. **Default values**: Sensible defaults for timestamps and flags

### Migration Strategy
1. **Incremental migrations**: Start with basic schema
2. **Data population**: Separate script to populate outlets from CSV
3. **Rollback support**: Ensure migrations can be reversed
4. **Testing**: Validate each migration step

## Implementation Steps

### Step 1: Create Database Structure
1. Create `backend/database/migrations/` directory
2. Write `001_initial_schema.sql` with complete schema
3. Add proper indexes and constraints
4. Include sample data for testing

### Step 2: Database Utilities
5. Create `backend/database/connection.py` for DB connectivity
6. Add utilities for common operations
7. Handle connection pooling and error handling
8. Configuration management for different environments

### Step 3: Data Population
9. Create script to populate outlets table from existing CSV
10. Add data validation and error handling
11. Handle duplicate detection and updates
12. Verify data integrity after population

### Step 4: Testing and Validation
13. Update existing integration tests
14. Add new tests for schema functionality
15. Test foreign key relationships
16. Validate performance with sample data

### Step 5: Documentation and Delivery
17. Update README with database setup instructions
18. Document schema design decisions
19. Create pull request with comprehensive description
20. Request review and address feedback

## Timeline Estimate
- Step 1: Schema creation (2 hours)
- Step 2: Database utilities (2 hours)
- Step 3: Data population (1 hour)
- Step 4: Testing (2 hours)
- Step 5: Documentation/PR (1 hour)

**Total Estimated Time: 8 hours**

## Next Actions
1. Create feature branch `feature/postgresql-schema`
2. Start with migration file creation
3. Build incrementally with testing at each step
4. Validate with existing outlets data