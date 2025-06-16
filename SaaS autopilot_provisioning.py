# Trello User Provisioning Script for CloudEagle AutoPilot

# Step 1: Install Packages and Dependencies (Commented for Local Execution)
# !pip install selenium python-dotenv webdriver-manager -q
# !apt-get update -q
# !apt-get install -y chromium-browser -q
# !apt-get install -y libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 -q

# Step 2: Create .env File for Credentials (Commented for Local Execution)
# with open(".env", "w") as f:
#     f.write("TRELL_USERNAME=your_trello_email\n")
#     f.write("TRELL_PASSWORD=your_trello_password\n")

# Step 3: Trello User Provisioning Script
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    WebDriverException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Load environment variables from .env file
if not os.path.exists(".env"):
    raise FileNotFoundError("Please create a .env file with TRELL_USERNAME and TRELL_PASSWORD.")
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class TrelloUserProvisioning:
    """Main class for Trello user provisioning automation"""
    
    def __init__(self, headless=True, timeout=30):
        """
        Initialize the automation class.
        
        Args:
            headless (bool): Run browser in headless mode (default: True).
            timeout (int): Default timeout for WebDriverWait in seconds (default: 30).
        """
        self.driver = None
        self.wait = None
        self.headless = headless
        self.timeout = timeout
        
        # Configuration
        self.base_url = "https://trello.com"
        self.login_url = f"{self.base_url}/login"
        
        # Load credentials from environment variables
        self.username = os.getenv("TRELL_USERNAME")
        self.password = os.getenv("TRELL_PASSWORD")
        if not self.username or not self.password:
            raise ValueError("TRELL_USERNAME or TRELL_PASSWORD missing in .env file.")
        
        # Target workspace and user details (customize these as needed)
        self.workspace_name = "Project X"
        self.new_user_email = "newuser@example.com"
        self.new_user_role = "Member"

    def setup_browser(self):
        """Initialize headless Chromium browser with anti-detection settings."""
        logger.info("Setting up Chromium browser...")
        
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless=new")
                logger.info("Running in headless mode")
            
            # Anti-detection and stability options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Use webdriver-manager to automatically download and manage ChromeDriver
            chrome_service = Service(ChromeDriverManager().install())
            chrome_options.binary_location = "/usr/bin/chromium-browser"  # Path to Chromium in Colab
            self.driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            logger.info("Browser setup completed")
            return True
            
        except WebDriverException as e:
            logger.error(f"Browser setup failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during browser setup: {e}")
            return False

    def login_to_trello(self):
        """Log in to Trello with environment credentials and handle CAPTCHAs."""
        logger.info("Starting Trello login...")
        
        try:
            self.driver.get(self.login_url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # CAPTCHA detection and manual resolution
            captcha_selectors = [
                "div[class*='captcha']", "iframe[src*='recaptcha']",
                "div[id*='captcha']", ".g-recaptcha"
            ]
            for selector in captcha_selectors:
                try:
                    captcha = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if captcha.is_displayed():
                        logger.warning("CAPTCHA detected! Solve it manually within 60 seconds.")
                        start_time = time.time()
                        while time.time() - start_time < 60:
                            try:
                                self.driver.find_element(By.CSS_SELECTOR, selector)
                                time.sleep(5)
                            except NoSuchElementException:
                                logger.info("CAPTCHA resolved. Proceeding...")
                                break
                        else:
                            raise TimeoutException("CAPTCHA not solved within 60 seconds.")
                except NoSuchElementException:
                    continue
            
            # Enter username
            username_field = self.wait.until(EC.element_to_be_clickable((By.ID, "user")))
            username_field.clear()
            username_field.send_keys(self.username)
            logger.info("Username entered")
            
            # Click 'Continue' button (Trello login flow may split username/password)
            continue_button = self.wait.until(EC.element_to_be_clickable((By.ID, "login")))
            self.driver.execute_script("arguments[0].click();", continue_button)
            
            # Enter password
            password_field = self.wait.until(EC.element_to_be_clickable((By.ID, "password")))
            password_field.clear()
            password_field.send_keys(self.password)
            logger.info("Password entered")
            
            # Submit login
            login_button = self.wait.until(EC.element_to_be_clickable((By.ID, "login-submit")))
            self.driver.execute_script("arguments[0].click();", login_button)
            
            # Verify login success
            self.wait.until(EC.url_contains("/boards"))
            logger.info("Login successful")
            return True
            
        except TimeoutException as e:
            logger.error(f"Login timed out: {e}")
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def navigate_to_workspace_settings(self):
        """Navigate to the specified workspace's member settings."""
        logger.info(f"Navigating to '{self.workspace_name}' settings...")
        
        try:
            # Wait for dashboard to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='header']")))
            
            # Access workspace switcher
            workspace_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='header-workspace-switcher-button']"))
            )
            self.driver.execute_script("arguments[0].click();", workspace_button)
            
            # Select the target workspace
            workspace_xpath = f"//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{self.workspace_name.lower()}')]"
            workspace_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, workspace_xpath)))
            self.driver.execute_script("arguments[0].click();", workspace_link)
            
            # Navigate to members section
            members_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='workspace-navigation-members-tab']"))
            )
            self.driver.execute_script("arguments[0].click();", members_button)
            
            logger.info("Reached workspace members section")
            return True
            
        except TimeoutException:
            logger.error("Timeout during workspace navigation")
            return False
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False

    def add_new_user(self):
        """Add a new user to the workspace with retry logic."""
        logger.info(f"Adding user: {self.new_user_email}")
        
        def retry_action(action, max_attempts=3, delay=2):
            for attempt in range(max_attempts):
                try:
                    return action()
                except (TimeoutException, StaleElementReferenceException, ElementClickInterceptedException) as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
            raise Exception(f"Failed after {max_attempts} attempts")

        try:
            # Click 'Invite' button
            invite_button = retry_action(lambda: self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='invite-to-workspace-button']"))
            ))
            self.driver.execute_script("arguments[0].click();", invite_button)
            
            # Enter email
            email_input = retry_action(lambda: self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='invite-to-workspace-email-input']"))
            ))
            email_input.clear()
            email_input.send_keys(self.new_user_email)
            
            # Submit invitation
            submit_button = retry_action(lambda: self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='invite-to-workspace-submit']"))
            ))
            self.driver.execute_script("arguments[0].click();", submit_button)
            
            logger.info("User invitation sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add user: {e}")
            return False

    def verify_user_addition(self):
        """Verify the new user appears in the workspace member list."""
        logger.info(f"Verifying user: {self.new_user_email}")
        
        try:
            for _ in range(3):  # Retry up to 3 times for page updates
                try:
                    member_xpath = f"//div[contains(@class, 'member-list')]//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{self.new_user_email.lower()}')]"
                    self.wait.until(EC.presence_of_element_located((By.XPATH, member_xpath)))
                    logger.info(f"User {self.new_user_email} verified in member list")
                    return True
                except TimeoutException:
                    time.sleep(2)
            logger.warning(f"Could not verify {self.new_user_email} in member list")
            return False
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

    def cleanup(self):
        """Close the browser session cleanly."""
        logger.info("Cleaning up...")
        
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        finally:
            self.driver = None
            self.wait = None

# Step 4: Run the Script
if __name__ == "__main__":
    try:
        automation = TrelloUserProvisioning(headless=True)  # Headless mode
        if automation.setup_browser():
            if automation.login_to_trello():
                if automation.navigate_to_workspace_settings():
                    if automation.add_new_user():
                        automation.verify_user_addition()
    finally:
        automation.cleanup()
