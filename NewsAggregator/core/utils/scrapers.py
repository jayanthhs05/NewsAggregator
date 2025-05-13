import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
import time
import random
import logging
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse
import json

logger = logging.getLogger(__name__)


def get_robots_delay(url):
    try:
        rp = RobotFileParser()
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        rp.set_url(f"{base_url}/robots.txt")
        rp.read()
        return rp.crawl_delay("*") or 5
    except Exception as e:
        logger.warning(f"Error reading robots.txt for {url}: {str(e)}")
        return 5


def is_allowed(url, user_agent="NewsAggregatorBot/1.0"):
    try:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        rp = RobotFileParser()
        rp.set_url(f"{base_url}/robots.txt")
        rp.read()

        return rp.can_fetch(user_agent, url)
    except Exception as e:
        logger.warning(f"Error checking robots.txt for {url}: {str(e)}")
        return True


def get_session(user_agent=None):
    if user_agent is None:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    })
    return session


def scrape_with_delay(url, session=None, selector=None, timeout=15):
    if not session:
        session = get_session()

    try:
        time.sleep(random.uniform(1, 3))  # Random delay between 1-3 seconds
        response = session.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")

        if selector:
            return soup.select(selector)
        return soup
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return None


def parse_date(date_str, formats=None):
    if not date_str:
        return datetime.now()

    # Handle ISO 8601 durations (e.g., P3M,47S)
    if date_str.startswith('P') and any(c in date_str for c in 'YMDHS'):
        logger.warning(f"Could not parse date (duration): {date_str}")
        return datetime.now()

    # Try using dateutil.parser if available
    try:
        from dateutil import parser as dateutil_parser
        return dateutil_parser.parse(date_str)
    except Exception:
        pass

    if formats is None:
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %b %Y",
            "%Y-%m-%d",
            "%B %d, %Y, %I:%M %p",
            "%B %d, %Y %H:%M",
            "%d %B %Y",
            "%A, %B %d, %Y",
            "%A %B %d %Y",
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%Y-%m-%dT%H:%M:%S.%fZ",      # RFC 3339/ISO 8601
            "%a, %d %b %Y %H:%M:%S GMT",  # RSS/Atom
        ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return datetime.now()


def scrape_npr(url):
    session = get_session()
    articles = []

    try:
        # Try the RSS feed first (more reliable than API)
        rss_url = "https://feeds.npr.org/1001/rss.xml"
        logger.info(f"Attempting to fetch NPR RSS feed from {rss_url}")
        response = session.get(rss_url, timeout=15)
        if response.status_code == 200:
            logger.info("Successfully fetched NPR RSS feed")
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")[:15]
            
            for item in items:
                try:
                    articles.append({
                        "title": item.title.text if item.title else "",
                        "content": item.description.text if item.description else "",
                        "date": item.pubDate.text if item.pubDate else "",
                        "url": item.link.text if item.link else "",
                    })
                except Exception as e:
                    logger.error(f"Error parsing NPR RSS item: {str(e)}")
                    continue
            return articles

        logger.warning(f"Failed to fetch NPR RSS feed, falling back to HTML scraping")
        # Fallback to HTML scraping
        soup = scrape_with_delay(url, session)
        if not soup:
            logger.error("Failed to scrape NPR HTML")
            return []

        # Updated selectors for NPR's current HTML structure
        headlines = soup.select("article") or soup.select(".story-wrap")

        for headline in headlines[:15]:
            try:
                # Try different possible title selectors
                title_elem = (
                    headline.select_one("h3 a") or 
                    headline.select_one(".title a") or 
                    headline.select_one("a.title") or
                    headline.select_one("h2 a")
                )
                
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                article_url = urljoin(url, title_elem.get("href", ""))

                if not article_url:
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                # Updated content selectors
                content_elements = (
                    article_soup.select(".storytext p") or 
                    article_soup.select("[data-testid='story-text'] p") or
                    article_soup.select(".story-body p") or
                    article_soup.select(".article-body p")
                )
                content = " ".join([p.text.strip() for p in content_elements if p.text.strip()])

                # Updated date selectors
                date_elem = (
                    article_soup.select_one("time") or
                    article_soup.select_one(".date") or
                    article_soup.select_one(".timestamp")
                )
                date_str = date_elem.get("datetime") if date_elem and date_elem.has_attr("datetime") else ""
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append({
                    "title": title,
                    "content": content[:5000],
                    "date": date.isoformat(),
                    "url": article_url,
                })

            except Exception as e:
                logger.error(f"Error parsing NPR article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping NPR: {str(e)}")
        return []


def scrape_guardian(url):
    session = get_session()
    articles = []

    try:
        # Try the API endpoint first
        api_url = "https://content.guardianapis.com/search"
        params = {
            "api-key": "test",  # You'll need to replace this with a real API key
            "show-fields": "bodyText,publication",
            "page-size": 15
        }
        response = session.get(api_url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("response", {}).get("results", [])[:15]:
                try:
                    articles.append({
                        "title": item.get("webTitle", ""),
                        "content": item.get("fields", {}).get("bodyText", ""),
                        "date": item.get("webPublicationDate", ""),
                        "url": item.get("webUrl", ""),
                    })
                except Exception as e:
                    logger.error(f"Error parsing Guardian article: {str(e)}")
                    continue
            return articles

        # Fallback to HTML scraping
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".fc-item__title") or soup.select(".js-headline-text")

        for headline in headlines[:15]:
            try:
                link_elem = headline.find_parent("a") or headline.find("a")

                if not link_elem:
                    continue

                title = headline.text.strip()
                article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url:
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(".article-body-commercial-selector p") or article_soup.select(".content__article-body p")
                content = " ".join([p.text.strip() for p in content_elements if p.text.strip()])

                date_elem = article_soup.select_one("time")
                date_str = date_elem.get("datetime") if date_elem and date_elem.has_attr("datetime") else ""
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append({
                    "title": title,
                    "content": content[:5000],
                    "date": date.isoformat(),
                    "url": article_url,
                })

            except Exception as e:
                logger.error(f"Error parsing Guardian article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping Guardian: {str(e)}")
        return []


def scrape_aljazeera(url):
    session = get_session()
    articles = []

    try:
        # Try the API endpoint first
        api_url = "https://www.aljazeera.com/api/v1/feed"
        response = session.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", [])[:15]:
                try:
                    articles.append({
                        "title": item.get("title", ""),
                        "content": item.get("description", ""),
                        "date": item.get("pubDate", ""),
                        "url": item.get("link", ""),
                    })
                except Exception as e:
                    logger.error(f"Error parsing Al Jazeera article: {str(e)}")
                    continue
            return articles

        # Fallback to HTML scraping
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".gc__title") or soup.select(".article-card__title")

        for headline in headlines[:15]:
            try:
                link_elem = headline.find("a") or headline.find_parent("a")

                if not link_elem:
                    continue

                title = headline.text.strip()
                article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url:
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(".wysiwyg p") or article_soup.select("article p")
                content = " ".join([p.text.strip() for p in content_elements if p.text.strip()])

                date_elem = article_soup.select_one(".article-dates__modified time") or article_soup.select_one("time")
                date_str = date_elem.get("datetime") if date_elem and date_elem.has_attr("datetime") else ""
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append({
                    "title": title,
                    "content": content[:5000],
                    "date": date.isoformat(),
                    "url": article_url,
                })

            except Exception as e:
                logger.error(f"Error parsing Al Jazeera article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping Al Jazeera: {str(e)}")
        return []


def scrape_abc_au(url):
    session = get_session()
    articles = []

    try:
        # Try the API endpoint first
        api_url = "https://www.abc.net.au/news/feed/45910/rss.xml"
        response = session.get(api_url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")[:15]
            
            for item in items:
                try:
                    articles.append({
                        "title": item.title.text if item.title else "",
                        "content": item.description.text if item.description else "",
                        "date": item.pubDate.text if item.pubDate else "",
                        "url": item.link.text if item.link else "",
                    })
                except Exception as e:
                    logger.error(f"Error parsing ABC AU article: {str(e)}")
                    continue
            return articles

        # Fallback to HTML scraping
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".doctype-article h3") or soup.select(".title-link")

        for headline in headlines[:15]:
            try:
                link_elem = headline.find("a") or headline.find_parent("a")

                if not link_elem:
                    continue

                title = headline.text.strip()
                article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url:
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(".article-body p") or article_soup.select("._1HzXw p")
                content = " ".join([p.text.strip() for p in content_elements if p.text.strip()])

                date_elem = article_soup.select_one(".timestamp") or article_soup.select_one("time")
                date_str = date_elem.get("datetime") if date_elem and date_elem.has_attr("datetime") else ""
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append({
                    "title": title,
                    "content": content[:5000],
                    "date": date.isoformat(),
                    "url": article_url,
                })

            except Exception as e:
                logger.error(f"Error parsing ABC AU article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping ABC AU: {str(e)}")
        return []


def scrape_usa_today(url):
    session = get_session()
    articles = []

    try:
        # Try the API endpoint first
        api_url = "https://www.usatoday.com/arc/outboundfeeds/rss/"
        response = session.get(api_url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")[:15]
            
            for item in items:
                try:
                    articles.append({
                        "title": item.title.text if item.title else "",
                        "content": item.description.text if item.description else "",
                        "date": item.pubDate.text if item.pubDate else "",
                        "url": item.link.text if item.link else "",
                    })
                except Exception as e:
                    logger.error(f"Error parsing USA Today RSS item: {str(e)}")
                    continue
            return articles

        # Fallback to HTML scraping
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".gnt_m_flm_a") or soup.select(".gnt_m_flm_a h3")

        for headline in headlines[:15]:
            try:
                link_elem = headline.find("a") or headline.find_parent("a")
                if not link_elem:
                    continue

                title = headline.text.strip()
                article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url:
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(".gnt_ar_b p") or article_soup.select(".gnt_ar_b")
                content = " ".join([p.text.strip() for p in content_elements if p.text.strip()])

                date_elem = article_soup.select_one("time") or article_soup.select_one(".gnt_ar_dt")
                date_str = date_elem.get("datetime") if date_elem and date_elem.has_attr("datetime") else ""
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append({
                    "title": title,
                    "content": content[:5000],
                    "date": date.isoformat(),
                    "url": article_url,
                })

            except Exception as e:
                logger.error(f"Error parsing USA Today article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping USA Today: {str(e)}")
        return []


SCRAPERS = {
    "npr.org": scrape_npr,
    "theguardian.com": scrape_guardian,
    "aljazeera.com": scrape_aljazeera,
    "abc.net.au": scrape_abc_au,
    "usatoday.com": scrape_usa_today,
}


def get_scraper_for_url(url):

    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    for known_domain, scraper in SCRAPERS.items():
        if known_domain in domain:
            return scraper

    return None
