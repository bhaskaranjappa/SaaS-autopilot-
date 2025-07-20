import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Add parent directory to path to import TrelloProvisioning
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from trello_provisioning import TrelloProvisioning, TrelloProvisioningError


class TestTrelloProvisioning(unittest.TestCase):
    """Test cases for TrelloProvisioning class"""

    def setUp(self):
        """Set up test environment"""
        # Create a patch for environment variables
        self.env_patcher = patch.dict('os.environ', {
            'TRELLO_USERNAME': 'test@example.com',
            'TRELLO_PASSWORD': 'test_password'
        })
        self.env_patcher.start()

        # Mock the webdriver setup
        self.driver_patcher = patch('trello_provisioning.webdriver.Chrome')
        self.mock_driver = self.driver_patcher.start()

        # Mock ChromeDriverManager
        self.cdm_patcher = patch('trello_provisioning.ChromeDriverManager')
        self.mock_cdm = self.cdm_patcher.start()
        self.mock_cdm.return_value.install.return_value = '/path/to/chromedriver'

        # Create instance with patched dependencies
        self.provisioning = TrelloProvisioning(headless=True)

        # Set mock driver
        self.provisioning.driver = self.mock_driver
        self.provisioning.wait = MagicMock()

    def tearDown(self):
        """Clean up after tests"""
        self.env_patcher.stop()
        self.driver_patcher.stop()
        self.cdm_patcher.stop()

    def test_init(self):
        """Test initialization with correct parameters"""
        self.assertEqual(self.provisioning.headless, True)
        self.assertEqual(self.provisioning.wait_timeout, 10)
        self.assertEqual(self.provisioning.credentials.username, 'test@example.com')
        self.assertEqual(self.provisioning.credentials.password, 'test_password')

    def test_missing_credentials(self):
        """Test initialization with missing credentials"""
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(TrelloProvisioningError):
                TrelloProvisioning()

    def test_login_success(self):
        """Test successful login flow"""
        with patch('trello_provisioning.TrelloProvisioning._wait_and_find_element') as mock_wait_find, \
             patch('trello_provisioning.TrelloProvisioning._handle_captcha_if_present') as mock_captcha:

            # Mock elements
            mock_username = MagicMock()
            mock_password = MagicMock()
            mock_login_button = MagicMock()

            # Set up mock element returns
            mock_wait_find.side_effect = [mock_username, mock_password, mock_login_button]

            # Mock successful login verification
            self.provisioning.wait.until.return_value = True

            # Execute login
            self.provisioning.login()

            # Verify expected calls
            self.provisioning.driver.get.assert_called_with('https://trello.com/login')
            mock_captcha.assert_called()
            mock_username.send_keys.assert_called_with('test@example.com')
            mock_password.send_keys.assert_called_with('test_password')

    def test_captcha_detection(self):
        """Test CAPTCHA detection and handling"""
        with patch('trello_provisioning.TrelloProvisioning._check_for_captcha') as mock_check:
            # Mock CAPTCHA present
            mock_check.return_value = True

            # Set non-headless mode to simulate manual intervention
            self.provisioning.headless = False

            # Mock the input function to simulate user pressing Enter
            with patch('builtins.input', return_value=''):
                self.provisioning._handle_captcha_if_present()
                mock_check.assert_called_once()

            # Test headless mode raises exception
            self.provisioning.headless = True
            with self.assertRaises(Exception):
                self.provisioning._handle_captcha_if_present()

    def test_add_new_user(self):
        """Test add_new_user functionality"""
        with patch('trello_provisioning.TrelloProvisioning._wait_and_find_element') as mock_wait_find:
            # Mock driver find_element to return our mock elements
            mock_invite_button = MagicMock()
            mock_email_input = MagicMock()

            self.provisioning.driver.find_element.side_effect = [
                mock_invite_button,
                NoSuchElementException(),  # Simulate one selector not found
                mock_email_input
            ]

            # Execute add_new_user
            self.provisioning.add_new_user("newuser@example.com")

            # Verify expected calls
            mock_invite_button.click.assert_called_once()
            mock_email_input.send_keys.assert_any_call("newuser@example.com")

    def test_verify_user_added(self):
        """Test user verification functionality"""
        # Mock finding the user in the member list
        self.provisioning.driver.find_elements.return_value = [MagicMock()]

        # Execute verification
        result = self.provisioning.verify_user_added("newuser@example.com")

        # Verify expected result
        self.assertTrue(result)

        # Test not finding the user
        self.provisioning.driver.find_elements.return_value = []
        result = self.provisioning.verify_user_added("newuser@example.com")
        self.assertFalse(result)

    def test_run_provisioning(self):
        """Test the full provisioning workflow"""
        with patch.multiple(
            'trello_provisioning.TrelloProvisioning',
            _setup_driver=MagicMock(),
            login=MagicMock(),
            navigate_to_workspace=MagicMock(),
            add_new_user=MagicMock(),
            verify_user_added=MagicMock(return_value=True)
        ) as mocks:

            # Execute provisioning
            result = self.provisioning.run_provisioning(
                email="newuser@example.com", 
                workspace="Project X"
            )

            # Verify all steps were called
            mocks['_setup_driver'].assert_called_once()
            mocks['login'].assert_called_once()
            mocks['navigate_to_workspace'].assert_called_once_with("Project X")
            mocks['add_new_user'].assert_called_once_with("newuser@example.com")
            mocks['verify_user_added'].assert_called_once_with("newuser@example.com")
            self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
