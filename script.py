# Create the main trello_provisioning.py file
trello_script = '''#!/usr/bin/env python3
"""
CloudEagle AutoPilot - Trello User Provisioning Automation

This script automates user provisioning in Trello workspaces using Selenium WebDriver.
It demonstrates AI-driven SaaS user management for applications without comprehensive APIs.

Author: CloudEagle.ai AI Product Manager Intern Assignment
Repository: https://github.com/bhaskaranjappa/cloudeagle-trello-provisioning
"""

import os
import sys
import time
import logging
import argparse
from typing import Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv


@dataclass
class TrelloCredentials:
    """Data class for storing Trello credentials"""
    username: str
    password: str


class TrelloProvisioningError(Exception):
    """Custom exception for Trello provisioning errors"""
    pass


class CaptchaDetectedException(TrelloProvisioningError):
    """Exception raised when CAPTCHA is detected"""
    pass


class TrelloProvisioning:
    """
    Main class for automating Trello user provisioning.
    
    This class handles login, workspace navigation, user invitation,
    and verification processes with comprehensive error handling.
    """
    
    def __init__(self, headless: bool = True, wait_timeout: int = 10):
        """
        Initialize the TrelloProvisioning instance.
        
        Args:
            headless (bool): Whether to run Chrome in headless mode
            wait_timeout (int): Default timeout for WebDriver waits
        """
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.max_retries = 3
        self.retry_delay_base = 1  # Base delay for exponential backoff
        
        # Setup logging
        self._setup_logging()
        
        # Load environment variables
        load_dotenv()
        self.credentials = self._load_credentials()
        
        logging.info("TrelloProvisioning initialized successfully")
    
    def _setup_logging(self) -> None:
        """Configure logging with both file and console handlers"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            handlers=[
                logging.FileHandler('automation.log', mode='a'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logging.info("=" * 60)
        logging.info("CloudEagle AutoPilot - Trello Provisioning Started")
        logging.info("=" * 60)
    
    def _load_credentials(self) -> TrelloCredentials:
        """
        Load Trello credentials from environment variables.
        
        Returns:
            TrelloCredentials: Loaded credentials
            
        Raises:
            TrelloProvisioningError: If credentials are missing
        """
        username = os.getenv('TRELLO_USERNAME')
        password = os.getenv('TRELLO_PASSWORD')
        
        if not username or not password:
            error_msg = "TRELLO_USERNAME and TRELLO_PASSWORD must be set in .env file"
            logging.error(error_msg)
            raise TrelloProvisioningError(error_msg)
        
        logging.info(f"Credentials loaded for user: {username}")
        return TrelloCredentials(username=username, password=password)
    
    def _setup_driver(self) -> None:
        """Setup Chrome WebDriver with optimal configuration"""
        try:
            chrome_options = Options()
            
            # Essential Chrome options for automation
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            if self.headless:
                chrome_options.add_argument('--headless=new')  # Use new headless mode
                logging.info("Running in headless mode")
            else:
                logging.info("Running in visible mode")
            
            # Use webdriver-manager for automatic ChromeDriver management
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configure timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(5)
            
            # Initialize WebDriverWait
            self.wait = WebDriverWait(self.driver, self.wait_timeout)
            
            # Maximize window for better element visibility
            if not self.headless:
                self.driver.maximize_window()
            
            logging.info("WebDriver setup completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to setup WebDriver: {str(e)}"
            logging.error(error_msg)
            raise TrelloProvisioningError(error_msg)
    
    def _retry_operation(self, operation, *args, **kwargs):
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation: Function to retry
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            TrelloProvisioningError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logging.debug(f"Attempt {attempt + 1}/{self.max_retries} for {operation.__name__}")
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                delay = self.retry_delay_base * (2 ** attempt)
                logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                time.sleep(delay)
        
        error_msg = f"Operation {operation.__name__} failed after {self.max_retries} attempts"
        logging.error(error_msg)
        raise TrelloProvisioningError(f"{error_msg}. Last error: {str(last_exception)}")
    
    def _wait_and_find_element(self, by: By, value: str, timeout: Optional[int] = None) -> object:
        """
        Wait for element to be present and return it.
        
        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Custom timeout (uses default if None)
            
        Returns:
            WebElement: Found element
        """
        wait_time = timeout or self.wait_timeout
        wait = WebDriverWait(self.driver, wait_time)
        return wait.until(EC.presence_of_element_located((by, value)))
    
    def _safe_click(self, element) -> None:
        """
        Safely click an element with retry logic.
        
        Args:
            element: WebElement to click
        """
        def click_operation():
            try:
                # Try regular click first
                element.click()
            except ElementClickInterceptedException:
                # If regular click fails, try JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
        
        self._retry_operation(click_operation)
    
    def _check_for_captcha(self) -> bool:
        """
        Check if CAPTCHA is present on the current page.
        
        Returns:
            bool: True if CAPTCHA detected, False otherwise
        """
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            ".g-recaptcha",
            "#recaptcha",
            ".captcha",
            "iframe[title*='captcha']",
            "iframe[title*='challenge']"
        ]
        
        for selector in captcha_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logging.warning(f"CAPTCHA detected using selector: {selector}")
                    return True
            except Exception:
                continue
        
        return False
    
    def _handle_captcha_if_present(self) -> None:
        """Handle CAPTCHA if detected"""
        if self._check_for_captcha():
            logging.warning("CAPTCHA detected! Manual intervention required.")
            if not self.headless:
                logging.info("Please solve the CAPTCHA manually in the browser window.")
                input("Press Enter after solving the CAPTCHA to continue...")
            else:
                raise CaptchaDetectedException("CAPTCHA detected in headless mode. Please run with --no-headless flag.")
    
    def login(self) -> None:
        """
        Login to Trello with comprehensive error handling.
        
        Raises:
            TrelloProvisioningError: If login fails
        """
        try:
            logging.info("Starting Trello login process")
            self.driver.get("https://trello.com/login")
            logging.info("Navigated to Trello login page")
            
            # Check for CAPTCHA on login page
            self._handle_captcha_if_present()
            
            # Wait for and fill username
            username_input = self._wait_and_find_element(By.ID, "username")
            username_input.clear()
            username_input.send_keys(self.credentials.username)
            logging.info("Username entered successfully")
            
            # Continue button (if present)
            try:
                continue_btn = self.driver.find_element(By.ID, "login-submit")
                self._safe_click(continue_btn)
                time.sleep(2)  # Wait for potential page transition
            except NoSuchElementException:
                logging.debug("Continue button not found, proceeding with password")
            
            # Wait for and fill password
            password_input = self._wait_and_find_element(By.ID, "password")
            password_input.clear()
            password_input.send_keys(self.credentials.password)
            logging.info("Password entered successfully")
            
            # Check for CAPTCHA before submitting
            self._handle_captcha_if_present()
            
            # Submit login form
            login_button = self._wait_and_find_element(By.ID, "login-submit")
            self._safe_click(login_button)
            
            # Wait for successful login (check for dashboard or boards page)
            try:
                self.wait.until(
                    lambda driver: "trello.com" in driver.current_url and 
                    ("boards" in driver.current_url or "home" in driver.current_url or 
                     len(driver.find_elements(By.CSS_SELECTOR, "[data-testid*='board']")) > 0)
                )
                logging.info("Login successful!")
            except TimeoutException:
                # Check if we're still on login page (might indicate failed login)
                if "login" in self.driver.current_url:
                    error_msg = "Login appears to have failed - still on login page"
                    logging.error(error_msg)
                    raise TrelloProvisioningError(error_msg)
                else:
                    logging.info("Login appears successful (page changed)")
            
        except CaptchaDetectedException:
            raise
        except Exception as e:
            error_msg = f"Login failed: {str(e)}"
            logging.error(error_msg)
            raise TrelloProvisioningError(error_msg)
    
    def navigate_to_workspace(self, workspace_name: str = "Project X") -> None:
        """
        Navigate to a specific workspace.
        
        Args:
            workspace_name (str): Name of the workspace to navigate to
            
        Raises:
            TrelloProvisioningError: If workspace navigation fails
        """
        try:
            logging.info(f"Navigating to workspace: {workspace_name}")
            
            # Multiple strategies to find and access workspace
            workspace_selectors = [
                f"//a[contains(text(), '{workspace_name}')]",
                f"//div[contains(text(), '{workspace_name}')]",
                f"//span[contains(text(), '{workspace_name}')]",
                f"//*[@data-testid='workspace-name'][contains(text(), '{workspace_name}')]",
                f"//*[contains(@class, 'workspace')]//*[contains(text(), '{workspace_name}')]"
            ]
            
            workspace_found = False
            
            for selector in workspace_selectors:
                try:
                    workspace_element = self.driver.find_element(By.XPATH, selector)
                    self._safe_click(workspace_element)
                    workspace_found = True
                    logging.info(f"Workspace '{workspace_name}' found and clicked using selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not workspace_found:
                # Try alternative approach - look for workspace in boards view
                try:
                    # Navigate to boards if not already there
                    self.driver.get("https://trello.com/boards")
                    time.sleep(3)
                    
                    # Look for workspace in boards view
                    for selector in workspace_selectors:
                        try:
                            workspace_element = self.driver.find_element(By.XPATH, selector)
                            self._safe_click(workspace_element)
                            workspace_found = True
                            logging.info(f"Workspace found in boards view")
                            break
                        except NoSuchElementException:
                            continue
                except Exception as e:
                    logging.warning(f"Failed to navigate to boards view: {str(e)}")
            
            if not workspace_found:
                error_msg = f"Workspace '{workspace_name}' not found"
                logging.error(error_msg)
                raise TrelloProvisioningError(error_msg)
            
            # Wait for workspace to load
            time.sleep(3)
            logging.info(f"Successfully navigated to workspace: {workspace_name}")
            
        except Exception as e:
            error_msg = f"Failed to navigate to workspace '{workspace_name}': {str(e)}"
            logging.error(error_msg)
            raise TrelloProvisioningError(error_msg)
    
    def add_new_user(self, email: str) -> None:
        """
        Add a new user to the current workspace.
        
        Args:
            email (str): Email address of the user to invite
            
        Raises:
            TrelloProvisioningError: If user invitation fails
        """
        try:
            logging.info(f"Adding new user: {email}")
            
            # Multiple strategies to find invite/members button
            invite_selectors = [
                "//button[contains(text(), 'Invite')]",
                "//button[contains(text(), 'Members')]",
                "//a[contains(text(), 'Invite')]",
                "//*[@data-testid='invite-button']",
                "//*[@data-testid='members-button']",
                "//button[contains(@class, 'invite')]",
                "//button[contains(@title, 'Invite')]",
                "//*[contains(@class, 'workspace-header')]//*[contains(text(), 'Invite')]"
            ]
            
            invite_button_found = False
            
            for selector in invite_selectors:
                try:
                    invite_button = self.driver.find_element(By.XPATH, selector)
                    self._safe_click(invite_button)
                    invite_button_found = True
                    logging.info(f"Invite button clicked using selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not invite_button_found:
                error_msg = "Could not find invite/members button"
                logging.error(error_msg)
                raise TrelloProvisioningError(error_msg)
            
            # Wait for invite modal/form to appear
            time.sleep(2)
            
            # Find email input field
            email_selectors = [
                "//input[@placeholder*='email']",
                "//input[@id*='email']",
                "//input[@name*='email']",
                "//input[@type='email']",
                "//*[@data-testid='invite-email-input']",
                "//textarea[contains(@placeholder, 'email')]"
            ]
            
            email_input_found = False
            
            for selector in email_selectors:
                try:
                    email_input = self.driver.find_element(By.XPATH, selector)
                    email_input.clear()
                    email_input.send_keys(email)
                    email_input_found = True
                    logging.info(f"Email entered using selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not email_input_found:
                error_msg = "Could not find email input field"
                logging.error(error_msg)
                raise TrelloProvisioningError(error_msg)
            
            # Submit invitation
            submit_selectors = [
                "//button[contains(text(), 'Send')]",
                "//button[contains(text(), 'Invite')]",
                "//button[@type='submit']",
                "//*[@data-testid='send-invite-button']",
                "//input[@type='submit']"
            ]
            
            submit_button_found = False
            
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.XPATH, selector)
                    self._safe_click(submit_button)
                    submit_button_found = True
                    logging.info(f"Invite sent using submit button: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            # Alternative: try pressing Enter
            if not submit_button_found:
                try:
                    email_input.send_keys(Keys.ENTER)
                    submit_button_found = True
                    logging.info("Invite sent using Enter key")
                except:
                    pass
            
            if not submit_button_found:
                error_msg = "Could not find submit button to send invitation"
                logging.error(error_msg)
                raise TrelloProvisioningError(error_msg)
            
            # Wait for confirmation
            time.sleep(3)
            logging.info(f"User invitation sent successfully for: {email}")
            
        except Exception as e:
            error_msg = f"Failed to add user '{email}': {str(e)}"
            logging.error(error_msg)
            raise TrelloProvisioningError(error_msg)
    
    def verify_user_added(self, email: str) -> bool:
        """
        Verify that the user was successfully added to the workspace.
        
        Args:
            email (str): Email address to verify
            
        Returns:
            bool: True if user is found in member list, False otherwise
        """
        try:
            logging.info(f"Verifying user addition: {email}")
            
            # Look for user in various possible locations
            user_verification_selectors = [
                f"//*[contains(text(), '{email}')]",
                f"//span[contains(@title, '{email}')]",
                f"//*[@data-testid='member'][contains(., '{email}')]",
                f"//*[contains(@class, 'member')][contains(., '{email}')]"
            ]
            
            for selector in user_verification_selectors:
                try:
                    user_elements = self.driver.find_elements(By.XPATH, selector)
                    if user_elements:
                        logging.info(f"User '{email}' verified successfully using selector: {selector}")
                        return True
                except NoSuchElementException:
                    continue
            
            # Additional verification: check for success message
            success_selectors = [
                "//*[contains(text(), 'invited')]",
                "//*[contains(text(), 'sent')]",
                "//*[contains(text(), 'added')]",
                "//*[contains(@class, 'success')]"
            ]
            
            for selector in success_selectors:
                try:
                    success_elements = self.driver.find_elements(By.XPATH, selector)
                    if success_elements:
                        logging.info(f"Success message found: {success_elements[0].text}")
                        return True
                except:
                    continue
            
            logging.warning(f"Could not verify user '{email}' was added")
            return False
            
        except Exception as e:
            logging.error(f"Error during user verification: {str(e)}")
            return False
    
    def run_provisioning(self, email: str = "newuser@example.com", workspace: str = "Project X") -> bool:
        """
        Run the complete provisioning workflow.
        
        Args:
            email (str): Email address to invite
            workspace (str): Workspace name
            
        Returns:
            bool: True if provisioning succeeded, False otherwise
        """
        success = False
        
        try:
            # Setup driver
            self._setup_driver()
            
            # Execute provisioning workflow
            self.login()
            self.navigate_to_workspace(workspace)
            self.add_new_user(email)
            success = self.verify_user_added(email)
            
            if success:
                logging.info("=" * 60)
                logging.info("PROVISIONING COMPLETED SUCCESSFULLY!")
                logging.info(f"User '{email}' has been invited to workspace '{workspace}'")
                logging.info("=" * 60)
            else:
                logging.warning("Provisioning completed but user verification failed")
            
        except CaptchaDetectedException as e:
            logging.error(f"CAPTCHA intervention required: {str(e)}")
        except TrelloProvisioningError as e:
            logging.error(f"Provisioning failed: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error during provisioning: {str(e)}")
        finally:
            self.cleanup()
        
        return success
    
    def cleanup(self) -> None:
        """Clean up resources and close browser"""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("WebDriver closed successfully")
            except Exception as e:
                logging.warning(f"Error closing WebDriver: {str(e)}")


def main():
    """Main entry point with command-line argument parsing"""
    parser = argparse.ArgumentParser(
        description="CloudEagle AutoPilot - Trello User Provisioning Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trello_provisioning.py                                    # Run with defaults
  python trello_provisioning.py --no-headless                     # Run with visible browser
  python trello_provisioning.py --email user@company.com          # Invite specific user
  python trello_provisioning.py --workspace "My Team"             # Use different workspace
        """
    )
    
    parser.add_argument(
        '--no-headless', 
        action='store_true',
        help='Run Chrome in visible mode (default: headless)'
    )
    
    parser.add_argument(
        '--email',
        default='newuser@example.com',
        help='Email address to invite (default: newuser@example.com)'
    )
    
    parser.add_argument(
        '--workspace',
        default='Project X',
        help='Workspace name to use (default: Project X)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='WebDriver wait timeout in seconds (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Create and run provisioning
    provisioning = TrelloProvisioning(
        headless=not args.no_headless,
        wait_timeout=args.timeout
    )
    
    success = provisioning.run_provisioning(
        email=args.email,
        workspace=args.workspace
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
'''

# Save the main script
with open('trello_provisioning.py', 'w', encoding='utf-8') as f:
    f.write(trello_script)

print("✅ Created trello_provisioning.py")
print(f"📄 File size: {len(trello_script)} characters")