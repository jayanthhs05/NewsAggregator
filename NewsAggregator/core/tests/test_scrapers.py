import unittest
import logging
from core.utils.scrapers import (
    get_scraper_for_url,
    scrape_npr,
    scrape_guardian,
    scrape_aljazeera,
    scrape_abc_au,
    SCRAPERS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestScrapers(unittest.TestCase):
    def setUp(self):
        # Test URLs for each news source
        self.test_urls = {
            'npr.org': 'https://www.npr.org/sections/news/',
            'theguardian.com': 'https://www.theguardian.com/international',
            'aljazeera.com': 'https://www.aljazeera.com/news/',
            'abc.net.au': 'https://www.abc.net.au/news/'
        }

    def test_npr_scraper(self):
        """Test NPR scraper specifically with detailed logging"""
        url = self.test_urls['npr.org']
        logger.info(f"Testing NPR scraper with URL: {url}")
        
        try:
            # Test API endpoint first
            logger.info("Attempting to use NPR API endpoint...")
            articles = scrape_npr(url)
            
            if not articles:
                logger.warning("No articles found from NPR API endpoint")
                
                # Try direct HTML scraping
                logger.info("Attempting direct HTML scraping...")
                from core.utils.scrapers import get_session, scrape_with_delay
                session = get_session()
                soup = scrape_with_delay(url, session)
                
                if soup:
                    logger.info("Successfully retrieved HTML content")
                    # Log the available headlines
                    headlines = soup.select(".title-link") or soup.select(".story-wrap")
                    logger.info(f"Found {len(headlines)} headline elements")
                    
                    if headlines:
                        for i, headline in enumerate(headlines[:3]):
                            logger.info(f"Headline {i+1}: {headline.text.strip()}")
                    else:
                        logger.warning("No headline elements found in the HTML")
                else:
                    logger.error("Failed to retrieve HTML content")
            else:
                logger.info(f"Successfully retrieved {len(articles)} articles from NPR")
                for i, article in enumerate(articles[:3]):
                    logger.info(f"Article {i+1}: {article['title']}")
            
            # Check if we got a list of articles
            self.assertIsInstance(articles, list, "NPR scraper did not return a list")
            
            if articles:
                # Check the structure of the first article
                article = articles[0]
                self.assertIsInstance(article, dict, "NPR article is not a dictionary")
                
                # Check required fields
                required_fields = ["title", "content", "date", "url"]
                for field in required_fields:
                    self.assertIn(field, article, f"NPR article missing {field}")
                    self.assertTrue(article[field], f"NPR article has empty {field}")
                
                logger.info(f"Successfully scraped article from NPR: {article['title']}")
            else:
                logger.warning("No articles found for NPR")
                
        except Exception as e:
            logger.error(f"Error testing NPR scraper: {str(e)}")
            raise

    def test_get_scraper_for_url(self):
        """Test if the correct scraper is returned for each URL"""
        for domain, url in self.test_urls.items():
            scraper = get_scraper_for_url(url)
            self.assertIsNotNone(scraper, f"No scraper found for {domain}")
            self.assertIn(scraper, SCRAPERS.values(), f"Scraper for {domain} not in SCRAPERS dict")

    def test_scraper_output_format(self):
        """Test if scrapers return data in the correct format"""
        for domain, url in self.test_urls.items():
            try:
                scraper = get_scraper_for_url(url)
                articles = scraper(url)
                
                # Log the number of articles found
                logger.info(f"Found {len(articles)} articles from {domain}")
                
                # Check if we got a list of articles
                self.assertIsInstance(articles, list, f"Scraper for {domain} did not return a list")
                
                if articles:
                    # Check the structure of the first article
                    article = articles[0]
                    self.assertIsInstance(article, dict, f"Article from {domain} is not a dictionary")
                    
                    # Check required fields
                    required_fields = ["title", "content", "date", "url"]
                    for field in required_fields:
                        self.assertIn(field, article, f"Article from {domain} missing {field}")
                        self.assertTrue(article[field], f"Article from {domain} has empty {field}")
                    
                    logger.info(f"Successfully scraped article from {domain}: {article['title']}")
                else:
                    logger.warning(f"No articles found for {domain}")
            except Exception as e:
                logger.error(f"Error testing {domain}: {str(e)}")
                raise

    def test_individual_scrapers(self):
        """Test each scraper individually"""
        scrapers = {
            'npr.org': scrape_npr,
            'theguardian.com': scrape_guardian,
            'aljazeera.com': scrape_aljazeera,
            'abc.net.au': scrape_abc_au
        }
        
        for domain, scraper in scrapers.items():
            try:
                url = self.test_urls[domain]
                articles = scraper(url)
                
                # Log the number of articles found
                logger.info(f"Found {len(articles)} articles from {domain}")
                
                # Check if we got a list of articles
                self.assertIsInstance(articles, list, f"Scraper for {domain} did not return a list")
                
                if articles:
                    # Check the structure of the first article
                    article = articles[0]
                    self.assertIsInstance(article, dict, f"Article from {domain} is not a dictionary")
                    
                    # Check required fields
                    required_fields = ["title", "content", "date", "url"]
                    for field in required_fields:
                        self.assertIn(field, article, f"Article from {domain} missing {field}")
                        self.assertTrue(article[field], f"Article from {domain} has empty {field}")
                    
                    logger.info(f"Successfully scraped article from {domain}: {article['title']}")
                else:
                    logger.warning(f"No articles found for {domain}")
            except Exception as e:
                logger.error(f"Error testing {domain}: {str(e)}")
                raise

if __name__ == '__main__':
    unittest.main() 