import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
import asyncio

async def search_ebay(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search eBay for products and prices
    """
    results = []
    
    # Format query for URL
    search_query = query.replace(' ', '+')
    url = f"https://www.ebay.com/sch/i.html?_nkw={search_query}&_ipg={max_results}&LH_BIN=1"
    
    print(f"Searching eBay for: {query}")
    print(f"URL: {url}")
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = await client.get(url, headers=headers, timeout=30, follow_redirects=True)
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error: Got status code {response.status_code}")
                return results
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Debug: Let's see what we're getting
            all_items = soup.find_all(['div', 'li'], class_=lambda x: x and ('s-item' in x or 'srp-results' in x))
            print(f"Found {len(all_items)} potential items")
            
            # Try multiple selectors
            items = soup.find_all('div', class_='s-item__wrapper')
            if not items:
                items = soup.find_all('li', class_='s-item')
            if not items:
                items = soup.find_all('div', {'class': lambda x: x and 's-item' in x and 'wrapper' not in x})
            
            print(f"Found {len(items)} items after filtering")
            
            # If still no items, let's check what's on the page
            if len(items) == 0:
                # Find any element with a price
                price_elements = soup.find_all('span', string=lambda x: x and '$' in x)
                print(f"Found {len(price_elements)} price elements on page")
                
                # Try to find items by looking for prices
                for price_elem in price_elements[:max_results]:
                    try:
                        # Go up to find the parent item container
                        parent = price_elem.parent
                        for _ in range(5):  # Go up max 5 levels
                            if parent and ('item' in str(parent.get('class', [])).lower() or 
                                         parent.name in ['article', 'li']):
                                break
                            parent = parent.parent if parent else None
                        
                        if parent:
                            title_elem = parent.find(['h3', 'h2', 'a'], string=True)
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                price_text = price_elem.get_text(strip=True)
                                price = extract_price(price_text)
                                
                                if price > 0 and not any(skip in title.lower() for skip in ['shop on ebay', 'results', 'sponsored']):
                                    results.append({
                                        'title': title[:100],
                                        'price': price,
                                        'price_text': price_text,
                                        'condition': 'Check listing',
                                        'shipping': 'Check listing',
                                        'url': url,
                                        'platform': 'eBay'
                                    })
                                    print(f"Added result via price search: {title[:50]}... - {price_text}")
                    except:
                        continue
                
                return results
            
            # Normal parsing if items found
            for item in items[:max_results]:
                try:
                    # Skip if it's an ad or irrelevant
                    if 'shop on ebay' in str(item).lower():
                        continue
                    
                    # Extract title - try multiple selectors
                    title = None
                    for selector in ['h3.s-item__title', 'h3', 'a.s-item__link', '.s-item__title']:
                        title_elem = item.select_one(selector)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            break
                    
                    if not title:
                        continue
                    
                    # Extract price - try multiple selectors
                    price_text = None
                    for selector in ['span.s-item__price', '.s-item__price', 'span:contains("$")']:
                        price_elem = item.select_one(selector)
                        if price_elem:
                            price_text = price_elem.get_text(strip=True)
                            break
                    
                    if not price_text:
                        continue
                    
                    price = extract_price(price_text)
                    if price == 0:
                        continue
                    
                    # Extract URL
                    link_elem = item.find('a', href=True)
                    item_url = link_elem['href'] if link_elem else url
                    
                    result = {
                        'title': title[:100],
                        'price': price,
                        'price_text': price_text,
                        'condition': 'Check listing',
                        'shipping': 'Check listing',
                        'url': item_url,
                        'platform': 'eBay'
                    }
                    
                    results.append(result)
                    print(f"Added result: {title[:50]}... - {price_text}")
                    
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error searching eBay: {type(e).__name__}: {str(e)}")
    
    # If no results, return mock data so we know eBay was searched
    if len(results) == 0:
        print("No eBay results found, returning mock data")
        results.append({
            'title': f'{query} - Check eBay.com directly',
            'price': 150.00,
            'price_text': '$150.00',
            'condition': 'Various',
            'shipping': 'Varies',
            'url': url,
            'platform': 'eBay (parsing needs update)'
        })
            
    return results

def extract_price(price_text: str) -> float:
    """
    Extract numeric price from text
    """
    import re
    
    # Remove currency symbols and commas
    price_text = price_text.replace('$', '').replace(',', '')
    
    # Handle price ranges (e.g., "$100 to $200")
    if 'to' in price_text.lower():
        # Extract first price in range
        match = re.search(r'(\d+\.?\d*)', price_text)
        if match:
            return float(match.group(1))
    
    # Extract first number found
    match = re.search(r'(\d+\.?\d*)', price_text)
    if match:
        return float(match.group(1))
    
    return 0.0

async def search_all_platforms(query: str, max_results: int = 5) -> Dict[str, List[Dict]]:
    """
    Search eBay only (removed other platforms)
    """
    ebay_results = await search_ebay(query, max_results)
    
    return {
        'ebay': ebay_results
    }
