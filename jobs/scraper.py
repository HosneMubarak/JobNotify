import apprise
import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
from datetime import datetime
from django.conf import settings

# Set up logging
logger = logging.getLogger('jobs.scraper')


class UpworkScraper:
    def __init__(self, max_retries=3, timeout=30, headless=True, debug=False):
        self.max_retries = max_retries
        self.timeout = timeout
        self.headless = headless
        self.debug = debug
        self.driver = None

    def configure_chrome_options(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        return chrome_options

    def setup_driver(self):
        try:
            options = self.configure_chrome_options()
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(self.timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to set up WebDriver: {str(e)}")
            return False

    def scrape_jobs(self, url):
        for attempt in range(self.max_retries):
            try:
                if not self.driver and not self.setup_driver():
                    return []

                logger.info(f"Attempt {attempt + 1}/{self.max_retries}: Fetching {url}")
                self.driver.get(url)

                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'article.job-tile'))
                )

                # Scroll to load dynamic content
                self.scroll_page()

                job_listings = self.extract_job_listings()

                if job_listings:
                    logger.info(f"Successfully scraped {len(job_listings)} job listings")
                    return job_listings
                else:
                    logger.warning("No job listings found")
                    if self.debug:
                        screenshot_path = f"{settings.MEDIA_ROOT}/screenshots/no_jobs_found_{int(time.time())}.png"
                        self.driver.save_screenshot(screenshot_path)

            except Exception as e:
                logger.error(f"Error in attempt {attempt + 1}: {str(e)}")
                if self.debug:
                    try:
                        screenshot_path = f"{settings.MEDIA_ROOT}/screenshots/error_screenshot_{int(time.time())}.png"
                        self.driver.save_screenshot(screenshot_path)
                    except:
                        pass

            if self.driver:
                self.driver.quit()
                self.driver = None

            # Wait before retrying with exponential backoff
            if attempt < self.max_retries - 1:
                wait_time = 5 * (2 ** attempt)  # Exponential backoff: 5, 10, 20 seconds...
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

        logger.error(f"All {self.max_retries} attempts failed")
        return []

    def scroll_page(self):
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            for i in range(3):
                scroll_point = total_height * (i + 1) // 4
                self.driver.execute_script(f"window.scrollTo(0, {scroll_point});")
                time.sleep(1)

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        except Exception as e:
            logger.warning(f"Error during page scrolling: {str(e)}")

    def extract_job_listings(self):
        job_elements = self.driver.find_elements(By.CSS_SELECTOR, 'article.job-tile')
        logger.info(f"Found {len(job_elements)} job elements")

        job_listings = []
        for index, job in enumerate(job_elements):
            job_data = {}

            try:
                title_element = job.find_element(By.CSS_SELECTOR, 'h2 .air3-link')
                job_data['title'] = title_element.text.strip()
                job_data['url'] = title_element.get_attribute('href')
            except Exception as e:
                logger.warning(f"Failed to extract title/URL for job {index}: {str(e)}")
                continue  # Skip jobs without title/URL

            try:
                job_info_elements = job.find_elements(By.CSS_SELECTOR, 'ul.job-tile-info-list li')
                for info in job_info_elements:
                    label = info.find_element(By.TAG_NAME, 'strong').text.strip()
                    if "Fixed Price" in label:
                        job_data['price_type'] = "Fixed Price"
                        job_data['price_range'] = label.strip()
                    elif "Hourly" in label:
                        job_data['price_type'] = "Hourly"
                        job_data['price_range'] = label.strip()
                    elif "Experience Level" in label:
                        job_data['experience_level'] = info.text.replace("Experience Level:", "").strip()
                    elif "Est. time" in label:
                        job_data['estimated_time'] = info.text.replace("Est. time:", "").strip()
            except Exception as e:
                logger.warning(f"Error extracting job info for job {index}: {str(e)}")

            try:
                skill_elements = job.find_elements(By.CSS_SELECTOR, '.air3-token-container .air3-token')
                skills = [skill.text.strip() for skill in skill_elements if skill.text.strip() != '+2']
                job_data['skills'] = ', '.join(skills)
            except Exception as e:
                job_data['skills'] = ""

            try:
                posted_date_element = job.find_element(By.CSS_SELECTOR,
                                                       '[data-test="job-pubilshed-date"] span:nth-of-type(2)')
                job_data['posted_date'] = posted_date_element.text.strip()
            except Exception as e:
                try:
                    # Alternative selector
                    posted_date_element = job.find_element(By.CSS_SELECTOR, '[data-test="job-pubilshed-date"]')
                    job_data['posted_date'] = posted_date_element.text.strip()
                except:
                    job_data['posted_date'] = ""

            # Get description if available
            try:
                description_element = job.find_element(By.CSS_SELECTOR, '.job-description')
                job_data['description'] = description_element.text.strip()
            except:
                job_data['description'] = ""

            job_listings.append(job_data)

        return job_listings

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")
            self.driver = None


def send_notification_via_apprise(config_url, title, message):
    """Send a notification using Apprise"""
    try:
        notifier = apprise.Apprise()
        notifier.add(config_url)

        # Escape the message if sending to Telegram which uses markdown
        if 'tgram://' in config_url:
            safe_message = html.escape(message)
        else:
            safe_message = message

        result = notifier.notify(body=safe_message, title=title)
        return result
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return False
