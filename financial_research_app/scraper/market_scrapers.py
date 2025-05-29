from .utils import get_previous_day_price
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import json # Added for SEC EDGAR JSON processing

# --- CIK Mapping Helper ---
# Global cache for CIK mapping to avoid refetching ticker.txt repeatedly
_cik_map_cache = None

def _fetch_and_parse_cik_map():
    """
    Fetches ticker.txt from SEC and parses it into a ticker -> CIK dictionary.
    CIKs are zero-padded to 10 digits.
    """
    global _cik_map_cache
    if _cik_map_cache is not None:
        return _cik_map_cache

    print("Fetching CIK map from SEC website...")
    ticker_url = "https://www.sec.gov/include/ticker.txt"
    local_cik_map = {}
    try:
        response = requests.get(ticker_url, headers={'User-Agent': 'Mozilla/5.0 FinancialResearchApp/1.0'})
        response.raise_for_status()
        # ticker.txt is a simple text file, tab-separated: ticker<TAB>CIK
        for line in response.text.splitlines():
            parts = line.strip().split('\t')
            if len(parts) == 2:
                ticker = parts[0].upper()
                cik = parts[1]
                local_cik_map[ticker] = str(cik).zfill(10) # Ensure CIK is 10 digits, zero-padded
        _cik_map_cache = local_cik_map
        print(f"CIK map loaded with {len(_cik_map_cache)} entries.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CIK map: {e}")
        # In case of error, return empty map or handle as appropriate
        # For now, allow it to proceed; functions using it should handle None CIK
    return _cik_map_cache

def _get_cik_for_ticker(ticker_symbol: str) -> str | None:
    """
    Retrieves the CIK for a given ticker symbol.
    Uses a cached map.
    """
    ticker_symbol = ticker_symbol.upper()
    cik_map = _fetch_and_parse_cik_map()
    if cik_map:
        return cik_map.get(ticker_symbol)
    return None
# --- End CIK Mapping Helper ---

# --- SEC EDGAR Filings Helper ---
def _fetch_sec_edgar_filings(cik: str, asset_symbol_for_logging: str) -> list[str]:
    """
    Fetches recent SEC EDGAR filings for a given CIK.
    Returns a list of URLs to the primary documents of the filings.
    """
    collected_links = []
    try:
        headers = {
            'User-Agent': 'FinancialResearchApp/1.0 myemail@example.com' 
        }
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        response = requests.get(submissions_url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status()
        
        submissions_data = response.json()
        
        recent_filings = submissions_data.get('filings', {}).get('recent', {})
        if not recent_filings or not recent_filings.get('accessionNumber'):
            print(f"No recent filings data structure found for CIK {cik} ({asset_symbol_for_logging}).")
            return collected_links

        cutoff_date = datetime.now() - timedelta(days=2) 

        accession_numbers = recent_filings.get('accessionNumber', [])
        filing_dates = recent_filings.get('filingDate', [])
        form_types = recent_filings.get('form', [])
        primary_documents = recent_filings.get('primaryDocument', [])

        for i in range(len(accession_numbers)):
            try:
                filing_date_str = filing_dates[i]
                filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
                
                if filing_date >= cutoff_date:
                    form = form_types[i]
                    if form.upper() in ["8-K", "10-K", "10-Q", "8K", "10K", "10Q"]:
                        accession_no_dashed = accession_numbers[i]
                        accession_no_no_dashes = accession_no_dashed.replace('-', '')
                        primary_doc_name = primary_documents[i]
                        
                        # Ensure CIK for path is not zero-padded
                        cik_for_path = str(int(cik)) 

                        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_for_path}/{accession_no_no_dashes}/{primary_doc_name}"
                        collected_links.append(filing_url)
            except ValueError as ve:
                print(f"Could not parse date '{filing_date_str}' for CIK {cik}, filing {accession_numbers[i]}: {ve}")
            except IndexError:
                print(f"Incomplete data for a recent filing entry for CIK {cik}.")
                break 
        
        return list(set(collected_links))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching SEC data for {asset_symbol_for_logging} (CIK {cik}): {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from SEC for {asset_symbol_for_logging} (CIK {cik}): {e}")
    except Exception as e:
        print(f"An unexpected error occurred while processing SEC filings for {asset_symbol_for_logging} (CIK {cik}): {e}")
    return collected_links # Return whatever was collected in case of partial success before error
# --- End SEC EDGAR Filings Helper ---

def scrape_b3(asset_symbol: str, config: dict) -> dict:
    """
    Scrapes B3 assets for price and recent news/reports.
    Fetches the previous day's price using yfinance.
    Scrapes B3 news portal for recent "Comunicados ao Mercado" and "Fatos Relevantes".
    """
    # Prepare symbols: one for yfinance, one for news scraping (usually the root)
    yfinance_symbol = asset_symbol
    if not yfinance_symbol.upper().endswith(".SA"):
        yfinance_symbol += ".SA"
    
    # The asset symbol for news search should be the root (e.g., PETR4, VALE3)
    # We assume asset_symbol is passed in this format.
    news_search_symbol = asset_symbol.upper().replace(".SA", "")

    price = get_previous_day_price(yfinance_symbol)
    collected_links = []

    try:
        news_url = "https://www.b3.com.br/pt_br/noticias/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(news_url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes

        soup = BeautifulSoup(response.content, "html.parser")

        # This is a guess based on common structures and the view_text_website output.
        # The actual B3 site might use different tags/classes.
        # We are looking for links and trying to find dates associated with them.
        
        # Attempt to find all links that look like news articles
        # Links on B3 news often look like: /pt_br/noticias/some-title-here.htm
        news_links_tags = soup.find_all('a', href=re.compile(r'/pt_br/noticias/.*\.(htm|html)$'))

        cutoff_date = datetime.now() - timedelta(days=2) # Last 48 hours

        for link_tag in news_links_tags:
            link_url = link_tag['href']
            if not link_url.startswith('http'):
                link_url = "https://www.b3.com.br" + link_url
            
            title = link_tag.get_text(strip=True)

            # Try to find the date. This is highly dependent on HTML structure.
            # We'll navigate around the link tag to find something that looks like a date.
            # This is a common pattern: date is a sibling or parent's sibling.
            date_text = None
            # Try to find date in a parent container, looking for specific text patterns or tags.
            # This part is very speculative.
            # Let's assume the date might be in a span or div near the link, or a sibling.
            # Example: <p class="date">23/05/2024</p> <h3><a href="...">Title</a></h3>
            # Or: <div><span>23/05/2024</span> <a href="...">Title</a></div>

            # Simplified approach: Look for date-like text in the parent of the link,
            # or siblings of the parent. This is fragile.
            parent_for_date = link_tag.parent
            date_element = None
            attempts = 0
            while parent_for_date and attempts < 3: # Search up to 3 levels
                # Regex to find DD/MM/YYYY or DD.MM.YYYY
                date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', parent_for_date.get_text())
                if date_match:
                    date_text = date_match.group(1)
                    break
                parent_for_date = parent_for_date.parent
                attempts += 1
            
            if not date_text: # Fallback if not found in parent, check siblings (less likely for well-structured HTML)
                if link_tag.find_previous_sibling(string=re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')):
                    date_text = link_tag.find_previous_sibling(string=re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')).strip()
                elif link_tag.find_next_sibling(string=re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')): # Less common
                     date_text = link_tag.find_next_sibling(string=re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')).strip()


            if date_text and title:
                try:
                    # B3 dates are DD/MM/YYYY
                    news_date = datetime.strptime(date_text, "%d/%m/%Y")
                    if news_date >= cutoff_date:
                        # Check if the asset symbol is in the title or link URL (heuristic)
                        # Using news_search_symbol (e.g., "PETR4")
                        if news_search_symbol.lower() in title.lower() or news_search_symbol.lower() in link_url.lower():
                            # Keywords for "Comunicados ao Mercado" or "Fatos Relevantes"
                            if "comunicado ao mercado" in title.lower() or \
                               "fato relevante" in title.lower() or \
                               "aviso aos acionistas" in title.lower() or \
                               news_search_symbol.lower() in title.lower(): # General news about the symbol
                                collected_links.append(link_url)
                except ValueError:
                    print(f"Warning: Could not parse date '{date_text}' for link {link_url}")
                    continue # Skip if date format is not as expected
        
        # Remove duplicates
        collected_links = list(set(collected_links))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching news from B3: {e}")
    except Exception as e:
        print(f"Error processing B3 news: {e}")

    return {"asset": asset_symbol, "price": price, "news_links": collected_links}

def scrape_nasdaq(asset_symbol: str, config: dict) -> dict:
    """
    Placeholder for scraping NASDAQ assets.
    Fetches the previous day's price using yfinance.
    """
    price = get_previous_day_price(asset_symbol) # yfinance uses the raw asset symbol for US exchanges
    collected_links = []
    
    cik = _get_cik_for_ticker(asset_symbol)
    if not cik:
        print(f"CIK not found for {asset_symbol}. Cannot fetch SEC filings.")
    else:
        collected_links = _fetch_sec_edgar_filings(cik, asset_symbol)
        
    return {"asset": asset_symbol, "price": price, "news_links": collected_links}

def scrape_nyse(asset_symbol: str, config: dict) -> dict:
    """
    Scrapes NYSE assets for price and recent SEC EDGAR filings.
    Fetches the previous day's price using yfinance.
    Uses SEC EDGAR for news/report links.
    """
    price = get_previous_day_price(asset_symbol) # yfinance uses the raw asset symbol for US exchanges
    collected_links = []

    cik = _get_cik_for_ticker(asset_symbol)
    if not cik:
        print(f"CIK not found for {asset_symbol}. Cannot fetch SEC filings.")
    else:
        collected_links = _fetch_sec_edgar_filings(cik, asset_symbol)

    return {"asset": asset_symbol, "price": price, "news_links": collected_links}
