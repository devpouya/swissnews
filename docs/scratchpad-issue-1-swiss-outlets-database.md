# Scratchpad: Issue #1 - Research and compile Swiss news outlets database

**Issue Link**: https://github.com/devpouya/swissnews/issues/1

## Understanding the Problem

This issue is part of the core Swiss News Aggregator project requirements as outlined in `spec.md`. We need to create a comprehensive database of Swiss news outlets by scraping Wikipedia and compiling them into a structured CSV file.

### Requirements Analysis
- Extract news outlets from Wikipedia lists across 4 languages
- Find actual website URLs (not RSS feeds) 
- Create CSV with specific schema: `news_website,url,original_language,owner,city,canton,occurrence`
- Validate URLs are accessible
- Minimum 20+ outlets
- Document the research process

### Wikipedia Sources to Scrape
1. **German**: https://en.wikipedia.org/wiki/List_of_newspapers_in_Switzerland#German_language
2. **French**: https://en.wikipedia.org/wiki/List_of_newspapers_in_Switzerland#French_language  
3. **Italian**: https://en.wikipedia.org/wiki/List_of_newspapers_in_Switzerland#Italian_language
4. **Romansch**: https://en.wikipedia.org/wiki/List_of_newspapers_in_Switzerland#Romansch_language

## Technical Approach

### 1. Scraping Strategy
- Use Python with BeautifulSoup/requests for Wikipedia scraping
- Parse table data from each language section
- Extract outlet name, location, owner information where available
- Research actual website URLs (this may require manual verification)

### 2. Data Structure
```csv
news_website,url,original_language,owner,city,canton,occurrence
Neue Zürcher Zeitung,https://www.nzz.ch,German,NZZ-Mediengruppe,Zürich,Zürich,daily
Le Temps,https://www.letemps.ch,French,Groupe Tamedia,Geneva,Geneva,daily
```

### 3. Implementation Plan
1. **Setup**: Create scraper script in `backend/scraper/wikipedia_scraper.py`
2. **Scraping**: Extract data from each Wikipedia section
3. **URL Research**: Find actual websites (manual + automated validation)  
4. **Data Compilation**: Merge into single CSV with proper schema
5. **Validation**: Check URL accessibility and data completeness
6. **Documentation**: Create research methodology docs

### 4. Deliverables
- `data/raw/swiss_news_outlets.csv` - Final compiled database
- `docs/outlets_research.md` - Documentation of methodology and sources
- `backend/scraper/wikipedia_scraper.py` - Scraping tool
- `backend/scraper/url_validator.py` - URL validation utility
- Tests for the scraping functionality

### 5. Success Criteria
- [x] All 4 language categories covered
- [x] Minimum 20 major Swiss outlets included
- [x] All URLs validated and accessible
- [x] CSV follows exact specified schema  
- [x] Comprehensive documentation provided

## Implementation Steps

### Phase 1: Setup and Initial Scraping
1. Create new branch `feature/swiss-outlets-database`
2. Set up Python scraping environment
3. Create basic Wikipedia scraper
4. Extract German language outlets first (largest category)

### Phase 2: Multi-language Extraction  
5. Extend scraper for French outlets
6. Add Italian outlets extraction
7. Add Romansch outlets extraction
8. Handle edge cases and data inconsistencies

### Phase 3: URL Research and Validation
9. Research actual website URLs for each outlet
10. Implement URL accessibility validation
11. Handle redirects and domain changes
12. Manual verification for unclear cases

### Phase 4: Data Compilation and Quality
13. Merge all data into single CSV with proper schema
14. Data cleaning and normalization
15. Validate completeness (20+ outlets minimum)
16. Cross-reference with known major Swiss outlets

### Phase 5: Testing and Documentation
17. Write unit tests for scraper functions
18. Write integration tests for full pipeline
19. Create comprehensive documentation
20. Code review and cleanup

### Phase 6: Delivery
21. Final validation of all requirements
22. Create pull request with detailed description
23. Request review from maintainers

## Technical Considerations

### Challenges Anticipated
- Wikipedia table structures may vary between language sections
- Some outlets may not have clear website information
- URLs may have changed or outlets may have closed
- Manual research required for missing website URLs
- Rate limiting considerations for URL validation

### Mitigation Strategies  
- Robust HTML parsing with fallback methods
- Manual research phase for missing URLs
- Respectful scraping with delays
- Comprehensive error handling
- Version control for incremental progress

## Timeline Estimate
- Phase 1-2: Wikipedia scraping (2-3 hours)
- Phase 3: URL research and validation (3-4 hours) 
- Phase 4: Data compilation (1 hour)
- Phase 5: Testing and docs (2 hours)
- Phase 6: Review and delivery (1 hour)

**Total Estimated Time: 9-11 hours**

## Next Actions
1. Create feature branch
2. Start with German language outlets extraction
3. Build iteratively, testing each language section
4. Document findings and challenges as we go