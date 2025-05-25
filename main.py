from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
from scraper import search_all_platforms, search_ebay, search_facebook

app = FastAPI(title="Price Comparison API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ItemRequest(BaseModel):
    query: str
    max_results: int = 5
    city: str = "San Francisco"
    state: str = "CA"

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5

class FacebookSearchRequest(BaseModel):
    query: str
    max_results: int = 5
    city: str = "San Francisco"
    state: str = "CA"

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
async def root():
    return {
        "message": "Price Comparison API",
        "endpoints": {
            "/compare_all_platforms": "POST - Compare prices across eBay and Facebook Marketplace",
            "/search/ebay": "POST - Search eBay only",
            "/search/facebook": "POST - Search Facebook Marketplace only",
            "/test_ebay_raw": "GET - Test eBay scraping"
        }
    }

@app.post("/compare_all_platforms")
async def compare_all_platforms(request: ItemRequest):
    """Compare prices across eBay and Facebook Marketplace"""
    
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Search all platforms
    try:
        platform_results = await search_all_platforms(
            request.query, 
            request.max_results,
            request.city,
            request.state
        )
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
        "location": f"{request.city}, {request.state}",
        "results": all_results,
        "lowest_price": min(prices),
        "average_price": sum(prices) / len(prices),
        "highest_price": max(prices),
        "total_results": len(all_results),
        "platform_summary": platform_summary
    }

@app.post("/search/ebay")
async def search_ebay_endpoint(request: SearchRequest):
    """Search only eBay"""
    results = await search_ebay(request.query, request.max_results)
    return {"query": request.query, "results": results}

@app.post("/search/facebook")
async def search_facebook_endpoint(request: FacebookSearchRequest):
    """Search only Facebook Marketplace"""
    results = await search_facebook(
        request.query, 
        request.max_results,
        request.city,
        request.state
    )
    return {
        "query": request.query,
        "location": f"{request.city}, {request.state}",
        "results": results
    }

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
