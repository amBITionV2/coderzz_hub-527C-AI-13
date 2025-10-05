"""
Test script to evaluate chatbot performance with 10 different queries.
"""
import asyncio
import httpx
import time
from typing import List, Dict

# Test queries
TEST_QUERIES = [
    "show me active floats",
    "which floats have higher temperatures",
    "find floats in pacific ocean",
    "show me floats in indian ocean",
    "what floats are measuring salinity",
    "find inactive floats",
    "show me all floats",
    "which floats are in maintenance",
    "find floats with temperature above 20",
    "show me floats in atlantic ocean"
]

async def test_query(client: httpx.AsyncClient, query: str) -> Dict:
    """Test a single query and return results."""
    start_time = time.time()
    
    try:
        response = await client.post(
            "http://localhost:8000/api/v1/ai/query",
            json={"question": query},
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        
        elapsed = time.time() - start_time
        
        return {
            "query": query,
            "success": True,
            "float_count": data.get("data_summary", {}).get("float_count", 0),
            "processing_time": data.get("processing_time", 0),
            "total_time": elapsed,
            "status": data.get("parameters", {}).get("status"),
            "location": data.get("parameters", {}).get("location"),
            "variables": data.get("parameters", {}).get("variables", [])
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "total_time": elapsed
        }

async def run_tests():
    """Run all test queries."""
    print("=" * 80)
    print("FloatChat AI Chatbot Performance Test")
    print("=" * 80)
    print(f"\nTesting {len(TEST_QUERIES)} queries...\n")
    
    async with httpx.AsyncClient() as client:
        results = []
        
        for i, query in enumerate(TEST_QUERIES, 1):
            print(f"[{i}/{len(TEST_QUERIES)}] Testing: {query}")
            result = await test_query(client, query)
            results.append(result)
            
            if result["success"]:
                print(f"  [OK] Found {result['float_count']} floats")
                print(f"  [TIME] Processing: {result['processing_time']:.2f}s | Total: {result['total_time']:.2f}s")
                if result.get("status"):
                    print(f"  [STATUS] {result['status']}")
                if result.get("location"):
                    print(f"  [LOCATION] {result['location']}")
                if result.get("variables"):
                    print(f"  [VARIABLES] {', '.join(result['variables'])}")
            else:
                print(f"  [ERROR] {result['error']}")
                print(f"  [TIME] Total: {result['total_time']:.2f}s")
            print()
        
        # Summary statistics
        print("=" * 80)
        print("Summary Statistics")
        print("=" * 80)
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        print(f"\nTotal queries: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            avg_processing = sum(r["processing_time"] for r in successful) / len(successful)
            avg_total = sum(r["total_time"] for r in successful) / len(successful)
            min_time = min(r["total_time"] for r in successful)
            max_time = max(r["total_time"] for r in successful)
            
            print(f"\nTiming Statistics:")
            print(f"  Average processing time: {avg_processing:.2f}s")
            print(f"  Average total time: {avg_total:.2f}s")
            print(f"  Fastest query: {min_time:.2f}s")
            print(f"  Slowest query: {max_time:.2f}s")
            
            # Float count statistics
            total_floats_found = sum(r["float_count"] for r in successful)
            avg_floats = total_floats_found / len(successful) if successful else 0
            
            print(f"\nResult Statistics:")
            print(f"  Total floats found: {total_floats_found}")
            print(f"  Average floats per query: {avg_floats:.1f}")
            
            # Parameter extraction success
            with_status = sum(1 for r in successful if r.get("status"))
            with_location = sum(1 for r in successful if r.get("location"))
            with_variables = sum(1 for r in successful if r.get("variables"))
            
            print(f"\nParameter Extraction:")
            print(f"  Queries with status filter: {with_status}/{len(successful)}")
            print(f"  Queries with location filter: {with_location}/{len(successful)}")
            print(f"  Queries with variable filter: {with_variables}/{len(successful)}")
        
        print("\n" + "=" * 80)
        print("Test Complete!")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_tests())
