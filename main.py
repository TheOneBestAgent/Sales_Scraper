from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from scraper import search_ebay, search_all_platforms

app = FastAPI(title="Price Comparison Bot")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ItemRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10

class PriceResult(BaseModel):
    title: str
    price: float
    price_text: str
    condition: str
    shipping: str
    url: str
    platform: str

class ComparisonResponse(BaseModel):
    query: str
    results: List[PriceResult]
    lowest_price: Optional[float]
    average_price: Optional[float]
    highest_price: Optional[float]
    total_results: int

@app.get("/")
def read_root():
    return {"message": "Price Comparison Bot API is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/compare_prices")
async def compare_prices(request: ItemRequest):
    """Compare prices for a product across platforms"""
    
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Search eBay
    try:
        results = await search_ebay(request.query, request.max_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")
    
    if not results:
        return ComparisonResponse(
            query=request.query,
            results=[],
            lowest_price=None,
            average_price=None,
            highest_price=None,
            total_results=0
        )
    
    # Convert to PriceResult objects
    price_results = []
    valid_prices = []
    
    for r in results:
        if r['price'] > 0:  # Only include items with valid prices
            price_results.append(PriceResult(**r))
            valid_prices.append(r['price'])
    
    # Calculate statistics
    lowest = min(valid_prices) if valid_prices else None
    highest = max(valid_prices) if valid_prices else None
    average = sum(valid_prices) / len(valid_prices) if valid_prices else None
    
    return ComparisonResponse(
        query=request.query,
        results=price_results,
        lowest_price=lowest,
        average_price=average,
        highest_price=highest,
        total_results=len(price_results)
    )

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify scraping works"""
    results = await search_ebay("iPhone 12", 3)
    return {"test_results": results}

@app.post("/compare_all_platforms")
async def compare_all_platforms(request: ItemRequest):
    """Compare prices across eBay, Mercari, and Facebook Marketplace"""
    
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Search all platforms
    try:
        platform_results = await search_all_platforms(request.query, request.max_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching platforms: {str(e)}")
    
    # Combine all results
    all_results = []
    for platform, results in platform_results.items():
        for item in results:
            if item.get('price', 0) > 0:
                all_results.append(PriceResult(**item))
    
    if not all_results:
        return ComparisonResponse(
            query=request.query,
            results=[],
            lowest_price=None,
            average_price=None,
            highest_price=None,
            total_results=0
        )
    
    # Sort by price
    all_results.sort(key=lambda x: x.price)
    
    # Calculate statistics
    prices = [r.price for r in all_results]
    
    # Group by platform for summary
    platform_summary = {}
    for result in all_results:
        if result.platform not in platform_summary:
            platform_summary[result.platform] = {
                'count': 0,
                'avg_price': 0,
                'prices': []
            }
        platform_summary[result.platform]['count'] += 1
        platform_summary[result.platform]['prices'].append(result.price)
    
    # Calculate platform averages
    for platform, data in platform_summary.items():
        if data['prices']:
            data['avg_price'] = sum(data['prices']) / len(data['prices'])
    
    return {
        "query": request.query,
        "results": all_results,
        "lowest_price": min(prices),
        "average_price": sum(prices) / len(prices),
        "highest_price": max(prices),
        "total_results": len(all_results),
        "platform_summary": platform_summary
    }

@app.post("/compare_prices_mock")
async def compare_prices_mock(request: ItemRequest):
    """Mock endpoint that always returns data for testing"""
    
    # Generate mock results based on the query
    mock_results = []
    base_price = 100.0
    
    for i in range(request.max_results):
        price = base_price + (i * 10) - (i * 3.5)
        mock_results.append(PriceResult(
            title=f"{request.query} - Option {i+1}",
            price=price,
            price_text=f"${price:.2f}",
            condition="New" if i % 2 == 0 else "Used",
            shipping="Free shipping" if i % 3 == 0 else f"${5 + i:.2f} shipping",
            url=f"https://example.com/item{i+1}",
            platform="eBay"
        ))
    
    prices = [r.price for r in mock_results]
    
    return ComparisonResponse(
        query=request.query,
        results=mock_results,
        lowest_price=min(prices),
        average_price=sum(prices) / len(prices),
        highest_price=max(prices),
        total_results=len(mock_results)
    )

@app.get("/test_ebay_raw")
async def test_ebay_raw():
    """Test eBay scraping and show raw results"""
    from scraper import search_ebay
    
    results = await search_ebay("iPhone 12", 3)
    
    return {
        "count": len(results),
        "raw_results": results,
        "prices": [r.get('price', 'NO PRICE') for r in results]
    }

