# scrapers.py - Additional portal-specific scrapers
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import pandas as pd

logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date from various formats"""
    if not date_str:
        return None
        
    date_str = str(date_str).strip()
    
    # Common formats
    formats = [
        '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S',
        '%d-%b-%Y', '%d %b %Y', '%B %d, %Y', '%d %B %Y',
        '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%d-%m-%Y',
        '%b %d, %Y', '%d %b %Y %I:%M %p'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
            
    try:
        return pd.to_datetime(date_str, errors='coerce')
    except:
        return None

def parse_value(value_str: str) -> float:
    """Parse monetary value from string"""
    if not value_str:
        return 0.0
        
    value_str = str(value_str)
    
    # Remove currency symbols and text
    value_str = re.sub(r'[^0-9.,]', '', value_str)
    value_str = value_str.replace(',', '')
    
    try:
        return float(value_str)
    except:
        return 0.0

class ProvincialScrapers:
    """Scrapers for provincial procurement portals"""
    
    @staticmethod
    async def scan_alberta_purchasing(driver, selenium_helper) -> List[Dict]:
        """Scan Alberta Purchasing Connection"""
        tenders = []
        
        try:
            driver.get("https://vendor.purchasingconnection.ca/")
            
            # Navigate to opportunities
            opp_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Opportunities"))
            )
            opp_link.click()
            
            # Search for training
            search_box = driver.find_element(By.ID, "ContentPlaceHolder1_txt_keyword")
            search_box.send_keys("training professional development")
            
            search_btn = driver.find_element(By.ID, "ContentPlaceHolder1_btn_search")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results_table = soup.find('table', id='ContentPlaceHolder1_GridView1')
            
            if results_table:
                rows = results_table.find_all('tr')[1:]  # Skip header
                for row in rows[:30]:
                    cells = row.find_all('td')
                    if len(cells) >= 5:
                        tender = {
                            'tender_id': cells[0].text.strip(),
                            'title': cells[1].text.strip(),
                            'organization': cells[2].text.strip(),
                            'portal': 'Alberta Purchasing Connection',
                            'value': 0,
                            'closing_date': parse_date(cells[4].text.strip()),
                            'posted_date': parse_date(cells[3].text.strip()),
                            'location': 'Alberta',
                            'tender_url': 'https://vendor.purchasingconnection.ca/',
                            'description': '',
                            'categories': [],
                            'keywords': []
                        }
                        
                        # Get link if available
                        link = cells[1].find('a')
                        if link:
                            tender['tender_url'] = 'https://vendor.purchasingconnection.ca/' + link.get('href', '')
                            
                        tenders.append(tender)
                        
        except Exception as e:
            logger.error(f"Error scanning Alberta Purchasing: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_saskatchewan_tenders(driver, selenium_helper) -> List[Dict]:
        """Scan SaskTenders"""
        tenders = []
        
        try:
            driver.get("https://sasktenders.ca/content/public/Search.aspx")
            
            # Enter search
            keyword_box = driver.find_element(By.ID, "ctl00_ContentPlaceHolder_KeywordTextBox")
            keyword_box.send_keys("training education professional development")
            
            # Submit search
            search_btn = driver.find_element(By.ID, "ctl00_ContentPlaceHolder_SearchButton")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = soup.find_all('div', class_='tender-result')
            
            for result in results[:30]:
                tender = {
                    'tender_id': result.get('data-tender-id', ''),
                    'title': result.find('h3').text.strip() if result.find('h3') else '',
                    'organization': result.find('span', class_='org').text.strip() if result.find('span', class_='org') else 'Saskatchewan Government',
                    'portal': 'SaskTenders',
                    'value': 0,
                    'closing_date': parse_date(result.find('span', class_='closing').text.strip() if result.find('span', class_='closing') else ''),
                    'posted_date': datetime.utcnow(),
                    'location': 'Saskatchewan',
                    'tender_url': 'https://sasktenders.ca' + result.find('a')['href'] if result.find('a') else '',
                    'description': '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning SaskTenders: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_manitoba_tenders(session) -> List[Dict]:
        """Scan Manitoba Tenders (non-Selenium)"""
        tenders = []
        
        try:
            async with session.get("https://www.gov.mb.ca/tenders/") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find tender listings
                    tender_links = soup.find_all('a', href=re.compile(r'/tenders/tender_'))
                    
                    for link in tender_links[:30]:
                        tender = {
                            'tender_id': link.get('href', '').split('/')[-1].replace('.html', ''),
                            'title': link.text.strip(),
                            'organization': 'Manitoba Government',
                            'portal': 'Manitoba Tenders',
                            'value': 0,
                            'closing_date': None,
                            'posted_date': datetime.utcnow(),
                            'location': 'Manitoba',
                            'tender_url': 'https://www.gov.mb.ca' + link.get('href', ''),
                            'description': '',
                            'categories': [],
                            'keywords': []
                        }
                        
                        tenders.append(tender)
                        
        except Exception as e:
            logger.error(f"Error scanning Manitoba Tenders: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_ontario_tenders(driver, selenium_helper) -> List[Dict]:
        """Scan Ontario Tenders Portal"""
        tenders = []
        
        try:
            driver.get("https://ontariotenders.ca/page/public/buyer")
            
            # Search for training
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchKeyword"))
            )
            search_input.send_keys("training professional development")
            search_input.submit()
            
            # Wait for results
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tender-list"))
            )
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_items = soup.find_all('div', class_='tender-item')
            
            for item in tender_items[:30]:
                tender = {
                    'tender_id': item.get('data-id', ''),
                    'title': item.find('h3', class_='tender-title').text.strip() if item.find('h3') else '',
                    'organization': item.find('div', class_='org-name').text.strip() if item.find('div', class_='org-name') else '',
                    'portal': 'Ontario Tenders Portal',
                    'value': parse_value(item.find('span', class_='value').text if item.find('span', class_='value') else '0'),
                    'closing_date': parse_date(item.find('span', class_='closing-date').text if item.find('span', class_='closing-date') else ''),
                    'posted_date': parse_date(item.find('span', class_='posted-date').text if item.find('span', class_='posted-date') else ''),
                    'location': 'Ontario',
                    'tender_url': 'https://ontariotenders.ca' + item.find('a')['href'] if item.find('a') else '',
                    'description': item.find('p', class_='description').text.strip() if item.find('p', class_='description') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning Ontario Tenders: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_ns_tenders(driver, selenium_helper) -> List[Dict]:
        """Scan Nova Scotia Tenders"""
        tenders = []
        
        try:
            driver.get("https://novascotia.ca/tenders/tenders/tender-search.aspx")
            
            # Enter search keywords
            keyword_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtKeywords")
            keyword_input.send_keys("training professional development education")
            
            # Submit search
            search_btn = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnSearch")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results_table = soup.find('table', id='ctl00_ContentPlaceHolder1_gvTenders')
            
            if results_table:
                rows = results_table.find_all('tr')[1:]  # Skip header
                for row in rows[:30]:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        tender = {
                            'tender_id': cells[0].text.strip(),
                            'title': cells[1].text.strip(),
                            'organization': cells[2].text.strip(),
                            'portal': 'Nova Scotia Tenders',
                            'value': 0,
                            'closing_date': parse_date(cells[3].text.strip()),
                            'posted_date': datetime.utcnow(),
                            'location': 'Nova Scotia',
                            'tender_url': 'https://novascotia.ca/tenders/',
                            'description': '',
                            'categories': [],
                            'keywords': []
                        }
                        
                        tenders.append(tender)
                        
        except Exception as e:
            logger.error(f"Error scanning NS Tenders: {e}")
            
        return tenders

class MunicipalScrapers:
    """Scrapers for municipal procurement portals"""
    
    @staticmethod
    async def scan_ottawa_bids(driver, selenium_helper) -> List[Dict]:
        """Scan Ottawa Bids and Tenders"""
        tenders = []
        
        try:
            driver.get("https://ottawa.bidsandtenders.ca/Module/Tenders/en")
            
            # Search for training
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchTb"))
            )
            search_box.send_keys("training professional development")
            search_box.submit()
            
            # Wait for results
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tender-row"))
            )
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_rows = soup.find_all('tr', class_='tender-row')
            
            for row in tender_rows[:30]:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    tender = {
                        'tender_id': cells[0].text.strip(),
                        'title': cells[1].text.strip(),
                        'organization': 'City of Ottawa',
                        'portal': 'City of Ottawa',
                        'value': 0,
                        'closing_date': parse_date(cells[3].text.strip()),
                        'posted_date': parse_date(cells[2].text.strip()),
                        'location': 'Ottawa',
                        'tender_url': 'https://ottawa.bidsandtenders.ca' + cells[1].find('a')['href'] if cells[1].find('a') else '',
                        'description': '',
                        'categories': [],
                        'keywords': []
                    }
                    
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Ottawa Bids: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_edmonton_bids(driver, selenium_helper) -> List[Dict]:
        """Scan Edmonton Bids and Tenders"""
        tenders = []
        
        try:
            driver.get("https://edmonton.bidsandtenders.ca/Module/Tenders/en")
            
            # Similar structure to Ottawa
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchTb"))
            )
            search_box.send_keys("training development education")
            search_box.submit()
            
            # Wait and parse
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tender-row"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_rows = soup.find_all('tr', class_='tender-row')
            
            for row in tender_rows[:30]:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    tender = {
                        'tender_id': cells[0].text.strip(),
                        'title': cells[1].text.strip(),
                        'organization': 'City of Edmonton',
                        'portal': 'City of Edmonton',
                        'value': 0,
                        'closing_date': parse_date(cells[3].text.strip()),
                        'posted_date': parse_date(cells[2].text.strip()),
                        'location': 'Edmonton',
                        'tender_url': 'https://edmonton.bidsandtenders.ca' + cells[1].find('a')['href'] if cells[1].find('a') else '',
                        'description': '',
                        'categories': [],
                        'keywords': []
                    }
                    
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Edmonton Bids: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_calgary_procurement(driver, selenium_helper) -> List[Dict]:
        """Scan Calgary Procurement"""
        tenders = []
        
        try:
            driver.get("https://procurement.calgary.ca/")
            
            # Navigate to opportunities
            opp_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Current Opportunities"))
            )
            opp_link.click()
            
            # Search
            search_input = driver.find_element(By.ID, "keyword-search")
            search_input.send_keys("training professional development")
            search_input.submit()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='opportunity')
            
            for opp in opportunities[:30]:
                tender = {
                    'tender_id': opp.get('data-id', ''),
                    'title': opp.find('h3').text.strip() if opp.find('h3') else '',
                    'organization': 'City of Calgary',
                    'portal': 'City of Calgary',
                    'value': parse_value(opp.find('span', class_='value').text if opp.find('span', class_='value') else '0'),
                    'closing_date': parse_date(opp.find('span', class_='closing').text if opp.find('span', class_='closing') else ''),
                    'posted_date': datetime.utcnow(),
                    'location': 'Calgary',
                    'tender_url': 'https://procurement.calgary.ca' + opp.find('a')['href'] if opp.find('a') else '',
                    'description': opp.find('p', class_='desc').text.strip() if opp.find('p', class_='desc') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning Calgary Procurement: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_winnipeg_bids(session) -> List[Dict]:
        """Scan Winnipeg Bids (non-Selenium)"""
        tenders = []
        try:
            async with session.get("https://winnipeg.ca/matmgt/bidopp.asp") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    bid_table = soup.find('table', class_='bidopptable')
                    if bid_table:
                        rows = bid_table.find_all('tr')[1:]
                        for row in rows[:30]:
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                tender = {
                                    'tender_id': cells[0].text.strip(),
                                    'title': cells[1].text.strip(),
                                    'organization': 'City of Winnipeg',
                                    'portal': 'City of Winnipeg',
                                    'value': 0,
                                    'closing_date': parse_date(cells[3].text.strip()),
                                    'posted_date': parse_date(cells[2].text.strip()),
                                    'location': 'Winnipeg',
                                    'tender_url': 'https://winnipeg.ca' + (cells[1].find('a')['href'] if cells[1].find('a') else ''),
                                    'description': '',
                                    'categories': [],
                                    'keywords': []
                                }
                                tenders.append(tender)
        except Exception as e:
            logger.error(f"Error scanning Winnipeg Bids: {e}")
        return tenders

    @staticmethod
    async def scan_vancouver_procurement(driver, selenium_helper) -> List[Dict]:
        """Scan Vancouver Procurement"""
        tenders = []
        try:
            driver.get("https://procure.vancouver.ca/psp/VFCPROD/SUPPLIER/ERP/h/?tab=DEFAULT")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "ptpglpage")))
            sourcing_link = driver.find_element(By.LINK_TEXT, "Sourcing")
            sourcing_link.click()
            search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "BUYER_SEARCH_WRK_DESCRLONG")))
            search_box.send_keys("training professional development")
            search_btn = driver.find_element(By.ID, "BUYER_SEARCH_WRK_SEARCH_PB")
            search_btn.click()
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opp_grid = soup.find('table', id='BUYER_SOURCING_SEARCH')
            if opp_grid:
                rows = opp_grid.find_all('tr')[1:]
                for row in rows[:30]:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        tender = {
                            'tender_id': cells[0].text.strip(),
                            'title': cells[1].text.strip(),
                            'organization': 'City of Vancouver',
                            'portal': 'City of Vancouver',
                            'value': 0,
                            'closing_date': parse_date(cells[3].text.strip()),
                            'posted_date': datetime.utcnow(),
                            'location': 'Vancouver',
                            'tender_url': driver.current_url,
                            'description': '',
                            'categories': [],
                            'keywords': []
                        }
                        tenders.append(tender)
        except Exception as e:
            logger.error(f"Error scanning Vancouver Procurement: {e}")
        return tenders

    @staticmethod
    async def scan_halifax_procurement(driver, selenium_helper) -> List[Dict]:
        """Scan Halifax Regional Municipality"""
        tenders = []
        
        try:
            driver.get("https://procurement.novascotia.ca/ns-tenders.aspx")
            
            # Filter by Halifax
            location_filter = driver.find_element(By.ID, "ddlLocation")
            location_filter.send_keys("Halifax")
            
            # Search for training
            keyword_box = driver.find_element(By.ID, "txtKeywords")
            keyword_box.send_keys("training professional development")
            
            search_btn = driver.find_element(By.ID, "btnSearch")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = soup.find_all('tr', class_='tender-row')
            
            for row in results[:30]:
                cells = row.find_all('td')
                if len(cells) >= 4 and 'Halifax' in cells[2].text:
                    tender = {
                        'tender_id': cells[0].text.strip(),
                        'title': cells[1].text.strip(),
                        'organization': 'Halifax Regional Municipality',
                        'portal': 'Halifax Regional Municipality',
                        'value': 0,
                        'closing_date': parse_date(cells[3].text.strip()),
                        'posted_date': datetime.utcnow(),
                        'location': 'Halifax',
                        'tender_url': 'https://procurement.novascotia.ca' + cells[1].find('a')['href'] if cells[1].find('a') else '',
                        'description': '',
                        'categories': [],
                        'keywords': []
                    }
                    
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Halifax Procurement: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_regina_procurement(driver, selenium_helper) -> List[Dict]:
        """Scan City of Regina"""
        tenders = []
        
        try:
            driver.get("https://procurement.regina.ca/")
            
            # Navigate to current opportunities
            current_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Current Opportunities"))
            )
            current_link.click()
            
            # Search
            search_input = driver.find_element(By.ID, "search-field")
            search_input.send_keys("training development")
            search_input.submit()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='opportunity-item')
            
            for opp in opportunities[:30]:
                tender = {
                    'tender_id': opp.get('data-ref', ''),
                    'title': opp.find('h3').text.strip() if opp.find('h3') else '',
                    'organization': 'City of Regina',
                    'portal': 'City of Regina',
                    'value': 0,
                    'closing_date': parse_date(opp.find('span', class_='closing-date').text if opp.find('span', class_='closing-date') else ''),
                    'posted_date': parse_date(opp.find('span', class_='posted-date').text if opp.find('span', class_='posted-date') else ''),
                    'location': 'Regina',
                    'tender_url': 'https://procurement.regina.ca' + opp.find('a')['href'] if opp.find('a') else '',
                    'description': opp.find('p', class_='description').text.strip() if opp.find('p', class_='description') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning Regina Procurement: {e}")
            
        return tenders

class SpecializedScrapers:
    """Scrapers for specialized procurement platforms"""
    
    @staticmethod
    async def scan_nbon_newbrunswick(driver, selenium_helper) -> List[Dict]:
        """Scan New Brunswick Opportunities Network"""
        tenders = []
        
        try:
            driver.get("https://nbon.gnb.ca/content/nbon/en/opportunities.html")
            
            # Search for training
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "keyword"))
            )
            search_box.send_keys("training professional development education")
            
            # Select relevant categories
            category_select = driver.find_element(By.ID, "category")
            categories = ["Professional Services", "Educational Services", "Training Services"]
            for cat in categories:
                try:
                    option = driver.find_element(By.XPATH, f"//option[contains(text(), '{cat}')]")
                    option.click()
                except:
                    pass
            
            # Submit search
            search_btn = driver.find_element(By.ID, "search-submit")
            search_btn.click()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='opportunity-listing')
            
            for opp in opportunities[:30]:
                tender = {
                    'tender_id': opp.get('data-opp-id', ''),
                    'title': opp.find('h3', class_='opp-title').text.strip() if opp.find('h3', class_='opp-title') else '',
                    'organization': opp.find('span', class_='org-name').text.strip() if opp.find('span', class_='org-name') else 'New Brunswick Government',
                    'portal': 'New Brunswick Opportunities Network',
                    'value': parse_value(opp.find('span', class_='value').text if opp.find('span', class_='value') else '0'),
                    'closing_date': parse_date(opp.find('span', class_='closing-date').text if opp.find('span', class_='closing-date') else ''),
                    'posted_date': parse_date(opp.find('span', class_='posted-date').text if opp.find('span', class_='posted-date') else ''),
                    'location': 'New Brunswick',
                    'tender_url': 'https://nbon.gnb.ca' + opp.find('a')['href'] if opp.find('a') else '',
                    'description': opp.find('p', class_='description').text.strip() if opp.find('p', class_='description') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning NBON: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_pei_tenders(session) -> List[Dict]:
        """Scan PEI Tenders"""
        tenders = []
        
        try:
            # PEI uses a simple listing page
            async with session.get("https://www.princeedwardisland.ca/en/search/site?f%5B0%5D=type%3Atender") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find search results
                    results = soup.find_all('li', class_='search-result')
                    
                    for result in results[:30]:
                        title_elem = result.find('h3', class_='title')
                        if title_elem:
                            # Check if training related
                            title = title_elem.text.strip()
                            if any(keyword in title.lower() for keyword in ['training', 'education', 'development', 'professional']):
                                tender = {
                                    'tender_id': result.get('data-id', f"PEI_{datetime.now().timestamp()}"),
                                    'title': title,
                                    'organization': 'PEI Government',
                                    'portal': 'PEI Tenders',
                                    'value': 0,
                                    'closing_date': None,
                                    'posted_date': datetime.utcnow(),
                                    'location': 'Prince Edward Island',
                                    'tender_url': 'https://www.princeedwardisland.ca' + title_elem.find('a')['href'] if title_elem.find('a') else '',
                                    'description': result.find('p', class_='search-snippet').text.strip() if result.find('p', class_='search-snippet') else '',
                                    'categories': [],
                                    'keywords': []
                                }
                                
                                # Try to extract date from description
                                desc = tender['description']
                                date_match = re.search(r'Closing[:\s]+([A-Za-z]+ \d+, \d{4})', desc)
                                if date_match:
                                    tender['closing_date'] = parse_date(date_match.group(1))
                                
                                tenders.append(tender)
                                
        except Exception as e:
            logger.error(f"Error scanning PEI Tenders: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_nl_procurement(session) -> List[Dict]:
        """Scan Newfoundland and Labrador Procurement"""
        tenders = []
        
        try:
            # Search for training-related commodities
            search_url = "https://www.gov.nl.ca/tenders/commodity-search/?commodity=training"
            
            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find tender listings
                    tender_list = soup.find('div', class_='tender-list')
                    if tender_list:
                        tender_items = tender_list.find_all('div', class_='tender-item')
                        
                        for item in tender_items[:30]:
                            tender = {
                                'tender_id': item.get('data-tender-id', ''),
                                'title': item.find('h3').text.strip() if item.find('h3') else '',
                                'organization': item.find('span', class_='dept').text.strip() if item.find('span', class_='dept') else 'NL Government',
                                'portal': 'Newfoundland Procurement',
                                'value': parse_value(item.find('span', class_='value').text if item.find('span', class_='value') else '0'),
                                'closing_date': parse_date(item.find('span', class_='closing').text if item.find('span', class_='closing') else ''),
                                'posted_date': parse_date(item.find('span', class_='posted').text if item.find('span', class_='posted') else ''),
                                'location': 'Newfoundland and Labrador',
                                'tender_url': 'https://www.gov.nl.ca' + item.find('a')['href'] if item.find('a') else '',
                                'description': item.find('p', class_='desc').text.strip() if item.find('p', class_='desc') else '',
                                'categories': [],
                                'keywords': []
                            }
                            
                            tenders.append(tender)
                            
        except Exception as e:
            logger.error(f"Error scanning NL Procurement: {e}")
            
        return tenders

class HealthEducationScrapers:
    """Scrapers for health and education sector procurement"""
    
    @staticmethod
    async def scan_buybc_health(driver, selenium_helper) -> List[Dict]:
        """Scan Buy BC Health"""
        tenders = []
        
        try:
            driver.get("https://www.bchealth.ca/tenders")
            
            # Search for training
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "tender-search"))
            )
            search_input.send_keys("training education professional development")
            search_input.submit()
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_cards = soup.find_all('div', class_='tender-card')
            
            for card in tender_cards[:30]:
                tender = {
                    'tender_id': card.get('data-tender-id', ''),
                    'title': card.find('h3', class_='tender-title').text.strip() if card.find('h3') else '',
                    'organization': card.find('span', class_='health-authority').text.strip() if card.find('span', class_='health-authority') else 'BC Health',
                    'portal': 'Buy BC Health',
                    'value': parse_value(card.find('span', class_='value').text if card.find('span', class_='value') else '0'),
                    'closing_date': parse_date(card.find('span', class_='closing').text if card.find('span', class_='closing') else ''),
                    'posted_date': parse_date(card.find('span', class_='posted').text if card.find('span', class_='posted') else ''),
                    'location': 'British Columbia',
                    'tender_url': 'https://www.bchealth.ca' + card.find('a')['href'] if card.find('a') else '',
                    'description': card.find('p', class_='description').text.strip() if card.find('p') else '',
                    'categories': [],
                    'keywords': []
                }
                
                tenders.append(tender)
                
        except Exception as e:
            logger.error(f"Error scanning Buy BC Health: {e}")
            
        return tenders
    
    @staticmethod
    async def scan_ontario_health(driver, selenium_helper) -> List[Dict]:
        """Scan Ontario Health via MERX"""
        tenders = []
        
        try:
            # Ontario Health posts on MERX
            driver.get("https://www.merx.com/search")
            
            # Search for Ontario Health training opportunities
            search_box = driver.find_element(By.ID, "keyword")
            search_box.send_keys("Ontario Health training professional development")
            
            # Filter by organization
            org_filter = driver.find_element(By.ID, "organization")
            org_filter.send_keys("Ontario Health")
            
            # Submit search
            search_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            search_btn.click()
            
            # Parse results (similar to MERX scraper)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            opportunities = soup.find_all('div', class_='row')
            
            for opp in opportunities[:20]:
                if 'Ontario Health' in opp.text:
                    tender = {
                        'tender_id': opp.get('data-id', ''),
                        'title': opp.find('a', class_='search-result-title').text.strip() if opp.find('a', class_='search-result-title') else '',
                        'organization': 'Ontario Health',
                        'portal': 'Ontario Health',
                        'value': 0,
                        'closing_date': parse_date(opp.find('span', class_='closing-date').text if opp.find('span', class_='closing-date') else ''),
                        'posted_date': parse_date(opp.find('span', class_='posted-date').text if opp.find('span', class_='posted-date') else ''),
                        'location': 'Ontario',
                        'tender_url': 'https://www.merx.com' + opp.find('a')['href'] if opp.find('a') else '',
                        'description': '',
                        'categories': [],
                        'keywords': []
                    }
                    
                    tenders.append(tender)
                    
        except Exception as e:
            logger.error(f"Error scanning Ontario Health: {e}")
            
        return tenders