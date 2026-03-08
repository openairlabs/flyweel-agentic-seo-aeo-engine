#!/usr/bin/env python3
"""Quick test to debug the issue"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

sys.path.insert(0, str(Path(__file__).parent))
from core.research import WebResearcher

async def test():
    async with WebResearcher() as web:
        try:
            result = await web.analyze_serp("test keyword")
            print(f"Result type: {type(result)}")
            print(f"Keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            print(f"Search results: {result.get('search_results', 'Missing')}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test())