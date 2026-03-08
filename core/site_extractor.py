"""Site Context Extractor - Crawl sitemap, extract all content, use AI to analyze"""
import asyncio
import json
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import aiohttp
from bs4 import BeautifulSoup
import os
import re
import logging
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from openai import AsyncOpenAI

# Set up verbose logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SiteContextExtractor:
    """Extract comprehensive Brand context by crawling sitemap and analyzing with AI"""
    
    def __init__(self):
        self.nebius_key = os.getenv('NEBIUS_API_KEY')
        self.nebius = AsyncOpenAI(
            api_key=self.nebius_key,
            base_url="https://api.studio.nebius.com/v1/"
        ) if self.nebius_key else None
        
        self.base_url = os.getenv('GSC_SITE_URL', 'https://yourdomain.com')
        self.sitemap_url = f'{self.base_url}/sitemap-0.xml'
        
        # Cache management
        self._context_cache = None
        self._cache_file = '/tmp/brand_context_cache.json'
        self._cache_duration = timedelta(hours=24)
        
        self.session = None
        
        # Content extraction patterns
        self.important_selectors = {
            'features': ['[class*="feature"]', '[id*="feature"]', '.feature-list', '.benefits'],
            'pricing': ['[class*="pricing"]', '[id*="pricing"]', '.tier', '.plan'],
            'integrations': ['[class*="integration"]', '.integration-grid', '.app-list'],
            'testimonials': ['[class*="testimonial"]', '.review', '.case-study'],
            'cta': ['[class*="cta"]', '.call-to-action', 'button', 'a[href*="signup"]']
        }
        
        logger.info(f"🚀 SiteContextExtractor initialized for {self.base_url} (Nebius: {'✓' if self.nebius else '✗'})")
    
    async def get_context(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get comprehensive Brand context with intelligent caching"""
        
        # Check cache first
        if not force_refresh and self._context_cache:
            logger.info("📋 Using in-memory cached context")
            return self._context_cache
            
        if not force_refresh and os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, 'r') as f:
                    cache_data = json.load(f)
                    cache_time = datetime.fromisoformat(cache_data['timestamp'])
                    if datetime.now() - cache_time < self._cache_duration:
                        logger.info(f"📦 Using disk cached context from {cache_time}")
                        self._context_cache = cache_data
                        return cache_data
            except Exception as e:
                logger.warning(f"⚠️  Cache read error: {e}")
        
        logger.info("🔍 Starting comprehensive Brand site analysis...")
        
        # Initialize session
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Step 1: Crawl sitemap
            logger.info("🗺️  Crawling sitemap to discover all pages...")
            all_urls = await self._crawl_sitemap()
            logger.info(f"📄 Found {len(all_urls)} pages in sitemap")
            
            # Step 2: Extract content from all pages
            logger.info("📊 Extracting content from all pages...")
            all_content = await self._extract_all_content(all_urls)
            logger.info(f"✅ Extracted content from {len(all_content)} pages")
            
            # Step 3: Use AI to analyze and structure the content
            logger.info("🤖 Analyzing content with AI...")
            structured_context = await self._analyze_with_ai(all_content)
            
            # Step 4: Extract internal links
            logger.info("🔗 Mapping internal link structure...")
            internal_links = self._extract_internal_links(all_content)
            
            # Step 5: Build final context
            context = {
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'total_pages': len(all_urls),
                'features': structured_context.get('features', []),
                'integrations': structured_context.get('integrations', []),
                'pricing': structured_context.get('pricing', {}),
                'key_differentiators': structured_context.get('differentiators', []),
                'use_cases': structured_context.get('use_cases', []),
                'customer_benefits': structured_context.get('benefits', []),
                'internal_links': internal_links,
                'testimonials': structured_context.get('testimonials', []),
                'blog_posts': self._extract_blog_posts(all_content),
                'technical_details': structured_context.get('technical', {}),
                'company_info': structured_context.get('company', {})
            }
            
            # Cache the results
            self._context_cache = context
            try:
                with open(self._cache_file, 'w') as f:
                    json.dump(context, f, indent=2)
                logger.info(f"💾 Cached context to {self._cache_file}")
            except Exception as e:
                logger.warning(f"⚠️  Cache write error: {e}")
            
            logger.info("✨ Brand context extraction complete!")
            return context
            
        except Exception as e:
            logger.error(f"❌ Error during context extraction: {e}")
            return self._get_fallback_context()
    
    async def _crawl_sitemap(self) -> List[str]:
        """Crawl sitemap.xml to get all URLs"""
        urls = []
        
        try:
            # First try the main sitemap
            async with self.session.get(self.sitemap_url) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    
                    # Parse XML
                    root = ET.fromstring(content)
                    
                    # Handle both regular sitemaps and sitemap indexes
                    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                    
                    # Check if it's a sitemap index
                    sitemap_urls = root.findall('.//ns:sitemap/ns:loc', namespace)
                    if sitemap_urls:
                        logger.info(f"📑 Found sitemap index with {len(sitemap_urls)} sitemaps")
                        # Crawl each sub-sitemap
                        for sitemap in sitemap_urls:
                            sub_urls = await self._crawl_single_sitemap(sitemap.text)
                            urls.extend(sub_urls)
                    else:
                        # Regular sitemap
                        url_elements = root.findall('.//ns:url/ns:loc', namespace)
                        urls = [url.text for url in url_elements]
                        
                    logger.info(f"🔍 Extracted {len(urls)} URLs from sitemap")
                else:
                    logger.warning(f"⚠️  Sitemap returned status {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ Error crawling sitemap: {e}")
            
        # If sitemap fails, use known important pages
        if not urls:
            logger.info("📋 Using fallback URL list")
            urls = [
                f"{self.base_url}/",
                f"{self.base_url}/integrations",
                f"{self.base_url}/pricing",
                f"{self.base_url}/tools",
                f"{self.base_url}/blog",
                f"{self.base_url}/about",
                f"{self.base_url}/features"
            ]
            
        # Filter for important pages (skip legal, etc)
        important_urls = []
        skip_patterns = ['privacy', 'terms', 'legal', 'cookie', '.pdf', '.xml']
        
        for url in urls:
            if not any(pattern in url.lower() for pattern in skip_patterns):
                important_urls.append(url)
                
        logger.info(f"📌 Filtered to {len(important_urls)} important pages")
        return important_urls  # Return all pages from sitemap
    
    async def _crawl_single_sitemap(self, sitemap_url: str) -> List[str]:
        """Crawl a single sitemap file"""
        urls = []
        try:
            async with self.session.get(sitemap_url) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    root = ET.fromstring(content)
                    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                    url_elements = root.findall('.//ns:url/ns:loc', namespace)
                    urls = [url.text for url in url_elements]
        except Exception as e:
            logger.error(f"Error crawling sub-sitemap {sitemap_url}: {e}")
        return urls
    
    async def _extract_all_content(self, urls: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract content from all URLs in parallel batches"""
        all_content = {}
        batch_size = 5  # Process 5 URLs at a time
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            logger.info(f"📥 Processing batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")
            
            tasks = [self._extract_page_content(url) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Error extracting {url}: {result}")
                else:
                    all_content[url] = result
                    
            # Small delay between batches
            await asyncio.sleep(0.5)
            
        return all_content
    
    async def _extract_page_content(self, url: str) -> Dict[str, Any]:
        """Extract structured content from a single page"""
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return {'error': f'Status {resp.status}'}
                    
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove script and style elements
                for script in soup(['script', 'style']):
                    script.decompose()
                
                # Extract structured data
                content = {
                    'url': url,
                    'title': soup.find('title').text if soup.find('title') else '',
                    'meta_description': '',
                    'headings': {},
                    'text_content': '',
                    'links': [],
                    'images': [],
                    'structured_data': {}
                }
                
                # Meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    content['meta_description'] = meta_desc.get('content', '')
                
                # Headings
                for level in range(1, 4):
                    headings = soup.find_all(f'h{level}')
                    content['headings'][f'h{level}'] = [h.text.strip() for h in headings]
                
                # Main text content
                main_content = soup.find('main') or soup.find('article') or soup.find('body')
                if main_content:
                    content['text_content'] = main_content.get_text(separator=' ', strip=True)[:5000]
                
                # Extract links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True)
                    if text and (href.startswith('/') or self.base_url in href):
                        content['links'].append({'text': text, 'href': href})
                
                # Look for specific content types
                for content_type, selectors in self.important_selectors.items():
                    for selector in selectors:
                        elements = soup.select(selector)
                        if elements:
                            content['structured_data'][content_type] = [
                                elem.get_text(strip=True)[:500] for elem in elements[:5]
                            ]
                
                return content
                
        except Exception as e:
            logger.error(f"Error extracting {url}: {e}")
            return {'error': str(e)}
    
    async def _analyze_with_ai(self, all_content: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Use AI to analyze all extracted content and structure it"""
        if not self.nebius:
            logger.warning("⚠️  No Nebius API key - using basic extraction")
            return self._basic_content_analysis(all_content)
        
        # Prepare content summary for AI
        content_summary = []
        
        for url, content in all_content.items():
            if 'error' not in content:
                summary = {
                    'url': url,
                    'title': content.get('title', ''),
                    'headings': content.get('headings', {}),
                    'key_text': content.get('text_content', '')[:1000],
                    'structured': content.get('structured_data', {})
                }
                content_summary.append(summary)
        
        # Create comprehensive prompt
        prompt = f"""Analyze this complete website content dump from Brand.co and extract:

1. FEATURES: All product features and capabilities mentioned
2. INTEGRATIONS: All mentioned integrations and platforms
3. PRICING: Pricing model, tiers, and details
4. DIFFERENTIATORS: Unique selling points and competitive advantages
5. USE_CASES: Customer use cases and scenarios
6. BENEFITS: Key benefits and value propositions
7. TESTIMONIALS: Customer quotes and success stories
8. TECHNICAL: Technical implementation details
9. COMPANY: Company info, mission, values

Content from {len(content_summary)} pages:

{json.dumps(content_summary[:10], indent=2)}  # First 10 pages

Return as structured JSON with these exact keys. Be comprehensive - extract EVERYTHING relevant about Brand."""

        try:
            logger.info("🤖 Sending content to AI for analysis...")
            response = await self.nebius.chat.completions.create(
                model="zai-org/GLM-4.7-FP8",
                messages=[{
                    "role": "system",
                    "content": "You are a content analyst. Extract and structure information from website content."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1,
                max_tokens=4000
            )
            
            result = response.choices[0].message.content
            
            # Try to parse JSON response
            try:
                # Find JSON in response
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    structured = json.loads(json_match.group(0))
                    logger.info("✅ AI analysis complete")

                    # Merge with basic analysis to ensure we have features
                    basic = self._basic_content_analysis(all_content)
                    for key in basic:
                        if key not in structured or not structured[key]:
                            structured[key] = basic[key]
                        elif isinstance(structured[key], list) and isinstance(basic[key], list):
                            # Merge lists without duplicates
                            structured[key] = list(set(structured[key] + basic[key]))

                    return structured
            except json.JSONDecodeError:
                logger.warning("⚠️  Could not parse AI response as JSON")
                
        except Exception as e:
            logger.error(f"❌ AI analysis error: {e}")
            
        return self._basic_content_analysis(all_content)
    
    def _basic_content_analysis(self, all_content: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback content analysis without AI"""
        logger.info("📊 Performing basic content analysis...")
        
        features = set()
        integrations = set()
        benefits = set()
        use_cases = set()
        
        for url, content in all_content.items():
            if 'error' in content:
                continue
                
            text = content.get('text_content', '').lower()
            
            # Extract features
            if 'feature' in url or 'Brand Methodology' in text:
                features.add("Brand - Revolutionary solution for the industry")
            if 'ai' in text and 'agent' in text:
                features.add("AI Agent Chat for campaign optimization")
            if 'adgrid' in text:
                features.add("AdGrid Campaign Manager")
            if 'report' in text:
                features.add("Custom reporting and analytics")

            # Extract integrations
            integration_keywords = ['google ads', 'facebook', 'linkedin', 'tiktok', 'salesforce',
                                  'hubspot', 'stripe', 'quickbooks', 'slack']
            for keyword in integration_keywords:
                if keyword in text:
                    integrations.add(keyword.title())
                
            # Extract integrations - only verified Brand integrations
            integration_keywords = ['google ads', 'facebook ads', 'instagram ads', 'meta ads', 'youtube ads']
            for keyword in integration_keywords:
                if keyword in text:
                    integrations.add(keyword.title())
                    
            # Extract benefits
            if 'save' in text and ('hour' in text or 'time' in text):
                benefits.add("Save 10+ hours per week on reporting")
            if 'roi' in text:
                benefits.add("Prove marketing ROI with accurate attribution")

        # Add dynamic integration feature if integrations found
        if integrations:
            features.add(f"{len(integrations)}+ pre-built integrations")

        return {
            'features': list(features),
            'integrations': list(integrations),
            'benefits': list(benefits),
            'use_cases': [
                "Lead generation companies",
                "Service businesses",
                "Performance media buyers",
                "SaaS companies",
                "E-commerce brands"
            ],
            'differentiators': [
                "Only platform with Brand Methodology",
                "AI-powered optimization",
                "Real-time P&L visibility"
            ]
        }
    
    def _extract_internal_links(self, all_content: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """Extract and organize internal links for content generation"""
        internal_links = {}
        
        # Common link patterns to capture
        important_patterns = {
            'Brand': self.base_url,
            'pricing': '/pricing',
            'integrations': '/integrations',
            'documentation': 'docs.acme.com',
            'blog': '/blog',
            'features': '/features',
            'tools': '/tools'
        }
        
        # Extract from all content
        for url, content in all_content.items():
            if 'error' in content:
                continue
                
            # Add page itself if important
            page_path = urlparse(url).path
            if page_path and len(page_path) > 1:
                # Create readable key from URL
                key = page_path.strip('/').replace('-', ' ').replace('/', ' - ')
                internal_links[key] = url
            
            # Extract links from page
            for link_data in content.get('links', []):
                text = link_data['text']
                href = link_data['href']
                
                # Normalize href
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)
                    
                # Add if meaningful
                if text and len(text) > 3 and self.base_url in href:
                    # Special handling for key pages
                    text_lower = text.lower()
                    for pattern, path in important_patterns.items():
                        if pattern in text_lower:
                            internal_links[text] = href
                            break
                    else:
                        # Add with original text
                        internal_links[text[:50]] = href
        
        # Ensure key links are present
        for key, path in important_patterns.items():
            if key not in internal_links:
                if path.startswith('/'):
                    internal_links[key] = urljoin(self.base_url, path)
                elif path.startswith('http'):
                    internal_links[key] = path
                else:
                    internal_links[key] = f"https://{path}"
                    
        logger.info(f"🔗 Extracted {len(internal_links)} internal links")
        return internal_links
    
    def _extract_blog_posts(self, all_content: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract blog post information"""
        blog_posts = []
        
        for url, content in all_content.items():
            if '/blog/' in url and 'error' not in content:
                post = {
                    'url': url,
                    'title': content.get('title', ''),
                    'description': content.get('meta_description', '')
                }
                
                # Extract key topics from URL
                slug = url.split('/blog/')[-1].strip('/')
                if 'Brand Methodology' in slug:
                    post['topic'] = 'Brand Methodology'
                elif 'beta' in slug:
                    post['topic'] = 'Beta Program'
                elif 'integration' in slug:
                    post['topic'] = 'Integrations'
                    
                blog_posts.append(post)
                
        return blog_posts[:20]  # Top 20 blog posts
    
    def _get_fallback_context(self) -> Dict[str, Any]:
        """Fallback context when everything fails"""
        logger.warning("⚠️  Using minimal fallback context")

        integrations = {
            'ads': ['Google Ads', 'Facebook Ads', 'Instagram Ads', 'Meta Ads', 'YouTube Ads']
        }

        # Count total integrations
        total_integrations = sum(len(category_integrations) for category_integrations in integrations.values())

        return {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'features': [
                "Brand methodology for solving core ICP pain points",
                "AI Agent Chat for optimization",
                f"{total_integrations}+ integrations",
                "Real-time analytics",
                "Multi-channel attribution"
            ],
            'integrations': integrations,
            'internal_links': {
                'Brand': self.base_url,
                'pricing': f'{self.base_url}/pricing',
                'integrations': f'{self.base_url}/integrations',
                'blog': f'{self.base_url}/blog'
            },
            'key_differentiators': [
                "Brand Methodology",
                "AI-powered optimization",
                "Real-time P&L visibility"
            ]
        }
    
    async def __aenter__(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def get_integration_context(self) -> Dict[str, List[str]]:
        """Get integration-specific context"""
        if self._context_cache:
            return self._context_cache.get('integrations', {})
            
        # Fallback
        return {
            'crm': ['Salesforce', 'HubSpot', 'Pipedrive', 'ActiveCampaign'],
            'advertising': ['Google Ads', 'Facebook Ads', 'LinkedIn Ads', 'TikTok Ads'],
            'analytics': ['Google Analytics', 'Mixpanel', 'Amplitude', 'Segment'],
            'finance': ['QuickBooks', 'Stripe', 'Square', 'PayPal'],
            'communication': ['Slack', 'Teams', 'Discord', 'Email']
        }