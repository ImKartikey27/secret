#!/usr/bin/env python3
"""
Crunchbase HTML Data Extractor - Multi-file Version
This script extracts organization data from multiple Crunchbase search results HTML files.
"""

import pandas as pd
from bs4 import BeautifulSoup
import re
import json
import sys
import os
import glob

def extract_crunchbase_data(html_file_path):
    """Extract organization data from Crunchbase HTML file"""
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
    except Exception as e:
        print(f"Error reading file {html_file_path}: {e}")
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    organizations = []
    
    # Method 1: Look for JSON data in script tags with specific patterns
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            script_content = script.string
            
            # Look for organization data in JSON structures
            # Pattern 1: Look for organization objects with identifiers
            org_pattern = r'"organization"[^}]*?"identifier"[^}]*?"value":\s*"([^"]+)"[^}]*?"name":\s*"([^"]+)"'
            matches = re.findall(org_pattern, script_content)
            
            for identifier, name in matches:
                if len(name) > 2 and not any(keyword in name.lower() for keyword in ['button', 'menu', 'search', 'filter', 'login']):
                    organizations.append({
                        'Name': name,
                        'Identifier': identifier,
                        'URL': f"https://www.crunchbase.com/organization/{identifier}"
                    })
            
            # Pattern 2: Look for company data structures
            company_pattern = r'"name":\s*"([^"]+)"[^}]*?"permalink":\s*"([^"]+)"'
            matches = re.findall(company_pattern, script_content)
            
            for name, permalink in matches:
                if (len(name) > 2 and 
                    not any(keyword in name.lower() for keyword in ['search', 'filter', 'menu', 'button', 'crunchbase', 'login']) and
                    not re.match(r'^[A-Z\s]{2,10}$', name)):  # Avoid all caps short strings
                    
                    organizations.append({
                        'Name': name,
                        'Identifier': permalink,
                        'URL': f"https://www.crunchbase.com/organization/{permalink}"
                    })
    
    # Method 2: Look for organization links in HTML
    org_links = soup.find_all('a', href=re.compile(r'/organization/'))
    for link in org_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        if (text and len(text) > 2 and 
            not any(keyword in text.lower() for keyword in ['view', 'more', 'see', 'all', 'profile', 'about']) and
            not re.match(r'^\d+$', text)):  # Avoid pure numbers
            
            # Extract organization identifier from URL
            org_match = re.search(r'/organization/([^/?]+)', href)
            if org_match:
                identifier = org_match.group(1)
                organizations.append({
                    'Name': text,
                    'Identifier': identifier,
                    'URL': f"https://www.crunchbase.com{href}" if href.startswith('/') else href
                })
    
    # Method 3: Look for structured data (JSON-LD)
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and 'name' in data:
                organizations.append({
                    'Name': data['name'],
                    'URL': data.get('url', '')
                })
        except (json.JSONDecodeError, AttributeError):
            continue
    
    # Remove duplicates and filter out invalid entries
    seen_names = set()
    filtered_orgs = []
    
    for org in organizations:
        name = org.get('Name', '').strip()
        
        # Skip if empty or already seen
        if not name or name.lower() in seen_names:
            continue
            
        # Skip common UI elements and invalid names
        invalid_patterns = [
            r'^(search|filter|menu|login|sign up|get started|learn more|view all)$',
            r'^\d+$',  # Pure numbers
            r'^[A-Z\s]{1,3}$',  # Short all-caps
            r'^(or|and|the|for|with|inc|llc|ltd)$',  # Common words
        ]
        
        if any(re.match(pattern, name, re.IGNORECASE) for pattern in invalid_patterns):
            continue
            
        seen_names.add(name.lower())
        filtered_orgs.append(org)
    
    return filtered_orgs

def load_existing_data(excel_file):
    """Load existing data from Excel file if it exists"""
    if os.path.exists(excel_file):
        try:
            df = pd.read_excel(excel_file, engine='openpyxl')
            print(f"Loaded {len(df)} existing organizations from {excel_file}")
            return df
        except Exception as e:
            print(f"Error reading existing Excel file: {e}")
            return pd.DataFrame()
    else:
        print(f"Excel file {excel_file} doesn't exist. Will create new file.")
        return pd.DataFrame()

def save_to_excel(all_organizations, output_file='crunchbase_orgs.xlsx'):
    """Save organization data to Excel file"""
    if not all_organizations:
        print("No organizations found.")
        return
    
    df = pd.DataFrame(all_organizations)
    
    # Ensure required columns exist
    required_columns = ['Name', 'Identifier', 'URL']
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
    
    # Remove duplicates based on Name (case-insensitive)
    df['Name_lower'] = df['Name'].str.lower()
    df = df.drop_duplicates(subset=['Name_lower'], keep='first')
    df = df.drop(columns=['Name_lower'])
    
    try:
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"Total {len(df)} unique organizations saved to {output_file}")
    except Exception as e:
        print(f"Error saving: {e}")

def find_html_files():
    """Find all crunchbase HTML files in current directory"""
    pattern = 'crunchbase-*.html'
    files = glob.glob(pattern)
    
    # Sort by number for consistent processing order
    def get_number(filename):
        match = re.search(r'crunchbase-(\d+)\.html', filename)
        return int(match.group(1)) if match else 0
    
    files.sort(key=get_number)
    return files

def main():
    output_file = 'crunchbase_orgs.xlsx'
    
    # Find all HTML files matching the pattern
    html_files = find_html_files()
    
    if not html_files:
        print("No crunchbase-*.html files found in current directory.")
        return
    
    print(f"Found {len(html_files)} HTML files to process:")
    for file in html_files:
        print(f"  - {file}")
    
    # Load existing data from Excel file
    existing_df = load_existing_data(output_file)
    existing_names = set()
    
    if not existing_df.empty:
        existing_names = set(existing_df['Name'].str.lower())
    
    # Process all HTML files
    all_new_organizations = []
    
    for html_file in html_files:
        print(f"\nProcessing {html_file}...")
        organizations = extract_crunchbase_data(html_file)
        
        if organizations:
            print(f"  Found {len(organizations)} organizations in {html_file}")
            all_new_organizations.extend(organizations)
        else:
            print(f"  No organizations found in {html_file}")
    
    if not all_new_organizations:
        print("\nNo new organizations found in any files.")
        return
    
    # Filter out organizations that already exist (case-insensitive)
    new_organizations = []
    for org in all_new_organizations:
        if org['Name'].lower() not in existing_names:
            new_organizations.append(org)
    
    print(f"\nFound {len(all_new_organizations)} total organizations")
    print(f"Found {len(new_organizations)} new organizations (after removing duplicates)")
    
    # Combine existing and new data
    if not existing_df.empty:
        combined_organizations = existing_df.to_dict('records') + new_organizations
    else:
        combined_organizations = new_organizations
    
    # Save to Excel
    if combined_organizations:
        save_to_excel(combined_organizations, output_file)
        print(f"\n✅ Processing complete! Check {output_file}")
    else:
        print("\nNo new data to add.")

if __name__ == "__main__":
    main()