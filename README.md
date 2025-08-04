# Swiss News Aggregator

A multilingual Swiss news aggregator website that displays the most recent articles and enables users to explore similar stories via semantic search.

## Project Structure

```
swissnews/
├── backend/
│   ├── scraper/          # Web scraping module for Swiss news outlets
│   ├── database/         # PostgreSQL database schemas and migrations
│   ├── vector_db/        # Vector database operations for embeddings
│   └── api/              # REST API endpoints
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── utils/        # Utility functions
│   │   └── types/        # TypeScript type definitions
│   └── public/           # Static assets
├── scripts/              # Automation and deployment scripts
├── data/
│   ├── raw/              # Raw scraped data
│   └── processed/        # Processed and cleaned data
├── config/               # Configuration files
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── deployment/           # Docker and deployment configurations
└── docs/                 # Documentation
```

## Features

- **Multilingual Support**: German, French, Italian, and English
- **Semantic Search**: Find similar articles using vector embeddings
- **Periodic Scraping**: Updates every 4 hours from major Swiss news outlets
- **Referendum Information**: Displays upcoming Swiss referendums
- **Future**: Fact-checking with Pro/Contra perspectives

## Getting Started

(Instructions will be added as components are implemented)
