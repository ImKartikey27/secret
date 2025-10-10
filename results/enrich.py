#!/usr/bin/env python3
import re, json
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
import glob
import os
import subprocess

INPUT_PATTERN = "g2-page-*.html"  
OUT_XLSX = "G2_Company_Data_All_Pages.xlsx"

def clean(s):
    if not s: return None
    s = re.sub(r"\s+", " ", s).strip()
    return s or None

def load_html(path):
    return Path(path).read_text(encoding="utf-8", errors="ignore")

def extract_number_from_text(text):
    if not text: return None
    cleaned = re.sub(r'[,\s]', '', str(text))
    match = re.search(r'(\d+)', cleaned)
    return int(match.group(1)) if match else None

def extract_seller_details_sections(soup):
    companies = []
    
    # Find all product cards and seller details sections
    product_cards = soup.find_all('div', {'class': re.compile(r'.*product.*card.*')})
    seller_sections = soup.find_all('div', {'id': re.compile(r'.*-seller_details.*')})
    all_sections = product_cards + seller_sections
    
    for section in all_sections:
        company_data = {}
        
        # Extract company name from itemprop="name"
        company_name_elem = section.find('div', {'itemprop': 'name'})
        if not company_name_elem:
            parent = section.parent
            if parent:
                company_name_elem = parent.find('div', {'itemprop': 'name'})
            if not company_name_elem:
                siblings = section.find_all_next('div', {'itemprop': 'name'}, limit=3)
                if siblings:
                    company_name_elem = siblings[0]
        
        if company_name_elem:
            company_data['company_name'] = clean(company_name_elem.get_text())
        
        # Extract seller name from link
        seller_link = section.find('a', {'class': 'link js-log-click'})
        if not seller_link:
            seller_link = section.find('a', href=re.compile(r'/sellers/'))
        
        if seller_link:
            company_data['seller_name'] = clean(seller_link.get_text())
        
        # Fallback to seller name if no company name found
        if not company_data.get('company_name') and company_data.get('seller_name'):
            company_data['company_name'] = company_data.get('seller_name')
        
        # Extract other details if we have company/seller name
        if company_data.get('company_name') or company_data.get('seller_name'):
            
            # Year Founded
            calendar_section = section.find('svg', {'class': re.compile(r'.*icon-calendar.*')})
            if calendar_section and calendar_section.parent:
                year_text = calendar_section.parent.parent.get_text()
                year_match = re.search(r'Year Founded\s*(\d{4})', year_text)
                if year_match:
                    company_data['year_founded'] = int(year_match.group(1))
            
            # HQ Location
            location_section = section.find('svg', {'class': re.compile(r'.*icon-location.*')})
            if location_section and location_section.parent:
                location_text = location_section.parent.parent.get_text()
                location_match = re.search(r'HQ Location\s*(.+?)(?:\n|$)', location_text)
                if location_match:
                    company_data['hq_location'] = clean(location_match.group(1))
            
            # Twitter Info
            twitter_section = section.find('svg', {'class': re.compile(r'.*icon-twitter.*')})
            if twitter_section and twitter_section.parent:
                twitter_text = twitter_section.parent.parent.get_text()
                
                followers_match = re.search(r'([\d,]+)\s+Twitter followers', twitter_text)
                if followers_match:
                    company_data['twitter_followers'] = extract_number_from_text(followers_match.group(1))
                
                twitter_handle_match = re.search(r'@([a-zA-Z_][a-zA-Z0-9_]*?)(?=\s|\d|$)', twitter_text)
                if twitter_handle_match:
                    company_data['twitter_id'] = twitter_handle_match.group(1)
            
            # LinkedIn Info
            linkedin_section = section.find('svg', {'class': re.compile(r'.*icon-linkedin.*')})
            if linkedin_section and linkedin_section.parent:
                linkedin_container = linkedin_section.parent.parent
                
                linkedin_link = linkedin_container.find('a', {'class': 'link js-log-click'})
                if linkedin_link:
                    linkedin_href = linkedin_link.get('href')
                    if 'linkedin.com' in linkedin_href:
                        company_data['linkedin_url'] = linkedin_href
                    else:
                        url_match = re.search(r'secure%5Burl%5D=([^&]+)', linkedin_href)
                        if url_match:
                            import urllib.parse
                            decoded_url = urllib.parse.unquote(url_match.group(1))
                            company_data['linkedin_url'] = decoded_url
                
                linkedin_text = linkedin_container.get_text()
                employees_match = re.search(r'([\d,]+)\s+employees on LinkedIn', linkedin_text)
                if employees_match:
                    company_data['linkedin_employees'] = extract_number_from_text(employees_match.group(1))
            
            # Company Website
            website_section = section.find('svg', {'class': re.compile(r'.*icon-website.*')})
            if website_section and website_section.parent:
                website_container = website_section.parent.parent
                website_button = website_container.find('button', {'class': 'link'})
                if website_button:
                    company_data['company_website'] = clean(website_button.get_text())
            
            companies.append(company_data)
    
    return companies

def merge_company_data(companies_list):
    merged = {}
    
    for companies in companies_list:
        for company in companies:
            key = company.get('company_name') or company.get('seller_name') or 'unknown'
            
            if key not in merged:
                merged[key] = company.copy()
            else:
                for field, value in company.items():
                    if value is not None and (field not in merged[key] or merged[key][field] is None):
                        merged[key][field] = value
    
    return list(merged.values())

def process_single_html_file(html_file):
    html = load_html(html_file)
    soup = BeautifulSoup(html, "lxml")
    return extract_seller_details_sections(soup)

def upload_to_webhook(file_path):
    """Upload Excel file to n8n webhook using curl."""
    webhook_url = "https://kartikey2710a.app.n8n.cloud/webhook/b2c7d41e-c5b6-4a46-814c-f2a9376b8e8e"
    
    curl_command = [
        'curl',
        '-X', 'POST',
        webhook_url,
        '-H', 'Content-Type: multipart/form-data',
        '-F', f'file=@{file_path}'
    ]
    
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=60)
        print("request sent")
        return result.returncode == 0
    except Exception:
        print("request failed")
        return False

def main():
    html_files = glob.glob(INPUT_PATTERN)
    
    if not html_files:
        return
    
    def extract_page_number(filename):
        match = re.search(r'g2-page-(\d+)\.html', filename)
        return int(match.group(1)) if match else 0
    
    html_files.sort(key=extract_page_number)
    
    all_companies_data = []
    
    for html_file in html_files:
        companies_from_page = process_single_html_file(html_file)
        all_companies_data.extend(companies_from_page)
    
    if not all_companies_data:
        return
    
    # Merge and deduplicate companies
    final_companies = merge_company_data([all_companies_data])
    
    # Create DataFrame
    df = pd.DataFrame(final_companies)
    
    # Define required columns
    required_columns = [
        'company_name', 'seller_name', 'year_founded', 'hq_location',
        'twitter_id', 'twitter_followers', 'linkedin_url', 'linkedin_employees',
        'company_website'
    ]
    
    # Add missing columns
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    # Reorder columns and remove duplicates
    df = df[required_columns + [col for col in df.columns if col not in required_columns]]
    df = df.drop_duplicates(subset=['company_name'], keep='first')
    
    # Save to Excel
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Company_Data", index=False)
    
    # Upload to webhook
    if os.path.exists(OUT_XLSX):
        upload_to_webhook(os.path.abspath(OUT_XLSX))

if __name__ == "__main__":
    main()