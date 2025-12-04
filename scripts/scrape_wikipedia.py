"""
Wikipedia scraper for quantum physics articles.
Respects robots.txt and implements polite rate limiting.
"""

import argparse
import json
import logging
import re
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from quantum_seeds import QUANTUM_KEYWORDS, QUANTUM_SEED_URLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WikipediaScraper:
    """Scraper for Wikipedia articles with robots.txt compliance"""

    def __init__(
        self,
        user_agent: str = "QuantumPhoenixBot/1.0 (Educational Demo)",
        delay_seconds: float = 2.0,
        timeout: int = 30,
        max_pages: int = 200
    ):
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self.max_pages = max_pages

        # Setup session with retries
        self.session = self._create_session()

        # Robots.txt parser
        self.robots_parser = RobotFileParser()
        self.robots_parser.set_url("https://en.wikipedia.org/robots.txt")

        # Rate limiting
        self.last_request_time = 0

        # Tracking
        self.visited_urls: Set[str] = set()
        self.scraped_pages: List[Dict] = []

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic"""
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update({
            'User-Agent': self.user_agent
        })

        return session

    def load_robots_txt(self):
        """Load and parse robots.txt"""
        try:
            logger.info("Loading robots.txt from Wikipedia...")
            self.robots_parser.read()
            logger.info("robots.txt loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load robots.txt: {e}")
            raise

    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        return self.robots_parser.can_fetch(self.user_agent, url)

    def respect_rate_limit(self):
        """Implement polite rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self.last_request_time = time.time()

    def extract_article_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract clean article content from Wikipedia page"""
        # Find the main content div
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return None

        # Find all paragraphs in the article body
        body_content = content_div.find('div', {'class': 'mw-parser-output'})
        if not body_content:
            return None

        # Remove unwanted elements
        for element in body_content.find_all(['table', 'style', 'script', 'sup', 'div']):
            if element.get('class'):
                # Keep certain informative divs but remove navboxes, infoboxes, etc.
                classes = element.get('class', [])
                if any(c in str(classes) for c in ['navbox', 'infobox', 'metadata', 'ambox', 'toc']):
                    element.decompose()
            elif element.name in ['table', 'style', 'script']:
                element.decompose()

        # Extract text from paragraphs
        paragraphs = body_content.find_all('p')
        text_parts = []

        for p in paragraphs:
            text = p.get_text(strip=True)
            # Filter out very short paragraphs and references
            if len(text) > 20 and not text.startswith('['):
                text_parts.append(text)

        clean_text = '\n\n'.join(text_parts)

        # Clean up excessive whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text)
        clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)

        return clean_text.strip()

    def extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract relevant Wikipedia article links"""
        links = []

        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return links

        for a_tag in content_div.find_all('a', href=True):
            href = a_tag['href']

            # Only process wiki article links
            if not href.startswith('/wiki/'):
                continue

            # Skip special pages
            if any(skip in href for skip in [':', 'Special:', 'Help:', 'Talk:', 'File:', 'Wikipedia:']):
                continue

            # Build full URL
            full_url = urljoin(current_url, href)

            # Check if link text or href contains quantum-related keywords
            link_text = a_tag.get_text().lower()
            href_lower = href.lower()

            if any(keyword in link_text or keyword in href_lower for keyword in QUANTUM_KEYWORDS):
                links.append(full_url)

        return links

    def scrape_page(self, url: str) -> Optional[Dict]:
        """Scrape a single Wikipedia page"""
        # Check if already visited
        if url in self.visited_urls:
            return None

        # Check robots.txt
        if not self.can_fetch(url):
            logger.warning(f"robots.txt disallows: {url}")
            return None

        # Mark as visited
        self.visited_urls.add(url)

        # Respect rate limiting
        self.respect_rate_limit()

        try:
            logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            # Extract title
            title_tag = soup.find('h1', {'id': 'firstHeading'})
            title = title_tag.get_text() if title_tag else urlparse(url).path.split('/')[-1]

            # Extract content
            content = self.extract_article_content(soup)
            if not content:
                logger.warning(f"No content extracted from: {url}")
                return None

            # Extract links for crawling
            links = self.extract_links(soup, url)

            page_data = {
                'id': urlparse(url).path.split('/')[-1],
                'url': url,
                'title': title,
                'content': content,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'outgoing_links': links[:20]  # Limit stored links
            }

            logger.info(f"Successfully scraped: {title} ({len(content)} chars)")
            return page_data

        except requests.RequestException as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            return None

    def crawl(self, seed_urls: List[str]) -> List[Dict]:
        """Crawl Wikipedia starting from seed URLs using BFS"""
        queue = deque(seed_urls)

        logger.info(f"Starting crawl with {len(seed_urls)} seed URLs")
        logger.info(f"Max pages: {self.max_pages}")

        while queue and len(self.scraped_pages) < self.max_pages:
            url = queue.popleft()

            # Skip if already visited
            if url in self.visited_urls:
                continue

            page_data = self.scrape_page(url)

            if page_data:
                self.scraped_pages.append(page_data)
                logger.info(f"Progress: {len(self.scraped_pages)}/{self.max_pages} pages")

                # Add outgoing links to queue
                for link in page_data.get('outgoing_links', []):
                    if link not in self.visited_urls:
                        queue.append(link)

        logger.info(f"Crawl complete. Scraped {len(self.scraped_pages)} pages")
        return self.scraped_pages

    def save_corpus(self, output_dir: Path):
        """Save scraped pages to disk"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save each page as individual JSON file
        for page in self.scraped_pages:
            page_id = page['id']
            filepath = output_dir / f"{page_id}.json"

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(page, f, indent=2, ensure_ascii=False)

        # Save index file
        index_data = {
            'total_pages': len(self.scraped_pages),
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'pages': [
                {
                    'id': p['id'],
                    'title': p['title'],
                    'url': p['url']
                }
                for p in self.scraped_pages
            ]
        }

        with open(output_dir / 'index.json', 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Corpus saved to {output_dir}")
        logger.info(f"Total pages: {len(self.scraped_pages)}")


def main():
    parser = argparse.ArgumentParser(description='Scrape Wikipedia quantum physics articles')
    parser.add_argument(
        '--max-pages',
        type=int,
        default=200,
        help='Maximum number of pages to scrape'
    )
    parser.add_argument(
        '--out',
        type=str,
        default='data/corpus/quantum',
        help='Output directory for scraped content'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds'
    )

    args = parser.parse_args()

    # Initialize scraper
    scraper = WikipediaScraper(
        delay_seconds=args.delay,
        max_pages=args.max_pages
    )

    # Load robots.txt
    scraper.load_robots_txt()

    # Crawl
    scraper.crawl(QUANTUM_SEED_URLS)

    # Save corpus
    output_dir = Path(args.out)
    scraper.save_corpus(output_dir)

    logger.info("Scraping complete!")


if __name__ == '__main__':
    main()
