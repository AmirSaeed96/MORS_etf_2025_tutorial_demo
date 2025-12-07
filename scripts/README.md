# Wikipedia Scraper Scripts

This directory contains scripts for building a quantum physics corpus from Wikipedia articles.

## 📋 Overview

There are **two methods** for scraping Wikipedia content:

1. **`scrape_wikipedia_api.py`** ✅ **RECOMMENDED** - Uses Wikipedia's official MediaWiki API
2. **`scrape_wikipedia.py`** ⚠️ **DEPRECATED** - HTML scraping (legacy method)

**Always use the API-based scraper unless you have a specific reason not to.**

## 🚀 Quick Start (Recommended Method)

### Using the MediaWiki API (Recommended)

```bash
# Basic usage with defaults
uv run python scripts/scrape_wikipedia_api.py

# Custom configuration
uv run python scripts/scrape_wikipedia_api.py \
    --max-pages 100 \
    --delay 1.0 \
    --out data/corpus/quantum
```

**Why use the API?**
- ✅ Officially supported by Wikipedia
- ✅ No robots.txt issues
- ✅ Faster and more reliable
- ✅ Returns clean, structured data
- ✅ Lower bandwidth usage
- ✅ No HTML parsing needed

## 📖 Detailed Usage

### scrape_wikipedia_api.py (Recommended)

**Description**: Fetches Wikipedia content using the official MediaWiki API.

**Arguments**:
```
--max-pages     Maximum number of pages to scrape (default: 200)
--out           Output directory (default: data/corpus/quantum)
--delay         Delay between requests in seconds (default: 1.0, minimum: 1.0)
--user-agent    Custom user agent (optional, should include contact info)
```

**Examples**:

```bash
# Scrape 50 pages for quick testing
uv run python scripts/scrape_wikipedia_api.py --max-pages 50

# Scrape with custom delay and output location
uv run python scripts/scrape_wikipedia_api.py \
    --max-pages 200 \
    --delay 1.5 \
    --out data/my_corpus

# Use custom user agent with your contact info
uv run python scripts/scrape_wikipedia_api.py \
    --user-agent "MyBot/1.0 (Contact: your.email@example.com; Educational Research)"
```

**Output Structure**:
```
data/corpus/quantum/
├── index.json                    # Corpus metadata and page index
├── Quantum_mechanics.json        # Individual page files
├── Quantum_entanglement.json
├── Quantum_computing.json
└── ...
```

**Expected Runtime**:
- 50 pages: ~1-2 minutes
- 200 pages: ~5-8 minutes
- Rate: ~1 page per second (with 1.0s delay)

---

### scrape_wikipedia.py (Legacy/Deprecated)

**Description**: Scrapes Wikipedia by parsing HTML pages. **Not recommended.**

**Why it might be blocked**:
- Some robots.txt parsers may block custom user agents
- Requires Mozilla-compatible user agent string
- More prone to breaking if Wikipedia changes their HTML structure
- Slower than API method
- Higher bandwidth usage

**Arguments**:
```
--max-pages     Maximum number of pages to scrape (default: 200)
--out           Output directory (default: data/corpus/quantum)
--delay         Delay between requests in seconds (default: 2.0, minimum: 2.0)
--user-agent    Custom Mozilla-compatible user agent (optional)
```

**When to use this method**:
- Only if the API method is not working
- If you need specific HTML elements not available via API
- For educational purposes to understand web scraping

**Example**:
```bash
# Use at your own risk - API method is better!
uv run python scripts/scrape_wikipedia.py \
    --max-pages 50 \
    --delay 2.0
```

---

## 🔧 Configuration Files

### quantum_seeds.py

Contains the seed URLs for quantum physics articles to start the crawl.

**Seed Categories**:
- Fundamental concepts (quantum mechanics, superposition, entanglement)
- Mathematical framework (Schrödinger equation, Hilbert space)
- Quantum properties (spin, tunneling, decoherence)
- Interpretations (Copenhagen, Many-worlds)
- Applications (quantum computing, cryptography)
- Advanced topics (QED, QCD, quantum gravity)
- Experimental physics (double-slit, Bell tests)

**Keyword Filtering**: Both scrapers use quantum-related keywords to discover additional relevant pages through links.

---

## 🛠️ Troubleshooting

### Issue: "robots.txt disallows" error

**Cause**: Using HTML scraper (`scrape_wikipedia.py`) with a user agent that Wikipedia's robots.txt blocks.

**Solution 1 (Best)**: Switch to API scraper
```bash
uv run python scripts/scrape_wikipedia_api.py
```

**Solution 2**: Update user agent in HTML scraper to include contact info
```bash
uv run python scripts/scrape_wikipedia.py \
    --user-agent "Mozilla/5.0 (compatible; YourBot/1.0; +https://yoursite.com; your@email.com)"
```

### Issue: "No API key" or authentication errors

**Answer**: Wikipedia's public API requires **NO API KEY**. If you see this error, you're likely using the wrong endpoint or method.

The correct API endpoint is: `https://en.wikipedia.org/w/api.php`

### Issue: Getting blocked or rate-limited

**Solutions**:
1. Increase delay between requests:
   ```bash
   --delay 2.0  # for API scraper
   --delay 3.0  # for HTML scraper
   ```

2. Use a proper user agent with contact info:
   ```bash
   --user-agent "BotName/1.0 (Contact: you@example.com; Purpose: Educational)"
   ```

3. Reduce max pages for testing:
   ```bash
   --max-pages 20
   ```

### Issue: Empty or missing content

**Possible causes**:
- Network connectivity issues
- Page redirects or disambiguation pages
- Articles with minimal text content
- API timeout

**Check**:
1. Review the logs for specific error messages
2. Verify internet connection
3. Check `index.json` to see which pages were successfully scraped
4. Try reducing `--max-pages` to isolate the issue

### Issue: Slow scraping

**Expected behavior**:
- API scraper: ~1 second per page (with default 1.0s delay)
- HTML scraper: ~2-3 seconds per page (with default 2.0s delay + parsing)

**If slower than expected**:
1. Check your internet connection
2. Verify Wikipedia.org is accessible
3. Check if your delay is set too high
4. Monitor network activity

---

## 📊 Output Format

Each scraped page is saved as a JSON file with this structure:

```json
{
  "id": "Quantum_mechanics",
  "url": "https://en.wikipedia.org/wiki/Quantum_mechanics",
  "title": "Quantum mechanics",
  "content": "Full article text content...",
  "scraped_at": "2025-12-07 10:30:45",
  "outgoing_links": [
    "https://en.wikipedia.org/wiki/Wave_function",
    "https://en.wikipedia.org/wiki/Quantum_superposition",
    "..."
  ]
}
```

The `index.json` file provides an overview:

```json
{
  "total_pages": 200,
  "scraped_at": "2025-12-07 10:45:12",
  "pages": [
    {
      "id": "Quantum_mechanics",
      "title": "Quantum mechanics",
      "url": "https://en.wikipedia.org/wiki/Quantum_mechanics"
    },
    ...
  ]
}
```

---

## 🔒 Best Practices

### User Agent Guidelines

**Always include**:
1. Bot name and version
2. Contact information (email or URL)
3. Purpose (e.g., "Educational Research")

**Good examples**:
```
"QuantumResearchBot/1.0 (Contact: researcher@university.edu; Educational Project)"
"MyBot/2.0 (+https://github.com/username/project; Academic Study)"
"Mozilla/5.0 (compatible; StudyBot/1.0; Contact: you@example.com)"
```

**Bad examples**:
```
"Python/3.9"              # No contact info
"MyBot"                   # No version or contact
"QuantumBot/1.0"          # No contact info or purpose
```

### Rate Limiting

**Recommended delays**:
- API scraper: 1.0 - 2.0 seconds (default: 1.0s)
- HTML scraper: 2.0 - 3.0 seconds (default: 2.0s)

**Why?**
- Respects Wikipedia's server resources
- Reduces chance of being blocked
- Follows polite web scraping etiquette
- Complies with Wikipedia's usage guidelines

### Corpus Size

**Recommendations**:
- **Testing**: 20-50 pages (~1-2 minutes)
- **Development**: 100-200 pages (~5-10 minutes)
- **Production**: 500-1000 pages (~20-40 minutes)

**Consider**:
- Storage space (each page ~5-50 KB)
- Processing time for indexing
- Relevance of additional pages

---

## 🔗 Next Steps

After scraping Wikipedia, you need to build a vector index:

```bash
# Build ChromaDB index from scraped corpus
uv run python scripts/build_index.py \
    --corpus-dir data/corpus/quantum \
    --chroma-dir .chroma/quantum_wiki
```

See the main [README.md](../README.md) for complete setup instructions.

---

## 📚 Additional Resources

- [Wikipedia API Documentation](https://www.mediawiki.org/wiki/API:Main_page)
- [Wikipedia Bot Policy](https://en.wikipedia.org/wiki/Wikipedia:Bots)
- [Robots Exclusion Standard](https://www.robotstxt.org/)
- [MediaWiki API Sandbox](https://en.wikipedia.org/wiki/Special:ApiSandbox)

---

## ⚠️ Legal & Ethical Notes

1. **Wikipedia Content License**: All Wikipedia content is licensed under CC BY-SA 3.0
2. **Robots.txt Compliance**: Both scrapers respect robots.txt (API automatically, HTML explicitly)
3. **Rate Limiting**: Always use appropriate delays between requests
4. **Attribution**: Properly attribute Wikipedia as the source in your project
5. **Educational Use**: These scripts are for educational/research purposes
6. **No Commercial Use**: Check Wikipedia's terms if using for commercial purposes

---

## 🐛 Known Issues

1. **HTML Scraper** may be blocked if user agent is not properly configured
2. **Disambiguation pages** may result in empty or unexpected content
3. **Very long articles** may occasionally timeout
4. **Link discovery** is limited to quantum-related keywords (by design)

---

## 💡 Tips

1. **Start small**: Test with `--max-pages 20` before running larger scrapes
2. **Monitor logs**: Watch for warnings about missing content or failed pages
3. **Check index.json**: Verify the pages you expected were scraped
4. **Use API scraper**: It's faster, more reliable, and officially supported
5. **Update user agent**: Include your actual contact information

---

**Questions?** Check the main [README.md](../README.md) or review Wikipedia's API documentation.
