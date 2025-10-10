#!/usr/bin/env python3
"""
Enhanced Clay Lead Scraper for React/SPA HTML - v2
================================================
"""

import re
import pandas as pd
import argparse
from bs4 import BeautifulSoup
import json
import urllib.parse

def extract_leads_from_clay_html(html_content):
    """Extract leads from Clay HTML using multiple improved strategies"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    leads = []
    
    print("🔍 Analyzing Clay HTML structure...")
    
    # Strategy 1: Extract from data attributes and URLs
    leads_from_urls = extract_from_embedded_urls(html_content, soup)
    if leads_from_urls:
        leads.extend(leads_from_urls)
        print(f"✅ Strategy 1: Found {len(leads_from_urls)} leads from embedded URLs")
    
    # Strategy 2: Extract from script tags with data
    leads_from_scripts = extract_from_script_data(html_content, soup)
    if leads_from_scripts:
        leads.extend(leads_from_scripts)
        print(f"✅ Strategy 2: Found {len(leads_from_scripts)} leads from script data")
    
    # Strategy 3: Extract from table-like structures
    leads_from_table = extract_from_table_structure(soup)
    if leads_from_table:
        leads.extend(leads_from_table)
        print(f"✅ Strategy 3: Found {len(leads_from_table)} leads from table structure")
    
    # Strategy 4: Brute force text extraction
    if not leads:
        leads_from_text = extract_from_raw_text(html_content)
        if leads_from_text:
            leads.extend(leads_from_text)
            print(f"✅ Strategy 4: Found {len(leads_from_text)} leads from raw text")
    
    # Remove duplicates based on LinkedIn URL
    unique_leads = []
    seen_urls = set()
    
    for lead in leads:
        linkedin_url = lead.get('LinkedIn Profile', '')
        if linkedin_url and linkedin_url not in seen_urls:
            seen_urls.add(linkedin_url)
            unique_leads.append(lead)
        elif not linkedin_url and lead.get('Full Name'):
            # Keep leads without LinkedIn but with names
            unique_leads.append(lead)
    
    return unique_leads

def extract_from_embedded_urls(html_content, soup):
    """Extract data from URLs embedded in the HTML"""
    leads = []
    
    # Find all LinkedIn URLs in the entire HTML
    linkedin_pattern = r'https://www\.linkedin\.com/in/([a-zA-Z0-9-]+)/?'
    linkedin_matches = list(set(re.findall(linkedin_pattern, html_content, re.IGNORECASE)))
    
    print(f"📊 Found {len(linkedin_matches)} unique LinkedIn profiles")
    
    for linkedin_id in linkedin_matches:
        linkedin_url = f"https://www.linkedin.com/in/{linkedin_id}/"
        
        lead = {
            'Find people': '',
            'Company Name': '',
            'First Name': '',
            'Last Name': '',
            'Full Name': '',
            'Job Title': '',
            'Location': '',
            'Company Domain': '',
            'LinkedIn Profile': linkedin_url,
            'Enrich person': '✓',
            'Connections': ''
        }
        
        # Try to find associated data near this LinkedIn URL
        url_context = extract_context_around_url(html_content, linkedin_url)
        if url_context:
            # Extract name from context
            name = extract_name_from_context(url_context)
            if name:
                lead['Full Name'] = name
                lead['Find people'] = name
                name_parts = name.split()
                if len(name_parts) >= 2:
                    lead['First Name'] = name_parts[0]
                    lead['Last Name'] = ' '.join(name_parts[1:])
            
            # Extract job title from context
            title = extract_title_from_context(url_context)
            if title:
                lead['Job Title'] = title
            
            # Extract company from context
            company = extract_company_from_context(url_context)
            if company:
                lead['Company Name'] = company
        
        leads.append(lead)
    
    return leads

def extract_context_around_url(html_content, url):
    """Extract context around a LinkedIn URL"""
    url_pos = html_content.find(url)
    if url_pos == -1:
        return ""
    
    # Get 3000 characters before and after the URL
    start = max(0, url_pos - 3000)
    end = min(len(html_content), url_pos + 3000)
    context = html_content[start:end]
    
    return context

def extract_name_from_context(context):
    """Extract person name from context"""
    # Remove HTML tags for cleaner text processing
    clean_context = re.sub(r'<[^>]+>', ' ', context)
    
    name_patterns = [
        # Names in quotes
        r'"([A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"',
        # Names with proper capitalization
        r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
        # Names in title attributes
        r'title="([A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+)"',
        # Names after common keywords
        r'(?:name|person|user|profile)[\s:]+([A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+)',
    ]
    
    for pattern in name_patterns:
        matches = re.findall(pattern, clean_context)
        for match in matches:
            # Filter out common false positives
            if (len(match) > 4 and len(match) < 50 and 
                not any(word in match.lower() for word in [
                    'linkedin', 'profile', 'company', 'click', 'button', 'header',
                    'table', 'cell', 'view', 'data', 'content', 'text', 'link',
                    'find', 'search', 'filter', 'sort', 'first', 'last', 'full'
                ])):
                return match.strip()
    
    return None

def extract_title_from_context(context):
    """Extract job title from context"""
    clean_context = re.sub(r'<[^>]+>', ' ', context)
    
    title_patterns = [
        # Common job titles
        r'\b([A-Z][^.]*?(?:CEO|CTO|CFO|COO|Director|Manager|Engineer|Developer|Analyst|Specialist|Coordinator|Assistant|Lead|Senior|Junior)[^.]*?)\b',
        # Titles in quotes
        r'"([^"]*(?:CEO|CTO|CFO|COO|Director|Manager|Engineer|Developer|Analyst)[^"]*)"',
        # Titles after "at" or "of"
        r'\bat\s+([A-Z][^.]+?)(?:\s|$)',
        r'\bof\s+([A-Z][^.]+?)(?:\s|$)',
    ]
    
    for pattern in title_patterns:
        matches = re.findall(pattern, clean_context, re.IGNORECASE)
        for match in matches:
            if len(match) > 3 and len(match) < 100:
                return match.strip()
    
    return None

def extract_company_from_context(context):
    """Extract company name from context"""
    clean_context = re.sub(r'<[^>]+>', ' ', context)
    
    company_patterns = [
        # Company names with "Inc", "Corp", "LLC", etc.
        r'\b([A-Z][A-Za-z\s&]+(?:Inc|Corp|LLC|Ltd|Company|Technologies|Solutions|Systems))\b',
        # Companies after "at"
        r'\bat\s+([A-Z][A-Za-z\s&]{2,30}?)(?:\s|$)',
        # Companies in quotes
        r'"([A-Z][A-Za-z\s&]{3,30})"',
    ]
    
    for pattern in company_patterns:
        matches = re.findall(pattern, clean_context)
        for match in matches:
            if (len(match) > 2 and len(match) < 50 and 
                not any(word in match.lower() for word in [
                    'linkedin', 'profile', 'company name', 'find people',
                    'first name', 'last name', 'job title', 'location'
                ])):
                return match.strip()
    
    return None

def extract_from_script_data(html_content, soup):
    """Extract data from JavaScript/JSON in script tags"""
    leads = []
    
    # Find script tags that might contain data
    script_tags = soup.find_all('script')
    
    for script in script_tags:
        if script.string:
            script_content = script.string
            
            # Look for JSON-like structures
            json_patterns = [
                r'window\.__[A-Z_]+__\s*=\s*({.+?});',
                r'"tableData"\s*:\s*(\[.+?\])',
                r'"rows"\s*:\s*(\[.+?\])',
                r'"people"\s*:\s*(\[.+?\])',
                r'"leads"\s*:\s*(\[.+?\])',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, script_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        extracted = process_json_data(data)
                        if extracted:
                            leads.extend(extracted)
                    except:
                        continue
    
    return leads

def process_json_data(data):
    """Process JSON data to extract lead information"""
    leads = []
    
    if isinstance(data, dict):
        # Process dictionary
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                leads.extend(process_json_data(value))
            elif isinstance(value, str) and 'linkedin.com/in/' in value:
                # Found a LinkedIn URL
                lead = create_lead_from_linkedin_url(value)
                if lead:
                    leads.append(lead)
    
    elif isinstance(data, list):
        # Process list
        for item in data:
            if isinstance(item, (dict, list)):
                leads.extend(process_json_data(item))
            elif isinstance(item, str) and 'linkedin.com/in/' in item:
                lead = create_lead_from_linkedin_url(item)
                if lead:
                    leads.append(lead)
    
    return leads

def create_lead_from_linkedin_url(url):
    """Create a lead object from a LinkedIn URL"""
    linkedin_match = re.search(r'https://www\.linkedin\.com/in/([a-zA-Z0-9-]+)', url)
    if linkedin_match:
        return {
            'Find people': '',
            'Company Name': '',
            'First Name': '',
            'Last Name': '',
            'Full Name': '',
            'Job Title': '',
            'Location': '',
            'Company Domain': '',
            'LinkedIn Profile': f"https://www.linkedin.com/in/{linkedin_match.group(1)}/",
            'Enrich person': '✓',
            'Connections': ''
        }
    return None

def extract_from_table_structure(soup):
    """Extract data from table-like HTML structures"""
    leads = []
    
    # Look for table rows or grid items
    row_selectors = [
        'div[id*="table-row"]',
        'div[data-testid*="row"]',
        'tr',
        'div[class*="row"]',
        'div[class*="grid-row"]'
    ]
    
    for selector in row_selectors:
        rows = soup.select(selector)
        if rows:
            print(f"📋 Found {len(rows)} potential table rows with selector: {selector}")
            
            for row in rows:
                lead = extract_lead_from_row(row)
                if lead:
                    leads.append(lead)
            
            if leads:
                break
    
    return leads

def extract_lead_from_row(row):
    """Extract lead data from a table row element"""
    row_text = row.get_text()
    row_html = str(row)
    
    # Extract LinkedIn URL
    linkedin_match = re.search(r'https://www\.linkedin\.com/in/([a-zA-Z0-9-]+)', row_html)
    if not linkedin_match:
        return None
    
    linkedin_url = f"https://www.linkedin.com/in/{linkedin_match.group(1)}/"
    
    lead = {
        'Find people': '',
        'Company Name': '',
        'First Name': '',
        'Last Name': '',
        'Full Name': '',
        'Job Title': '',
        'Location': '',
        'Company Domain': '',
        'LinkedIn Profile': linkedin_url,
        'Enrich person': '✓',
        'Connections': ''
    }
    
    # Extract name from row
    name = extract_name_from_context(row_text)
    if name:
        lead['Full Name'] = name
        lead['Find people'] = name
        name_parts = name.split()
        if len(name_parts) >= 2:
            lead['First Name'] = name_parts[0]
            lead['Last Name'] = ' '.join(name_parts[1:])
    
    return lead

def extract_from_raw_text(html_content):
    """Brute force extraction from raw text"""
    leads = []
    
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    # Find LinkedIn URLs
    linkedin_pattern = r'https://www\.linkedin\.com/in/([a-zA-Z0-9-]+)/?'
    linkedin_matches = re.findall(linkedin_pattern, clean_text)
    
    # Split text into chunks around LinkedIn URLs
    for linkedin_id in linkedin_matches:
        linkedin_url = f"https://www.linkedin.com/in/{linkedin_id}/"
        
        # Find the position and extract surrounding text
        url_pos = clean_text.find(linkedin_url)
        if url_pos != -1:
            start = max(0, url_pos - 500)
            end = min(len(clean_text), url_pos + 500)
            chunk = clean_text[start:end]
            
            lead = {
                'Find people': '',
                'Company Name': '',
                'First Name': '',
                'Last Name': '',
                'Full Name': '',
                'Job Title': '',
                'Location': '',
                'Company Domain': '',
                'LinkedIn Profile': linkedin_url,
                'Enrich person': '✓',
                'Connections': ''
            }
            
            # Try to extract name from chunk
            name_patterns = [
                r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',
                r'\b([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)\b',
                r'\b([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)\b'
            ]
            
            for pattern in name_patterns:
                names = re.findall(pattern, chunk)
                for name in names:
                    if (len(name) > 4 and 
                        not any(word in name.lower() for word in [
                            'linkedin', 'profile', 'company', 'find', 'people'
                        ])):
                        lead['Full Name'] = name
                        lead['Find people'] = name
                        parts = name.split()
                        lead['First Name'] = parts[0]
                        lead['Last Name'] = ' '.join(parts[1:])
                        break
                
                if lead['Full Name']:
                    break
            
            leads.append(lead)
    
    return leads

def export_to_excel(leads, filename):
    """Export leads to Excel file"""
    if not leads:
        print("❌ No leads to export!")
        return False
    
    df = pd.DataFrame(leads)
    
    # Ensure column order
    columns = [
        'Find people', 'Company Name', 'First Name', 'Last Name', 'Full Name',
        'Job Title', 'Location', 'Company Domain', 'LinkedIn Profile',
        'Enrich person', 'Connections'
    ]
    
    for col in columns:
        if col not in df.columns:
            df[col] = ''
    
    df = df[columns].fillna('')
    
    try:
        df.to_excel(filename, index=False)
        print(f"✅ Exported {len(df)} leads to {filename}")
        
        # Show sample data
        print("\n📋 Sample leads:")
        for i, row in df.head(5).iterrows():
            print(f"{i+1}. {row['Full Name'] or 'N/A'}")
            if row['Job Title']:
                print(f"   Title: {row['Job Title']}")
            if row['LinkedIn Profile']:
                print(f"   LinkedIn: {row['LinkedIn Profile']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Enhanced Clay Lead Scraper v2')
    parser.add_argument('input_file', help='Clay HTML file')
    parser.add_argument('output_file', nargs='?', default='clay_leads_v2.xlsx',
                       help='Output Excel file')
    
    args = parser.parse_args()
    
    try:
        print("🚀 Enhanced Clay Lead Scraper v2")
        print(f"📁 Processing: {args.input_file}")
        
        with open(args.input_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        leads = extract_leads_from_clay_html(html_content)
        
        if leads:
            print(f"\n🎉 Successfully extracted {len(leads)} leads!")
            export_to_excel(leads, args.output_file)
            print(f"\n✅ Complete! Check {args.output_file}")
        else:
            print("\n❌ No leads found")
            print("💡 The data might be loaded dynamically via JavaScript")
            print("💡 Try exporting the Clay table as CSV from the interface instead")
            
    except FileNotFoundError:
        print(f"❌ File not found: {args.input_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()