"""Repo Context Extractor - Parse astro-site repo for brand context

Replaces live site scraping with local repo parsing for:
- Faster context extraction (no network calls)
- Access to unpublished content
- Accurate internal links from actual content
"""
import json
import re
import hashlib
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RepoContextExtractor:
    """Extract brand context from astro-site repository content

    Produces output compatible with SiteContextExtractor for drop-in replacement.
    """

    # Default paths
    ASTRO_REPO_PATH = Path(os.getenv("ASTRO_SITE_PATH", "../my-astro-site")) / "src"
    CACHE_PATH = Path("/tmp/brand_repo_context_cache.json")

    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize with optional custom repo path

        Args:
            repo_path: Path to astro-site/apps/web/src (defaults to standard location)
        """
        self.repo_path = repo_path or self.ASTRO_REPO_PATH
        self.content_path = self.repo_path / "content"

        # Content collection directories
        self.blog_path = self.content_path / "blog"
        self.integrations_path = self.content_path / "integrations"
        self.authors_path = self.content_path / "authors"
        self.updates_path = self.content_path / "updates"
        self.tools_path = self.content_path / "tools"

        # Track stats
        self._stats = {
            'blog_posts': 0,
            'integrations': 0,
            'authors': 0,
            'internal_links': 0,
        }

        logger.debug(f"🗂️  RepoContextExtractor initialized for {self.repo_path}")

    def extract_context(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Extract comprehensive brand context from repo

        Args:
            force_refresh: Bypass cache and re-extract

        Returns:
            Dict compatible with SiteContextExtractor output format
        """
        # Check cache validity
        if not force_refresh and self._is_cache_valid():
            logger.debug("📦 Using cached repo context")
            return self._load_cache()

        logger.debug(f"🔍 Extracting context from {self.repo_path}")

        # Verify repo exists
        if not self.content_path.exists():
            logger.error(f"❌ Content path not found: {self.content_path}")
            return self._get_fallback_context()

        # Extract all content collections
        blog_posts = self._extract_blog_posts()
        integrations = self._extract_integrations()
        authors = self._extract_authors()

        # Build derived data
        internal_links = self._build_internal_links_map(blog_posts, integrations)
        features = self._extract_features_from_integrations(integrations)
        brand_patterns = self._extract_brand_patterns(blog_posts)

        # Build context in SiteContextExtractor-compatible format
        context = {
            'timestamp': datetime.now().isoformat(),
            'source': 'astro-site-repo',
            'base_url': os.getenv('GSC_SITE_URL', 'https://yourdomain.com'),
            'total_pages': len(blog_posts) + sum(len(cats) for cats in integrations.values()),

            # Core content
            'features': features,
            'integrations': self._flatten_integrations(integrations),
            'pricing': self._get_pricing_info(),
            'key_differentiators': self._get_differentiators(),
            'use_cases': self._get_use_cases(),
            'customer_benefits': self._get_benefits(),
            'internal_links': internal_links,
            'testimonials': [],  # Would need testimonials content collection
            'blog_posts': blog_posts,
            'technical_details': {},
            'company_info': self._get_company_info(authors),

            # Additional repo-specific data
            'authors': authors,
            'integrations_by_category': integrations,
            'brand_patterns': brand_patterns,

            # Cache metadata
            '_file_hash': self._compute_content_hash(),
            '_stats': self._stats,
        }

        # Update stats
        self._stats['blog_posts'] = len(blog_posts)
        self._stats['integrations'] = sum(len(cats) for cats in integrations.values())
        self._stats['internal_links'] = len(internal_links)

        # Save cache
        self._save_cache(context)

        logger.debug(f"✨ Context extraction complete: {self._stats['blog_posts']} posts, "
                   f"{self._stats['integrations']} integrations, {self._stats['internal_links']} links")

        return context

    def _extract_blog_posts(self) -> List[Dict[str, Any]]:
        """Extract blog post metadata and content summaries"""
        posts = []

        if not self.blog_path.exists():
            logger.warning(f"⚠️  Blog path not found: {self.blog_path}")
            return posts

        for mdx_file in self.blog_path.glob("*.mdx"):
            # Skip templates and drafts starting with _
            if mdx_file.name.startswith("_"):
                continue

            try:
                content = mdx_file.read_text(encoding='utf-8')
                frontmatter = self._parse_frontmatter(content)

                # Skip drafts in production context
                if frontmatter.get('draft', False):
                    continue

                post = {
                    'slug': mdx_file.stem,
                    'title': frontmatter.get('title', ''),
                    'description': frontmatter.get('description', ''),
                    'url': f"https://acme.com/blog/{mdx_file.stem}",
                    'tags': frontmatter.get('tags', []),
                    'category': frontmatter.get('category', ''),
                    'categories': frontmatter.get('categories', []),
                    'publish_date': str(frontmatter.get('publishDate', '')),
                    'author': frontmatter.get('author', 'Brand Team'),
                    'internal_links_used': self._extract_internal_links_from_content(content),
                    'word_count': len(content.split()),
                }
                posts.append(post)

            except Exception as e:
                logger.warning(f"⚠️  Error parsing {mdx_file.name}: {e}")

        # Sort by publish date (newest first)
        posts.sort(key=lambda x: x.get('publish_date', ''), reverse=True)

        logger.debug(f"📝 Extracted {len(posts)} blog posts")
        return posts

    def _extract_integrations(self, live_only: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Extract integrations organized by category

        Args:
            live_only: If True, only include verified=true integrations (green dot).
                      These are integrations actually live in the Brand app.
        """
        integrations = {
            'crm': [],
            'advertising': [],
            'analytics': [],
            'finance': [],
            'distribution': [],
            'tracking': [],
            'communication': [],
            'developer': [],
            'productivity': [],
            'social': [],
            'other': [],
        }

        if not self.integrations_path.exists():
            logger.warning(f"⚠️  Integrations path not found: {self.integrations_path}")
            return integrations

        skipped_count = 0
        for mdx_file in self.integrations_path.glob("*.mdx"):
            if mdx_file.name.startswith("_"):
                continue

            try:
                content = mdx_file.read_text(encoding='utf-8')
                frontmatter = self._parse_frontmatter(content)

                # Filter by verified status (green dot = live in app)
                is_verified = frontmatter.get('verified', False)
                if live_only and not is_verified:
                    skipped_count += 1
                    continue  # Skip "coming soon" integrations

                integration = {
                    'name': frontmatter.get('name', mdx_file.stem.replace('-', ' ').title()),
                    'slug': mdx_file.stem,
                    'description': frontmatter.get('description', ''),
                    'url': f"https://acme.com/integrations/{mdx_file.stem}",
                    'capabilities': frontmatter.get('capabilities', []),
                    'tags': frontmatter.get('tags', []),
                    'icon': frontmatter.get('icon', ''),
                    'featured': frontmatter.get('featured', False),
                    'verified': is_verified,  # Include verified status
                }

                # Categorize
                category = frontmatter.get('category', 'other').lower()
                if category in integrations:
                    integrations[category].append(integration)
                else:
                    integrations['other'].append(integration)

            except Exception as e:
                logger.warning(f"⚠️  Error parsing {mdx_file.name}: {e}")

        total = sum(len(cats) for cats in integrations.values())
        if live_only and skipped_count > 0:
            logger.debug(f"🔌 Extracted {total} LIVE integrations (skipped {skipped_count} coming-soon)")
        else:
            logger.debug(f"🔌 Extracted {total} integrations across {len([c for c in integrations.values() if c])} categories")
        return integrations

    def _extract_authors(self) -> List[Dict[str, Any]]:
        """Extract author profiles for E-E-A-T signals"""
        authors = []

        if not self.authors_path.exists():
            logger.warning(f"⚠️  Authors path not found: {self.authors_path}")
            return authors

        for json_file in self.authors_path.glob("*.json"):
            try:
                author_data = json.loads(json_file.read_text(encoding='utf-8'))
                authors.append({
                    'id': json_file.stem,
                    'name': author_data.get('name', ''),
                    'role': author_data.get('role', ''),
                    'jobTitle': author_data.get('jobTitle', ''),
                    'expertise': author_data.get('expertise', []),
                    'bio': author_data.get('bio', ''),
                    'avatar': author_data.get('avatar', ''),
                    'social': author_data.get('social', {}),
                })
            except Exception as e:
                logger.warning(f"⚠️  Error parsing {json_file.name}: {e}")

        logger.debug(f"👤 Extracted {len(authors)} authors")
        self._stats['authors'] = len(authors)
        return authors

    def _build_internal_links_map(
        self,
        blog_posts: List[Dict],
        integrations: Dict[str, List[Dict]]
    ) -> Dict[str, str]:
        """Build comprehensive internal links map from all content"""
        links = {
            # Core pages (always available)
            'Brand': 'https://acme.com/',
            'pricing': 'https://acme.com/pricing',
            'integrations': 'https://acme.com/integrations',
            'blog': 'https://acme.com/blog',
            'tools': 'https://acme.com/tools',

            # Product pages
            'AI Agent': 'https://acme.com/ai-agents',
            'Brand AI Agent': 'https://acme.com/ai-agents',
            'Brand Methodology': 'https://acme.com/blog/introducing-brand-methodology',
            'AdGrid': 'https://acme.com/adgrid',
            'Brand AdGrid': 'https://acme.com/adgrid',

            # MCP product - critical for MCP-related content
            'MCP': 'https://acme.com/mcp',
            'Brand MCP': 'https://acme.com/mcp',
            'Model Context Protocol': 'https://acme.com/mcp',
        }

        # Add integration pages with multiple key variations
        for category, items in integrations.items():
            for integration in items:
                name = integration['name']
                slug = integration['slug']
                url = integration['url']

                # Add by exact name
                links[name] = url

                # Add common variations
                if 'Ads' in name:
                    # "Facebook Ads" -> also link "Facebook"
                    base_name = name.replace(' Ads', '')
                    if base_name not in links:
                        links[base_name] = url

        # Add blog post links by title keywords
        for post in blog_posts:
            title = post['title']
            slug = post['slug']
            url = post['url']

            # Add full title
            links[title] = url

            # Extract key phrases (2-3 words) for natural linking
            key_phrases = self._extract_linkable_phrases(title)
            for phrase in key_phrases[:2]:  # Limit to avoid over-linking
                if phrase not in links and len(phrase) >= 10:
                    links[phrase] = url

        logger.debug(f"🔗 Built {len(links)} internal links")
        return links

    def _extract_features_from_integrations(
        self,
        integrations: Dict[str, List[Dict]]
    ) -> List[str]:
        """Extract unique features/capabilities from all integrations"""
        features = set()

        # Known Brand-specific features
        core_features = [
            'Brand Methodology',
            'Real-time P&L visibility',
            'AdGrid Campaign Manager',
            'AI Agent Chat',
            'Pre-built integrations',
            'Revenue attribution',
            'Deal stage sync',
            'Audience enrichment',
            'Write-back capability',
        ]
        features.update(core_features)

        # Extract capabilities from integrations
        for category, items in integrations.items():
            for integration in items:
                capabilities = integration.get('capabilities', [])
                features.update(capabilities)

        return list(features)[:30]  # Limit for context size

    def _extract_brand_patterns(self, blog_posts: List[Dict]) -> Dict[str, Any]:
        """Extract brand voice patterns from existing blog prose"""
        patterns = {
            'cta_patterns': [],
            'heading_styles': [],
            'common_phrases': [],
        }

        # Sample from recent posts
        for post in blog_posts[:5]:
            slug = post['slug']
            mdx_path = self.blog_path / f"{slug}.mdx"

            if not mdx_path.exists():
                continue

            try:
                content = mdx_path.read_text(encoding='utf-8')

                # Extract CTA link patterns
                cta_matches = re.findall(
                    r'\[([^\]]+)\]\(https://(?:www\.)?brand\.co[^\)]+\)',
                    content
                )
                patterns['cta_patterns'].extend(cta_matches[:3])

                # Extract H2 heading styles
                h2_matches = re.findall(r'^## (.+)$', content, re.MULTILINE)
                patterns['heading_styles'].extend(h2_matches[:5])

            except Exception:
                pass

        # Deduplicate
        patterns['cta_patterns'] = list(set(patterns['cta_patterns']))[:10]
        patterns['heading_styles'] = list(set(patterns['heading_styles']))[:15]

        return patterns

    def _extract_internal_links_from_content(self, content: str) -> List[str]:
        """Extract acme.com links used in content"""
        pattern = r'\[([^\]]+)\]\((https://(?:www\.)?brand\.co[^\)]+)\)'
        matches = re.findall(pattern, content)
        return [url for _, url in matches]

    def _extract_linkable_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text suitable for linking"""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was',
            'your', 'how', 'what', 'why', 'when', 'best', 'top', 'guide',
        }

        words = text.split()
        phrases = []

        # 2-3 word phrases
        for i in range(len(words) - 1):
            w1 = words[i].lower().strip('.,!?:')
            w2 = words[i + 1].lower().strip('.,!?:') if i + 1 < len(words) else ''

            if w1 not in stop_words and w2 not in stop_words:
                phrase = f"{words[i]} {words[i + 1]}"
                if len(phrase) >= 8:
                    phrases.append(phrase.strip('.,!?:'))

        return phrases

    def _flatten_integrations(self, integrations: Dict[str, List[Dict]]) -> List[str]:
        """Flatten integrations to simple list for compatibility"""
        flat = []
        for category, items in integrations.items():
            for item in items:
                flat.append(item['name'])
        return flat

    def _get_pricing_info(self) -> Dict[str, Any]:
        """Get pricing information (static for now)"""
        return {
            'model': 'subscription',
            'tiers': ['Starter', 'Growth', 'Scale'],
            'has_free_trial': True,
        }

    def _get_differentiators(self) -> List[str]:
        """Get key differentiators"""
        return [
            "Brand methodology for solving core ICP pain points",
            "Real-time P&L visibility across all ad channels",
            "AI-powered optimization recommendations",
            "Write-back capability to ad platforms via AdGrid",
            "Zero technical expertise required",
            "13+ pre-built integrations",
            "Two-way CRM sync for closed-loop attribution",
        ]

    def _get_use_cases(self) -> List[str]:
        """Get primary use cases"""
        return [
            "Lead generation companies",
            "Sales-led service companies",
            "Performance media buyers",
            "High-ticket service businesses",
            "Multi-channel advertisers",
            "Agencies managing client spend",
        ]

    def _get_benefits(self) -> List[str]:
        """Get customer benefits"""
        return [
            "Save 10+ hours per week on reporting",
            "Prove marketing ROI with accurate attribution",
            "Real-time profitability insights",
            "Automated data reconciliation",
            "Connect all data sources effortlessly",
            "Make data-driven decisions faster",
        ]

    def _get_company_info(self, authors: List[Dict]) -> Dict[str, Any]:
        """Get company information from authors"""
        return {
            'name': 'Brand',
            'url': os.getenv('GSC_SITE_URL', 'https://yourdomain.com'),
            'team': [a['name'] for a in authors],
        }

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from MDX content"""
        if not content.startswith('---'):
            return {}

        try:
            # Find frontmatter boundaries
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1].strip()
                return yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError as e:
            logger.warning(f"⚠️  YAML parse error: {e}")
        except Exception as e:
            logger.warning(f"⚠️  Frontmatter parse error: {e}")

        return {}

    def _compute_content_hash(self) -> str:
        """Compute hash of content files for cache invalidation"""
        hasher = hashlib.md5()

        # Include modification times of all content files
        for path in [self.blog_path, self.integrations_path, self.authors_path]:
            if not path.exists():
                continue
            for file in sorted(path.glob("*")):
                if file.is_file():
                    hasher.update(f"{file}:{file.stat().st_mtime}".encode())

        return hasher.hexdigest()

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid based on file changes"""
        if not self.CACHE_PATH.exists():
            return False

        try:
            cache = json.loads(self.CACHE_PATH.read_text(encoding='utf-8'))
            cached_hash = cache.get('_file_hash', '')
            current_hash = self._compute_content_hash()

            if cached_hash == current_hash:
                logger.debug("Cache hash matches - using cached context")
                return True
            else:
                logger.debug("📝 Content files changed - refreshing context")
                return False

        except Exception as e:
            logger.warning(f"⚠️  Cache validation error: {e}")
            return False

    def _load_cache(self) -> Dict[str, Any]:
        """Load cached context"""
        try:
            return json.loads(self.CACHE_PATH.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning(f"⚠️  Cache load error: {e}")
            return self._get_fallback_context()

    def _save_cache(self, context: Dict[str, Any]) -> None:
        """Save context to cache file"""
        try:
            self.CACHE_PATH.write_text(
                json.dumps(context, indent=2, default=str),
                encoding='utf-8'
            )
            logger.debug(f"💾 Cached context to {self.CACHE_PATH}")
        except Exception as e:
            logger.warning(f"⚠️  Cache save error: {e}")

    def _get_fallback_context(self) -> Dict[str, Any]:
        """Return minimal fallback context if extraction fails"""
        logger.warning("⚠️  Using fallback context")
        return {
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback',
            'base_url': os.getenv('GSC_SITE_URL', 'https://yourdomain.com'),
            'total_pages': 0,
            'features': self._get_differentiators(),
            'integrations': [],
            'pricing': self._get_pricing_info(),
            'key_differentiators': self._get_differentiators(),
            'use_cases': self._get_use_cases(),
            'customer_benefits': self._get_benefits(),
            'internal_links': {
                'Brand': 'https://acme.com/',
                'pricing': 'https://acme.com/pricing',
                'integrations': 'https://acme.com/integrations',
                'blog': 'https://acme.com/blog',
            },
            'testimonials': [],
            'blog_posts': [],
            'technical_details': {},
            'company_info': {'name': 'Brand', 'url': os.getenv('GSC_SITE_URL', 'https://yourdomain.com')},
        }


# Convenience function for quick testing
def extract_repo_context(force_refresh: bool = False) -> Dict[str, Any]:
    """Quick helper to extract repo context"""
    extractor = RepoContextExtractor()
    return extractor.extract_context(force_refresh=force_refresh)


if __name__ == "__main__":
    # Test extraction
    logging.basicConfig(level=logging.INFO)
    context = extract_repo_context(force_refresh=True)
    print(f"\nExtracted context:")
    print(f"  Blog posts: {len(context.get('blog_posts', []))}")
    print(f"  Integrations: {len(context.get('integrations', []))}")
    print(f"  Internal links: {len(context.get('internal_links', {}))}")
    print(f"  Features: {len(context.get('features', []))}")
