#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Child Info Extractor - Extract child IDs and names from ChildPaths HTML

Extracts child information from HTML files and exports to CSV or Excel.

Author: wolketich
Last updated: 2025-04-29
"""

import re
import logging
import sys
import csv
import os
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Union
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('child_extractor')

class ChildInfoExtractor:
    """Extract child information from ChildPaths HTML."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.child_id_pattern = re.compile(r'/child/([^/]+)')
        self.all_children = []
        
    def _sanitize_text(self, text: Optional[str]) -> str:
        """Clean up text - handling whitespace, non-breaking spaces, etc."""
        if not text:
            return ""
        return ' '.join(text.replace('\xa0', ' ').split())
    
    def _extract_child_id(self, href: str) -> Optional[str]:
        """Pull the child ID from a URL."""
        if not href:
            return None
            
        match = self.child_id_pattern.search(href)
        return match.group(1) if match else None
    
    def _find_child_name(self, anchor_tag) -> str:
        """Extract child name from the anchor tag structure."""
        # First try the expected structure
        name_div = anchor_tag.find('div', {'class': ['col-lg-8', 'col-xs-8']})
        
        if name_div:
            return self._sanitize_text(name_div.text)
            
        # If that didn't work, try a few common variations
        alt_name_div = anchor_tag.find('div', text=re.compile(r'\w+'))
        if alt_name_div:
            return self._sanitize_text(alt_name_div.text)
            
        # Last resort: just get all text from the anchor
        all_text = self._sanitize_text(anchor_tag.text)
        if all_text:
            return all_text
            
        return "Unknown"
    
    def process_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Read and process HTML from a file
        
        Args:
            file_path: Path to the HTML file
            
        Returns:
            List of extracted child information dictionaries
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                logger.info(f"Successfully read file: {file_path} ({len(html_content)} bytes)")
                return self.extract_from_html(html_content, source=os.path.basename(file_path))
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return []
    
    def process_directory(self, dir_path: str, extension: str = '.html') -> List[Dict[str, str]]:
        """
        Process all HTML files in a directory
        
        Args:
            dir_path: Path to directory containing HTML files
            extension: File extension to filter for
            
        Returns:
            List of all extracted child information
        """
        results = []
        try:
            files = [f for f in os.listdir(dir_path) if f.endswith(extension)]
            logger.info(f"Found {len(files)} {extension} files in {dir_path}")
            
            for file in files:
                file_path = os.path.join(dir_path, file)
                file_results = self.process_file(file_path)
                results.extend(file_results)
                logger.info(f"Extracted {len(file_results)} children from {file}")
            
            return results
        except Exception as e:
            logger.error(f"Failed to process directory {dir_path}: {e}")
            return []
    
    def extract_from_html(self, html_content: str, source: str = "unknown") -> List[Dict[str, str]]:
        """
        Parse HTML and extract all child information.
        
        Args:
            html_content: HTML string to parse
            source: Source identifier for tracking
            
        Returns:
            List of dictionaries with child information
        """
        if not html_content:
            logger.warning("Empty HTML content provided")
            return []
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
            return []
        
        children = []
        child_links = soup.find_all('a', href=re.compile(r'/child/'))
        
        if not child_links and self.debug:
            logger.debug("No child links found - might be using unexpected HTML structure")
            all_links = soup.find_all('a')
            for link in all_links:
                logger.debug(f"Found link: {link.get('href')}")
        
        for idx, a_tag in enumerate(child_links):
            try:
                href = a_tag.get('href', '')
                child_id = self._extract_child_id(href)
                
                if not child_id:
                    logger.warning(f"Could not extract child ID from link: {href}")
                    continue
                
                child_name = self._find_child_name(a_tag)
                
                if not child_name or child_name == "Unknown":
                    logger.warning(f"Could not extract name for child ID: {child_id}")
                    parent_row = a_tag.find_parent('div', {'class': 'row'})
                    if parent_row:
                        all_text = self._sanitize_text(parent_row.text)
                        for common_text in ["overview", "profile", "details"]:
                            all_text = all_text.replace(common_text, "")
                        if all_text:
                            child_name = all_text
                
                child_info = {
                    'id': child_id,
                    'name': child_name,
                    'source': source,
                    'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Check if this child is already in our list (avoid duplicates)
                if not any(c['id'] == child_id for c in self.all_children):
                    children.append(child_info)
                    self.all_children.append(child_info)
                
            except Exception as e:
                logger.error(f"Error processing child #{idx+1}: {e}")
                continue
        
        if not children:
            logger.warning(f"No children extracted from source: {source}")
            
        return children
    
    def export_to_csv(self, filename: str = None) -> str:
        """
        Export all extracted children to CSV file
        
        Args:
            filename: Optional filename to use for the CSV
            
        Returns:
            Path to the created CSV file
        """
        if not self.all_children:
            logger.warning("No children to export")
            return ""
            
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"child_data_{timestamp}.csv"
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'name', 'source', 'extraction_time']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for child in self.all_children:
                    writer.writerow(child)
                    
            logger.info(f"Successfully exported {len(self.all_children)} children to {filename}")
            return os.path.abspath(filename)
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return ""
    
    def export_to_excel(self, filename: str = None) -> str:
        """
        Export all extracted children to Excel file
        
        Args:
            filename: Optional filename to use for the Excel file
            
        Returns:
            Path to the created Excel file
        """
        if not self.all_children:
            logger.warning("No children to export")
            return ""
            
        try:
            # Only import pandas when needed
            import pandas as pd
        except ImportError:
            logger.error("pandas is required for Excel export. Please install it with: pip install pandas openpyxl")
            return ""
            
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"child_data_{timestamp}.xlsx"
            
        try:
            df = pd.DataFrame(self.all_children)
            df.to_excel(filename, index=False, engine='openpyxl')
            
            logger.info(f"Successfully exported {len(self.all_children)} children to {filename}")
            return os.path.abspath(filename)
            
        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            return ""


def main():
    """Command-line interface for the extractor."""
    parser = argparse.ArgumentParser(
        description='Extract child IDs and names from ChildPaths HTML files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single HTML file
  python child_info_extractor.py -f path/to/file.html -o output.csv
  
  # Process all HTML files in a directory
  python child_info_extractor.py -d path/to/directory -o output.xlsx
  
  # Interactive mode
  python child_info_extractor.py -i
  
  # Process specific files with debug info
  python child_info_extractor.py -f file1.html file2.html -v
  """
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-f', '--files', nargs='+', help='HTML file(s) to process')
    input_group.add_argument('-d', '--directory', help='Directory containing HTML files to process')
    input_group.add_argument('-i', '--interactive', action='store_true', help='Run in interactive mode')
    
    parser.add_argument('-o', '--output', help='Output file path (CSV or Excel)')
    parser.add_argument('-e', '--extension', default='.html', help='File extension when processing directory (default: .html)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug output')
    parser.add_argument('--format', choices=['csv', 'excel'], default='csv', help='Output format (default: csv)')
    parser.add_argument('--live', action='store_true', help='Extract data live from ChildPaths.ie via Selenium')
    parser.add_argument('--email', help='Email for ChildPaths login (used with --live)')
    parser.add_argument('--password', help='Password for ChildPaths login (used with --live)')

    
    args = parser.parse_args()
    
    extractor = ChildInfoExtractor(debug=args.verbose)
    
    # Display header
    print("\n" + "="*60)
    print("  ChildPaths Information Extractor")
    print(f"  User: {os.getlogin() or 'Unknown'} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if args.live:
        if not args.email or not args.password:
            print("Error: --email and --password are required for --live mode")
            return

        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        print("\nRunning in LIVE mode using Selenium...")

        options = Options()
        options.add_argument("--headless")  # comment out if debugging
        driver = webdriver.Chrome(options=options)

        try:
            wait = WebDriverWait(driver, 10)

            # Log in
            driver.get('https://app.childpaths.ie/auth/login')
            wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(args.email)
            driver.find_element(By.ID, "password").send_keys(args.password)
            driver.find_element(By.CSS_SELECTOR, "#signin-form > button").click()

            # Go to child list
            wait.until(EC.url_contains("/dashboard"))  # wait for post-login redirect
            driver.get('https://app.childpaths.ie/child/index')
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#child-index-table > tbody tr")))

            # Get first child info
            first_row = driver.find_element(By.CSS_SELECTOR, "#child-index-table > tbody tr")
            profile_link_tag = first_row.find_element(By.CSS_SELECTOR, "td:nth-of-type(2) a")
            first_child_name = profile_link_tag.text.strip()
            profile_href = profile_link_tag.get_attribute("href")
            first_child_id = profile_href.split("/child/")[1].split("/")[0]

            extractor = ChildInfoExtractor(debug=args.verbose)
            extractor.all_children.append({
                'id': first_child_id,
                'name': first_child_name,
                'source': 'child-index',
                'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            # Switch modal
            driver.get(f"https://app.childpaths.ie/child/{first_child_id}/switch")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#main-body > div.modal-wrapper")))
            modal = driver.find_element(By.CSS_SELECTOR, "#main-body > div.modal-wrapper")
            html_content = modal.get_attribute("outerHTML")

            # Parse modal
            children = extractor.extract_from_html(html_content, source='live_session')

            # Export
            if args.format == 'excel':
                filepath = extractor.export_to_excel(args.output)
            else:
                filepath = extractor.export_to_csv(args.output)

            if filepath:
                print(f"\n✅ Exported {len(extractor.all_children)} children to: {filepath}")
            else:
                print("\n❌ Failed to export data.")

        finally:
            driver.quit()
        return


    if args.interactive:
        run_interactive_mode(extractor)
        return
    
    # Process input sources
    if args.files:
        for file_path in args.files:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                continue
                
            print(f"\nProcessing file: {file_path}")
            children = extractor.process_file(file_path)
            print(f"Extracted {len(children)} children from this file")
    
    elif args.directory:
        if not os.path.isdir(args.directory):
            logger.error(f"Directory not found: {args.directory}")
            return
            
        print(f"\nProcessing all {args.extension} files in: {args.directory}")
        children = extractor.process_directory(args.directory, args.extension)
        print(f"Extracted {len(children)} children from all files")
    
    # Output results
    if not extractor.all_children:
        print("\nNo children were extracted. Please check your input files.")
        return
    
    # Determine output filename
    output_filename = args.output
    if not output_filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        extension = '.xlsx' if args.format == 'excel' else '.csv'
        output_filename = f"child_data_{timestamp}{extension}"
    
    # Export based on format
    if args.format == 'excel' or output_filename.endswith(('.xlsx', '.xls')):
        filepath = extractor.export_to_excel(output_filename)
    else:
        filepath = extractor.export_to_csv(output_filename)
    
    if filepath:
        print(f"\nSuccessfully exported {len(extractor.all_children)} children to: {filepath}")
    else:
        print("\nFailed to export data. Check log for details.")


def run_interactive_mode(extractor):
    """Run the interactive command-line interface."""
    print("\nInteractive Mode")
    print("This tool extracts child IDs and names from ChildPaths HTML files.")
    
    while True:
        print("\n" + "-"*60)
        print("Menu:")
        print("1. Process an HTML file")
        print("2. Process a directory of HTML files")
        print("3. Export current data")
        print("4. View summary of extracted data")
        print("5. Quit")
        print("-"*60)
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            file_path = input("Enter the path to the HTML file: ").strip()
            if not os.path.exists(file_path):
                print(f"Error: File not found: {file_path}")
                continue
                
            print(f"\nProcessing file: {file_path}")
            children = extractor.process_file(file_path)
            print(f"Extracted {len(children)} children from this file")
            
        elif choice == '2':
            dir_path = input("Enter the directory path: ").strip()
            if not os.path.isdir(dir_path):
                print(f"Error: Directory not found: {dir_path}")
                continue
                
            extension = input("Enter file extension to process (default: .html): ").strip() or '.html'
            print(f"\nProcessing all {extension} files in: {dir_path}")
            children = extractor.process_directory(dir_path, extension)
            print(f"Extracted {len(children)} children from all files")
            
        elif choice == '3':
            if not extractor.all_children:
                print("No children to export. Please process some files first.")
                continue
                
            export_format = input("Export as CSV or Excel? (csv/excel): ").strip().lower()
            
            if export_format == 'csv':
                default_filename = f"child_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filename = input(f"Enter filename (default: {default_filename}): ").strip()
                filename = filename or default_filename
                
                filepath = extractor.export_to_csv(filename)
                if filepath:
                    print(f"Data exported to: {filepath}")
            
            elif export_format == 'excel':
                default_filename = f"child_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                filename = input(f"Enter filename (default: {default_filename}): ").strip()
                filename = filename or default_filename
                
                filepath = extractor.export_to_excel(filename)
                if filepath:
                    print(f"Data exported to: {filepath}")
            
            else:
                print("Invalid format. Please choose 'csv' or 'excel'.")
            
        elif choice == '4':
            if not extractor.all_children:
                print("No children have been extracted yet.")
                continue
                
            print(f"\nExtracted {len(extractor.all_children)} children in total:")
            
            # Group by source
            sources = {}
            for child in extractor.all_children:
                source = child.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
                
            print("\nBreakdown by source:")
            for source, count in sources.items():
                print(f"  {source}: {count} children")
                
            # Show sample of data
            print("\nSample data (first 5 entries):")
            for i, child in enumerate(extractor.all_children[:5]):
                print(f"  {i+1}. {child['name']} (ID: {child['id']})")
                
            if len(extractor.all_children) > 5:
                print(f"  ... and {len(extractor.all_children)-5} more")
            
        elif choice == '5':
            # Ask if they want to save before quitting if they have data
            if extractor.all_children:
                save_action = input("Save data before quitting? (yes/no): ").strip().lower()
                if save_action in ('yes', 'y'):
                    export_format = input("Export as CSV or Excel? (csv/excel): ").strip().lower()
                    
                    if export_format == 'csv':
                        default_filename = f"child_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        filename = input(f"Enter filename (default: {default_filename}): ").strip()
                        filename = filename or default_filename
                        
                        filepath = extractor.export_to_csv(filename)
                        if filepath:
                            print(f"Data exported to: {filepath}")
                    
                    elif export_format == 'excel':
                        default_filename = f"child_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        filename = input(f"Enter filename (default: {default_filename}): ").strip()
                        filename = filename or default_filename
                        
                        filepath = extractor.export_to_excel(filename)
                        if filepath:
                            print(f"Data exported to: {filepath}")
            
            print("\nThank you for using the ChildPaths Information Extractor. Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")


if __name__ == "__main__":
    main()