import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, #format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='crawl.log',
                    filemode='w',
                    encoding='utf-8-sig'
)

logger = logging.getLogger(__name__)

visited = set()

def crawl(url, base):
    if "%2Fotzyvy%2Fotzyvy" in url:
        return
    if "?PAGEN_1=" in url:
        return
    if url in visited:
        return
    visited.add(url)
    logger.info(f"Crawling {url}")
    try:
        response = requests.get(url, allow_redirects=False, timeout=5)
        if response.is_redirect or response.status_code in (301, 302):
            redirect_url = response.headers.get('Location')
            if redirect_url and redirect_url.endswith('/'):
                print(f"🔁 Redirect to slash: {url} → {redirect_url}")
                logger.info(f"Redirect to slash: {url} → {redirect_url}")
        if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
            soup = BeautifulSoup(response.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                next_url = urljoin(base, a['href'])
                if base in next_url and urlparse(next_url).scheme.startswith('http'):
                    crawl(next_url, base)
    except Exception as e:
        print(f"⚠️ Error with {url}: {e}")
        logger.error(f"Error with {url}: {e}")

# Пример запуска
start_url = "https://www.rusgeocom.ru"
crawl(start_url, start_url)