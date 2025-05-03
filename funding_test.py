#!/usr/bin/env python3
"""
Funding Allocation Data Extractor

Merged Script:
- Retains full terminal UX and interactive matching
- Implements base claim detection by total weeks covered (not by block frequency)
- Detects base claim as lowest-hours most-covered period
- Breaks funding into periods with Start/End, grouped by hours+rate
- Detects base claim and outputs complementary claims only when extra hours appear
- Generates: forAutoFiller.csv, toChildPathsUploader.xlsx, unmatchedChildren.csv
"""

import argparse
import sys
import pandas as pd
import re
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import Counter

# Terminal formatting
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_status(message, status="info"):
    color = {
        "info": Colors.CYAN,
        "success": Colors.GREEN,
        "error": Colors.RED,
        "warning": Colors.YELLOW
    }.get(status, Colors.CYAN)
    print(f"{color}{message}{Colors.ENDC}")

def normalize_name(name: str) -> str:
    return ' '.join(name.lower().split()) if isinstance(name, str) else ""

def clean_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = re.sub(r'(?i)\bfather\b', '', name)
    name = name.replace('-', ' ')
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    return ' '.join(name.split())

def extract_hours_and_rate(description: str) -> Tuple[Optional[float], Optional[float]]:
    match = re.search(r'(\d+\.\d+|\d+) hours x €(\d+\.\d+|\d+)', str(description))
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

def find_potential_matches(name: str, system_names: List[str], max_matches: int = 5) -> List[Tuple[str, int]]:
    name_words = set(normalize_name(name).split())
    scores = []
    for sys_name in system_names:
        sys_words = set(normalize_name(sys_name).split())
        common = name_words.intersection(sys_words)
        if common:
            scores.append((sys_name, len(common)))
    scores.sort(key=lambda x: -x[1])
    return scores[:15] if scores and scores[0][1] == 1 else scores[:max_matches]

def interactive_matching(unmatched_children: List[Dict], system_names: List[str]) -> Dict[str, str]:
    matches = {}
    for idx, child in enumerate(unmatched_children):
        child_name = child['Child Name']
        chick = child.get('CHICK', '')
        clear_screen()
        print(f"Unmatched ({idx+1}/{len(unmatched_children)}): {child_name}  CHICK: {chick}")
        options = find_potential_matches(child_name, system_names)
        for i, (opt, _) in enumerate(options):
            print(f"{i+1}) {opt}")
        print("0) Skip")
        choice = input("Choose: ").strip()
        if choice == '0':
            continue
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                matches[child_name] = options[idx][0]
                print_status(f"Matched {child_name} -> {options[idx][0]}", "success")
        except:
            continue
    return matches

def get_funding_blocks(df: pd.DataFrame, claim_until: str) -> Tuple[pd.DataFrame, str, str, Tuple[float, float]]:
    df = df[["Allocation Description", "Allocation Date"]].dropna()
    if df.empty:
        return pd.DataFrame(), "", "", (0, 0)

    def parse(row):
        hours, rate = extract_hours_and_rate(row['Allocation Description'])
        end = pd.to_datetime(row['Allocation Date'], dayfirst=True, errors='coerce')
        if pd.isna(end):
            return None
        start = end - timedelta(days=6)
        return pd.Series([hours, rate, start.date(), end.date()])

    parsed = df.apply(parse, axis=1).dropna()
    if parsed.empty:
        return pd.DataFrame(), "", "", (0, 0)

    parsed.columns = ['Hours', 'Rate', 'Start', 'End']
    parsed.sort_values('Start', inplace=True)

    subsidy_end = datetime.strptime(claim_until, "%d/%m/%Y").date()
    subsidy_start = subsidy_end - timedelta(weeks=52) + timedelta(days=1)

    parsed = parsed[(parsed['Start'] <= subsidy_end) & (parsed['End'] >= subsidy_start)]
    if parsed.empty:
        return pd.DataFrame(), "", "", (0, 0)

    parsed['Start'] = parsed['Start'].apply(lambda d: max(d, subsidy_start))
    parsed['End'] = parsed['End'].apply(lambda d: min(d, subsidy_end))

    grouped = []
    current = parsed.iloc[0].to_dict()

    for i in range(1, len(parsed)):
        row = parsed.iloc[i]
        prev_end = current['End']
        new_start = row['Start']
        if row['Hours'] == current['Hours'] and row['Rate'] == current['Rate'] and new_start == prev_end + timedelta(days=1):
            current['End'] = row['End']
        else:
            grouped.append(current)
            current = row.to_dict()
    grouped.append(current)

    blocks = pd.DataFrame(grouped)
    blocks['Start'] = pd.to_datetime(blocks['Start'])
    blocks['End'] = pd.to_datetime(blocks['End'])

    # Compute total days for each (Hours, Rate) and pick the lowest hours among those with the max days
    blocks['Days'] = (blocks['End'] - blocks['Start']).dt.days + 1
    days_summary = blocks.groupby(['Hours', 'Rate'])['Days'].sum().reset_index()
    max_days = days_summary['Days'].max()
    base_block = days_summary[days_summary['Days'] == max_days].sort_values(by='Hours').iloc[0]
    base_hours, base_rate = base_block['Hours'], base_block['Rate']

    blocks['Start'] = blocks['Start'].dt.strftime("%d/%m/%Y")
    blocks['End'] = blocks['End'].dt.strftime("%d/%m/%Y")

    claim_start = blocks['Start'].min()
    claim_end = blocks['End'].max()

    return blocks, claim_start, claim_end, (base_hours, base_rate)

# (main remains unchanged)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--children', required=True)
    parser.add_argument('--funding', required=True)
    parser.add_argument('--system', required=True)
    parser.add_argument('--output-dir', default='output')
    parser.add_argument('--interactive', action='store_true')
    args = parser.parse_args()

    clear_screen()
    print_status("Loading input files...")
    children_df = pd.read_excel(args.children)
    funding_df = pd.read_excel(args.funding)
    if args.system.lower().endswith('.csv'):
        system_df = pd.read_csv(args.system)
    else:
        system_df = pd.read_excel(args.system)

    unmatched = []
    name_map = {}
    result_rows = []
    uploader_rows = []

    system_names = system_df['name'].dropna().tolist()
    for name in children_df['Child']:
        norm = normalize_name(name)
        match = next((s for s in system_names if normalize_name(s) == norm), None)
        if match:
            name_map[name] = match
        else:
            unmatched.append(name)

    if args.interactive and unmatched:
        unmatched_dicts = [{"Child Name": name, "CHICK": children_df.loc[children_df['Child'] == name, 'CHICK'].values[0]} for name in unmatched]
        matched = interactive_matching(unmatched_dicts, system_names)
        name_map.update(matched)

    for _, child in children_df.iterrows():
        name = child['Child']
        chick = child['CHICK']
        dob = child['Date of Birth']
        claim_until = child['Claim Until']

        if name not in name_map:
            continue

        child_funding = funding_df[funding_df['Child'] == name]
        blocks, claim_start, claim_end, base = get_funding_blocks(child_funding, str(claim_until))
        if blocks.empty:
            continue

        base_hours, base_rate = base
        uploader_rows.append({'Child': name, 'CHICK': chick, 'Date of Birth': dob, 'Claim Until': claim_end})
        result_rows.append({
            'Child': name, 'CHICK': chick, 'Date of Birth': dob, 'Claim Until': claim_end,
            'Weekly Total': int(base_hours), 'Hour rate': f"€{base_rate:.2f}",
            'Funding Start': claim_start
        })

        for _, block in blocks.iterrows():
            if (block['Hours'], block['Rate']) == base:
                continue
            diff = int(block['Hours'] - base_hours)
            if diff <= 0:
                continue
            uploader_rows.append({'Child': name, 'CHICK': chick, 'Date of Birth': dob, 'Claim Until': block['End']})
            result_rows.append({
                'Child': name, 'CHICK': chick, 'Date of Birth': dob, 'Claim Until': block['End'],
                'Weekly Total': diff, 'Hour rate': f"€{block['Rate']:.2f}",
                'Funding Start': block['Start']
            })

    os.makedirs(args.output_dir, exist_ok=True)
    pd.DataFrame(uploader_rows).to_excel(os.path.join(args.output_dir, 'toChildPathsUploader.xlsx'), index=False)
    pd.DataFrame(result_rows).to_csv(os.path.join(args.output_dir, 'forAutoFiller.csv'), index=False, encoding='utf-8-sig')

    unmatched_final = [u for u in unmatched if u not in name_map]
    if unmatched_final:
        pd.DataFrame({'Unmatched': unmatched_final}).to_csv(os.path.join(args.output_dir, 'unmatchedChildren.csv'), index=False)
        print_status(f"Saved {len(unmatched_final)} unmatched children.", "warning")

    print_status("Done. Files saved to output folder.", "success")

if __name__ == '__main__':
    main() # — but ensure wherever autofiller file is written,
# `blocks['Start']` is included in the export columns)
