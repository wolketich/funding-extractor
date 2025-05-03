#!/usr/bin/env python3
"""
Funding Allocation Data Extractor

This script extracts funding information from Excel files and matches children with the main system.

Usage:
    python funding_extractor.py --children CHILDREN_FILE --funding FUNDING_FILE --system SYSTEM_FILE [--output-dir OUTPUT_DIR]
"""

import argparse
import sys
import pandas as pd
import re
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import Counter


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}===== {text} ====={Colors.ENDC}\n")


def print_status(message, status="info"):
    """Print a status message with color coding."""
    if status == "info":
        print(f"{Colors.CYAN}ℹ {message}{Colors.ENDC}")
    elif status == "success":
        print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")
    elif status == "error":
        print(f"{Colors.RED}✗ {message}{Colors.ENDC}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠ {message}{Colors.ENDC}")


def print_progress(current, total, message="Processing", length=40):
    """Print a progress bar."""
    percent = current / total
    bar = '█' * int(percent * length) + '-' * (length - int(percent * length))
    print(f"\r{Colors.BLUE}{message}: |{bar}| {int(percent*100)}% ({current}/{total}){Colors.ENDC}", end='')
    if current == total:
        print()


def clean_name(name: str) -> str:
    """
    Clean a name by removing "father", dashes, and keeping only alphanumeric characters and spaces.
    
    Parameters:
    -----------
    name : str
        Name to clean
        
    Returns:
    --------
    str
        Cleaned name
    """
    if not name or not isinstance(name, str):
        return ""
    
    # Remove "father" (case-insensitive)
    name = re.sub(r'(?i)\bfather\b', '', name)
    
    # Remove dashes
    name = name.replace('-', ' ')
    
    # Keep only alphanumeric characters and spaces
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    
    # Remove extra spaces
    name = ' '.join(name.split())
    
    return name


def normalize_name(name: str) -> str:
    """
    Normalize a name for case-insensitive comparison.
    
    Parameters:
    -----------
    name : str
        Name to normalize
        
    Returns:
    --------
    str
        Normalized name (lowercase, no extra spaces)
    """
    if not name or not isinstance(name, str):
        return ""
    return ' '.join(name.lower().split())


def extract_hours_and_rate(description: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract hours and rate from allocation description.
    
    Parameters:
    -----------
    description : str
        Description string like "30.00 hours x €2.79"
        
    Returns:
    --------
    Tuple[Optional[float], Optional[float]]
        Tuple of (hours, rate), or (None, None) if extraction fails
    """
    if not description or not isinstance(description, str):
        return None, None
        
    match = re.search(r'(\d+\.\d+|\d+) hours x €(\d+\.\d+|\d+)', description)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def find_potential_matches(name: str, system_names: List[str], max_matches: int = 5) -> List[Tuple[str, int]]:
    """
    Find potential matches for a name in the system based on word overlap.
    
    Parameters:
    -----------
    name : str
        Name to find matches for
    system_names : List[str]
        List of names in the main system
    max_matches : int
        Maximum number of matches to return (default 5, but will return up to 15 when single-word matches)
        
    Returns:
    --------
    List[Tuple[str, int]]
        List of (name, matching_word_count) tuples, sorted by match count descending
    """
    if not name or not isinstance(name, str):
        return []
        
    # Split name into words and convert to lowercase
    normalized_name = normalize_name(name)
    name_words = set(normalized_name.split())
    
    # Calculate word overlap for each system name
    matches = []
    for system_name in system_names:
        if not isinstance(system_name, str):
            continue
            
        normalized_system_name = normalize_name(system_name)
        system_words = set(normalized_system_name.split())
        common_words = name_words.intersection(system_words)
        
        # Only consider if there's at least one matching word
        if common_words:
            matches.append((system_name, len(common_words)))
    
    # Sort by number of matching words (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    # If the best match only has 1 matching word, return more options (up to 15)
    if matches and matches[0][1] == 1:
        return matches[:15]  # Return more options for single-word matches
    
    return matches[:max_matches]  # Otherwise return the default number


def interactive_matching(unmatched_children: List[Dict], system_names: List[str]) -> Dict[str, str]:
    """
    Interactive terminal process for matching unmatched children.
    
    Parameters:
    -----------
    unmatched_children : List[Dict]
        List of dictionaries with child information
    system_names : List[str]
        List of names in the main system
        
    Returns:
    --------
    Dict[str, str]
        Dictionary mapping original names to matched system names
    """
    matches = {}
    total = len(unmatched_children)
    processed = 0
    
    clear_screen()
    print_header("INTERACTIVE NAME MATCHING")
    print_status(f"Found {total} children that need matching", "info")
    print()
    
    for idx, child in enumerate(unmatched_children):
        child_name = child['Child Name']
        chick = child.get('CHICK', '')
        
        # Clear screen for each new child
        clear_screen()
        
        # Display current progress
        print(f"Processing: {idx+1} of {total}")
        
        # Get current date/time and user
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_user = "wolketich"
        print(f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {current_time}")
        print(f"Current User's Login: {current_user}")
        print()
        
        # Display the unmatched child
        print(f"Unmatched Name: {Colors.YELLOW}{child_name}{Colors.ENDC}")
        if chick:
            print(f"CHICK: {chick}")
        
        # Get potential matches - potentially more if only single-word matches
        potential_matches = find_potential_matches(child_name, system_names)
        
        # Display possible matches in the requested format
        print("\nPossible Matches")
        
        for i, (match_name, word_count) in enumerate(potential_matches, 1):
            match_info = f"{match_name}"
            if word_count == 1:
                match_info += f" (single-word match)"  # Indicate single-word matches
            print(f"{i}) {match_info}")
        
        # Add the skip option
        print(f"\n0) No Match (skip)")
        
        # Get user choice
        while True:
            choice = input("\nSelect option: ").strip()
            
            if choice == '0':
                print_status("Skipping this child", "info")
                processed += 1
                break
                
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(potential_matches):
                    selected_match = potential_matches[choice_idx][0]
                    matches[child_name] = selected_match
                    print_status(f"Matched '{child_name}' to '{selected_match}'", "success")
                    processed += 1
                    time.sleep(1)  # Brief pause to show the success message
                    break
                else:
                    print_status("Invalid selection. Try again.", "error")
            except ValueError:
                print_status("Please enter a number between 0 and " + str(len(potential_matches)), "error")
    
    # Show final summary
    clear_screen()
    print_header("MATCHING COMPLETE")
    print_status(f"Processed {processed} of {total} children", "info")
    print_status(f"Created {len(matches)} manual matches", "success")
    print_status(f"Skipped {processed - len(matches)} children", "info")
    
    return matches


def extract_funding_data(children_file: str, funding_file: str, system_file: str, 
                         interactive: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract funding data and check if children exist in the main system.
    
    Parameters:
    -----------
    children_file : str
        Path to the Excel file containing children's details
    funding_file : str
        Path to the Excel file containing funding details
    system_file : str
        Path to the Excel file containing main system data
    interactive : bool
        Whether to enable interactive matching in terminal
        
    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame]
        Tuple containing:
        1. DataFrame with funding data and system match status
        2. DataFrame with unmatched children and potential matches
    """
    print_status(f"Reading Excel files...", "info")
    
    try:
        # Read Excel files
        children_df = pd.read_excel(children_file)
        funding_df = pd.read_excel(funding_file)
        system_df = pd.read_excel(system_file)
        
        print_status(f"Successfully read: {os.path.basename(children_file)}", "success")
        print_status(f"Successfully read: {os.path.basename(funding_file)}", "success")
        print_status(f"Successfully read: {os.path.basename(system_file)}", "success")
    except Exception as e:
        print_status(f"Error reading Excel files: {e}", "error")
        sys.exit(1)
    
    # Get column names and handle possible variations
    print_status("Identifying column names...", "info")
    
    child_col = next((col for col in children_df.columns if 'Child' in col), None)
    dob_col = next((col for col in children_df.columns if 'Birth' in col), None)
    chick_col = next((col for col in children_df.columns if 'CHICK' in col), None)
    claim_until_col = next((col for col in children_df.columns if 'Claim Until' in col), None)
    
    funding_child_col = next((col for col in funding_df.columns if 'Child' in col), None)
    alloc_desc_col = next((col for col in funding_df.columns if 'Description' in col), None)
    alloc_date_col = next((col for col in funding_df.columns if 'Date' in col and 'Approved' not in col), None)
    
    system_name_col = 'name'
    
    if not all([child_col, funding_child_col, alloc_desc_col, alloc_date_col]):
        print_status("Required columns not found in input files", "error")
        sys.exit(1)
    
    if system_name_col not in system_df.columns:
        print_status(f"Name column '{system_name_col}' not found in system file", "error")
        sys.exit(1)
    
    print_status("Columns identified successfully", "success")
    
    # Get list of system names for matching
    system_names = system_df[system_name_col].dropna().tolist()
    
    # Create dictionary of normalized system names for case-insensitive matching
    normalized_system_names = {normalize_name(name): name for name in system_names}
    
    # Create empty lists to store result rows
    result_rows = []
    unmatched_rows = []
    
    # Get current date for filtering allocations
    current_date = datetime.now().date()
    
    # Process each child
    total_children = len(children_df)
    print_header(f"PROCESSING {total_children} CHILDREN")
    
    for idx, (_, child_row) in enumerate(children_df.iterrows()):
        child_name = child_row[child_col]
        dob = child_row.get(dob_col, None) if dob_col else None
        chick = child_row.get(chick_col, None) if chick_col else None
        claim_until = child_row.get(claim_until_col, None) if claim_until_col else None
        
        # Clean the child name
        cleaned_name = clean_name(child_name)
        
        print_progress(idx + 1, total_children, f"Processing {cleaned_name}")
        
        # Get all funding entries for this child
        child_funding = funding_df[funding_df[funding_child_col] == child_name]
        
        # Initialize values
        start_date = None
        hour_values = set()
        latest_rate = None
        
        if len(child_funding) > 0:
            # Make a copy to avoid modifying the original DataFrame
            child_funding = child_funding.copy()
            
            # Convert dates column to datetime safely
            try:
                # First try to convert using default format
                date_col = pd.to_datetime(child_funding[alloc_date_col], errors='coerce', dayfirst=True)
                
                # If that fails, try different common formats
                if date_col.isna().all():
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y']:
                        try:
                            date_col = pd.to_datetime(child_funding[alloc_date_col], format=fmt, errors='coerce', dayfirst=True)
                            if not date_col.isna().all():
                                break
                        except:
                            continue
                
                child_funding['date_converted'] = date_col
                
                # Only keep rows with valid dates
                child_funding = child_funding.dropna(subset=['date_converted'])
                
                if len(child_funding) == 0:
                    print_status(f"No valid dates found for {child_name}", "warning")
                    continue
                    
            except Exception as e:
                print_status(f"Error converting dates for {child_name}: {e}", "error")
                continue
            
            # Find start date (earliest allocation date minus 6 days)
            min_date = child_funding['date_converted'].min()
            claim_until_date = pd.to_datetime(claim_until, errors='coerce') if claim_until else None

            if not pd.isna(min_date) and not pd.isna(claim_until_date):
                # Calculate CHICK start (expiry - 363 days, then round to Monday)
                chick_start = claim_until_date - timedelta(days=363)
                chick_start -= timedelta(days=chick_start.weekday())

                if min_date > claim_until_date:
                    start_date = "ERROR: allocation after expiry"
                elif chick_start <= min_date <= claim_until_date:
                    start_date = min_date.date()
                else:
                    start_date = chick_start.date()
            else:
                start_date = None  # or handle/log missing dates
            
            # Filter allocations to only include current or future ones
            # Safely compare dates - convert datetime to date objects first
            try:
                current_or_future_funding = child_funding[
                    child_funding['date_converted'].dt.date >= current_date
                ]
            except:
                # If the dt.date approach fails, try an alternative method
                current_or_future_funding = child_funding[
                    child_funding['date_converted'] >= pd.Timestamp(current_date)
                ]
            
            # If no current/future funding, use all funding (as fallback)
            if len(current_or_future_funding) == 0:
                print_status(f"No current/future funding found for {child_name}, using all funding", "warning")
                current_or_future_funding = child_funding
            
            # Collect all distinct hour values from current or future funding
            for _, fund_row in current_or_future_funding.iterrows():
                desc = fund_row.get(alloc_desc_col, '')
                hours, rate = extract_hours_and_rate(desc)
                
                if hours is not None:
                    hour_values.add(hours)
                if rate is not None:
                    latest_rate = rate
            
            # Get most recent rate by sorting by date
            latest_entries = current_or_future_funding.sort_values(by='date_converted', ascending=False)
            for _, fund_row in latest_entries.iterrows():
                desc = fund_row.get(alloc_desc_col, '')
                _, rate = extract_hours_and_rate(desc)
                if rate is not None:
                    latest_rate = rate
                    break
        
        # Format the weekly total as a sorted string (e.g., "21/30")
        weekly_total = "/".join(map(str, sorted(int(h) for h in hour_values))) if hour_values else ""
        
        # Format the start date
        start_date_str = start_date.strftime("%d/%m/%Y") if start_date else ""
        
        # Check if child is in the main system (case-insensitive)
        normalized_child_name = normalize_name(child_name)
        system_match = "Yes" if normalized_child_name in normalized_system_names else "No"
        
        # If not matched directly, find potential matches
        potential_matches = []
        if system_match == "No":
            match_results = find_potential_matches(child_name, system_names)
            potential_matches = [name for name, _ in match_results]
            
            # Store just the first 5 matches in the unmatched list
            # (all potential matches will be shown during interactive matching)

            unmatched_rows.append({
                'Child Name': child_name,
                'CHICK': chick,
                'Potential Match 1': potential_matches[0] if len(potential_matches) > 0 else "",
                'Potential Match 2': potential_matches[1] if len(potential_matches) > 1 else "",
                'Potential Match 3': potential_matches[2] if len(potential_matches) > 2 else "",
                'Potential Match 4': potential_matches[3] if len(potential_matches) > 3 else "",
                'Potential Match 5': potential_matches[4] if len(potential_matches) > 4 else ""
            })
        
        # Add row for this child
        result_rows.append({
            'Child': cleaned_name,  # Use cleaned name in output
            'Original Child Name': child_name,  # Keep original for reference
            'Date of Birth': dob,
            'CHICK': chick,
            'Claim Until': claim_until,
            'Start date': start_date_str,
            'Weekly Total': weekly_total,
            'Hour rate': f"€{latest_rate:.2f}" if latest_rate is not None else "",
            'In System': system_match
        })
    
    # Create DataFrames from result rows
    result_df = pd.DataFrame(result_rows)
    unmatched_df = pd.DataFrame(unmatched_rows)
    
    # Interactive matching if enabled
    if interactive and not unmatched_df.empty:
        print_header("STARTING INTERACTIVE MATCHING")
        print_status(f"Found {len(unmatched_df)} children not matched in the system", "info")
        time.sleep(1)  # Short pause for user to read the message
        
        unmatched_list = unmatched_df.to_dict('records')
        matches = interactive_matching(unmatched_list, system_names)
        
        # Update result DataFrame with manual matches
        for original, matched in matches.items():
            mask = result_df['Original Child Name'] == original
            result_df.loc[mask, 'In System'] = 'Manual Match'
            
            # Use the matched name (cleaned) instead of the original name
            cleaned_matched_name = clean_name(matched)
            result_df.loc[mask, 'Child'] = cleaned_matched_name
            
            # Store the matched name for reference
            if 'Matched Name' not in result_df.columns:
                result_df['Matched Name'] = ""
            result_df.loc[mask, 'Matched Name'] = matched
    
    return result_df, unmatched_df


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract funding allocation data from Excel files and match with main system'
    )
    
    parser.add_argument(
        '--children', '-c', 
        required=True,
        help='Path to Excel file containing children details'
    )
    
    parser.add_argument(
        '--funding', '-f',
        required=True, 
        help='Path to Excel file containing funding allocation details'
    )
    
    parser.add_argument(
        '--system', '-s',
        required=True,
        help='Path to Excel file containing main system data'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='output',
        help='Output directory path (default: output)'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Enable interactive matching in terminal'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Display verbose output'
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    clear_screen()
    print_header("FUNDING ALLOCATION DATA EXTRACTOR")
    
    args = parse_arguments()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = "wolketich"
    
    print_status(f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {timestamp}", "info")
    print_status(f"Current User's Login: {user}", "info")
    print_status(f"Processing files:", "info")
    print_status(f"- Children: {args.children}", "info")
    print_status(f"- Funding: {args.funding}", "info")
    print_status(f"- System: {args.system}", "info")
    print_status(f"- Output Directory: {args.output_dir}", "info")
    
    try:
        # Extract funding data and check system matches
        result_df, unmatched_df = extract_funding_data(
            args.children, args.funding, args.system, args.interactive
        )
        
        # Add metadata
        result_df['Generated Date (UTC)'] = timestamp
        result_df['Generated By'] = user
        
        unmatched_df['Generated Date (UTC)'] = timestamp
        unmatched_df['Generated By'] = user
        
        # Display summary statistics
        print_header("SUMMARY")
        print_status(f"Processed {len(result_df)} children", "success")
        print_status(f"Children with funding data: {result_df['Weekly Total'].str.len().gt(0).sum()}", "info")
        print_status(f"Children found in system: {(result_df['In System'] == 'Yes').sum()}", "success")
        print_status(f"Children not found in system: {(result_df['In System'] == 'No').sum()}", "warning")
        
        if 'Matched Name' in result_df.columns:
            manual_matches = (result_df['In System'] == 'Manual Match').sum()
            print_status(f"Children manually matched: {manual_matches}", "info")
        
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Create basic child information file (File 1)
        basic_info_df = result_df[['Child', 'CHICK', 'Date of Birth', 'Claim Until']].copy()
        basic_output_path = os.path.join(args.output_dir, "toChildPathsUploader.xlsx")
        basic_info_df.to_excel(basic_output_path, index=False)
        print_status(f"Basic child information saved to {basic_output_path}", "success")
        
        # Create complete funding information file (File 2)
        complete_info_df = result_df[['Child', 'CHICK', 'Date of Birth', 'Claim Until', 
                                     'Start date', 'Weekly Total', 'Hour rate']].copy()
        complete_output_path = os.path.join(args.output_dir, "forAutoFiller.csv")
        complete_info_df.to_csv(complete_output_path, index=False, encoding='utf-8-sig')
        print_status(f"Complete funding information saved to {complete_output_path}", "success")
        
        # Save unmatched report if there are any unmatched children
        if not unmatched_df.empty:
            unmatched_output_path = os.path.join(args.output_dir, "unmatchedChildren.csv")
            unmatched_df.to_csv(unmatched_output_path, index=False)
            print_status(f"Unmatched children report saved to {unmatched_output_path}", "success")
        
    except Exception as e:
        print_status(f"Error: {e}", "error")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
    
    print_header("PROCESS COMPLETE")


if __name__ == "__main__":
    main()