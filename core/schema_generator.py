"""
JSON-LD Schema Markup Generator for Research Content

Generates schema.org compliant JSON-LD for:
- BlogPosting (with E-E-A-T author signals)
- FAQPage (for AI visibility and featured snippets)
- ClaimReview (for fact-checked data points)
- HowTo (for guide-style content)

Aligns with astro-site frontmatter structure (apps/web/src/content/blog/*.mdx).
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SchemaGenerator:
    """Generate JSON-LD schema markup for research and blog content."""

    def __init__(self, author_profiles_path: Optional[Path] = None):
        """
        Initialize schema generator with author profiles.

        Args:
            author_profiles_path: Path to author_profiles.json (optional)
        """
        if author_profiles_path is None:
            author_profiles_path = Path(__file__).parent.parent / 'config' / 'author_profiles.json'

        self.author_profiles = self._load_author_profiles(author_profiles_path)

    def _load_author_profiles(self, path: Path) -> Dict[str, Any]:
        """Load author E-E-A-T profiles from config."""
        try:
            with open(path, 'r') as f:
                profiles = json.load(f)
                logger.debug(f"✅ Loaded {len([k for k in profiles.keys() if not k.startswith('_')])} author profiles")
                return profiles
        except FileNotFoundError:
            logger.warning(f"⚠️  author_profiles.json not found at {path}, using default")
            return {
                "_default_fallback": {
                    "name": "Brand Team",
                    "schema": {
                        "@type": "Organization",
                        "name": "Brand",
                        "url": "https://www.acme.com"
                    }
                }
            }
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in author_profiles.json: {e}")
            return {}

    def _get_author_schema(self, author_name: str) -> Dict[str, Any]:
        """
        Get author schema from profiles with fallback.

        Args:
            author_name: Author name from frontmatter (e.g., "Brand Team")

        Returns:
            Author schema dict (@type: Person or Organization)
        """
        # Try exact match
        if author_name in self.author_profiles:
            return self.author_profiles[author_name].get('schema', {})

        # Fallback to default
        logger.debug(f"Author '{author_name}' not in profiles, using fallback")
        return self.author_profiles.get('_default_fallback', {}).get('schema', {
            "@type": "Organization",
            "name": "Brand",
            "url": "https://www.acme.com"
        })

    def generate_blog_posting_schema(
        self,
        frontmatter: Dict[str, Any],
        content: str,
        canonical_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate BlogPosting JSON-LD schema.

        Args:
            frontmatter: Astro MDX frontmatter dict
            content: Full MDX content for wordCount
            canonical_url: Canonical URL (fallback to frontmatter.canonical)

        Returns:
            BlogPosting schema dict

        Schema fields:
        - @context, @type, @id
        - headline (from seo.title or title)
        - description (from seo.description or description)
        - image (from image.src or seo.ogImage)
        - datePublished, dateModified
        - author (from author_profiles with E-E-A-T)
        - publisher (Brand organization)
        - wordCount, articleSection (from category)
        """
        url = canonical_url or frontmatter.get('canonical', '')
        if not url:
            logger.warning("⚠️  No canonical URL provided for BlogPosting schema")

        # Extract metadata
        title = frontmatter.get('seo', {}).get('title') or frontmatter.get('title', '')
        description = frontmatter.get('seo', {}).get('description') or frontmatter.get('description', '')

        # Image handling - support both nested and direct paths
        image_data = frontmatter.get('image', {})
        if isinstance(image_data, dict):
            image_src = image_data.get('src', '')
            image_alt = image_data.get('alt', title)
        else:
            image_src = frontmatter.get('seo', {}).get('ogImage', '')
            image_alt = title

        # Convert relative image paths to absolute
        if image_src and not image_src.startswith('http'):
            if image_src.startswith('/'):
                image_src = f"https://www.acme.com{image_src}"
            else:
                image_src = f"https://www.acme.com/{image_src}"

        # Dates
        published = frontmatter.get('publishDate', datetime.now().isoformat())
        modified = frontmatter.get('updatedDate', published)

        # Author from profiles
        author_name = frontmatter.get('author', 'Brand Team')
        author_schema = self._get_author_schema(author_name)

        # Word count (rough estimate from content length)
        word_count = len(content.split())

        # Article section from category
        category = frontmatter.get('category', 'Marketing')

        schema = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "@id": f"{url}#article",
            "headline": title[:110],  # Schema.org recommends ≤110 chars
            "description": description,
            "image": {
                "@type": "ImageObject",
                "url": image_src,
                "alt": image_alt
            } if image_src else None,
            "datePublished": published,
            "dateModified": modified,
            "author": author_schema,
            "publisher": {
                "@type": "Organization",
                "@id": "https://www.acme.com/#organization",
                "name": "Brand",
                "url": "https://www.acme.com",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://www.acme.com/logo.png",
                    "width": 600,
                    "height": 60
                }
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": url
            },
            "wordCount": word_count,
            "articleSection": category.capitalize(),
            "inLanguage": "en-US"
        }

        # Remove None values
        schema = {k: v for k, v in schema.items() if v is not None}

        logger.debug(f"✅ Generated BlogPosting schema ({word_count} words)")
        return schema

    def generate_faq_page_schema(
        self,
        faq_list: List[Dict[str, str]],
        canonical_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate FAQPage JSON-LD schema from frontmatter FAQ array.

        Args:
            faq_list: List of {question: str, answer: str} dicts
            canonical_url: Page URL for @id

        Returns:
            FAQPage schema dict or None if <12 FAQs (AEO 2026 threshold)

        Requirement: ≥12 FAQs for 90% AI visibility (seo_optimization.json)
        """
        if not faq_list or len(faq_list) < 12:
            logger.debug(f"⏭️  Skipping FAQPage schema ({len(faq_list) if faq_list else 0} FAQs, need ≥12)")
            return None

        url = canonical_url or ""

        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "@id": f"{url}#faqpage" if url else None,
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq['question'],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": faq['answer']
                    }
                }
                for faq in faq_list[:15]  # Limit to top 15 per SEO config
            ]
        }

        # Remove None values
        schema = {k: v for k, v in schema.items() if v is not None}

        logger.debug(f"✅ Generated FAQPage schema ({len(faq_list)} FAQs)")
        return schema

    def generate_claim_review_schema(
        self,
        claims: List[Dict[str, Any]],
        canonical_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate ClaimReview JSON-LD schema for fact-checked claims.

        Args:
            claims: List of verified claims with structure:
                {
                    'claim': str,
                    'source': str,
                    'confidence': str (RESEARCH/INDUSTRY/OBSERVATIONAL),
                    'date_published': str (optional)
                }
            canonical_url: Page URL for itemReviewed.url

        Returns:
            List of ClaimReview schema dicts (one per claim)

        Maps confidence levels to truthfulness ratings:
        - RESEARCH → "True" (peer-reviewed, .edu/.gov)
        - INDUSTRY → "Mostly True" (established publications)
        - OBSERVATIONAL → "Unverified" (community sources)
        """
        if not claims:
            return []

        # Confidence to rating mapping (per seo_optimization.json)
        confidence_map = {
            'RESEARCH': 'True',
            'INDUSTRY': 'Mostly True',
            'OBSERVATIONAL': 'Unverified'
        }

        schemas = []
        for i, claim_data in enumerate(claims[:10], 1):  # Limit to 10 claims
            claim_text = claim_data.get('claim', '')
            source = claim_data.get('source', 'research')
            confidence = claim_data.get('confidence', 'OBSERVATIONAL')
            date_pub = claim_data.get('date_published', datetime.now().isoformat())

            rating = confidence_map.get(confidence, 'Unverified')

            schema = {
                "@context": "https://schema.org",
                "@type": "ClaimReview",
                "@id": f"{canonical_url}#claim-{i}" if canonical_url else None,
                "datePublished": date_pub,
                "url": canonical_url,
                "claimReviewed": claim_text,
                "itemReviewed": {
                    "@type": "Claim",
                    "author": {
                        "@type": "Organization",
                        "name": source
                    },
                    "datePublished": date_pub,
                    "text": claim_text
                },
                "reviewRating": {
                    "@type": "Rating",
                    "ratingValue": rating,
                    "bestRating": "True",
                    "worstRating": "False",
                    "alternateName": confidence
                },
                "author": {
                    "@type": "Organization",
                    "name": "Brand Research Team",
                    "url": "https://www.acme.com"
                }
            }

            # Remove None values
            schema = {k: v for k, v in schema.items() if v is not None}
            schemas.append(schema)

        logger.debug(f"✅ Generated {len(schemas)} ClaimReview schemas")
        return schemas

    def generate_how_to_schema(
        self,
        title: str,
        description: str,
        steps: List[Dict[str, str]],
        canonical_url: Optional[str] = None,
        total_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate HowTo JSON-LD schema for guide content.

        Args:
            title: Guide title
            description: Guide description
            steps: List of {name: str, text: str, image: str (optional)} dicts
            canonical_url: Page URL
            total_time: ISO 8601 duration (e.g., "PT30M" for 30 minutes)

        Returns:
            HowTo schema dict or None if <3 steps
        """
        if not steps or len(steps) < 3:
            logger.debug(f"⏭️  Skipping HowTo schema ({len(steps) if steps else 0} steps, need ≥3)")
            return None

        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "@id": f"{canonical_url}#howto" if canonical_url else None,
            "name": title,
            "description": description,
            "step": [
                {
                    "@type": "HowToStep",
                    "position": i,
                    "name": step['name'],
                    "text": step['text'],
                    "image": step.get('image')
                }
                for i, step in enumerate(steps, 1)
            ]
        }

        if total_time:
            schema['totalTime'] = total_time

        # Remove None values from steps
        schema['step'] = [
            {k: v for k, v in step.items() if v is not None}
            for step in schema['step']
        ]

        # Remove None values from schema
        schema = {k: v for k, v in schema.items() if v is not None}

        logger.debug(f"✅ Generated HowTo schema ({len(steps)} steps)")
        return schema

    def generate_complete_schema_markup(
        self,
        frontmatter: Dict[str, Any],
        content: str,
        verified_claims: Optional[List[Dict[str, Any]]] = None,
        guide_steps: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete @graph JSON-LD with all applicable schemas.

        This is the main entry point for formatter.py integration.

        Args:
            frontmatter: Astro MDX frontmatter dict
            content: Full MDX content
            verified_claims: Optional list of fact-checked claims
            guide_steps: Optional list of guide steps for HowTo

        Returns:
            Complete JSON-LD dict with @graph array containing all schemas

        Usage in formatter.py:
            schema_gen = SchemaGenerator()
            jsonld = schema_gen.generate_complete_schema_markup(frontmatter, content)
            frontmatter['seo']['jsonld'] = json.dumps(jsonld)
        """
        canonical = frontmatter.get('canonical', '')
        graphs = []

        # 1. BlogPosting (always)
        blog_schema = self.generate_blog_posting_schema(frontmatter, content, canonical)
        graphs.append(blog_schema)

        # 2. FAQPage (if ≥12 FAQs)
        faq_list = frontmatter.get('faq', [])
        if faq_list:
            faq_schema = self.generate_faq_page_schema(faq_list, canonical)
            if faq_schema:
                graphs.append(faq_schema)

        # 3. ClaimReview (if verified claims provided)
        if verified_claims:
            claim_schemas = self.generate_claim_review_schema(verified_claims, canonical)
            graphs.extend(claim_schemas)

        # 4. HowTo (if guide steps provided)
        if guide_steps:
            title = frontmatter.get('title', '')
            description = frontmatter.get('description', '')
            howto_schema = self.generate_how_to_schema(title, description, guide_steps, canonical)
            if howto_schema:
                graphs.append(howto_schema)

        # Wrap in @graph for multiple schemas
        if len(graphs) == 1:
            complete_schema = graphs[0]
        else:
            complete_schema = {
                "@context": "https://schema.org",
                "@graph": graphs
            }

        logger.info(f"✅ Generated complete schema markup ({len(graphs)} schemas)")
        return complete_schema

    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Basic validation of generated schema.

        Args:
            schema: Generated JSON-LD schema dict

        Returns:
            True if schema passes basic validation

        Validates:
        - Required @context and @type present
        - No empty required fields
        - Valid URLs (if present)
        """
        # Check required top-level fields
        if '@graph' in schema:
            # Multiple schemas in graph
            for item in schema.get('@graph', []):
                if not item.get('@type'):
                    logger.error("❌ Schema validation failed: missing @type in @graph item")
                    return False
        else:
            # Single schema
            if not schema.get('@context') or not schema.get('@type'):
                logger.error("❌ Schema validation failed: missing @context or @type")
                return False

        # Validate URLs (if present)
        url_fields = ['url', '@id', 'mainEntityOfPage']
        for field in url_fields:
            url = schema.get(field)
            if isinstance(url, dict):
                url = url.get('@id') or url.get('url')
            if url and not (url.startswith('http://') or url.startswith('https://')):
                logger.warning(f"⚠️  Invalid URL in {field}: {url}")

        logger.debug("✅ Schema validation passed")
        return True
