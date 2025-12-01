import time
import os
import csv
import re
from typing import Optional, Tuple, List, Dict
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class SeleniumWebDriverContextManager:
    """
    Context manager that creates and tears down a Selenium WebDriver.
    """

    def __init__(
        self,
        browser: str = "chrome",
        headless: bool = False,
        implicit_wait: int = 5,
        page_load_timeout: int = 30,
        window_size: Optional[Tuple[int, int]] = (1400, 1000),
    ):
        self.browser = browser.lower()
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.page_load_timeout = page_load_timeout
        self.window_size = window_size
        self.driver: Optional[WebDriver] = None

    def __enter__(self) -> WebDriver:
        if self.browser == "chrome":
            options = ChromeOptions()
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            if self.window_size:
                options.add_argument(f"--window-size={self.window_size[0]},{self.window_size[1]}")

            # Selenium Manager will download the matching driver automatically
            self.driver = webdriver.Chrome(options=options)
        else:
            raise ValueError(f"Unsupported browser: {self.browser}")

        # timeouts and waits
        self.driver.implicitly_wait(self.implicit_wait)
        self.driver.set_page_load_timeout(self.page_load_timeout)
        return self.driver

    def __exit__(self, exc_type, exc_value, exc_tb):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass


class HTMLReportAutomation:
    """
    Automation class for extracting data from HTML pytest report.
    Handles table extraction and chart filter iteration.
    """

    def __init__(self, driver: WebDriver, output_dir: str = "output"):
        self.driver = driver
        self.output_dir = Path(output_dir)
        self.screenshots_dir = self.output_dir / "screenshots"
        self.csv_dir = self.output_dir / "csv_files"
        
        # Create output directories
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        
        self.wait = WebDriverWait(self.driver, 15)

    def extract_table_to_csv(self, output_filename: str = "table.csv") -> None:
        """
        Extract table content from HTML report and save to CSV.
        """
        print("Extracting table content...")
        
        try:
            time.sleep(2)  # Give JS time to execute
            
            # Attempt 1: Wait for tbody elements to be rendered by JavaScript
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody.results-table-row"))
                )
                print("✓ JavaScript-rendered table content detected")
            except TimeoutException:
                print("⚠ Timeout waiting for JS-rendered content, proceeding anyway...")
            
            # Attempt 2: Try locating table by ID (for headers)
            try:
                table = self.wait.until(
                    EC.presence_of_element_located((By.ID, "results-table"))
                )
                print("✓ Table found using ID locator")
            except TimeoutException:
                # Attempt 3: Try XPath as fallback
                table = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//table[@id='results-table']"))
                )
                print("✓ Table found using XPath locator")
            
            # Extract headers using CSS Selector
            try:
                header = table.find_element(By.CSS_SELECTOR, "thead tr")
                headers = [th.text.strip() for th in header.find_elements(By.TAG_NAME, "th")]
                # Add Error Details column
                headers.append("Error Details")
                print(f"✓ Found {len(headers)} columns: {headers}")
            except NoSuchElementException:
                print("✗ No table header found")
                headers = []
            
            # Extract rows - each test has its own tbody with class 'results-table-row'
            rows_data = []
            try:
                # Find all tbody elements (each represents one test result row)
                tbodies = self.driver.find_elements(By.CSS_SELECTOR, "tbody.results-table-row")
                print(f"✓ Found {len(tbodies)} tbody elements")
                
                for tbody in tbodies:
                    try:
                        # Find the main collapsible row (first tr in tbody)
                        collapsible_row = tbody.find_element(By.CSS_SELECTOR, "tr.collapsible")
                        cells = collapsible_row.find_elements(By.TAG_NAME, "td")
                        row_data = [cell.text.strip() for cell in cells]
                        
                        # Extract error details/logs from extras-row
                        error_details = ""
                        try:
                            extras_row = tbody.find_element(By.CSS_SELECTOR, "tr.extras-row")
                            log_div = extras_row.find_element(By.CSS_SELECTOR, "div.log")
                            if log_div:
                                error_details = log_div.text.strip()
                        except NoSuchElementException:
                            pass
                        
                        # Append error details as an additional column
                        if row_data:
                            row_data.append(error_details if error_details else "No log output captured.")
                            rows_data.append(row_data)
                    except Exception as e:
                        print(f"Warning: Error extracting row from tbody: {e}")
                        continue
                
                print(f"✓ Extracted {len(rows_data)} rows with error details")
            except NoSuchElementException:
                print("✗ No tbody elements found")
            
            # Save to CSV
            csv_path = self.csv_dir / output_filename
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                writer.writerows(rows_data)
            
            print(f"✓ Table saved to: {csv_path}")
            
        except TimeoutException:
            print("✗ Error: Table not found within timeout period")
            raise
        except Exception as e:
            print(f"✗ Error extracting table: {e}")
            raise

    def extract_summary_data_to_csv(self, output_filename: str = "summary.csv") -> None:
        """
        Extract summary statistics from the report (passed, failed, etc.)
        """
        print("Extracting summary data...")
        
        try:
            # Locate summary section
            summary = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "summary"))
            )
            
            # Extract statistics by reading text content from span elements
            stats = []
            
            # The HTML structure has spans like: <span class="failed">8 Failed,</span>
            # We need to extract the number from the text
            for result_type in ['failed', 'passed', 'skipped', 'error', 'xfailed', 'xpassed', 'rerun']:
                try:
                    span_element = summary.find_element(By.CSS_SELECTOR, f"span.{result_type}")
                    text = span_element.text.strip()
                    
                    # Extract the number from text like "8 Failed," or "16 Passed,"
                    import re
                    match = re.search(r'(\d+)', text)
                    if match:
                        count = int(match.group(1))
                        stats.append([result_type.capitalize(), count])
                        print(f"  Found {result_type}: {count}")
                except NoSuchElementException:
                    # Element not found, skip
                    continue
                except Exception as e:
                    print(f"  Warning: Error parsing {result_type}: {e}")
                    continue
            
            # Save to CSV
            csv_path = self.csv_dir / output_filename
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Status', 'Count'])
                writer.writerows(stats)
            
            print(f"✓ Summary saved to: {csv_path}")
            
        except Exception as e:
            print(f"Warning: Could not extract summary data: {e}")

    def take_screenshot(self, filename: str) -> None:
        """Take a screenshot and save it."""
        screenshot_path = self.screenshots_dir / f"{filename}.png"
        self.driver.save_screenshot(str(screenshot_path))
        print(f"✓ Screenshot saved: {screenshot_path}")

    def interact_with_filters_and_extract(self) -> None:
        """
        Iterate through filter checkboxes (passed, failed, skipped, etc.),
        take screenshots, and extract visible data at each stage.
        """
        print("\nInteracting with filters...")
        
        try:
            # Take initial screenshot (all filters on)
            self.take_screenshot("filter_all")
            self.extract_current_visible_data("filter_all.csv")
            
            # Find all filter checkboxes - use data-test-result attribute from HTML
            filter_checkboxes = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "input.filter[data-test-result]"
            )
            
            if not filter_checkboxes:
                print("✗ No filter checkboxes found")
                return
            
            print(f"✓ Found {len(filter_checkboxes)} filter options")
            
            # Process ALL filters (both enabled and disabled) to create CSV for each
            all_filter_types = []
            for checkbox in filter_checkboxes:
                filter_type = checkbox.get_attribute('data-test-result')
                is_disabled = checkbox.get_attribute('disabled') is not None
                all_filter_types.append((checkbox, filter_type, is_disabled))
            
            print(f"✓ {len(all_filter_types)} filters found (enabled and disabled)")
            
            # Iterate through each filter
            for i, (target_checkbox, filter_type, is_disabled) in enumerate(all_filter_types):
                try:
                    print(f"\nProcessing filter {i+1}/{len(all_filter_types)}: {filter_type} {'(disabled)' if is_disabled else ''}")
                    
                    if is_disabled:
                        # For disabled filters, turn off all and try to enable this one (will show 0 results)
                        print(f"  ⚠ {filter_type} is disabled (0 results) - capturing screenshot")
                        
                        # Turn off all filters first
                        all_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input.filter[data-test-result]")
                        for cb in all_checkboxes:
                            if cb.get_attribute('disabled') is None and cb.is_selected():
                                self.driver.execute_script("arguments[0].click();", cb)
                        time.sleep(0.5)
                        
                        # Take screenshot showing empty state
                        self.take_screenshot(f"filter_{filter_type}")
                        
                        # Create empty CSV with just headers
                        csv_path = self.csv_dir / f"filter_{filter_type}.csv"
                        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(['Result', 'Test', 'Duration', 'Links'])
                        continue
                    
                    # Re-fetch all checkboxes (DOM might have changed)
                    all_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input.filter[data-test-result]")
                    
                    # Turn OFF all filters first
                    for cb in all_checkboxes:
                        if cb.get_attribute('disabled') is None and cb.is_selected():
                            self.driver.execute_script("arguments[0].click();", cb)
                    
                    time.sleep(0.3)
                    
                    # Now turn ON only the target filter
                    # Re-fetch the target checkbox by its data-test-result attribute
                    target_cb = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        f"input.filter[data-test-result='{filter_type}']"
                    )
                    
                    if not target_cb.is_selected():
                        self.driver.execute_script("arguments[0].click();", target_cb)
                    
                    time.sleep(0.8)  # Wait for JavaScript to filter rows
                    
                    # Take screenshot showing only this filter (matching CSV filename)
                    self.take_screenshot(f"filter_{filter_type}")
                    
                    # Extract visible data with filter name as filename (e.g., "filter_failed.csv", "filter_passed.csv")
                    self.extract_current_visible_data(f"filter_{filter_type}.csv")
                    
                    print(f"  ✓ Captured {filter_type} filter state")
                    
                except Exception as e:
                    print(f"✗ Error processing filter {filter_type}: {e}")
                    continue
            
            # Edge case: unselect all filters
            print("\nEdge case: Unselecting all filters...")
            all_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input.filter[data-test-result]")
            for checkbox in all_checkboxes:
                try:
                    is_disabled = checkbox.get_attribute('disabled') is not None
                    if not is_disabled and checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                        time.sleep(0.2)
                except:
                    pass
            
            time.sleep(0.5)
            self.take_screenshot("filter_none")
            self.extract_current_visible_data("filter_none.csv")
            
            print(f"\n✓ Filter interaction complete")
            
        except Exception as e:
            print(f"✗ Error during filter interaction: {e}")
            raise

    def extract_current_visible_data(self, output_filename: str) -> None:
        """
        Extract currently visible rows in the results table.
        """
        try:
            time.sleep(0.5)
            
            visible_rows = []
            
            # Find all tbody elements with class 'results-table-row'
            all_tbodies = self.driver.find_elements(By.CSS_SELECTOR, "tbody.results-table-row")
            
            for tbody in all_tbodies:
                # Check if tbody is visible (not filtered out)
                if tbody.is_displayed():
                    try:
                        # Get the collapsible row (main data row) from this tbody
                        collapsible_row = tbody.find_element(By.CSS_SELECTOR, "tr.collapsible")
                        cells = collapsible_row.find_elements(By.TAG_NAME, "td")
                        row_data = [cell.text.strip() for cell in cells]
                        if row_data:
                            visible_rows.append(row_data)
                    except:
                        continue
            
            # Get headers
            table = self.driver.find_element(By.ID, "results-table")
            header_cells = table.find_elements(By.XPATH, ".//thead//th")
            headers = [th.text.strip() for th in header_cells]
            
            # Save to CSV
            csv_path = self.csv_dir / output_filename
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                writer.writerows(visible_rows)
            
            print(f"  ✓ Extracted {len(visible_rows)} visible rows to {output_filename}")
            
        except Exception as e:
            print(f"  Warning: Could not extract visible data: {e}")


def main(report_path: str, headless: bool = False):
    """
    Main automation flow.
    
    Args:
        report_path: Path to the HTML report file
        headless: Whether to run browser in headless mode
    """
    print("=" * 60)
    print("HTML Report Automation Starting")
    print("=" * 60)
    
    # Convert to absolute path and file:// URL
    report_file = Path(report_path).resolve()
    if not report_file.exists():
        raise FileNotFoundError(f"Report file not found: {report_file}")
    
    file_url = f"file:///{str(report_file).replace(os.sep, '/')}"
    print(f"\nReport URL: {file_url}")
    
    with SeleniumWebDriverContextManager(headless=headless) as driver:
        # Load the HTML report
        driver.get(file_url)
        print("✓ Report loaded successfully")
        
        # Wait for page to fully load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "results-table"))
        )
        
        # Initialize automation helper
        automation = HTMLReportAutomation(driver, output_dir="output")
        
        # Task 2: Extract table to CSV
        print("\n" + "=" * 60)
        print("TASK 2: Table Extraction")
        print("=" * 60)
        automation.extract_table_to_csv("table.csv")
        automation.extract_summary_data_to_csv("summary.csv")
        
        # Task 3: Doughnut chart / Filter interaction
        print("\n" + "=" * 60)
        print("TASK 3: Filter Interaction & Screenshots")
        print("=" * 60)
        automation.interact_with_filters_and_extract()
        
        print("\n" + "=" * 60)
        print("Automation Complete!")
        print("=" * 60)
        print(f"\nOutputs:")
        print(f"  - CSV files: {automation.csv_dir}")
        print(f"  - Screenshots: {automation.screenshots_dir}")
        print("=" * 60)
        
        if not headless:
            time.sleep(2)


if __name__ == "__main__":
    # Path to the HTML report
    report_path = r"report.html"
    
    # Run automation
    main(report_path=report_path, headless=False)