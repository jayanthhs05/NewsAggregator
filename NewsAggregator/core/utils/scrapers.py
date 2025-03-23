import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser


def get_robots_delay(url):
    rp = RobotFileParser()
    rp.set_url(f"{url}/robots.txt")
    rp.read()
    return rp.crawl_delay("*") or 5


def scrape_apnews(url):
    delay = get_robots_delay(url)
    session = requests.Session()
    session.headers.update({"User-Agent": "NewsAggregatorBot/1.0"})

    response = session.get(url, timeout=10)
    soup = BeautifulSoup(response.content, "lxml")

    articles = []
    for item in soup.select(".FeedCard"):
        articles.append(
            {
                "title": item.select_one("h2").text.strip(),
                "content": item.select_one(".content").text.strip(),
                "date": item.select_one("time")["datetime"],
            }
        )

    return articles
