#!/usr/bin/env python3
"""
Crunchbase HTML Data Extractor
This script extracts organization data from Crunchbase search results HTML files.
"""

import pandas as pd
from bs4 import BeautifulSoup
import re
import json
import sys
import os

def extract_crunchbase_data(html_file_path):
    """Extract organization data from Crunchbase HTML file"""
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
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

def save_to_excel(organizations, output_file='crunchbase_organizations.xlsx'):
    """Save organization data to Excel file"""
    if not organizations:
        print("No organizations found.")
        return
    
    df = pd.DataFrame(organizations)
    
    # Ensure required columns exist
    required_columns = ['Name', 'Identifier', 'URL']
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
    
    try:
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"Extracted {len(df)} organizations saved to {output_file}")
    except Exception as e:
        print(f"Error saving: {e}")

def main():
    html_file = 'crunchBase-1759584850668.html'
    
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
    
    if not os.path.exists(html_file):
        print(f"File {html_file} not found.")
        return
    
    organizations = extract_crunchbase_data(html_file)
    
    if organizations:
        output_file = f"crunchbase_orgs_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        save_to_excel(organizations, output_file)
    else:
        print("No organization data found.")

if __name__ == "__main__":
    main()