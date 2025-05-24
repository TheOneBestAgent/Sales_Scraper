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
    
    async with httpx.AsyncClient() as client:
        try:
            # Add headers to look like a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = await client.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find all item containers
            items = soup.find_all('div', class_='s-item__wrapper')
            
            for item in items[:max_results]:
                try:
                    # Extract title
                    title_elem = item.find('h3', class_='s-item__title')
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    
                    # Skip irrelevant results
                    if 'Shop on eBay' in title:
                        continue
                    
                    # Extract price
                    price_elem = item.find('span', class_='s-item__price')
                    if not price_elem:
                        continue
                    
                    price_text = price_elem.text.strip()
                    # Extract numeric price
                    price = extract_price(price_text)
                    
                    # Extract URL
                    link_elem = item.find('a', class_='s-item__link')
                    url = link_elem['href'] if link_elem else ""
                    
                    # Extract condition
                    condition_elem = item.find('span', class_='SECONDARY_INFO')
                    condition = condition_elem.text.strip() if condition_elem else "Not specified"
                    
                    # Extract shipping
                    shipping_elem = item.find('span', class_='s-item__shipping')
                    shipping = shipping_elem.text.strip() if shipping_elem else "Not specified"
                    
                    results.append({
                        'title': title[:100],  # Limit title length
                        'price': price,
                        'price_text': price_text,
                        'condition': condition,
                        'shipping': shipping,
                        'url': url,
                        'platform': 'eBay'
                    })
                    
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error searching eBay: {e}")
            
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
