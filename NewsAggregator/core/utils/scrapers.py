import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
import time
import random
import logging
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse

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


def get_session(user_agent="NewsAggregatorBot/1.0"):
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def scrape_with_delay(url, session=None, selector=None):

    if not session:
        session = get_session()

    delay = get_robots_delay(url)

    if not is_allowed(url):
        logger.warning(f"Scraping not allowed for {url} according to robots.txt")
        return None

    try:
        time.sleep(delay + random.uniform(1, 2))
        response = session.get(url, timeout=10)
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
        ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return datetime.now()


def scrape_apnews(url):
    session = get_session()
    articles = []

    try:
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        for item in soup.select(".FeedCard"):
            try:
                title_elem = item.select_one("h2")
                content_elem = item.select_one(".content")
                date_elem = item.select_one("time")
                link_elem = item.select_one("a")

                if (
                    title_elem
                    and content_elem
                    and date_elem
                    and date_elem.has_attr("datetime")
                ):
                    article_url = urljoin(url, link_elem["href"]) if link_elem else None
                    articles.append(
                        {
                            "title": title_elem.text.strip(),
                            "content": content_elem.text.strip(),
                            "date": date_elem["datetime"],
                            "url": article_url,
                        }
                    )
            except Exception as e:
                logger.error(f"Error parsing AP News article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping AP News: {str(e)}")
        return []


def scrape_reuters(url):
    session = get_session()
    articles = []

    try:
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        article_elements = (
            soup.select("article.story")
            or soup.select(".story-card")
            or soup.select(".media-story-card")
        )

        for article in article_elements[:15]:
            try:
                title_elem = article.select_one("h3") or article.select_one(
                    ".story-title"
                )
                link_elem = article.select_one("a")

                if not title_elem or not link_elem:
                    continue

                title = title_elem.text.strip()
                article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    "p.paragraph"
                ) or article_soup.select(".article-body p")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one("time") or article_soup.select_one(
                    ".article-date"
                )
                date_str = (
                    date_elem["datetime"]
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing Reuters article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping Reuters: {str(e)}")
        return []


def scrape_bbc(url):
    session = get_session()
    articles = []

    try:
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".gs-c-promo") or soup.select(".media-list__item")

        for headline in headlines[:15]:
            try:
                title_elem = headline.select_one(
                    ".gs-c-promo-heading__title"
                ) or headline.select_one("h3")
                link_elem = headline.select_one("a")

                if not title_elem or not link_elem:
                    continue

                title = title_elem.text.strip()
                article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    "[data-component='text-block']"
                ) or article_soup.select(".ssrcss-11r1m41-RichTextComponentWrapper")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one("time")
                date_str = (
                    date_elem.get("datetime")
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing BBC article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping BBC: {str(e)}")
        return []


def scrape_npr(url):
    session = get_session()
    articles = []

    try:
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".title-link") or soup.select(".story-wrap")

        for headline in headlines[:15]:
            try:
                if headline.name == "a":
                    title = headline.text.strip()
                    article_url = urljoin(url, headline.get("href", ""))
                else:
                    title_elem = headline.select_one("h3 a") or headline.select_one(
                        ".title"
                    )
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    article_url = urljoin(url, title_elem.get("href", ""))

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    ".storytext p"
                ) or article_soup.select("[data-testid='story-text'] p")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one("time")
                date_str = (
                    date_elem.get("datetime")
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

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

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    ".article-body-commercial-selector p"
                ) or article_soup.select(".content__article-body p")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one("time")
                date_str = (
                    date_elem.get("datetime")
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing Guardian article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping Guardian: {str(e)}")
        return []


def scrape_cnn(url):
    session = get_session()
    articles = []

    try:
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".container__headline") or soup.select(".cd__headline")

        for headline in headlines[:15]:
            try:
                link_elem = headline.find("a")

                if not link_elem:
                    continue

                title = headline.text.strip()
                article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    ".article__content p"
                ) or article_soup.select(".zn-body__paragraph")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one(
                    ".update-time"
                ) or article_soup.select_one("time")
                date_str = (
                    date_elem.get("datetime")
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()
                    date_str = re.sub(r"^(Updated|Published)\s+", "", date_str)

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing CNN article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping CNN: {str(e)}")
        return []


def scrape_aljazeera(url):
    session = get_session()
    articles = []

    try:
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

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    ".wysiwyg p"
                ) or article_soup.select("article p")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one(
                    ".article-dates__modified time"
                ) or article_soup.select_one("time")
                date_str = (
                    date_elem.get("datetime")
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing Al Jazeera article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping Al Jazeera: {str(e)}")
        return []


def scrape_pbs(url):
    session = get_session()
    articles = []

    try:
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".card-lg__title") or soup.select(".post-title")

        for headline in headlines[:15]:
            try:
                link_elem = headline.find("a") or headline.find_parent("a")

                if not link_elem:
                    continue

                title = headline.text.strip()
                article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    ".body-text p"
                ) or article_soup.select(".pbs-content p")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one(
                    ".post-date time"
                ) or article_soup.select_one("time")
                date_str = (
                    date_elem.get("datetime")
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing PBS article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping PBS: {str(e)}")
        return []


def scrape_usatoday(url):
    session = get_session()
    articles = []

    try:
        soup = scrape_with_delay(url, session)
        if not soup:
            return []

        headlines = soup.select(".gnt_m_th") or soup.select(".css-16tnb46")

        for headline in headlines[:15]:
            try:
                if headline.name == "a":
                    title = headline.text.strip()
                    article_url = urljoin(url, headline.get("href", ""))
                else:
                    link_elem = headline.find("a") or headline.find_parent("a")
                    if not link_elem:
                        continue
                    title = headline.text.strip()
                    article_url = urljoin(url, link_elem.get("href", ""))

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    ".gnt_ar_b p"
                ) or article_soup.select(".story-text p")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one(
                    ".gnt_ar_dt"
                ) or article_soup.select_one("time")
                date_str = (
                    date_elem.get("datetime")
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing USA Today article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping USA Today: {str(e)}")
        return []


def scrape_abc_au(url):
    session = get_session()
    articles = []

    try:
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

                if not article_url or not is_allowed(article_url):
                    continue

                article_soup = scrape_with_delay(article_url, session)
                if not article_soup:
                    continue

                content_elements = article_soup.select(
                    ".article-body p"
                ) or article_soup.select("._1HzXw p")
                content = " ".join(
                    [p.text.strip() for p in content_elements if p.text.strip()]
                )

                date_elem = article_soup.select_one(
                    ".timestamp"
                ) or article_soup.select_one("time")
                date_str = (
                    date_elem.get("datetime")
                    if date_elem and date_elem.has_attr("datetime")
                    else ""
                )
                if not date_str and date_elem:
                    date_str = date_elem.text.strip()

                date = parse_date(date_str)

                articles.append(
                    {
                        "title": title,
                        "content": content[:5000],
                        "date": date.isoformat(),
                        "url": article_url,
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing ABC AU article: {str(e)}")
                continue

        return articles
    except Exception as e:
        logger.error(f"Error scraping ABC AU: {str(e)}")
        return []


SCRAPERS = {
    "apnews.com": scrape_apnews,
    "reuters.com": scrape_reuters,
    "bbc.com": scrape_bbc,
    "bbc.co.uk": scrape_bbc,
    "npr.org": scrape_npr,
    "theguardian.com": scrape_guardian,
    "cnn.com": scrape_cnn,
    "aljazeera.com": scrape_aljazeera,
    "pbs.org": scrape_pbs,
    "usatoday.com": scrape_usatoday,
    "abc.net.au": scrape_abc_au,
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
