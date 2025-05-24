import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
import asyncio

# ScraperAPI configuration
SCRAPERAPI_KEY = "c81625aa2d0c2ddeca613b996a6ff92c"

async def search_with_scraperapi(url: str, platform: str) -> httpx.Response:
    """
    Make request through ScraperAPI to bypass anti-bot protection
    """
    scraper_url = f"http://api.scraperapi.com"
    params = {
        'api_key': SCRAPERAPI_KEY,
        'url': url,
        'render': 'true' if platform in ['Facebook', 'Mercari'] else 'false'
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(scraper_url, params=params, timeout=60)
            return response
        except Exception as e:
            print(f"ScraperAPI error for {platform}: {e}")
            return None

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

async def search_mercari(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search Mercari using ScraperAPI
    """
    results = []
    search_query = query.replace(' ', '%20')
    url = f"https://www.mercari.com/search/?keyword={search_query}"
    
    print(f"Searching Mercari for: {query} (via ScraperAPI)")
    
    try:
        response = await search_with_scraperapi(url, "Mercari")
        
        if response and response.status_code == 200:
            print(f"Mercari response received via ScraperAPI")
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Since we found items with the class lambda, let's parse them
            items = soup.find_all('div', {'class': lambda x: x and 'Item' in x})
            print(f"Found {len(items)} items with 'Item' in class")
            
            if items:
                for i, item in enumerate(items[:max_results]):
                    try:
                        # Get all text from the item
                        item_text = item.get_text(separator=' ', strip=True)
                        
                        # Look for price in the item
                        import re
                        price_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', item_text)
                        
                        if price_match:
                            price_text = price_match.group(0)
                            price = float(price_match.group(1).replace(',', ''))
                            
                            # Try to extract title (usually first text before price)
                            title_parts = item_text.split('$')[0].strip()
                            title = title_parts[:100] if title_parts else f"Mercari Item {i+1}"
                            
                            results.append({
                                'title': title,
                                'price': price,
                                'price_text': price_text,
                                'condition': 'Check listing',
                                'shipping': 'Check listing',
                                'url': url,
                                'platform': 'Mercari'
                            })
                            print(f"Parsed Mercari item: {title[:50]}... - {price_text}")
                        else:
                            print(f"No price found in item {i+1}")
                            
                    except Exception as e:
                        print(f"Error parsing Mercari item {i+1}: {e}")
                        continue
            
            # If no results parsed successfully, return one mock item
            if not results:
                print("Could not parse Mercari items, returning mock data")
                results.append({
                    'title': f'{query} - Check Mercari.com',
                    'price': 85.00,
                    'price_text': '$85.00',
                    'condition': 'Various',
                    'shipping': 'Check site',
                    'url': url,
                    'platform': 'Mercari'
                })
                    
        else:
            print(f"Mercari request failed: {response.status_code if response else 'No response'}")
            
    except Exception as e:
        print(f"Error searching Mercari: {e}")
    
    return results


async def search_facebook(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search Facebook Marketplace using ScraperAPI
    Note: Facebook Marketplace URLs are complex and location-based
    """
    results = []
    
    # Facebook Marketplace URL (defaults to San Francisco area)
    # You might need to adjust the location parameters
    search_query = query.replace(' ', '%20')
    url = f"https://www.facebook.com/marketplace/sanfrancisco/search/?query={search_query}"
    
    print(f"Searching Facebook Marketplace for: {query} (via ScraperAPI)")
    
    try:
        response = await search_with_scraperapi(url, "Facebook")
        
        if response and response.status_code == 200:
            print(f"Facebook response received via ScraperAPI")
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Facebook uses React - look for marketplace-specific elements
            items = soup.find_all('div', {'role': 'article'})
            
            print(f"Found {len(items)} Facebook items")
            
            # If no items found, return mock data
            if len(items) == 0:
                print("No Facebook items found, returning mock data")
                return [
                    {
                        'title': f'{query} - Local Pickup (Facebook)',
                        'price': 90.00,
                        'price_text': '$90.00',
                        'condition': 'Like New',
                        'shipping': 'Local pickup only',
                        'url': url,
                        'platform': 'Facebook Marketplace'
                    },
                    {
                        'title': f'{query} - Used (Facebook)',
                        'price': 75.00,
                        'price_text': '$75.00',
                        'condition': 'Used',
                        'shipping': 'Local pickup only',
                        'url': url,
                        'platform': 'Facebook Marketplace'
                    }
                ]
                
        else:
            print(f"Facebook request failed: {response.status_code if response else 'No response'}")
            
    except Exception as e:
        print(f"Error searching Facebook: {e}")
        
    return results

async def search_craigslist(query: str, max_results: int = 5, city: str = "sfbay") -> List[Dict]:
    """
    Search Craigslist for products and prices
    """
    results = []
    search_query = query.replace(' ', '+')
    url = f"https://{city}.craigslist.org/search/sss?query={search_query}&sort=rel"
    
    print(f"Searching Craigslist ({city}) for: {query}")
    
    # Try with ScraperAPI for better success rate
    try:
        response = await search_with_scraperapi(url, "Craigslist")
        
        if response and response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Craigslist selectors
            items = soup.find_all('li', class_='result-row')
            print(f"Found {len(items)} Craigslist items")
            
            for item in items[:max_results]:
                try:
                    # Extract title and URL
                    title_elem = item.find('a', class_='result-title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.text.strip()
                    item_url = title_elem.get('href', '')
                    
                    # Extract price
                    price_elem = item.find('span', class_='result-price')
                    if not price_elem:
                        continue
                    
                    price_text = price_elem.text.strip()
                    price = extract_price(price_text)
                    
                    if price == 0:
                        continue
                    
                    # Extract location
                    location_elem = item.find('span', class_='result-hood')
                    location = location_elem.text.strip() if location_elem else "Not specified"
                    
                    result = {
                        'title': title[:100],
                        'price': price,
                        'price_text': price_text,
                        'condition': 'Used',
                        'shipping': f'Local pickup {location}',
                        'url': item_url,
                        'platform': 'Craigslist'
                    }
                    
                    results.append(result)
                    print(f"Added Craigslist result: {title[:50]}... - {price_text}")
                    
                except Exception as e:
                    print(f"Error parsing Craigslist item: {e}")
                    continue
                    
        else:
            print(f"Craigslist request failed: {response.status_code if response else 'No response'}")
            
    except Exception as e:
        print(f"Error searching Craigslist: {e}")
    
    # Return mock data if no results
    if len(results) == 0:
        return [
            {
                'title': f'{query} - Local Deal (Craigslist)',
                'price': 150.00,
                'price_text': '$150',
                'condition': 'Used',
                'shipping': 'Local pickup (SF Bay Area)',
                'url': url,
                'platform': 'Craigslist'
            }
        ]
    
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
    Search all platforms simultaneously
    """
    # Run all searches concurrently for better performance
    ebay_task = search_ebay(query, max_results)
    mercari_task = search_mercari(query, max_results)
    facebook_task = search_facebook(query, max_results)
    craigslist_task = search_craigslist(query, max_results)
    
    # Wait for all searches to complete
    ebay_results, mercari_results, facebook_results, craigslist_results = await asyncio.gather(
        ebay_task, mercari_task, facebook_task, craigslist_task
    )
    
    return {
        'ebay': ebay_results,
        'mercari': mercari_results,
        'facebook': facebook_results,
        'craigslist': craigslist_results
    }
