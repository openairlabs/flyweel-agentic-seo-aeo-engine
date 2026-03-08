#!/usr/bin/env python3
"""Test full generation with all styles"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

sys.path.insert(0, str(Path(__file__).parent))
from core.generator import ContentGenerator

async def test_all_styles():
    """Test each content style"""
    generator = ContentGenerator()
    
    styles = ['standard', 'comparison', 'guide', 'research', 'news', 'category']
    test_keywords = {
        'standard': 'CRM integration',
        'comparison': 'HubSpot vs Salesforce',
        'guide': 'how to track ad spend',
        'research': 'marketing automation trends',
        'news': 'AI in advertising 2024',
        'category': 'best lead attribution tools'
    }
    
    for style in styles:
        keyword = test_keywords.get(style, 'marketing automation')
        print(f"\n{'='*60}")
        print(f"Testing {style.upper()} style with keyword: {keyword}")
        print('='*60)
        
        try:
            result = await generator.generate(keyword, style)
            
            if result['success']:
                print(f"✅ Success!")
                print(f"   Title: {result['title']}")
                print(f"   Words: {result['metrics']['word_count']}")
                print(f"   H2 Sections: {result['metrics']['h2_sections']}")
                print(f"   Time: {result['metrics']['generation_time']:.1f}s")
                
                # Save sample
                output_dir = Path('test_output')
                output_dir.mkdir(exist_ok=True)
                
                filename = f"test_{style}_{result['slug']}.mdx"
                filepath = output_dir / filename
                
                with open(filepath, 'w') as f:
                    f.write(result['content'])
                print(f"   Saved to: {filepath}")
                
                # Show content preview
                # Skip frontmatter and show actual content
                content_lines = result['content'].split('\n')
                content_start = 0
                for i, line in enumerate(content_lines):
                    if line.strip() == '---' and i > 0:  # End of frontmatter
                        content_start = i + 1
                        break
                
                preview = '\n'.join(content_lines[content_start:content_start+10])
                print(f"\n   Preview:\n   {preview}\n")
                
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Small delay between tests
        await asyncio.sleep(2)

async def main():
    print("🧪 Testing V2 Content Generation - All Styles\n")
    
    # Check API keys
    api_status = {
        'PERPLEXITY_API_KEY': '✅' if os.getenv('PERPLEXITY_API_KEY') else '❌',
        'GROQ_API_KEY': '✅' if os.getenv('GROQ_API_KEY') else '❌',
        'GOOGLE_API_KEY': '✅' if os.getenv('GOOGLE_API_KEY') else '❌',
    }
    
    print("API Status:")
    for key, status in api_status.items():
        print(f"  {status} {key}")
    
    print("\nNote: Missing APIs will use fallback data\n")
    
    # Ask which test to run
    print("Choose test:")
    print("1. Test single style")
    print("2. Test all styles")
    print("3. Quick test (standard style only)")
    
    choice = input("\nChoice (1-3): ").strip()
    
    if choice == '1':
        style = input("Style (standard/comparison/guide/research/news/category): ").strip()
        keyword = input("Keyword: ").strip()
        
        generator = ContentGenerator()
        result = await generator.generate(keyword, style)
        
        if result['success']:
            print(f"\n✅ Generated successfully!")
            print(f"Title: {result['title']}")
            print(f"Words: {result['metrics']['word_count']}")
            
            # Save
            output_dir = Path('test_output')
            output_dir.mkdir(exist_ok=True)
            filepath = output_dir / f"{result['slug']}.mdx"
            with open(filepath, 'w') as f:
                f.write(result['content'])
            print(f"Saved to: {filepath}")
    
    elif choice == '2':
        await test_all_styles()
    
    else:
        # Quick test
        generator = ContentGenerator()
        result = await generator.generate("marketing automation", "standard")
        print(f"\n{'✅ Success' if result['success'] else '❌ Failed'}")
        print(f"Generated {result['metrics']['word_count']} words in {result['metrics']['generation_time']:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())