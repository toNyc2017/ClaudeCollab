from playwright.sync_api import sync_playwright, TimeoutError
import time
from datetime import datetime
import os
import json
import sys
from pathlib import Path
import random
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/email_extractor.log')
    ]
)

class EmailExtractor:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.debug_mode = True
        self.extracted_content = []
        self.base_delay = 3  # Base delay between actions in seconds

    def random_delay(self, min_delay=None, max_extra=2):
        if min_delay is None:
            min_delay = self.base_delay
        time.sleep(min_delay + random.uniform(0, max_extra))

    def debug_print(self, message):
        if self.debug_mode:
            logging.debug(message)

    def save_debug_screenshot(self, page, name):
        if self.debug_mode:
            filename = f"/tmp/outlook_debug_{name}_{int(time.time())}.png"
            try:
                page.screenshot(path=filename)
                logging.debug(f"Debug screenshot saved: {filename}")
            except Exception as e:
                logging.error(f"Failed to save screenshot: {e}")

    def wait_for_load(self, page, timeout=30):
        logging.info("Waiting for page to load...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
                page.wait_for_load_state("domcontentloaded", timeout=5000)
                time.sleep(1)
                return True
            except Exception as e:
                logging.debug(f"Still loading... ({str(e)})")
                time.sleep(1)
        return False

    def login_to_outlook(self, page):
        try:
            logging.info("\nLogging in to Outlook...")
            page.goto("https://outlook.office365.com/")
            logging.debug("Page loaded, waiting for elements...")
            
            # Take screenshot of initial page
            self.save_debug_screenshot(page, "initial_page")
            
            # Wait for and log the page title
            logging.debug(f"Page title: {page.title()}")
            
            # Get page content for debugging
            content = page.content()
            logging.debug(f"Page content length: {len(content)}")
            
            # Handle sign in button
            try:
                sign_in_button = page.wait_for_selector("text=Sign in", timeout=5000)
                if sign_in_button and sign_in_button.is_visible():
                    logging.debug("Found sign in button, clicking...")
                    sign_in_button.click()
                    self.random_delay()
            except TimeoutError:
                logging.debug("No sign in button found, might be already on login page")
            
            # Take screenshot after potential sign in click
            self.save_debug_screenshot(page, "after_signin_click")
            
            # Handle email input
            try:
                logging.debug("Looking for email input...")
                email_input = page.wait_for_selector("input[type='email']", timeout=10000)
                if email_input:
                    logging.debug("Found email input, filling...")
                    email_input.fill(self.email)
                    self.random_delay(1)
                    page.keyboard.press("Enter")
                    logging.debug("Email entered and submitted")
            except TimeoutError:
                logging.error("Could not find email input field")
                return False
            
            # Take screenshot after email entry
            self.save_debug_screenshot(page, "after_email")
            
            # Handle password input
            try:
                logging.debug("Looking for password input...")
                password_input = page.wait_for_selector("input[type='password']", timeout=10000)
                if password_input:
                    logging.debug("Found password input, filling...")
                    password_input.fill(self.password)
                    self.random_delay(1)
                    page.keyboard.press("Enter")
                    logging.debug("Password entered and submitted")
            except TimeoutError:
                logging.error("Could not find password input field")
                return False
            
            # Take screenshot after password entry
            self.save_debug_screenshot(page, "after_password")
            
            # Handle 2FA if needed
            try:
                auth_code_element = page.wait_for_selector("text=Enter code", timeout=10000)
                if auth_code_element:
                    logging.info("\n*** 2FA Required ***")
                    auth_code = input("Enter the 2FA code: ")
                    code_input = page.wait_for_selector("input[type='tel']", timeout=10000)
                    if code_input:
                        code_input.fill(auth_code)
                        self.random_delay(1)
                        page.keyboard.press("Enter")
                        logging.debug("2FA code entered")
            except TimeoutError:
                logging.debug("No 2FA prompt detected")
            
            # Wait for inbox
            logging.info("Waiting for Outlook to load...")
            try:
                # Wait for something that indicates we're in the inbox
                page.wait_for_selector('div[role="list"]', timeout=20000)
                logging.info("Successfully logged in!")
                self.save_debug_screenshot(page, "inbox_loaded")
                return True
            except TimeoutError:
                logging.error("Could not detect inbox after login")
                self.save_debug_screenshot(page, "login_failed")
                return False

        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            self.save_debug_screenshot(page, "login_error")
            return False

    def extract_email_content(self, page):
        try:
            logging.info("Waiting for email content to load...")
            page.wait_for_selector('div[role="document"]', timeout=5000)
            self.random_delay(2)

            content = page.evaluate('''() => {
                const element = document.querySelector('div[role="document"]');
                return element ? element.innerText : '';
            }''')

            return content

        except Exception as e:
            logging.error(f"Error extracting content: {e}")
            return None

    def extract_email_metadata(self, item):
        try:
            subject_element = item.query_selector('div[role="heading"]')
            date_element = item.query_selector('div[title*="/"]')
            
            subject = subject_element.inner_text() if subject_element else "No subject"
            date = date_element.get_attribute('title') if date_element else "Date unknown"
            
            return subject, date
        except Exception as e:
            logging.error(f"Error extracting metadata: {e}")
            return "No subject", "Date unknown"

    def save_content(self):
        try:
            if not self.extracted_content:
                return None
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'/tmp/lynn_gadue_emails_{timestamp}.txt'
            
            header = [
                "=" * 80,
                "EMAILS FROM LYNN GADUE",
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "=" * 80,
                ""
            ]
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(header + self.extracted_content))
            
            logging.info(f'\nSaved emails to {filename}')
            return filename
            
        except Exception as e:
            logging.error(f"Error saving content: {e}")
            return None

    def process_visible_emails(self, page):
        try:
            items = page.query_selector_all('div[role="listitem"]')
            lynn_items = []
            
            logging.info("Scanning for Lynn's emails...")
            for item in items:
                try:
                    if "Lynn Gadue" in item.inner_text():
                        lynn_items.append(item)
                except Exception as e:
                    logging.error(f"Error checking item: {e}")
                    continue
            
            total_items = len(lynn_items)
            logging.info(f"\nFound {total_items} emails from Lynn")
            
            if total_items == 0:
                return False
            
            for i, item in enumerate(lynn_items, 1):
                try:
                    subject, date = self.extract_email_metadata(item)
                    logging.info(f"\nProcessing email {i}/{total_items}")
                    logging.info(f"Subject: {subject}")
                    logging.info(f"Date: {date}")
                    
                    item.click()
                    self.random_delay(2)
                    
                    content = self.extract_email_content(page)
                    if content:
                        logging.info(f"Extracted {len(content)} characters")
                        
                        email_text = [
                            "-" * 80,
                            f"Subject: {subject}",
                            f"Date: {date}",
                            "-" * 40,
                            content,
                            "-" * 80,
                            ""
                        ]
                        self.extracted_content.extend(email_text)
                        
                        self.save_content()
                    
                    logging.info("Returning to email list...")
                    page.go_back()
                    self.random_delay(2)
                    
                except Exception as e:
                    logging.error(f"Error processing email {i}: {e}")
                    self.save_debug_screenshot(page, f"error_email_{i}")
                    continue
            
            return True
            
        except Exception as e:
            logging.error(f"Error processing emails: {e}")
            return False

    def extract_emails(self, page):
        try:
            logging.info("\nStarting email extraction...")
            self.save_debug_screenshot(page, "before_extraction")
            
            if self.process_visible_emails(page):
                return self.save_content()
            else:
                logging.info("No emails found to process")
                return None
            
        except Exception as e:
            logging.error(f"Error during extraction: {e}")
            return self.save_content()

def main():
    email = "tolds@3clife.info"
    password = "annuiTy2024!"
    
    logging.info("Starting email extraction process...")
    extractor = EmailExtractor(email, password)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            if extractor.login_to_outlook(page):
                logging.info("\nLogin successful!")
                filename = extractor.extract_emails(page)
                if filename:
                    logging.info("\nExtraction completed!")
                    logging.info(f"Final file saved as: {filename}")
                else:
                    logging.info("\nExtraction failed!")
            else:
                logging.info("\nLogin failed!")
        except Exception as e:
            logging.error(f"\nError: {e}")
        finally:
            logging.info("\nClosing browser...")
            context.close()
            browser.close()

if __name__ == "__main__":
    main()
