#!/usr/bin/env python3
import re, json
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
import glob
import os

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

def extract_seller_details_sections(soup, page_number=None):
    companies = []
    seller_sections = soup.find_all('div', {'id': re.compile(r'.*-seller_details.*')})
    
    for section in seller_sections:
        company_data = {'source': 'seller_details', 'page_number': page_number}
        
        seller_link = section.find('a', {'class': 'link js-log-click'})
        if seller_link:
            company_data['seller_name'] = clean(seller_link.get_text())
            company_data['company_name'] = clean(seller_link.get_text())
        
        calendar_section = section.find('svg', {'class': re.compile(r'.*icon-calendar.*')})
        if calendar_section and calendar_section.parent:
            year_text = calendar_section.parent.parent.get_text()
            year_match = re.search(r'Year Founded\s*(\d{4})', year_text)
            if year_match:
                company_data['year_founded'] = int(year_match.group(1))
        
        location_section = section.find('svg', {'class': re.compile(r'.*icon-location.*')})
        if location_section and location_section.parent:
            location_text = location_section.parent.parent.get_text()
            location_match = re.search(r'HQ Location\s*(.+?)(?:\n|$)', location_text)
            if location_match:
                company_data['hq_location'] = clean(location_match.group(1))
        
        twitter_section = section.find('svg', {'class': re.compile(r'.*icon-twitter.*')})
        if twitter_section and twitter_section.parent:
            twitter_text = twitter_section.parent.parent.get_text()
            
            twitter_handle_match = re.search(r'@(\w+)', twitter_text)
            if twitter_handle_match:
                company_data['twitter_id'] = twitter_handle_match.group(1)
            
            followers_match = re.search(r'([\d,]+)\s+Twitter followers', twitter_text)
            if followers_match:
                company_data['twitter_followers'] = extract_number_from_text(followers_match.group(1))
        
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
        
        website_section = section.find('svg', {'class': re.compile(r'.*icon-website.*')})
        if website_section and website_section.parent:
            website_container = website_section.parent.parent
            website_button = website_container.find('button', {'class': 'link'})
            if website_button:
                company_data['company_website'] = clean(website_button.get_text())
        
        if company_data.get('company_name'):
            companies.append(company_data)
    
    return companies

def extract_product_descriptions(soup, page_number=None):
    product_descriptions = {}
    desc_sections = soup.find_all('div', {'class': 'fw-semibold mb-half flex ai-c c-midnight-100'})
    
    for section in desc_sections:
        if 'Product Description' in section.get_text():
            desc_container = section.parent
            if desc_container:
                desc_spans = desc_container.find_all('span', {'class': 'product-listing__paragraph'})
                for span in desc_spans:
                    desc_text = clean(span.get_text())
                    if desc_text and len(desc_text) > 50:
                        parent_container = desc_container.parent
                        if parent_container:
                            seller_link = parent_container.find('a', href=re.compile(r'/sellers/'))
                            if seller_link:
                                company_name = clean(seller_link.get_text())
                                product_descriptions[company_name] = desc_text
    
    return product_descriptions

def extract_from_text_patterns(soup, page_number=None):
    companies = []
    full_text = soup.get_text()
    
    twitter_patterns = [
        r'@(\w+)[\s\S]*?([\d,]+)\s+Twitter followers',
        r'([\d,]+)\s+Twitter followers[\s\S]*?@(\w+)',
    ]
    
    for pattern in twitter_patterns:
        matches = re.finditer(pattern, full_text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) == 2:
                if match.group(1).isdigit() or ',' in match.group(1):
                    twitter_followers = extract_number_from_text(match.group(1))
                    twitter_handle = match.group(2)
                else:
                    twitter_handle = match.group(1)
                    twitter_followers = extract_number_from_text(match.group(2))
                
                companies.append({
                    'twitter_id': twitter_handle,
                    'twitter_followers': twitter_followers,
                    'source': 'text_pattern',
                    'page_number': page_number
                })
    
    linkedin_matches = re.finditer(r'([\d,]+)\s+employees on LinkedIn', full_text, re.IGNORECASE)
    for i, match in enumerate(linkedin_matches):
        employee_count = extract_number_from_text(match.group(1))
        if i < len(companies):
            companies[i]['linkedin_employees'] = employee_count
        else:
            companies.append({
                'linkedin_employees': employee_count,
                'source': 'text_pattern',
                'page_number': page_number
            })
    
    year_matches = re.finditer(r'Year Founded[\s:]*(\d{4})', full_text, re.IGNORECASE)
    for i, match in enumerate(year_matches):
        year = int(match.group(1))
        if i < len(companies):
            companies[i]['year_founded'] = year
        else:
            companies.append({
                'year_founded': year,
                'source': 'text_pattern',
                'page_number': page_number
            })
    
    hq_matches = re.finditer(r'HQ Location[\s:]*([A-Za-z\s,]+?)(?:\n|Year|Twitter|LinkedIn|$)', full_text, re.IGNORECASE)
    for i, match in enumerate(hq_matches):
        location = clean(match.group(1))
        if location and i < len(companies):
            companies[i]['hq_location'] = location
        elif location:
            companies.append({
                'hq_location': location,
                'source': 'text_pattern',
                'page_number': page_number
            })
    
    return companies

def extract_phone_numbers(soup):
    phone_numbers = []
    phone_patterns = [
        r'\+?1?[-.\s]?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
        r'\+?(\d{1,3})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})',
    ]
    
    full_text = soup.get_text()
    
    for pattern in phone_patterns:
        matches = re.finditer(pattern, full_text)
        for match in matches:
            phone = ''.join(match.groups())
            if len(phone) >= 10:
                phone_numbers.append(phone)
    
    return phone_numbers

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

def process_single_html_file(html_file, page_number):
    html = load_html(html_file)
    soup = BeautifulSoup(html, "lxml")
    
    seller_details_data = extract_seller_details_sections(soup, page_number)
    product_descriptions = extract_product_descriptions(soup, page_number)
    text_pattern_data = extract_from_text_patterns(soup, page_number)
    phone_numbers = extract_phone_numbers(soup)
    
    all_companies = merge_company_data([seller_details_data, text_pattern_data])
    
    for company in all_companies:
        company_name = company.get('company_name') or company.get('seller_name')
        if company_name and company_name in product_descriptions:
            company['overview'] = product_descriptions[company_name]
    
    if phone_numbers:
        for i, company in enumerate(all_companies):
            if i < len(phone_numbers):
                company['phone_number'] = phone_numbers[i]
    
    try:
        os.remove(html_file)
    except Exception:
        pass
    
    return all_companies

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
        page_number = extract_page_number(html_file)
        companies_from_page = process_single_html_file(html_file, page_number)
        all_companies_data.extend(companies_from_page)
    
    if not all_companies_data:
        return
    
    df = pd.DataFrame(all_companies_data)
    
    required_columns = [
        'company_name', 'seller_name', 'year_founded', 'hq_location',
        'twitter_id', 'twitter_followers', 'linkedin_url', 'linkedin_employees',
        'phone_number', 'overview', 'page_number', 'source'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    df = df[required_columns + [col for col in df.columns if col not in required_columns]]
    df = df.drop_duplicates(subset=['company_name'], keep='first')
    
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Company_Data", index=False)

if __name__ == "__main__":
    main()