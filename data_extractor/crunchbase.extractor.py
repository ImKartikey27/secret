#!/usr/bin/env python3

import os
import re
import pandas as pd
from bs4 import BeautifulSoup
import argparse
import subprocess
from typing import Dict, Tuple

class CrunchbaseDataExtractor:
    """Simplified Crunchbase HTML data extractor with core functionality."""
    
    def __init__(self):
        self.data_fields = [
            'Name', 'Founders', 'About', 'Phone', 'Contact Email', 
            'Lead Investors', 'People Headcount', 'Monthly Web visits', 
            'IT Spends', 'Total IP', 'actively Used Products', 
            'Company Location', 'Company domain link', 'Facebook link', 'LinkedIn Link'
        ]
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"')
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[^\w\s\-\.,@:/()&]', '', text)
        
        return text
    
    def extract_company_name(self, soup: BeautifulSoup, text: str) -> str:
        """Extract company name."""
        title = soup.find('title')
        if title:
            title_text = title.get_text()
            match = re.search(r'^([^-]+?)\s*-\s*Crunchbase', title_text)
            if match:
                name = self.clean_text(match.group(1))
                if 2 <= len(name) <= 50:
                    return name
        
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            h1_text = self.clean_text(h1.get_text())
            if 2 <= len(h1_text) <= 50 and not any(x in h1_text.lower() for x in ['search', 'filter', 'menu']):
                return h1_text
        
        name_patterns = [
            r'^([A-Z][A-Za-z0-9\s&.-]{1,49})\s+(?:is a|provides|offers)',
            r'About\s+([A-Z][A-Za-z0-9\s&.-]{1,49})\s+',
            r'([A-Z][A-Za-z0-9\s&.-]{1,49})\s+-\s+Crunchbase'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = self.clean_text(match.group(1))
                if 2 <= len(name) <= 50:
                    return name
        
        return ""
    
    def extract_founders(self, soup: BeautifulSoup, text: str) -> str:
        """Extract founder information."""
        founders = set()
        
        founder_patterns = [
            r'([A-Z][a-zA-Z\s]+?):\s*Co-Founder',
            r'Co-Founder[^A-Z]*([A-Z][a-zA-Z\s]+?)(?:\s|$|\n)',
            r'Founded by\s+([A-Z][a-zA-Z\s]+?)(?:\s+and\s+([A-Z][a-zA-Z\s]+?))?',
            r'Founder[s]?:\s*([A-Z][a-zA-Z\s]+?)(?:\n|$|,)',
            r'Key People\s+([A-Z][a-zA-Z\s]+?):\s*(?:Co-)?Founder',
            r'([A-Z][a-zA-Z\s]+?)\s+and\s+([A-Z][a-zA-Z\s]+?).*?(?:co-)?founder',
        ]
        
        for pattern in founder_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    for name in match:
                        if name:
                            clean_name = self.clean_text(name)
                            if 5 <= len(clean_name) <= 50 and ' ' in clean_name:
                                founders.add(clean_name)
                else:
                    clean_name = self.clean_text(match)
                    if 5 <= len(clean_name) <= 50 and ' ' in clean_name:
                        founders.add(clean_name)
        
        founder_list = sorted(list(founders))[:5]
        return '; '.join(founder_list)
    
    def extract_about(self, soup: BeautifulSoup, text: str) -> str:
        """Extract company description."""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content = self.clean_text(meta_desc.get('content'))
            if 50 <= len(content) <= 500:
                return content
        
        about_patterns = [
            r'(?:is a|provides|offers)\s+([^.]{50,400}\.)',
            r'About.*?\n([^.]{50,400}\.)',
            r'Description[:\s]+([^.]{50,400}\.)',
            r'([A-Z][^.]{100,400}\.)\s*(?:The company|Founded|Headquartered)',
        ]
        
        for pattern in about_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                about_text = self.clean_text(match.group(1))
                if 50 <= len(about_text) <= 500:
                    return about_text
        
        return ""
    
    def extract_contact_info(self, text: str) -> Tuple[str, str]:
        """Extract phone and email."""
        phone = ""
        email = ""
        
        phone_patterns = [
            r'Phone\s+Number\s+([0-9\-\(\)\+\s]{10,20})',
            r'Contact.*?(?:Phone|Tel)[:\s]+([0-9\-\(\)\+\s]{10,20})',
            r'(\+?1[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
            r'([0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean_phone = self.clean_text(match)
                digits_only = re.sub(r'[^\d]', '', clean_phone)
                if 10 <= len(digits_only) <= 15:
                    phone = clean_phone
                    break
            if phone:
                break
        
        email_patterns = [
            r'Contact\s+Email\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'Email[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        ]
        
        for pattern in email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if '@' in match and '.' in match.split('@')[1]:
                    if not any(x in match.lower() for x in ['example.com', 'test.com', 'noreply']):
                        email = self.clean_text(match)
                        break
            if email:
                break
        
        return phone, email
    
    def extract_financial_data(self, text: str) -> Dict[str, str]:
        """Extract financial and business metrics."""
        data = {}
        
        # Investors
        investor_patterns = [
            r'investors?\s+including\s+([A-Z][^.]{10,150})',
            r'funded\s+by\s+([A-Z][^.]{10,150})',
            r'backed\s+by\s+([A-Z][^.]{10,150})',
            r'([A-Z][A-Za-z\s&]+)\s+and\s+([A-Z][A-Za-z\s&]+).*?investor'
        ]
        
        for pattern in investor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                investors = self.clean_text(match.group(1))
                if 5 <= len(investors) <= 200:
                    data['Lead Investors'] = investors
                    break
        
        # Headcount
        headcount_patterns = [
            r'Headcount\s+([0-9,\-\s]+)',
            r'([0-9,]+\s*-\s*[0-9,]+)\s*employees?',
            r'employee[s]?\s*[:\s]+([0-9,\-\s]+)',
            r'([0-9]{2,})\s*-\s*([0-9]{3,})\s*(?:people|employees?)'
        ]
        
        for pattern in headcount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    headcount = f"{match[0]}-{match[1]}"
                else:
                    headcount = str(match)
                
                clean_headcount = self.clean_text(headcount)
                if any(char.isdigit() for char in clean_headcount):
                    data['People Headcount'] = clean_headcount
                    break
            if 'People Headcount' in data:
                break
        
        # Web visits
        visits_patterns = [
            r'Monthly\s+Web\s+Visits[:\s\n]+([0-9,]+)',
            r'([0-9,]{6,})\s*monthly.*?visits',
            r'visits[:\s]+([0-9,]{6,})'
        ]
        
        for pattern in visits_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                visits = self.clean_text(match)
                if len(visits.replace(',', '').replace(' ', '')) >= 4:
                    data['Monthly Web visits'] = visits
                    break
            if 'Monthly Web visits' in data:
                break
        
        # IT Spend
        spend_patterns = [
            r'IT\s+Spend[:\s\n]+(\$[0-9,MKB]+)',
            r'projected\s+to\s+spend\s+(\$[0-9,MKB]+).*?IT',
            r'(\$[0-9,]+[MKB]?)\s*.*?IT.*?spend'
        ]
        
        for pattern in spend_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                spend = self.clean_text(match)
                if '$' in spend and any(char.isdigit() for char in spend):
                    data['IT Spends'] = spend
                    break
            if 'IT Spends' in data:
                break
        
        # IP Count
        ip_patterns = [
            r'Total\s+IP[:\s\n]+([0-9,]+)',
            r'intellectual\s+property.*?includes\s+([0-9,]+)',
            r'([0-9,]+)\s*(?:registered\s+)?patents?',
            r'([0-9,]+)\s*(?:registered\s+)?trademarks?'
        ]
        
        for pattern in ip_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                ip_count = self.clean_text(match)
                if any(char.isdigit() for char in ip_count):
                    data['Total IP'] = ip_count
                    break
            if 'Total IP' in data:
                break
        
        # Products Used
        product_patterns = [
            r'uses\s+([0-9,]+)\s*technology\s+products?.*?including\s+([^.]{20,200})',
            r'technology.*?including\s+([^.]{20,200})',
            r'powered\s+by\s+([^.]{20,200})'
        ]
        
        for pattern in product_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    products = match[1] if len(match) > 1 else match[0]
                else:
                    products = match
                
                clean_products = self.clean_text(products)
                if 10 <= len(clean_products) <= 300:
                    data['actively Used Products'] = clean_products
                    break
            if 'actively Used Products' in data:
                break
        
        return data
    
    def extract_location(self, text: str) -> str:
        """Extract company location."""
        location_patterns = [
            r'(?:located|headquartered)\s+in\s+([A-Z][^.]{10,100})',
            r'(?:headquarters|HQ)[:\s]+([A-Z][^.]{10,100})',
            r'([A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+)(?:\.|$)',
            r'based\s+in\s+([A-Z][^.]{10,100})'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                location = self.clean_text(match)
                if 10 <= len(location) <= 100 and ',' in location:
                    return location
        
        return ""
    
    def extract_links(self, soup: BeautifulSoup, text: str) -> Dict[str, str]:
        """Extract domain and social media links."""
        links = {'Company domain link': '', 'Facebook link': '', 'LinkedIn Link': ''}
        
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '').lower()
            
            if 'crunchbase.com' in href:
                continue
            
            if 'facebook.com' in href and not links['Facebook link']:
                full_href = link.get('href')
                if '/pages/' in full_href or len(full_href.split('/')) >= 4:
                    links['Facebook link'] = full_href
            
            elif 'linkedin.com/company' in href and not links['LinkedIn Link']:
                links['LinkedIn Link'] = link.get('href')
            
            elif (href.startswith('http') and 
                  not any(x in href for x in ['twitter.com', 'instagram.com', 'youtube.com', 
                                             'google.com', 'facebook.com', 'linkedin.com']) and
                  not links['Company domain link']):
                domain_match = re.search(r'https?://(?:www\.)?([a-zA-Z0-9.-]+)', href)
                if domain_match:
                    domain = domain_match.group(1)
                    if ('.' in domain and 
                        len(domain.split('.')) >= 2 and 
                        not domain.endswith(('.gov', '.edu')) and
                        len(domain) <= 50):
                        links['Company domain link'] = domain
        
        if not links['Company domain link']:
            domain_patterns = [
                r'(?:www\.)?([a-zA-Z0-9.-]+\.(?:com|org|net|io))',
                r'visit\s+(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'website[:\s]+(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ]
            
            for pattern in domain_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if not any(x in match.lower() for x in ['crunchbase', 'linkedin', 'facebook']):
                        if len(match) <= 50 and '.' in match:
                            links['Company domain link'] = match.lower()
                            break
                if links['Company domain link']:
                    break
        
        return links
    
    def extract_data_from_html(self, html_file_path: str) -> Dict[str, str]:
        """Main extraction method for a single HTML file."""
        try:
            with open(html_file_path, 'r', encoding='utf-8', errors='ignore') as file:
                html_content = file.read()
        except Exception:
            return {field: "" for field in self.data_fields}
        
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        extracted_data = {field: "" for field in self.data_fields}
        
        try:
            extracted_data['Name'] = self.extract_company_name(soup, text)
            extracted_data['Founders'] = self.extract_founders(soup, text)
            extracted_data['About'] = self.extract_about(soup, text)
            
            phone, email = self.extract_contact_info(text)
            extracted_data['Phone'] = phone
            extracted_data['Contact Email'] = email
            
            financial_data = self.extract_financial_data(text)
            extracted_data.update(financial_data)
            
            extracted_data['Company Location'] = self.extract_location(text)
            
            links = self.extract_links(soup, text)
            extracted_data.update(links)
            
        except Exception:
            pass
        
        return extracted_data
    
    def upload_to_n8n(self, file_path: str) -> bool:
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
            return result.returncode == 0
        except Exception:
            return False
    
    def process_html_files(self, input_folder: str, output_file: str) -> None:
        """Process all HTML files and generate Excel output."""
        if not os.path.exists(input_folder):
            return
        
        html_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.html')]
        
        if not html_files:
            return
        
        all_data = []
        
        for html_file in html_files:
            file_path = os.path.join(input_folder, html_file)
            extracted_data = self.extract_data_from_html(file_path)
            extracted_data['Source File'] = html_file
            all_data.append(extracted_data)
            
            # Delete HTML file after processing
            try:
                os.remove(file_path)
            except Exception:
                pass
        
        # Create and save DataFrame
        df = pd.DataFrame(all_data)
        column_order = self.data_fields + ['Source File']
        df = df[column_order]
        
        # Save Excel file
        try:
            df.to_excel(output_file, index=False, engine='openpyxl')
            
            # Upload to n8n webhook
            if os.path.exists(output_file):
                self.upload_to_n8n(output_file)
                
        except Exception:
            csv_file = output_file.replace('.xlsx', '.csv')
            df.to_csv(csv_file, index=False)
            
            # Try to upload CSV if Excel failed
            if os.path.exists(csv_file):
                self.upload_to_n8n(csv_file)

def main():
    parser = argparse.ArgumentParser(description='Extract company data from Crunchbase HTML files')
    parser.add_argument('--input_folder', '-i', required=True, help='Path to folder containing HTML files')
    parser.add_argument('--output_file', '-o', default='crunchbase_companies.xlsx', help='Output Excel file path')
    
    args = parser.parse_args()
    
    extractor = CrunchbaseDataExtractor()
    extractor.process_html_files(args.input_folder, args.output_file)

if __name__ == "__main__":
    main()