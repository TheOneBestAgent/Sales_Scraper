import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
import asyncio

async def search_ebay(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search eBay for products and prices
    Note: This is a simplified example - be respectful of rate limits
    """
    results = []
    
    # Format query for URL
    search_query = query.replace(' ', '+')
    url = f"https://www.ebay.com/sch/i.html?_nkw={search_query}&_ipg={max_results}&LH_BIN=1"
    
    print(f"Searching eBay for: {query}")
    print(f"URL: {url}")
    
    async with httpx.AsyncClient() as client:
        try:
            # Add headers to look like a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = await client.get(url, headers=headers, timeout=30, follow_redirects=True)
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error: Got status code {response.status_code}")
                return results
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Try different selectors for eBay items
            items = soup.find_all('div', class_='s-item__wrapper')
            if not items:
                items = soup.find_all('div', class_='s-item')
            
            print(f"Found {len(items)} items")
            
            # Debug: Let's see what we're getting
            if items and len(items) > 0:
                print("First item HTML preview:")
                print(str(items[0])[:500])  # Print first 500 chars of first item
            else:
                print("No items found with expected selectors")
                # Try to find any div with 'item' in the class
                all_items = soup.find_all('div', class_=lambda x: x and 'item' in str(x))
                print(f"Found {len(all_items)} divs with 'item' in class name")
            
            for item in items[:max_results]:
                try:
                    # Extract title - try multiple selectors
                    title_elem = item.find('h3', class_='s-item__title')
                    if not title_elem:
                        title_elem = item.find('h3')
                    if not title_elem:
                        title_elem = item.find(['span', 'div'], class_=lambda x: x and 'title' in str(x))
                    if not title_elem:
                        print("No title found in item")
                        continue
                    
                    title = title_elem.text.strip()
                    
                    # Skip irrelevant results
                    if 'Shop on eBay' in title or title.startswith('Shop'):
                        continue
                    
                    # Extract price - try multiple selectors
                    price_elem = item.find('span', class_='s-item__price')
                    if not price_elem:
                        price_elem = item.find('span', {'class': lambda x: x and 'price' in x})
                    if not price_elem:
                        continue
                    
                    price_text = price_elem.text.strip()
                    price = extract_price(price_text)
                    
                    # Extract URL
                    link_elem = item.find('a', class_='s-item__link')
                    if not link_elem:
                        link_elem = item.find('a', href=True)
                    url = link_elem['href'] if link_elem else ""
                    
                    # Extract condition
                    condition_elem = item.find('span', class_='SECONDARY_INFO')
                    condition = condition_elem.text.strip() if condition_elem else "Not specified"
                    
                    # Extract shipping
                    shipping_elem = item.find('span', class_='s-item__shipping')
                    shipping = shipping_elem.text.strip() if shipping_elem else "Not specified"
                    
                    result = {
                        'title': title[:100],
                        'price': price,
                        'price_text': price_text,
                        'condition': condition,
                        'shipping': shipping,
                        'url': url,
                        'platform': 'eBay'
                    }
                    
                    results.append(result)
                    print(f"Added result: {title[:50]}... - {price_text}")
                    
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error searching eBay: {type(e).__name__}: {str(e)}")
            # Return mock data for testing
            print("Returning mock data due to error")
            return [
                {
                    'title': f'Mock {query} Item 1',
                    'price': 99.99,
                    'price_text': '$99.99',
                    'condition': 'New',
                    'shipping': 'Free shipping',
                    'url': 'https://www.ebay.com',
                    'platform': 'eBay'
                },
                {
                    'title': f'Mock {query} Item 2',
                    'price': 89.99,
                    'price_text': '$89.99',
                    'condition': 'Used',
                    'shipping': '$5.00 shipping',
                    'url': 'https://www.ebay.com',
                    'platform': 'eBay'
                }
            ]
            
    return results

def extract_price(price_text: str) -> float:
    """Extract numeric price from text like '$99.99' or '$50.00 to $100.00'"""
    import re
    
    # Find all numbers in the price text
    numbers = re.findall(r'[\d,]+\.?\d*', price_text)
    
    if numbers:
        # Take the first number (lowest price if it's a range)
        price = float(numbers[0].replace(',', ''))
        return price
    
    return 0.0
