#!/usr/bin/env python3
"""
Funding Allocation Data Extractor

This script extracts funding information from Excel files containing child and funding data.
It identifies different hour allocations (term vs holiday) and outputs consolidated information.

Usage:
    python funding_extractor.py --children CHILDREN_FILE --funding FUNDING_FILE [--output OUTPUT_FILE]
"""

import argparse
import sys
import pandas as pd
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set


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


def extract_funding_data(children_file: str, funding_file: str) -> pd.DataFrame:
    """
    Extract and process funding allocation information from Excel files.
    
    Parameters:
    -----------
    children_file : str
        Path to the Excel file containing children's details
    funding_file : str
        Path to the Excel file containing funding details
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: Child name, Date of Birth, CHICK, Claim Until, 
        Start date, Weekly Total, Hour rate
    """
    try:
        # Read Excel files
        children_df = pd.read_excel(children_file)
        funding_df = pd.read_excel(funding_file)
    except Exception as e:
        print(f"Error reading Excel files: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create empty list to store result rows
    result_rows = []
    
    # Get column names and handle possible variations
    child_col = next((col for col in children_df.columns if 'Child' in col), None)
    dob_col = next((col for col in children_df.columns if 'Birth' in col), None)
    chick_col = next((col for col in children_df.columns if 'CHICK' in col), None)
    claim_until_col = next((col for col in children_df.columns if 'Claim Until' in col), None)
    
    funding_child_col = next((col for col in funding_df.columns if 'Child' in col), None)
    alloc_desc_col = next((col for col in funding_df.columns if 'Description' in col), None)
    alloc_date_col = next((col for col in funding_df.columns if 'Date' in col and 'Approved' not in col), None)
    
    if not all([child_col, funding_child_col, alloc_desc_col, alloc_date_col]):
        print("Required columns not found in input files", file=sys.stderr)
        sys.exit(1)
    
    # Process each child
    for _, child_row in children_df.iterrows():
        child_name = child_row[child_col]
        dob = child_row.get(dob_col, None) if dob_col else None
        chick = child_row.get(chick_col, None) if chick_col else None
        claim_until = child_row.get(claim_until_col, None) if claim_until_col else None
        
        # Get all funding entries for this child
        child_funding = funding_df[funding_df[funding_child_col] == child_name]
        
        # Initialize values
        start_date = None
        hour_values = set()
        latest_rate = None
        
        if len(child_funding) > 0:
            # Convert dates to datetime
            child_funding = child_funding.copy()
            try:
                child_funding.loc[:, alloc_date_col] = pd.to_datetime(
                    child_funding[alloc_date_col], dayfirst=True, errors='coerce'
                )
            except Exception as e:
                print(f"Error converting dates for {child_name}: {e}", file=sys.stderr)
                continue
            
            # Find start date (earliest allocation date minus 6 days)
            min_date = child_funding[alloc_date_col].min()
            if not pd.isna(min_date):
                # Adjust from Sunday to Monday (subtract 6 days)
                start_date = (min_date - timedelta(days=6))
            
            # Collect all distinct hour values
            for _, fund_row in child_funding.iterrows():
                desc = fund_row.get(alloc_desc_col, '')
                hours, rate = extract_hours_and_rate(desc)
                
                if hours is not None:
                    hour_values.add(hours)
                if rate is not None:
                    latest_rate = rate  # Will end up with the last rate processed
            
            # Get most recent rate by sorting by date
            latest_entries = child_funding.sort_values(by=alloc_date_col, ascending=False)
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
        
        # Add row for this child
        result_rows.append({
            'Child name': child_name,
            'Date of Birth': dob,
            'CHICK': chick,
            'Claim Until': claim_until,
            'Start date': start_date_str,
            'Weekly Total': weekly_total,
            'Hour rate': f"€{latest_rate:.2f}" if latest_rate is not None else ""
        })
    
    # Create DataFrame from result rows
    return pd.DataFrame(result_rows)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract funding allocation data from Excel files'
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
        '--output', '-o',
        default='funding_summary.xlsx',
        help='Output Excel file path (default: funding_summary.xlsx)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Display verbose output'
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()
    
    if args.verbose:
        print(f"Processing files:")
        print(f"- Children: {args.children}")
        print(f"- Funding: {args.funding}")
    
    try:
        # Extract funding data
        result_df = extract_funding_data(args.children, args.funding)
        
        # Display summary if verbose
        if args.verbose:
            print(f"\nProcessed {len(result_df)} children")
            print(f"Children with funding data: {result_df['Weekly Total'].str.len().gt(0).sum()}")
            
        # Save to Excel
        result_df.to_excel(args.output, index=False)
        
        print(f"Results saved to {args.output}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()