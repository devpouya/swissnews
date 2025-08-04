Aggregator for swiss news websites.

# PLAN The Architecture
- This is the spec document for the project
- Ask clarifiying questions if necessary

# Overview:
A multilingual Swiss news aggregator website that displays the most recent articles and enables users to explore similar stories via semantic search.

# Core Features:

## Homepage:
- Displays the latest articles as cards.
- Includes a section for upcoming Swiss referendums.

## Article Page:
- Clicking a card leads to a page with semantically similar articles.
- Similarity determined using a vector database based on headline embeddings.

## Data Pipeline:
- Articles scraped from all major Swiss news outlets every 4 hours.
- Headlines + metadata stored in a vector DB for similarity search.

## Multilingual Support:
- Available in German, French, Italian, and English.
- Language toggle via tabs; translation powered by an LLM.
- If there is an original version of the article in the corresponding language, use that, otherwise translate.

## Fact-Checking (Future Feature):
- Each article will include LLM-generated Pro and Contra perspectives.
- Based on full article text and headline.

## 1. Scraper
Goal:
Scrape all Swiss news websites every 4 hours and store new articles in a VectorDB database.

1. Scrape all the swiss news websites every 4 hours
2. The list of news outlets can be found
    - https://en.wikipedia.org/wiki/List_of_newspapers_in_Switzerland#German_language
    - They are categorized into German, French, Italian, Romansch and Other languages
    - Find the corresponding website for each, NOT the RSS feed, and save them in a csv file with the following field
    - news website, url, original language, Owner, City, Canton, Occurrence
3. The scraper has to run periodically, every 4 hours, and scrape all the new articles that appeared since the last scrape
4. The scraped articles will be stored with the text (if no paywall), metadata, date and outlet published in a PostgreSQL database

## 2. Vector DB
Goal:
Store article embeddings to enable fast semantic similarity search between headlines and retrieve related articles.

1. For each scraped article, generate an embedding from the headline using a pre-trained language model.
2. Store embeddings in a vector database (e.g., Pinecone, Weaviate, FAISS), alongside:
    - article_id, headline, language, publish_date, outlet_name.
3. Given a selected article, perform a vector similarity query to retrieve semantically similar headlines.
4. Results are filtered to exclude the original article and optionally limited by language or date range.
5. The vector DB is updated every 4 hours, synchronized with the scraper.

## 3. Testing
1. Think hard to add the most impactful tests
2. Add end 2 end tests
3. Add them to a CI/CD pipeline, and if it doesn't exist, create one.
