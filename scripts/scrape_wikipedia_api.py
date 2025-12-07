"""
Wikipedia API-based scraper for quantum physics articles.
Uses the official MediaWiki API, which is the recommended approach.
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Set
from collections import deque

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from quantum_seeds import QUANTUM_SEED_URLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WikipediaAPIScraper:
    """Scraper using Wikipedia's official MediaWiki API"""

    def __init__(
        self,
        user_agent: str = "QuantumPhoenixBot/1.0 (Educational Research Project; Contact: your.email@example.com)",
        delay_seconds: float = 1.0,
        timeout: int = 30,
        max_pages: int = 200
    ):
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self.max_pages = max_pages

        # Wikipedia API endpoint
        self.api_url = "https://en.wikipedia.org/w/api.php"

        # Setup session with retries
        self.session = self._create_session()

        # Rate limiting
        self.last_request_time = 0

        # Tracking
        self.visited_titles: Set[str] = set()
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

    def respect_rate_limit(self):
        """Implement polite rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self.last_request_time = time.time()

    def url_to_title(self, url: str) -> str:
        """Extract Wikipedia title from URL"""
        # https://en.wikipedia.org/wiki/Quantum_mechanics -> Quantum_mechanics
        if '/wiki/' in url:
            return url.split('/wiki/')[-1]
        return url

    def get_page_content(self, title: str) -> Dict:
        """Get page content using MediaWiki API"""
        self.respect_rate_limit()

        params = {
            'action': 'query',
            'format': 'json',
            'titles': title,
            'prop': 'extracts|info|links',
            'explaintext': True,  # Get plain text instead of HTML
            'exsectionformat': 'plain',
            'pllimit': 50,  # Get up to 50 links
            'inprop': 'url',
            'redirects': 1  # Follow redirects
        }

        try:
            logger.info(f"Fetching: {title}")
            response = self.session.get(
                self.api_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Extract page data
            pages = data.get('query', {}).get('pages', {})
            page_id = list(pages.keys())[0]
            page_data = pages[page_id]

            # Check if page exists
            if 'missing' in page_data:
                logger.warning(f"Page not found: {title}")
                return None

            # Extract content
            content = page_data.get('extract', '')
            if not content or len(content) < 100:
                logger.warning(f"Insufficient content for: {title}")
                return None

            # Extract links
            links = []
            for link in page_data.get('links', []):
                link_title = link.get('title', '')
                # Only include links that might be quantum-related
                link_lower = link_title.lower()
                quantum_keywords = ['quantum', 'physics', 'mechanics', 'particle', 'wave',
                                   'photon', 'electron', 'atom', 'spin', 'entangle']
                if any(kw in link_lower for kw in quantum_keywords):
                    links.append(f"https://en.wikipedia.org/wiki/{link_title.replace(' ', '_')}")

            result = {
                'id': title.replace(' ', '_'),
                'url': page_data.get('fullurl', f"https://en.wikipedia.org/wiki/{title}"),
                'title': page_data.get('title', title),
                'content': content,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'outgoing_links': links[:20]  # Limit stored links
            }

            logger.info(f"Successfully fetched: {result['title']} ({len(content)} chars)")
            return result

        except requests.RequestException as e:
            logger.error(f"Error fetching {title}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {title}: {e}")
            return None

    def crawl(self, seed_urls: List[str]) -> List[Dict]:
        """Crawl Wikipedia starting from seed URLs using BFS"""
        # Convert URLs to titles
        seed_titles = [self.url_to_title(url) for url in seed_urls]
        queue = deque(seed_titles)

        logger.info(f"Starting crawl with {len(seed_titles)} seed titles")
        logger.info(f"Max pages: {self.max_pages}")

        while queue and len(self.scraped_pages) < self.max_pages:
            title = queue.popleft()

            # Skip if already visited
            if title in self.visited_titles:
                continue

            self.visited_titles.add(title)

            page_data = self.get_page_content(title)

            if page_data:
                self.scraped_pages.append(page_data)
                logger.info(f"Progress: {len(self.scraped_pages)}/{self.max_pages} pages")

                # Add outgoing links to queue
                for link in page_data.get('outgoing_links', []):
                    link_title = self.url_to_title(link)
                    if link_title not in self.visited_titles:
                        queue.append(link_title)

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
    parser = argparse.ArgumentParser(
        description='Scrape Wikipedia quantum physics articles using the MediaWiki API (RECOMMENDED METHOD)'
    )
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
        default=1.0,
        help='Delay between requests in seconds (minimum 1.0 for politeness)'
    )
    parser.add_argument(
        '--user-agent',
        type=str,
        default=None,
        help='Custom user agent string (should include contact info)'
    )

    args = parser.parse_args()

    # Initialize scraper with optional custom user agent
    kwargs = {
        'delay_seconds': max(args.delay, 1.0),  # Enforce minimum 1 second
        'max_pages': args.max_pages
    }
    if args.user_agent:
        kwargs['user_agent'] = args.user_agent

    scraper = WikipediaAPIScraper(**kwargs)

    # Crawl using API
    scraper.crawl(QUANTUM_SEED_URLS)

    # Save corpus
    output_dir = Path(args.out)
    scraper.save_corpus(output_dir)

    logger.info("Scraping complete!")


if __name__ == '__main__':
    main()
