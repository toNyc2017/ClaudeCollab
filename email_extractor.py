from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import os
import json
import sys
from pathlib import Path
import random
import pyperclip  # For clipboard operations

class EmailExtractor:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.debug_mode = True
        self.extracted_content = []
        self.base_delay = 3  # Base delay between actions in seconds

    def random_delay(self, min_delay=None, max_extra=2):
        """Add a random delay between actions to seem more human-like"""
        if min_delay is None:
            min_delay = self.base_delay
        time.sleep(min_delay + random.uniform(0, max_extra))

    def debug_print(self, message):
        if self.debug_mode:
            print(f"[DEBUG] {message}")

    def save_debug_screenshot(self, page, name):
        if self.debug_mode:
            filename = f"/tmp/outlook_debug_{name}_{int(time.time())}.png"
            page.screenshot(path=filename)
            print(f"Debug screenshot saved: {filename}")

    def wait_for_load(self, page, timeout=30):
        print("Waiting for page to load...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
                page.wait_for_load_state("domcontentloaded", timeout=5000)
                time.sleep(1)
                return True
            except Exception as e:
                print(f"Still loading... ({str(e)})")
                time.sleep(1)
        return False

    def login_to_outlook(self, page):
        try:
            print("\nLogging in to Outlook...")
            page.goto("https://outlook.office365.com/")
            self.wait_for_load(page)
            self.save_debug_screenshot(page, "initial_load")

            # Handle sign in
            sign_in_button = page.query_selector("text=Sign in")
            if sign_in_button and sign_in_button.is_visible():
                self.debug_print("Found sign in button")
                sign_in_button.click()
                self.random_delay()

            # Enter email
            self.debug_print("Looking for email input")
            email_input = page.wait_for_selector("input[type='email']", timeout=10000)
            if email_input:
                self.debug_print("Found email input")
                email_input.fill(self.email)
                self.random_delay(1)
                page.keyboard.press("Enter")
                self.random_delay(2)

            # Enter password
            self.debug_print("Looking for password input")
            password_input = page.wait_for_selector("input[type='password']", timeout=10000)
            if password_input:
                self.debug_print("Found password input")
                password_input.fill(self.password)
                self.random_delay(1)
                page.keyboard.press("Enter")
                self.random_delay(3)

            # Handle 2FA if needed
            try:
                auth_code_element = page.wait_for_selector("text=Enter code", timeout=10000)
                if auth_code_element:
                    print("\n*** 2FA Required ***")
                    print("Please enter the authentication code manually")
                    input("Press Enter after entering the code...")
            except:
                self.debug_print("No 2FA prompt detected")

            # Wait for main interface
            print("Waiting for Outlook to load...")
            self.wait_for_load(page)
            self.save_debug_screenshot(page, "after_login")
            return True

        except Exception as e:
            print(f"Login error: {e}")
            self.save_debug_screenshot(page, "login_error")
            return False

    def extract_email_content_with_keyboard(self, page):
        """Extract email content using keyboard shortcuts"""
        try:
            # Wait for content to be visible
            print("Waiting for email content to load...")
            page.wait_for_selector('div[role="document"]', timeout=5000)
            self.random_delay(2)

            # Press Ctrl+A to select all
            print("Selecting all content...")
            page.keyboard.press("Control+a")
            self.random_delay(1)

            # Press Ctrl+C to copy
            print("Copying content...")
            page.keyboard.press("Control+c")
            self.random_delay(1)

            # Get clipboard content
            try:
                content = pyperclip.paste()
                if content:
                    return content
            except Exception as e:
                print(f"Error getting clipboard content: {e}")

            # Fallback: try to get content directly
            content = page.evaluate('''() => {
                const element = document.querySelector('div[role="document"]');
                return element ? element.innerText : '';
            }''')

            return content

        except Exception as e:
            print(f"Error extracting content: {e}")
            return None

    def extract_email_metadata(self, item):
        """Extract subject and date from email item"""
        try:
            subject_element = item.query_selector('div[role="heading"]')
            date_element = item.query_selector('div[title*="/"]')
            
            subject = subject_element.inner_text() if subject_element else "No subject"
            date = date_element.get_attribute('title') if date_element else "Date unknown"
            
            return subject, date
        except Exception as e:
            print(f"Error extracting metadata: {e}")
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
            
            print(f'\nSaved emails to {filename}')
            return filename
            
        except Exception as e:
            print(f"Error saving content: {e}")
            return None

    def process_visible_emails(self, page):
        """Process all visible email items on the page"""
        try:
            # Look for email items with Lynn's name
            items = page.query_selector_all('div[role="listitem"]')
            lynn_items = []
            
            print("Scanning for Lynn's emails...")
            for item in items:
                try:
                    if "Lynn Gadue" in item.inner_text():
                        lynn_items.append(item)
                except Exception as e:
                    print(f"Error checking item: {e}")
                    continue
            
            total_items = len(lynn_items)
            print(f"\nFound {total_items} emails from Lynn")
            
            if total_items == 0:
                return False
            
            # Process each email
            for i, item in enumerate(lynn_items, 1):
                try:
                    # Get metadata before clicking
                    subject, date = self.extract_email_metadata(item)
                    print(f"\nProcessing email {i}/{total_items}")
                    print(f"Subject: {subject}")
                    print(f"Date: {date}")
                    
                    # Click to open email
                    print("Opening email...")
                    item.click()
                    self.random_delay(2)
                    
                    # Extract content using keyboard shortcuts
                    content = self.extract_email_content_with_keyboard(page)
                    if content:
                        print(f"Extracted {len(content)} characters")
                        
                        # Format and save the content
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
                        
                        # Save progress
                        self.save_content()
                    
                    # Return to list
                    print("Returning to email list...")
                    page.go_back()
                    self.random_delay(2)
                    
                except Exception as e:
                    print(f"Error processing email {i}: {e}")
                    self.save_debug_screenshot(page, f"error_email_{i}")
                    continue
            
            return True
            
        except Exception as e:
            print(f"Error processing emails: {e}")
            return False

    def extract_emails(self, page):
        try:
            print("\nStarting email extraction...")
            self.save_debug_screenshot(page, "before_extraction")
            
            # Process visible emails
            if self.process_visible_emails(page):
                return self.save_content()
            else:
                print("No emails found to process")
                return None
            
        except Exception as e:
            print(f"Error during extraction: {e}")
            return self.save_content()

def main():
    email = "tolds@3clife.info"
    password = "annuiTy2024!"
    
    extractor = EmailExtractor(email, password)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            if extractor.login_to_outlook(page):
                print("\nLogin successful!")
                filename = extractor.extract_emails(page)
                if filename:
                    print("\nExtraction completed!")
                    print(f"Final file saved as: {filename}")
                else:
                    print("\nExtraction failed!")
            else:
                print("\nLogin failed!")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            print("\nClosing browser...")
            context.close()
            browser.close()

if __name__ == "__main__":
    main()
