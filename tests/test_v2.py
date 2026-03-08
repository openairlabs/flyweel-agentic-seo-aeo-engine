#!/usr/bin/env python3
"""Test V2 - Quick verification that it actually works"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

sys.path.insert(0, str(Path(__file__).parent))
from core.ai_router import SmartAIRouter
from core.research import WebResearcher, CommunityResearcher
from core.site_extractor import SiteContextExtractor

async def test_components():
    """Test each component individually"""
    print("🧪 Testing V2 Components...\n")
    
    # Test AI Router
    print("1️⃣ Testing AI Router...")
    try:
        async with SmartAIRouter() as ai:
            result = await ai.research("What is Brand Methodology?")
            print(f"   ✅ Perplexity research: {len(result.get('choices', [{}])[0].get('message', {}).get('content', ''))} chars")
    except Exception as e:
        print(f"   ❌ AI Router failed: {e}")
    
    # Test Web Researcher  
    print("\n2️⃣ Testing Web Researcher...")
    try:
        async with WebResearcher() as web:
            serp = await web.analyze_serp("CRM integration")
            print(f"   ✅ SERP analysis: {len(serp.get('search_results', []))} results, {len(serp.get('paa_questions', []))} PAA")
            if serp.get('gsc_data'):
                print(f"   ✅ GSC data: {serp['gsc_data'].get('impressions', 0)} impressions")
    except Exception as e:
        print(f"   ❌ Web Researcher failed: {e}")
    
    # Test Community Researcher
    print("\n3️⃣ Testing Community Researcher...")
    try:
        async with CommunityResearcher() as community:
            reddit = await community.mine_reddit("marketing automation")
            print(f"   ✅ Reddit mining: {len(reddit.get('insights', []))} insights, {len(reddit.get('questions', []))} questions")
    except Exception as e:
        print(f"   ❌ Community Researcher failed: {e}")
    
    # Test Site Extractor
    print("\n4️⃣ Testing Site Extractor...")
    try:
        extractor = SiteContextExtractor()
        context = await extractor.get_context()
        if 'error' not in context:
            print(f"   ✅ Site context: {len(context.get('features', []))} features, {len(context.get('integrations', []))} integrations")
        else:
            print(f"   ⚠️  Site extraction skipped: {context['error']}")
    except Exception as e:
        print(f"   ❌ Site Extractor failed: {e}")
    
    print("\n✅ Component testing complete!")

async def test_generation():
    """Test full generation"""
    print("\n🚀 Testing Full Generation...\n")
    
    from core.generator import ContentGenerator
    
    generator = ContentGenerator()
    result = await generator.generate("lead attribution software", "standard")
    
    if result['success']:
        print(f"""
✅ GENERATION SUCCESSFUL
━━━━━━━━━━━━━━━━━━━━━
Title: {result['title']}
Words: {result['metrics']['word_count']}
Time: {result['metrics']['generation_time']:.1f}s
━━━━━━━━━━━━━━━━━━━━━
        """)
    else:
        print(f"❌ Generation failed: {result.get('error')}")

async def main():
    # Run tests
    await test_components()
    
    # Ask if user wants to test full generation
    response = input("\n💡 Test full generation? (y/n): ")
    if response.lower() == 'y':
        await test_generation()

if __name__ == "__main__":
    asyncio.run(main())