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
        self.base_delay = 3

    def random_delay(self, min_delay=None, max_extra=2):
        if min_delay is None:
            min_delay = self.base_delay
        time.sleep(min_delay + random.uniform(0, max_extra))

    def save_debug_screenshot(self, page, name):
        if self.debug_mode:
            filename = f"/tmp/outlook_debug_{name}_{int(time.time())}.png"
            try:
                page.screenshot(path=filename)
                logging.debug(f"Debug screenshot saved: {filename}")
            except Exception as e:
                logging.error(f"Failed to save screenshot: {e}")

    def check_page_state(self, page, stage):
        """Log detailed information about the current page state"""
        try:
            # Get page title
            title = page.title()
            logging.debug(f"Stage: {stage} - Title: {title}")
            
            # Log URL
            url = page.url
            logging.debug(f"URL: {url}")
            
            # Log visible text
            text = page.inner_text('body')
            logging.debug(f"Visible text (first 200 chars): {text[:200]}")
            
            # Take screenshot
            self.save_debug_screenshot(page, f"state_{stage}")
            
            # Check for common error messages
            error_messages = [
                "something went wrong",
                "error",
                "invalid",
                "incorrect",
                "failed"
            ]
            
            for msg in error_messages:
                if msg.lower() in text.lower():
                    logging.error(f"Found error message containing '{msg}'")
            
            return {
                'title': title,
                'url': url,
                'text': text
            }
            
        except Exception as e:
            logging.error(f"Error checking page state: {e}")
            return None

    def handle_additional_prompts(self, page):
        """Handle various authentication prompts and popups"""
        try:
            # List of common buttons/links to check for
            common_elements = [
                "text=Stay signed in",
                "text=Yes",
                "text=Next",
                "text=Continue",
                "text=I agree",
                "text=Accept",
                "text=Skip",
                "text=Not now",
                'button:has-text("Next")',
                'button:has-text("Continue")',
                'button:has-text("Skip")',
                'button:has-text("Yes")'
            ]
            
            for selector in common_elements:
                try:
                    element = page.wait_for_selector(selector, timeout=2000)
                    if element and element.is_visible():
                        logging.debug(f"Found and clicking: {selector}")
                        element.click()
                        self.random_delay(2)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logging.error(f"Error handling additional prompts: {e}")
            return False

    def wait_for_load(self, page, timeout=30):
        logging.info(f"Waiting for page to load (timeout: {timeout}s)...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
                page.wait_for_load_state("domcontentloaded", timeout=5000)
                self.check_page_state(page, "load_complete")
                return True
            except Exception as e:
                logging.debug(f"Still loading... ({str(e)})")
                time.sleep(1)
        return False

    def login_to_outlook(self, page):
        try:
            logging.info("\nLogging in to Outlook...")
            page.goto("https://outlook.office365.com/")
            self.wait_for_load(page)
            
            # Initial page state
            self.check_page_state(page, "initial")
            
            # Handle sign in
            sign_in_button = page.query_selector("text=Sign in")
            if sign_in_button and sign_in_button.is_visible():
                logging.debug("Found sign in button")
                sign_in_button.click()
                self.random_delay()
            
            # Check state after sign in click
            self.check_page_state(page, "after_signin")
            
            # Enter email
            logging.debug("Looking for email input")
            email_input = page.wait_for_selector("input[type='email']", timeout=10000)
            if email_input:
                logging.debug("Found email input")
                email_input.fill(self.email)
                self.random_delay(1)
                page.keyboard.press("Enter")
                logging.debug("Email submitted")
            
            # Check state after email
            self.check_page_state(page, "after_email")
            
            # Enter password
            logging.debug("Looking for password input")
            password_input = page.wait_for_selector("input[type='password']", timeout=10000)
            if password_input:
                logging.debug("Found password input")
                password_input.fill(self.password)
                self.random_delay(1)
                page.keyboard.press("Enter")
                logging.debug("Password submitted")
            
            # Check state after password
            self.check_page_state(page, "after_password")
            
            # Handle any additional prompts
            max_prompt_checks = 5
            prompt_count = 0
            
            while prompt_count < max_prompt_checks:
                logging.debug(f"Checking for additional prompts (attempt {prompt_count + 1}/{max_prompt_checks})")
                
                # Check current page state
                state = self.check_page_state(page, f"prompt_check_{prompt_count}")
                
                # Try to handle any prompts
                if self.handle_additional_prompts(page):
                    logging.debug("Handled a prompt, waiting before next check")
                    self.random_delay(2)
                else:
                    logging.debug("No prompts found in this check")
                
                # Check if we've reached the inbox
                try:
                    inbox = page.wait_for_selector('div[role="list"]', timeout=5000)
                    if inbox:
                        logging.info("Successfully reached inbox!")
                        return True
                except:
                    pass
                
                prompt_count += 1
            
            logging.error("Failed to reach inbox after handling prompts")
            return False

        except Exception as e:
            logging.error(f"Login error: {e}")
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
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-dev-shm-usage']
        )
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
