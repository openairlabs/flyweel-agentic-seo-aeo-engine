"""Astro Formatter - Complete Astro blog compatibility with all features"""
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import os

# Schema generation and validation
from core.schema_generator import SchemaGenerator
from core.fact_checker import FactChecker

logger = logging.getLogger(__name__)


# SEO Validation Gates (Phase 4.2)
# Load limits from config with sensible defaults
def _load_seo_limits() -> Dict[str, Any]:
    """Load SEO character limits from config."""
    config_path = Path(__file__).parent.parent / 'config' / 'seo_optimization.json'
    defaults = {
        'title': {'min': 30, 'max': 70, 'ideal_min': 50, 'ideal_max': 60},
        'meta': {'min': 120, 'max': 160, 'ideal_min': 150, 'ideal_max': 160}
    }

    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                title_rules = config.get('title_rules', {})
                meta_rules = config.get('meta_description_rules', {})

                return {
                    'title': {
                        'min': title_rules.get('min_length', 30),
                        'max': title_rules.get('max_length', 70),
                        'ideal_min': title_rules.get('ideal_length', [50, 60])[0],
                        'ideal_max': title_rules.get('ideal_length', [50, 60])[1]
                    },
                    'meta': {
                        'min': meta_rules.get('min_length', 120),
                        'max': meta_rules.get('max_length', 160),
                        'ideal_min': meta_rules.get('ideal_length', [150, 160])[0],
                        'ideal_max': meta_rules.get('ideal_length', [150, 160])[1]
                    }
                }
        except Exception:
            pass

    return defaults


_SEO_LIMITS = _load_seo_limits()


def validate_title(title: str, keyword: Optional[str] = None) -> Tuple[bool, str, List[str]]:
    """
    Validate title against SEO rules.

    Returns:
        Tuple of (is_valid, validated_title, list of issues)

    Validation rules:
    - Length: 30-70 chars, ideal 50-60
    - Contains primary keyword (if provided)
    - No banned words
    """
    issues = []
    limits = _SEO_LIMITS['title']

    # Clean title
    clean_title = title.strip()

    # Length validation
    if len(clean_title) < limits['min']:
        issues.append(f"Title too short ({len(clean_title)} chars, min {limits['min']})")
    elif len(clean_title) > limits['max']:
        issues.append(f"Title too long ({len(clean_title)} chars, max {limits['max']})")
        # Truncate at word boundary
        truncated = clean_title[:limits['max']]
        last_space = truncated.rfind(' ')
        if last_space > limits['min']:
            clean_title = truncated[:last_space]
        else:
            clean_title = truncated
        logger.warning(f"⚠️  Title truncated to {len(clean_title)} chars")

    if limits['ideal_min'] <= len(clean_title) <= limits['ideal_max']:
        logger.info(f"✅ Title length optimal: {len(clean_title)} chars")
    elif len(clean_title) <= limits['max']:
        logger.info(f"ℹ️  Title length acceptable: {len(clean_title)} chars (ideal: {limits['ideal_min']}-{limits['ideal_max']})")

    # Keyword check
    if keyword:
        keyword_lower = keyword.lower()
        # Check if any significant words from keyword are in title
        significant_words = [w for w in keyword_lower.split() if len(w) > 3]
        title_lower = clean_title.lower()
        keyword_match = any(word in title_lower for word in significant_words)

        if not keyword_match:
            issues.append(f"Primary keyword '{keyword}' not found in title")

    # Load banned words
    config_path = Path(__file__).parent.parent / 'config' / 'seo_optimization.json'
    banned_words = []
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                banned_words = config.get('title_rules', {}).get('banned_words', [])
        except Exception:
            pass

    # Check for banned words
    for banned in banned_words:
        if banned.lower() in clean_title.lower():
            issues.append(f"Contains banned word: '{banned}'")

    is_valid = len(issues) == 0
    return (is_valid, clean_title, issues)


def validate_meta_description(description: str, keyword: Optional[str] = None) -> Tuple[bool, str, List[str]]:
    """
    Validate meta description against SEO rules.

    Returns:
        Tuple of (is_valid, validated_description, list of issues)

    Validation rules:
    - Length: 120-160 chars, ideal 150-160
    - Contains primary keyword in first 50 chars (if provided)
    - Ends with CTA-like content
    """
    issues = []
    limits = _SEO_LIMITS['meta']

    # Clean description
    clean_desc = description.strip()

    # Length validation
    if len(clean_desc) < limits['min']:
        issues.append(f"Meta description too short ({len(clean_desc)} chars, min {limits['min']})")
    elif len(clean_desc) > limits['max']:
        issues.append(f"Meta description too long ({len(clean_desc)} chars, max {limits['max']})")
        # Truncate at word boundary
        truncated = clean_desc[:limits['max']]
        last_space = truncated.rfind(' ')
        if last_space > limits['min']:
            clean_desc = truncated[:last_space]
        else:
            clean_desc = truncated
        logger.warning(f"⚠️  Meta description truncated to {len(clean_desc)} chars")

    if limits['ideal_min'] <= len(clean_desc) <= limits['ideal_max']:
        logger.info(f"✅ Meta description length optimal: {len(clean_desc)} chars")
    elif len(clean_desc) <= limits['max']:
        logger.info(f"ℹ️  Meta description length acceptable: {len(clean_desc)} chars (ideal: {limits['ideal_min']}-{limits['ideal_max']})")

    # Keyword in first 50 chars check
    if keyword:
        first_50 = clean_desc[:50].lower()
        keyword_words = [w.lower() for w in keyword.split() if len(w) > 3]
        keyword_in_first_50 = any(word in first_50 for word in keyword_words)

        if not keyword_in_first_50:
            issues.append(f"Primary keyword not found in first 50 chars of meta description")

    is_valid = len(issues) == 0
    return (is_valid, clean_desc, issues)


def validate_frontmatter_seo(frontmatter: Dict[str, Any], keyword: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate and fix frontmatter for SEO compliance.

    Returns validated frontmatter with any issues logged.
    """
    validated = frontmatter.copy()
    all_issues = []

    # Validate title
    if 'title' in validated:
        is_valid, clean_title, issues = validate_title(validated['title'], keyword)
        validated['title'] = clean_title
        all_issues.extend(issues)

    # Validate description
    if 'description' in validated:
        is_valid, clean_desc, issues = validate_meta_description(validated['description'], keyword)
        validated['description'] = clean_desc
        all_issues.extend(issues)

    # Log issues
    if all_issues:
        logger.warning(f"⚠️  SEO validation issues found:")
        for issue in all_issues:
            logger.warning(f"   - {issue}")
    else:
        logger.info(f"✅ Frontmatter SEO validation passed")

    return validated

class AstroFormatter:
    """Format content for Astro blog with all required components"""

    def __init__(self, site_context=None, brand_mode='full'):
        self.author_email = os.getenv('AUTHOR_EMAIL', 'hello@acme.com')
        self.blog_schema = self._load_blog_schema()
        self.content_templates = self._load_content_templates()
        self.brand_voice_config = self._load_brand_voice_config()
        self.seo_config = self._load_seo_config()
        self.site_context = site_context
        self.brand_mode = brand_mode

        # Initialize schema generator and fact checker (10x research quality)
        self.schema_generator = SchemaGenerator()
        self.fact_checker = FactChecker()

        # Build intelligent link opportunity map from site context (disabled if mode is 'none')
        if brand_mode != 'none':
            self.link_opportunities = self._build_link_opportunity_map(site_context)
        else:
            self.link_opportunities = {}

    def _load_blog_schema(self):
        """Load blog content schema if available"""
        # Try project config first, fall back to parent project
        config_dir = Path(__file__).parent.parent / 'config'
        schema_path = config_dir / 'blog-content-schema.json'

        if not schema_path.exists():
            # Fall back to parent project
            schema_path = Path(__file__).parent.parent / 'config' / 'blog-content-schema.json'

        if schema_path.exists():
            with open(schema_path, 'r') as f:
                return json.load(f)
        return None

    def _load_content_templates(self):
        """Load content templates for different styles"""
        # Try project config first, fall back to parent project
        config_dir = Path(__file__).parent.parent / 'config'
        templates_path = config_dir / 'content-templates.json'

        if not templates_path.exists():
            # Fall back to parent project
            templates_path = Path(__file__).parent.parent / 'config' / 'content-templates.json'

        if templates_path.exists():
            with open(templates_path, 'r') as f:
                return json.load(f)
        return {}

    def _load_brand_voice_config(self):
        """Load brand voice configuration"""
        config_dir = Path(__file__).parent.parent / 'config'
        config_path = config_dir / 'brand_voice_config.json'

        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}

    def _load_seo_config(self) -> Dict[str, Any]:
        """Load SEO optimization configuration"""
        config_path = Path(__file__).parent.parent / 'config' / 'seo_optimization.json'
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _generate_slug(self, keyword: str) -> str:
        """Generate URL slug from keyword"""
        slug = keyword.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')

    def _calculate_reading_time(self, content: str) -> str:
        """Calculate reading time from content word count (265 WPM - Medium standard)"""
        # Remove code blocks and imports from word count
        import re
        clean = re.sub(r'```[\s\S]*?```', '', content)  # Remove code blocks
        clean = re.sub(r'^import.*$', '', clean, flags=re.MULTILINE)  # Remove imports
        clean = re.sub(r'<[^>]+>', '', clean)  # Remove HTML/JSX tags
        words = len(clean.split())
        minutes = max(1, round(words / 265))  # 265 WPM is Medium's standard
        return f"{minutes} min read"

    def _build_faq_array(self, paa_questions: List[str], content: str) -> List[Dict[str, str]]:
        """Build FAQ array from PAA questions for YAML frontmatter"""
        faq_items = []
        if not paa_questions:
            return faq_items

        for question in paa_questions[:10]:
            question = question.strip()
            if not question:
                continue
            if not question.endswith('?'):
                question += '?'

            answer = self._extract_short_answer_for_frontmatter(question, content)
            if answer:
                faq_items.append({
                    'question': question,
                    'answer': answer
                })

        return faq_items

    def _extract_short_answer_for_frontmatter(self, question: str, content: str) -> str:
        """Extract a SHORT concise answer (1-2 sentences, max 300 chars) for frontmatter FAQ array"""
        question_words = set(re.findall(r'\w+', question.lower()))
        question_words -= {'what', 'how', 'why', 'when', 'where', 'which', 'is', 'are', 'the', 'a', 'an', 'do', 'does', 'can', 'will', 'should'}

        paragraphs = re.split(r'\n\n+', content)
        best_para = ""
        best_score = 0

        for para in paragraphs:
            if len(para) < 50 or para.startswith('#') or para.startswith('import'):
                continue
            para_words = set(re.findall(r'\w+', para.lower()))
            score = len(question_words & para_words)
            if score > best_score:
                best_score = score
                best_para = para

        if best_para:
            sentences = re.split(r'(?<=[.!?])\s+', best_para)
            answer = ' '.join(sentences[:2])
            if len(answer) > 300:
                answer = answer[:297] + '...'
            answer = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', answer)
            answer = re.sub(r'\*\*([^\*]+)\*\*', r'\1', answer)
            return answer.strip()

        return ""

    def _build_link_opportunity_map(self, site_context: Optional[Dict]) -> Dict[str, Dict]:
        """Build intelligent link opportunity map from sitemap content"""

        link_map = {}

        if not site_context:
            return link_map

        # Extract from blog posts
        for post in site_context.get('blog_posts', []):
            if not post.get('url') or not post.get('title'):
                continue

            # Extract key linkable terms from title
            title_terms = self._extract_linkable_terms(post['title'])
            for term in title_terms:
                term_lower = term.lower()
                # Only add if term is meaningful (3+ chars)
                if len(term) >= 3:
                    link_map[term_lower] = {
                        'url': post['url'],
                        'title': post['title'],
                        'type': 'blog',
                        'anchor_text': term
                    }

        # Extract from internal links (sitemap pages)
        for text, url in site_context.get('internal_links', {}).items():
            if text and url:
                term_lower = text.lower()
                link_map[term_lower] = {
                    'url': url,
                    'title': text,
                    'type': 'page',
                    'anchor_text': text
                }

        return link_map

    def _extract_linkable_terms(self, text: str) -> List[str]:
        """Extract meaningful terms from text that could be link anchors"""
        if not text:
            return []

        # Remove common filler words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during'
        }

        # Split into words and filter
        words = re.findall(r'\b\w+\b', text.lower())
        terms = []

        # Extract individual meaningful words
        for word in words:
            if word not in stop_words and len(word) >= 4:
                terms.append(word)

        # Extract 2-3 word phrases (better for linking)
        words_list = text.split()
        for i in range(len(words_list)):
            # 2-word phrases
            if i + 1 < len(words_list):
                phrase = f"{words_list[i]} {words_list[i+1]}"
                if len(phrase) >= 8:  # Meaningful phrase length
                    terms.append(phrase)

            # 3-word phrases
            if i + 2 < len(words_list):
                phrase = f"{words_list[i]} {words_list[i+1]} {words_list[i+2]}"
                if len(phrase) >= 12:
                    terms.append(phrase)

        return terms[:10]  # Limit to top 10 terms

    def _validate_frontmatter(self, frontmatter: Dict[str, Any], slug: str) -> List[str]:
        """Validate frontmatter against Astro requirements"""
        warnings = []

        # Required fields
        required_fields = ['title', 'publishDate', 'description', 'author', 'image', 'tags', 'category']
        for field in required_fields:
            if field not in frontmatter or not frontmatter[field]:
                warnings.append(f"Missing required field: {field}")

        # Image validation
        if 'image' in frontmatter:
            image = frontmatter['image']
            if not isinstance(image, dict):
                warnings.append("Image must be a dict with 'src' and 'alt' fields")
            else:
                if 'src' not in image or not image['src'].startswith('/src/assets/blog/'):
                    warnings.append(f"Image src must start with /src/assets/blog/, got: {image.get('src', 'missing')}")
                if 'src' in image and not image['src'].endswith('.webp'):
                    warnings.append(f"Image should be .webp format, got: {image['src']}")
                if 'alt' not in image or not image['alt']:
                    warnings.append("Image missing alt text")

        # Title length (SEO best practice)
        if 'title' in frontmatter and len(frontmatter['title']) > 60:
            warnings.append(f"Title too long for SEO ({len(frontmatter['title'])} chars, max 60)")

        # Description length (SEO best practice)
        if 'description' in frontmatter:
            desc_len = len(frontmatter['description'])
            if desc_len < 120:
                warnings.append(f"Description too short ({desc_len} chars, min 120)")
            elif desc_len > 160:
                warnings.append(f"Description too long ({desc_len} chars, max 160)")

        # Tags validation
        if 'tags' in frontmatter:
            if not isinstance(frontmatter['tags'], list):
                warnings.append("Tags must be a list")
            elif len(frontmatter['tags']) < 2:
                warnings.append("Should have at least 2 tags for SEO")
            elif len(frontmatter['tags']) > 8:
                warnings.append(f"Too many tags ({len(frontmatter['tags'])}, max 8)")

        return warnings

    def format(self, content: str, keyword: str, style: str = "standard",
              research_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Format content with complete Astro frontmatter and all sections"""

        # Generate metadata (with SEO optimization)
        title = self._generate_title(content, keyword, style)
        meta_description = self._generate_meta_description(content, keyword, style=style)
        slug = self._create_slug(title)

        # Extract sections
        h2_sections = self._extract_h2_sections(content)

        # Process content based on style
        processed_content = self._process_content_by_style(content, style, keyword, research_data)

        # Add FAQ section from PAA questions (with internal linking)
        serp_data = (research_data.get('serp') or {}) if research_data else {}
        if serp_data:
            paa_questions = serp_data.get('paa_questions', [])
            if isinstance(paa_questions, list) and paa_questions:
                processed_content = self._add_qa_section(processed_content, paa_questions, keyword)

        # Add comparison table for comparison style
        if style == "comparison":
            processed_content = self._add_comparison_table(processed_content, keyword)

        # Add ROI calculator for relevant content
        if self._should_include_roi_calculator(keyword, processed_content):
            processed_content = self._add_roi_calculator(processed_content)

        # Add internal links
        processed_content = self._add_internal_links(processed_content)

        # Add citations from research
        if research_data:
            processed_content = self._add_citations(processed_content, research_data, style)

        # Process external links (add nofollow for SEO)
        processed_content = self._process_external_links(processed_content)

        # Build complete frontmatter (astro schema compliant)
        frontmatter = {
            'title': title,
            'publishDate': datetime.now().strftime('%Y-%m-%d'),
            'description': meta_description,
            'author': 'Brand Team',
            'image': {
                'src': f'/src/assets/blog/{slug}-hero.webp',
                'alt': f'Hero image for {title}'
            },
            'tags': self._generate_tags(keyword, content, style),
            'category': self._determine_category(keyword, content),
            'featured': False,
            'draft': False,
            'readingTime': str(self._calculate_read_time(processed_content)),
            'updatedDate': datetime.now().strftime('%Y-%m-%d')
        }

        # Phase 6.3: Feature page specific frontmatter
        if style == 'feature':
            frontmatter['byline'] = self._generate_feature_byline(keyword, content)
            frontmatter['features'] = self._extract_feature_list(processed_content)
            frontmatter['cta'] = {
                'text': 'Get Started Free',
                'url': 'https://acme.com/signup'
            }
            frontmatter['category'] = 'features'

        # SEO validation gates - validate and fix title/meta (Phase 4.2)
        frontmatter = validate_frontmatter_seo(frontmatter, keyword)
        title = frontmatter['title']  # May have been truncated
        meta_description = frontmatter['description']  # May have been truncated

        # Validate frontmatter against Astro requirements
        validation_warnings = self._validate_frontmatter(frontmatter, slug)
        if validation_warnings:
            for warning in validation_warnings:
                logger.warning(f"⚠️  Frontmatter validation: {warning}")

        # Build complete MDX with all components
        mdx_content = self._build_complete_mdx(frontmatter, processed_content, keyword, h2_sections, research_data, style)

        return {
            'title': title,
            'meta_description': meta_description,
            'slug': slug,
            'content': mdx_content,
            'h2_sections': h2_sections,
            'tags': frontmatter['tags'],
            'category': frontmatter['category'],
            'style': style
        }
    
    def _process_content_by_style(self, content: str, style: str, keyword: str,
                                 research_data: Optional[Dict] = None) -> str:
        """Process content based on style template"""

        # Style-specific processing
        if style == "comparison":
            content = self._enhance_comparison_content(content, keyword)
        elif style == "guide":
            content = self._enhance_guide_content(content, keyword)
        elif style == "research":
            content = self._enhance_research_content(content, research_data)
        elif style == "news":
            content = self._enhance_news_content(content)
        elif style == "category":
            content = self._enhance_category_content(content, keyword)
        elif style == "top-compare":
            content = self._enhance_top_compare_content(content, keyword)

        return content
    
    def _enhance_comparison_content(self, content: str, keyword: str) -> str:
        """Enhance comparison style content"""
        # Add comparison markers if not present
        if "## Quick Comparison" not in content:
            # Find a good spot to insert comparison
            first_h2_pos = content.find("## ")
            if first_h2_pos > 0:
                content = (content[:first_h2_pos] + 
                          "## Quick Comparison\n\n" +
                          "[Comparison table will be inserted here]\n\n" +
                          content[first_h2_pos:])
        return content
    
    def _enhance_guide_content(self, content: str, keyword: str) -> str:
        """Enhance guide style content"""
        # Ensure step-by-step structure
        if "## Step" not in content and "## How to" not in content:
            # Add step markers
            h2_sections = re.findall(r'^## (.+)$', content, re.MULTILINE)
            for i, section in enumerate(h2_sections[:5], 1):
                if not section.startswith("Step"):
                    content = content.replace(f"## {section}", f"## Step {i}: {section}")
        return content
    
    def _enhance_research_content(self, content: str, research_data: Optional[Dict]) -> str:
        """Enhance research style content with citations"""
        if research_data:
            # Add research methodology section if missing (professional, no metadata exposure)
            if "## Research Methodology" not in content and "## Our Research" not in content:
                methodology = "\n\n## Research Methodology\n\n"
                methodology += "This comprehensive analysis draws from:\n\n"

                # Only mention SERP analysis - no Reddit/Quora platform exposure
                serp_results = (research_data.get('serp') or {}).get('search_results', [])
                if serp_results:
                    methodology += f"- In-depth analysis of {len(serp_results)} authoritative industry sources\n"

                methodology += "- Current market data and industry benchmarks\n"
                methodology += "- Expert insights from leading practitioners\n"
                methodology += "- Systematic evaluation using established research frameworks\n"

                # Insert after introduction
                first_h2 = content.find("## ")
                if first_h2 > 0:
                    content = content[:first_h2] + methodology + "\n" + content[first_h2:]

        return content
    
    def _enhance_news_content(self, content: str) -> str:
        """Enhance news style content"""
        # Add publication date context
        today = datetime.now().strftime("%B %d, %Y")
        if today not in content:
            # Add date after title
            content = re.sub(r'^(#[^#\n]+)\n', f'\\1\n\n*Published on {today}*\n\n', content)
        return content
    
    def _enhance_category_content(self, content: str, keyword: str) -> str:
        """Enhance category overview content"""
        # Ensure category structure
        if "## Overview" not in content:
            first_h2 = content.find("## ")
            if first_h2 > 0:
                content = content[:first_h2] + f"## {keyword.title()} Overview\n\n" + content[first_h2:]
        return content

    def _enhance_top_compare_content(self, content: str, keyword: str) -> str:
        """Enhance top-compare style content with proper structure

        This method ensures the top-compare article has:
        - Quick comparison summary table
        - Numbered solution sections
        - Proper heading hierarchy
        """
        # Ensure Quick Comparison section exists at the top
        if "## Quick Comparison" not in content:
            # Find first H2 and insert Quick Comparison before it
            first_h2_pos = content.find("## ")
            if first_h2_pos > 0:
                quick_compare_placeholder = """## Quick Comparison

| # | Solution | Best For | Pricing |
|---|----------|----------|---------|
| 1 | [Solution details will be extracted from content below] | | |

"""
                content = content[:first_h2_pos] + quick_compare_placeholder + content[first_h2_pos:]

        # Ensure "How to Choose" section exists
        if "## How to Choose" not in content:
            # Find FAQ section or end of solutions
            faq_pos = content.find("## Frequently Asked Questions")
            if faq_pos < 0:
                faq_pos = content.find("## FAQ")
            if faq_pos < 0:
                faq_pos = len(content)

            how_to_choose = """

## How to Choose the Right Solution

When evaluating your options, consider these key factors:

- **Budget:** Match pricing models to your investment capacity
- **Team Expertise:** Consider internal capabilities and learning curve
- **Integration Needs:** Ensure compatibility with existing tech stack
- **Timeline:** Align expected results with your business goals
- **Industry Fit:** Look for solutions with relevant experience

"""
            # Insert before FAQ
            content = content[:faq_pos] + how_to_choose + content[faq_pos:]

        # Ensure Conclusion section exists
        if "## Conclusion" not in content:
            faq_pos = content.find("## Frequently Asked Questions")
            if faq_pos < 0:
                faq_pos = content.find("## FAQ")
            if faq_pos > 0:
                conclusion = f"""

## Conclusion

Each solution on this list brings unique strengths to {keyword}. The right choice depends on your specific needs, budget, and growth trajectory. Consider scheduling demos with your top 2-3 picks to see which platform best fits your workflow.

"""
                content = content[:faq_pos] + conclusion + content[faq_pos:]

        return content

    def _prioritize_long_tail_questions(self, questions: List[str]) -> List[str]:
        """Prioritize long-tail questions for FAQ section"""
        if not questions:
            return []

        scored_questions = []
        for q in questions:
            score = 0
            word_count = len(q.split())

            # Long-tail indicators (higher score = more specific/long-tail)
            if word_count >= 7:  # Longer questions = more specific
                score += 3
            elif word_count >= 5:
                score += 2

            # Specific question words indicate long-tail intent
            long_tail_phrases = [
                'specific', 'best way', 'difference between', 'how long', 'how much',
                'what happens when', 'can i', 'should i', 'do i need', 'vs', 'versus',
                'compare', 'comparison', 'alternative', 'instead of', 'better than',
                'step by step', 'easiest way', 'fastest way', 'cheapest', 'most expensive',
                'which is better', 'pros and cons', 'advantages', 'disadvantages',
                'worth it', 'best time', 'when should', 'how often'
            ]
            q_lower = q.lower()
            for phrase in long_tail_phrases:
                if phrase in q_lower:
                    score += 2
                    break

            # Avoid generic short questions
            generic_patterns = ['what is', 'define', 'meaning of', 'what are']
            if any(g in q_lower for g in generic_patterns) and word_count < 6:
                score -= 2

            scored_questions.append((score, word_count, q))

        # Sort by score (highest first), then by length (longer first)
        scored_questions.sort(key=lambda x: (x[0], x[1]), reverse=True)

        return [q for _, _, q in scored_questions]

    def _add_qa_section(self, content: str, paa_questions: List[str], keyword: str = "") -> str:
        """Add Q&A section with PAA questions prioritizing long-tail queries"""
        if not paa_questions or not isinstance(paa_questions, list):
            return content

        # Check if FAQ already exists to avoid duplicates (comprehensive patterns)
        faq_patterns = [
            r'##\s*Frequently Asked Questions',
            r'##\s*FAQ',
            r'##\s*Your Top Questions',
            r'##\s*Common Questions',
            r'##\s*Questions (?:and Answers|& Answers)',
            r'##\s*Q&A',
            r'###\s*[^#\n]+\?'  # Any H3 ending with question mark indicates FAQ section
        ]

        # If ANY FAQ pattern is found, skip adding duplicate FAQ section
        for pattern in faq_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.debug(f"✓ FAQ section already exists (matched pattern: {pattern}), skipping duplicate")
                return content

        # Get FAQ heading format from config (default to contextual)
        faq_config = self.brand_voice_config.get('faq_heading_format', {})
        faq_style = faq_config.get('style', 'contextual')
        faq_options = faq_config.get('options', {
            'contextual': 'Your Top Questions About {keyword}',
            'standard': 'Frequently Asked Questions'
        })

        # Generate heading based on style
        if faq_style == 'contextual' and keyword:
            heading = faq_options['contextual'].format(keyword=keyword.title())
        else:
            heading = faq_options.get('standard', 'Frequently Asked Questions')

        qa_section = f"\n\n## {heading}\n\n"

        # Prioritize long-tail questions for better SEO value
        questions_list = list(paa_questions) if isinstance(paa_questions, (list, tuple)) else []
        questions_list = self._prioritize_long_tail_questions(questions_list)

        # AEO 2026: Enforce minimum 12 questions for optimal AI citation (90% visibility target)
        min_faqs = self.seo_config.get('faq_rules', {}).get('min_questions', 12)

        if len(questions_list) < min_faqs:
            logger.warning(f"⚠️  Only {len(questions_list)} PAA questions available. Generating {min_faqs - len(questions_list)} additional AEO-optimized questions...")

            # Generate additional questions using AI
            additional_questions = self._generate_aeo_questions(
                keyword=keyword,
                existing_questions=questions_list,
                count_needed=min_faqs - len(questions_list),
                content=content
            )

            questions_list.extend(additional_questions)
            logger.info(f"✅ Generated {len(additional_questions)} additional AEO questions. Total: {len(questions_list)}")

        # Include top 15 long-tail questions for better long-tail SEO coverage
        for question in questions_list[:15]:
            # Clean question
            question = question.strip()
            if not question.endswith('?'):
                question += '?'

            qa_section += f"### {question}\n\n"

            # Use improved extraction with filtering and internal linking
            answer = self._extract_answer_for_question(content, question)
            qa_section += f"{answer}\n\n"

        # Add before conclusion or at end
        conclusion_pos = content.rfind("## Conclusion")
        if conclusion_pos > 0:
            content = content[:conclusion_pos] + qa_section + content[conclusion_pos:]
        else:
            content += qa_section

        return content

    def _extract_answer_for_question(self, content: str, question: str) -> str:
        """Extract relevant answer from content for a question with internal linking"""
        # Extract question keywords
        keywords = re.findall(r'\w+', question.lower())
        keywords = [kw for kw in keywords if len(kw) > 3]  # Filter short words

        paragraphs = content.split('\n\n')
        best_para = ""
        best_score = 0
        best_position = 999

        for idx, para in enumerate(paragraphs):
            # Filter out invalid paragraphs
            if len(para) < 100:  # Minimum content length
                continue
            if para.startswith('#'):  # Skip headings
                continue
            if para.startswith('---'):  # Skip frontmatter
                continue
            if 'import ' in para or '<' in para[:10]:  # Skip imports and components
                continue
            if para.startswith('title:') or para.startswith('description:'):  # Skip frontmatter fields
                continue

            # Score based on keyword matches
            keyword_score = sum(1 for kw in keywords if kw in para.lower())

            # Bonus for quality indicators
            quality_score = 0
            if '**' in para:  # Has bold text
                quality_score += 1
            if any(marker in para for marker in ['*   ', '- ', '1. ', '2. ']):  # Has bullets/lists
                quality_score += 1
            if 'for example' in para.lower() or 'e.g.' in para.lower():  # Has examples
                quality_score += 2

            # Combined score with position weight (earlier = better)
            total_score = (keyword_score * 3) + quality_score - (idx * 0.1)

            if total_score > best_score:
                best_score = total_score
                best_para = para
                best_position = idx

        if best_para and best_score > 2:
            # Clean but preserve structure
            answer = best_para.strip()

            # Add intelligent internal links
            answer = self._inject_faq_internal_links(answer)

            # Ensure reasonable length (300-500 words ideal)
            words = answer.split()
            if len(words) > 150:
                # Find good breaking point (sentence end)
                truncate_at = ' '.join(words[:150])
                last_period = truncate_at.rfind('.')
                if last_period > 100:
                    answer = truncate_at[:last_period + 1]

            return answer

        # Enhanced fallback with internal linking (using real site links)
        fallback = f"{question.replace('?', '')} requires a strategic approach that connects your CRM data with advertising platforms. "

        # Get Brand link from site context
        if self.site_context and 'internal_links' in self.site_context:
            brand_url = self.site_context['internal_links'].get('Brand', 'https://acme.com')
            fallback += f"Platforms like [Brand]({brand_url}) make this process effortless with automated integrations and real-time insights across all your ad channels."
        else:
            fallback += f"Modern platforms make this process effortless with automated integrations and real-time insights across all your ad channels."

        return fallback

    def _generate_aeo_questions(self, keyword: str, existing_questions: List[str], count_needed: int, content: str) -> List[str]:
        """
        Generate AEO-optimized questions when PAA data is insufficient.
        Uses AI to create natural language questions based on content and keyword intent.

        2026 AEO Best Practices:
        - Long-tail questions (7+ words)
        - Natural language format
        - Cover all question types: what, how, why, when, where, which
        - Business outcome focused for ICP (sales-led, pipeline-led businesses)
        """
        from .ai_router import SmartAIRouter

        router = SmartAIRouter()

        # Analyze existing questions to identify gaps
        existing_types = {
            'what': sum(1 for q in existing_questions if q.lower().startswith('what')),
            'how': sum(1 for q in existing_questions if q.lower().startswith('how')),
            'why': sum(1 for q in existing_questions if q.lower().startswith('why')),
            'when': sum(1 for q in existing_questions if q.lower().startswith('when')),
            'where': sum(1 for q in existing_questions if q.lower().startswith('where')),
            'which': sum(1 for q in existing_questions if q.lower().startswith('which')),
            'can': sum(1 for q in existing_questions if q.lower().startswith('can')),
            'should': sum(1 for q in existing_questions if q.lower().startswith('should')),
            'is': sum(1 for q in existing_questions if q.lower().startswith('is')),
            'are': sum(1 for q in existing_questions if q.lower().startswith('are')),
            'does': sum(1 for q in existing_questions if q.lower().startswith('does')),
            'do': sum(1 for q in existing_questions if q.lower().startswith('do'))
        }

        # Priority order for missing question types (AEO optimization)
        priority_types = [k for k, v in sorted(existing_types.items(), key=lambda x: x[1])][:5]

        prompt = f"""Generate {count_needed} natural language FAQ questions about "{keyword}" that would appear in Google's "People Also Ask" section.

EXISTING QUESTIONS (avoid duplication):
{chr(10).join(f'- {q}' for q in existing_questions)}

REQUIREMENTS (AEO 2026 - Target 90% AI Visibility):
1. **Long-tail questions** (7-12 words minimum) for AEO optimization
2. **Question type diversity** - prioritize underrepresented types: {', '.join(priority_types)}
3. **Business outcome focused** - relevant to:
   - Sales-led businesses (ad spend → lead capture → sales team → close)
   - Pipeline-led businesses (marketing → nurture → convert over time)
   - Media buyers, marketers, business owners dealing with operational challenges
4. **Natural language** - how real people search ("How do I..." not "Methods for...")
5. **Semantically distinct** - don't overlap with existing questions
6. **Answer-worthy** - each question should have a clear, substantive answer in the content

OUTPUT FORMAT (one per line, no numbering):
- Question 1 here?
- Question 2 here?
- Question 3 here?
"""

        try:
            response = router.gemini.generate_content(prompt)
            raw_text = response.text.strip()

            # Parse questions from response
            questions = []
            for line in raw_text.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    question = line.lstrip('-•*').strip()
                    # Validate: must end with ?, be 7+ words, not duplicate
                    if question and question.endswith('?') and len(question.split()) >= 7:
                        # Check not too similar to existing
                        if not any(question.lower()[:30] in eq.lower() or eq.lower()[:30] in question.lower()
                                 for eq in existing_questions):
                            questions.append(question)

            logger.info(f"✅ AI-generated {len(questions)} AEO-optimized questions (requested: {count_needed})")
            return questions[:count_needed]

        except Exception as e:
            logger.error(f"❌ Failed to generate AEO questions: {e}")
            # Fallback: generic business-focused questions
            fallback_questions = [
                f"What are the key benefits of using {keyword} for sales-led businesses with long sales cycles?",
                f"How can pipeline-led businesses measure ROI and attribution when implementing {keyword}?",
                f"Which features should media buyers and marketers prioritize when evaluating {keyword} solutions?",
                f"Why do industry professionals choose {keyword} over traditional manual methods?",
                f"When should businesses consider adopting {keyword} to improve their advertising operations?",
                f"Where do the biggest efficiency gains come from when implementing {keyword} for ad spend tracking?",
                f"How does {keyword} help sales teams connect ad spend directly to closed revenue?",
                f"What common challenges do agencies face when rolling out {keyword} across multiple clients?",
                f"Can {keyword} integrate with existing CRM and attribution systems for unified reporting?",
                f"Should businesses implement {keyword} in-house or work with specialized implementation partners?"
            ]
            logger.info(f"⚠️  Using {min(count_needed, len(fallback_questions))} fallback business-focused questions")
            return fallback_questions[:count_needed]

    def _inject_faq_internal_links(self, text: str) -> str:
        """Inject contextual internal links into FAQ answers using dynamic sitemap data"""

        # Skip if 'none' mode is enabled (educational content only)
        if self.brand_mode == 'none':
            return text

        # Use link opportunities from sitemap if available, otherwise return text unchanged
        if not self.link_opportunities:
            # Fallback to basic Brand link if we have site context
            internal_links = (self.site_context.get('internal_links') or {}) if self.site_context else {}
            if internal_links.get('Brand'):
                brand_url = internal_links['Brand']
                # Only link Brand once if not already linked
                if '[Brand]' not in text and 'Brand' in text:
                    text = text.replace('Brand', f'[Brand]({brand_url})', 1)
            return text

        # Build smart link patterns from sitemap data
        # This uses the link_opportunities already built from sitemap in __init__
        link_patterns = {}

        # Extract linkable terms from site context
        if self.site_context and 'internal_links' in self.site_context:
            for link_text, url in self.site_context['internal_links'].items():
                # Create regex pattern for this term
                # Escape special chars and add word boundaries
                safe_term = re.escape(link_text)
                pattern = rf'\b{safe_term}\b'
                link_patterns[pattern] = (link_text, url)

        # Track which links we've added (only link first occurrence)
        added_links = set()
        max_links = 3  # Limit to 3 internal links per FAQ answer

        for pattern, (link_text, url) in link_patterns.items():
            if len(added_links) >= max_links:
                break

            # Check if already linked
            if url in text or link_text.lower() in added_links:
                continue

            # Find first occurrence
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Check it's not already in a link
                start = match.start()
                before = text[max(0, start-20):start]
                after = text[match.end():min(len(text), match.end()+5)]

                if '[' not in before.split('\n')[-1] and '](' not in after:
                    # Replace first occurrence only with actual matched text (preserve case)
                    matched_text = match.group(0)
                    replacement = f'[{matched_text}]({url})'
                    text = text[:start] + replacement + text[match.end():]
                    added_links.add(link_text.lower())

        return text
    
    def _add_comparison_table(self, content: str, keyword: str) -> str:
        """Add comparison table component for comparison content"""
        if "[Comparison table will be inserted here]" in content:
            # Generate comparison table component
            table = self._generate_comparison_component(keyword)
            content = content.replace("[Comparison table will be inserted here]", table)

        return content
    
    def _generate_comparison_component(self, keyword: str) -> str:
        """Generate a styled comparison table component"""
        # Get integration count from site context if available
        integration_count = "11+"
        if self.site_context and 'integrations' in self.site_context:
            if isinstance(self.site_context['integrations'], dict):
                total = sum(len(integrations) for integrations in self.site_context['integrations'].values())
                integration_count = f"{total}+"
            elif isinstance(self.site_context['integrations'], list):
                integration_count = f"{len(self.site_context['integrations'])}+"

        # Extract comparison context from keyword
        competitor_name = "Alternative"
        if " vs " in keyword.lower():
            items = keyword.lower().split(" vs ")
            competitor_name = items[1].strip().title() if len(items) > 1 else "Alternative"
        elif " versus " in keyword.lower():
            items = keyword.lower().split(" versus ")
            competitor_name = items[1].strip().title() if len(items) > 1 else "Alternative"
        elif " or " in keyword.lower():
            items = keyword.lower().split(" or ")
            competitor_name = items[1].strip().title() if len(items) > 1 else "Alternative"

        # Generate component with props
        component = f"""
<ComparisonTable
  title="Feature Comparison"
  description="See how Brand compares to {competitor_name}"
  competitorName="{competitor_name}"
  items={{[
    {{
      feature: "Ease of Use",
      brand: "Intuitive interface, no technical expertise required",
      competitor: "Moderate learning curve",
      highlight: true
    }},
    {{
      feature: "Platform Integrations",
      brand: "{integration_count} pre-built integrations",
      competitor: "Limited integrations",
      highlight: true
    }},
    {{
      feature: "Attribution Tracking",
      brand: true,
      competitor: true
    }},
    {{
      feature: "Real-time P&L Visibility",
      brand: true,
      competitor: false,
      highlight: true
    }},
    {{
      feature: "AI-Powered Insights",
      brand: "Advanced AI agent chat",
      competitor: "Basic analytics",
      highlight: true
    }},
    {{
      feature: "Custom Reporting",
      brand: "Unlimited custom dashboards",
      competitor: "Limited templates"
    }},
    {{
      feature: "Support",
      brand: "Dedicated success manager",
      competitor: "Email support"
    }},
    {{
      feature: "Scalability",
      brand: "Enterprise-ready",
      competitor: "SMB focused"
    }}
  ]}}
/>
"""
        return component
    
    def _add_roi_calculator(self, content: str) -> str:
        """Add pricing CTA section (replaces iframe embed for better SEO)"""

        # If 'none' mode, add minimal CTA only (educational content)
        if self.brand_mode == 'none':
            cta_section = "\n\nReady to explore solutions?\n\n<a href=\"https://acme.com/pricing\">View Pricing</a>\n\n"
            return content + cta_section

        cta_section = """

Ready to stop wasting budget on guesswork? See how Brand connects your CRM to ad platforms for real-time optimization.

<a href="https://acme.com/pricing" class="group/cta relative inline-flex items-center justify-center gap-1.5 select-none text-center tracking-wide transition-all overflow-hidden cursor-pointer transform-gpu hover:scale-[1.01] active:scale-[0.99] rounded-lg font-funnel-sans text-base font-medium py-2 px-4 h-9 no-underline">
  <div class="absolute inset-0 rounded-lg p-[1px] transition-all duration-500 bg-gradient-to-br from-[#74BD96] via-[#A4FED3] to-[#5fa87f] opacity-90 group-hover/cta:opacity-20">
    <div class="absolute inset-0 rounded-lg transition-all duration-500 bg-gradient-to-br from-[#74BD96]/80 via-[#5fa87f]/60 to-[#A4FED3]/80 group-hover/cta:opacity-0" />
  </div>
  <div class="absolute inset-[1px] bg-gradient-to-br from-[#74BD96]/30 via-[#A4FED3]/20 to-[#5fa87f]/30 rounded-lg backdrop-blur-xl transition-all duration-500 group-hover/cta:opacity-0" />
  <div class="absolute inset-[1px] bg-gradient-to-r from-transparent via-[#90DAB8]/10 to-transparent rounded-lg transition-all duration-500 group-hover/cta:opacity-0" />
  <div class="absolute inset-[1px] opacity-0 transition-all duration-500 bg-white/[0.005] group-hover/cta:opacity-2 rounded-lg backdrop-blur-xl" />
  <div class="relative flex items-center justify-center gap-1.5">
    <span class="font-medium tracking-tight transition-all duration-500 text-[#1B211E] group-hover/cta:bg-gradient-to-r group-hover/cta:from-[#90DAB8] group-hover/cta:via-[#A4FED3] group-hover/cta:to-[#90DAB8] group-hover/cta:bg-clip-text group-hover/cta:text-transparent">
      View Pricing
    </span>
    <Icon name="pixelarticons:trending-up" class="relative top-[0.5px] text-[#1B211E] transition-all duration-500 group-hover/cta:text-[#90DAB8] w-[15px] h-[15px]" />
  </div>
</a>

"""

        # Add before conclusion or at end
        conclusion_pos = content.rfind("## Conclusion")
        if conclusion_pos > 0:
            content = content[:conclusion_pos] + cta_section + content[conclusion_pos:]
        else:
            # If no conclusion, add before FAQ or at end
            faq_pos = content.rfind("## Frequently Asked Questions")
            if faq_pos > 0:
                content = content[:faq_pos] + cta_section + content[faq_pos:]
            else:
                content += cta_section

        return content
    
    def _should_include_roi_calculator(self, keyword: str, content: str) -> bool:
        """Determine if ROI calculator should be included"""
        roi_keywords = [
            'roi', 'return on investment', 'ad spend', 'budget', 'cost',
            'savings', 'efficiency', 'optimization', 'performance'
        ]
        
        keyword_lower = keyword.lower()
        content_lower = content.lower()
        
        return any(kw in keyword_lower or kw in content_lower for kw in roi_keywords)
    
    def _add_internal_links(self, content: str) -> str:
        """Add internal links using dynamic sitemap knowledge and intelligent matching"""

        # Skip if 'none' mode is enabled (educational content only)
        if self.brand_mode == 'none':
            return content

        # Use dynamic links from site context if available
        if self.site_context and 'internal_links' in self.site_context:
            internal_links = self.site_context['internal_links']
        else:
            # Fallback to essential links
            internal_links = {
                "Brand": "https://acme.com/",
                "integrations": "https://acme.com/integrations",
                "pricing": "https://acme.com/pricing",
                "documentation": "https://docs.acme.com",
                "blog": "https://acme.com/blog"
            }

        # First, add pricing CTAs after Brand mentions
        content = self._add_pricing_ctas(content, internal_links.get('pricing', 'https://acme.com/pricing'))

        # Second, add contextual links using link opportunity map
        if self.link_opportunities:
            content = self._add_contextual_links(content, self.link_opportunities)

        # Third, add basic internal links (for key terms like "Brand", "pricing")
        for term, url in internal_links.items():
            # Case-insensitive replacement, but only first occurrence
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)

            def replace_first(match):
                # Don't replace if already in a link
                start_pos = match.start()
                end_pos = match.end()
                surrounding_text = content[max(0, start_pos-20):min(len(content), end_pos+20)]
                if '](http' in surrounding_text or '](' in surrounding_text:
                    return match.group(0)
                return f"[{match.group(0)}]({url})"

            content = pattern.sub(replace_first, content, count=1)

        return content

    def _add_contextual_links(self, content: str, link_map: Dict[str, Dict]) -> str:
        """Add contextual internal links based on intelligent term matching"""

        # Track which links we've already added
        added_links = set()
        max_links_per_term = 2  # Maximum times to link the same term
        max_total_links = 15  # Maximum total contextual links

        # Sort link opportunities by length (longer phrases first for better matching)
        sorted_terms = sorted(link_map.keys(), key=len, reverse=True)

        for term in sorted_terms:
            if len(added_links) >= max_total_links:
                break

            link_data = link_map[term]
            url = link_data['url']
            anchor_text = link_data.get('anchor_text', term)

            # Track occurrences of this term
            link_key = f"{term}:{url}"
            if link_key in added_links:
                continue

            # Create case-insensitive pattern with word boundaries
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)

            # Find all matches
            matches = list(pattern.finditer(content))

            if not matches:
                continue

            # Only link first 1-2 occurrences
            replacements_made = 0
            for match in matches[:max_links_per_term]:
                start_pos = match.start()
                end_pos = match.end()

                # Check if already within a link
                # Look backwards for '[' and forwards for ']('
                before_text = content[max(0, start_pos - 50):start_pos]
                after_text = content[end_pos:min(len(content), end_pos + 50)]

                # Skip if already part of a link
                if '[' in before_text.split('\n')[-1] and '](' in after_text.split('\n')[0]:
                    continue

                # Skip if in a heading
                line_start = content.rfind('\n', max(0, start_pos - 100), start_pos)
                line_text = content[line_start:start_pos] if line_start != -1 else content[:start_pos]
                if line_text.strip().startswith('#'):
                    continue

                # Replace match with link
                matched_text = match.group(0)
                link_replacement = f"[{matched_text}]({url})"

                content = content[:start_pos] + link_replacement + content[end_pos:]

                # Update tracking
                added_links.add(link_key)
                replacements_made += 1

                # Adjust future match positions (content changed)
                offset = len(link_replacement) - len(matched_text)
                matches = [
                    type('Match', (), {
                        'start': lambda m=m: m.start() + offset if m.start() > end_pos else m.start(),
                        'end': lambda m=m: m.end() + offset if m.end() > end_pos else m.end(),
                        'group': m.group
                    })()
                    for m in matches
                ]

                if replacements_made >= max_links_per_term:
                    break

        return content

    def _add_pricing_ctas(self, content: str, pricing_url: str) -> str:
        """Add strategically placed pricing CTAs after Brand mentions (max 2)"""

        # Skip if 'none' mode is enabled (educational content only)
        if self.brand_mode == 'none':
            return content

        # Find all Brand mentions
        brand_pattern = r'\b(Brand)\b(?![^[]*\])'  # Match Brand not already in links
        
        # Split content into sentences to add CTAs contextually
        sentences = content.split('. ')
        modified_sentences = []
        cta_count = 0
        max_ctas = 2  # Limit CTAs to avoid being overly salesy
        
        for i, sentence in enumerate(sentences):
            if cta_count < max_ctas and re.search(brand_pattern, sentence, re.IGNORECASE):
                # Check if this is a good place for a CTA (mentions benefits, features, or solutions)
                cta_keywords = ['helps', 'enables', 'provides', 'offers', 'allows', 'makes', 
                               'solution', 'platform', 'tool', 'feature', 'capability', 'benefit',
                               'streamline', 'optimize', 'improve', 'enhance', 'automate']
                
                if any(keyword in sentence.lower() for keyword in cta_keywords):
                    # Add a subtle, contextual CTA after the sentence
                    if 'pricing' not in sentence.lower() and 'cost' not in sentence.lower():
                        # Choose appropriate CTA based on context
                        if any(word in sentence.lower() for word in ['solution', 'platform', 'tool']):
                            cta = f" ([See pricing]({pricing_url}))"
                        elif any(word in sentence.lower() for word in ['feature', 'capability', 'offers']):
                            cta = f" ([View plans]({pricing_url}))"
                        else:
                            cta = f" ([Learn more]({pricing_url}))"
                        
                        sentence += cta
                        cta_count += 1
            
            modified_sentences.append(sentence)
        
        return '. '.join(modified_sentences)
    
    def _extract_topic_from_url(self, url: str) -> str:
        """Extract readable topic from Reddit/Quora URL for better citation context"""
        # Extract from Reddit: /r/PPC/comments/abc/topic-name/ → "r/PPC: Topic Name"
        reddit_match = re.search(r'/r/(\w+)/comments/\w+/([^/]+)', url)
        if reddit_match:
            subreddit = reddit_match.group(1)
            topic = reddit_match.group(2).replace('-', ' ').replace('_', ' ').title()
            return f"r/{subreddit}: {topic[:60]}"

        # Extract from Quora: /What-is-the-best-way → "What is the best way..."
        quora_match = re.search(r'/([A-Z][^/]+)$', url)
        if quora_match:
            topic = quora_match.group(1).replace('-', ' ')[:70]
            return topic

        return ""

    def _extract_source_title(self, citation: dict) -> str:
        """Extract descriptive title for citation with E-E-A-T signals

        Priorities:
        1. Use existing title from research data (Perplexity provides these)
        2. Extract meaningful title from URL patterns
        3. Fallback to domain/platform name
        """
        url = citation.get('url', '')

        # Priority 1: Use existing title if available
        if citation.get('title') and len(citation['title']) > 10:
            title = citation['title']
            # Clean up overly long titles
            if len(title) > 80:
                title = title[:77] + "..."
            return title

        # Priority 2: Extract from URL patterns

        # Reddit: r/SubredditName/comments/id/descriptive-slug
        reddit_match = re.search(r'/r/(\w+)/comments/\w+/([^/]+)', url)
        if reddit_match:
            subreddit = reddit_match.group(1)
            slug = reddit_match.group(2).replace('_', ' ').replace('-', ' ')
            # Capitalize words for readability
            words = slug.split()
            title = ' '.join(word.capitalize() for word in words if len(word) > 2)
            if len(title) > 60:
                title = title[:57] + "..."
            return f"{title} - r/{subreddit}"

        # Quora: /What-is-the-best-way-to-do-X
        quora_match = re.search(r'/([A-Z][^/]+)$', url)
        if quora_match:
            title = quora_match.group(1).replace('-', ' ')
            if len(title) > 70:
                title = title[:67] + "..."
            return title

        # Authority sites: Extract from domain
        domain_match = re.search(r'//(?:www\.)?([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1)

            # Known authority domains with better labels
            authority_domains = {
                'hubspot.com': 'HubSpot Marketing Resources',
                'searchengineland.com': 'Search Engine Land Industry Report',
                'moz.com': 'Moz SEO Best Practices',
                'marketingland.com': 'Marketing Land Industry Analysis',
                'adweek.com': 'Adweek Marketing Insights',
                'forbes.com': 'Forbes Business Analysis',
                'entrepreneur.com': 'Entrepreneur Industry Report',
                'inc.com': 'Inc. Business Insights',
                'gartner.com': 'Gartner Research Report',
                'forrester.com': 'Forrester Industry Study'
            }

            for domain_key, label in authority_domains.items():
                if domain_key in domain:
                    return label

            # Extract readable name from domain
            clean_domain = domain.replace('www.', '').replace('.com', '').replace('.io', '').replace('.ai', '')
            return clean_domain.title() + ' Industry Resource'

        # Priority 3: Fallback to platform name
        platform = citation.get('platform', 'Industry Source')
        if len(platform) > 70:
            platform = platform[:67] + "..."
        return platform

    def _get_source_type(self, citation: dict) -> str:
        """Get descriptive source type for E-E-A-T credibility signals"""

        url = citation.get('url', '')

        # Check citation type first
        if citation.get('type') == 'serp':
            # Research/authority sources get higher E-E-A-T labels
            if any(domain in url for domain in ['.edu', '.gov', '.org']):
                return "Educational/Government Resource"
            elif any(keyword in url.lower() for keyword in ['research', 'study', 'white-paper', 'whitepaper']):
                return "Research Study"
            elif any(keyword in url.lower() for keyword in ['report', 'benchmark', 'survey', 'data']):
                return "Industry Report"
            elif any(keyword in url.lower() for keyword in ['guide', 'best-practices', 'how-to']):
                return "Expert Guide"
            else:
                return "Industry Analysis"

        # Community sources
        elif 'reddit.com' in url:
            return "Community Discussion"

        elif 'quora.com' in url:
            return "Expert Q&A"

        # Default for unknown types
        else:
            return "Industry Resource"

    def _add_citations(self, content: str, research_data: Dict[str, Any], style: str = "standard") -> str:
        """Add contextual citations with descriptive anchor text

        For research style: Only uses authoritative SERP citations (no community sources)
        For other styles: Uses all citation types (SERP, Reddit, Quora)
        """
        # Collect all citations from research
        all_citations = []

        # For research style, skip community citations - only use authoritative sources
        community_data = (research_data.get('community') or {})
        if style != "research":
            # Extract Reddit citations (only for non-research styles)
            reddit_data = (community_data.get('reddit') or {})
            reddit_citations = reddit_data.get('citations', [])
            for citation in reddit_citations:
                if isinstance(citation, dict) and citation.get('url'):
                    all_citations.append({
                        'url': citation['url'],
                        'platform': citation.get('platform', 'Reddit'),
                        'type': 'community'
                    })

            # Extract Quora citations (only for non-research styles)
            quora_data = (community_data.get('quora') or {})
            quora_citations = quora_data.get('citations', [])
            for citation in quora_citations:
                if isinstance(citation, dict) and citation.get('url'):
                    all_citations.append({
                        'url': citation['url'],
                        'platform': citation.get('platform', 'Quora'),
                        'type': 'community'
                    })

        # Extract SERP/Perplexity citations (from sonar-deep-research/sonar-reasoning-pro)
        # These are highest priority - authoritative research sources
        serp_data = (research_data.get('serp') or {})
        serp_analysis = (serp_data.get('serp_analysis') or {})
        serp_citations = serp_analysis.get('citations', [])

        for citation in serp_citations:
            # Perplexity citations can be strings (URLs) or dicts
            if isinstance(citation, str):
                all_citations.append({
                    'url': citation,
                    'platform': 'Research Source',
                    'type': 'serp'
                })
            elif isinstance(citation, dict):
                # Extract URL from dict (Perplexity format varies)
                url = citation.get('url') or citation.get('link') or str(citation)
                if url and url.startswith('http'):
                    title = citation.get('title', citation.get('name', 'Research Source'))
                    all_citations.append({
                        'url': url,
                        'platform': title,
                        'type': 'serp'
                    })

        if not all_citations:
            return content

        # Find sentences that make claims needing citations
        # Comprehensive patterns optimized for research-style content
        all_citation_patterns = [
            # === RESEARCH TERMINOLOGY (Primary for research style) ===
            r'((?:our|the) analysis (?:reveals|shows|demonstrates|indicates)[^.]+\.)',
            r'(data (?:demonstrates|shows|reveals|indicates|suggests)[^.]+\.)',
            r'((?:research|industry) (?:data|findings|analysis) (?:shows|indicates|reveals|confirms)[^.]+\.)',
            r'(market analysis (?:suggests|shows|reveals|indicates)[^.]+\.)',
            r'((?:quantitative|empirical) (?:assessment|evidence|analysis) (?:indicates|supports|shows)[^.]+\.)',
            r'(comparative evaluation (?:shows|reveals|indicates)[^.]+\.)',

            # === STATISTICAL CLAIMS (High priority for all styles) ===
            r'((?:averaging|average|median) \$?\d+(?:[.,]\d+)?(?:%| (?:per|each|in))?[^.]+\.)',
            r'((?:average|median) [^.]*?\$\d+(?:[.,]\d+)?[^.]+\.)',  # Flexible: average ... $70.11 ... .
            r'(\d+(?:[.,]\d+)?% (?:increase|decrease|reduction|improvement|growth|of|higher|lower)[^.]+\.)',
            r'((?:from |range of )?\$\d+(?:[.,]\d+)? (?:to|-)?\s?\$?\d+(?:[.,]\d+)?[^.]+\.)',
            r'(\d+–\d+% [^.]+\.)',

            # === INDUSTRY/EXPERT ATTRIBUTION ===
            r'(according to [^.]+\.)',
            r'((?:industry|leading|performance) (?:experts|marketers|analysts|professionals) (?:argue|suggest|recommend|agree)[^.]+\.)',
            r'(experts (?:recommend|suggest|agree|argue)[^.]+\.)',

            # === STUDY/RESEARCH REFERENCES ===
            r'(studies (?:show|indicate|reveal|suggest|demonstrate)[^.]+\.)',
            r'(research (?:shows|indicates|reveals|suggests|demonstrates)[^.]+\.)',
            r'((?:a|the) (?:study|survey|report|analysis) (?:found|showed|revealed|indicated)[^.]+\.)',

            # === CLAIM LANGUAGE ===
            r'((?:businesses|companies|advertisers|organizations) (?:report|experience|achieve|see)[^.]+\d+[^.]*\.)',
            r'(this (?:shows|demonstrates|reveals|indicates)[^.]+\.)',
            r'((?:data|evidence|analysis) (?:confirms|validates|supports)[^.]+\.)',

            # === LEGACY PATTERNS (for backward compatibility) ===
            r'(users report[^.]+\.)',
            r'(many (?:users|businesses|companies)[^.]+\.)',
        ]

        # Filter patterns based on style
        if style == "research":
            # Research style uses ALL patterns for maximum coverage
            citation_patterns = all_citation_patterns
        else:
            # Other styles skip research-specific terminology patterns
            citation_patterns = [p for p in all_citation_patterns
                               if not p.startswith(r'((?:our|the) analysis')
                               and not p.startswith(r'((?:quantitative|empirical)')]

        citation_index = 0
        used_citations = []  # Track which citations were actually used

        for pattern in citation_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                if citation_index < len(all_citations):
                    citation = all_citations[citation_index]
                    citation_number = citation_index + 1

                    # Add numbered inline citation as linked superscript: [1], [2], etc.
                    # Links to corresponding citation at bottom with #cite-N anchor
                    replacement = match.group(1).rstrip('.') + f' <a href="#cite-{citation_number}" class="citation-ref">[{citation_number}]</a>.'
                    content = content.replace(match.group(1), replacement)

                    used_citations.append(citation)
                    citation_index += 1

        # Add references section if citations were used (only if 2+ citations)
        if citation_index >= 2 and "## Sources" not in content and "## References" not in content:
            # Use CitationsSection component (collapsible by default)
            references = '\n\n<CitationsSection>\n\n'

            # Add intro text with E-E-A-T signals
            references += "> This article cites the following authoritative sources:\n\n"

            # Build numbered reference list with descriptive titles and anchor IDs
            for i, citation in enumerate(used_citations, 1):
                # Extract descriptive title for E-E-A-T
                title = self._extract_source_title(citation)

                # Get source type for credibility signals
                source_type = self._get_source_type(citation)

                # Build reference entry with anchor ID: <span id="cite-1">[1]</span> [Title](URL) - Type
                references += f'<span id="cite-{i}">[{i}]</span> [{title}]({citation["url"]}) - {source_type}\n'

            references += '\n</CitationsSection>\n'
            content += references

        return content
    
    def _determine_category(self, keyword: str, content: str) -> str:
        """Determine content category"""
        categories = {
            'integration': ['integration', 'api', 'connect', 'sync', 'webhook'],
            'analytics': ['analytics', 'metrics', 'reporting', 'dashboard', 'data'],
            'automation': ['automation', 'automate', 'workflow', 'ai', 'automatic'],
            'advertising': ['ads', 'advertising', 'campaign', 'ad spend', 'ppc'],
            'attribution': ['attribution', 'tracking', 'lead', 'conversion'],
            'strategy': ['strategy', 'optimize', 'roi', 'growth', 'scaling']
        }
        
        keyword_lower = keyword.lower()
        content_lower = content.lower()[:1000]  # Check first 1000 chars
        
        scores = {}
        for category, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in keyword_lower or kw in content_lower)
            scores[category] = score
        
        # Return category with highest score
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return 'general'
    
    def _calculate_read_time(self, content: str) -> int:
        """Calculate read time in minutes"""
        words = len(content.split())
        return max(1, round(words / 200))  # 200 words per minute
    
    def _generate_title(self, content: str, keyword: str, style: str) -> str:
        """Generate SEO-optimized title based on style"""
        # Try to extract title from content
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Generate based on style
            year = datetime.now().year
            
            if style == "comparison":
                title = f"{keyword.title()} - Complete Comparison {year}"
            elif style == "guide":
                title = f"How to {keyword.title()}: Complete Guide"
            elif style == "research":
                title = f"{keyword.title()} Research: Data & Insights {year}"
            elif style == "news":
                title = f"{keyword.title()}: Latest Updates & Trends"
            elif style == "category":
                title = f"Best {keyword.title()} Tools & Solutions {year}"
            else:
                title = f"{keyword.title()} - Everything You Need to Know"
        
        # Ensure keyword is in title
        if keyword.lower() not in title.lower():
            title = f"{keyword.title()}: {title}"
        
        # Optimize length
        if len(title) > 60:
            title = title[:57] + "..."
        elif len(title) < 40:
            title = f"{title} | Brand"
            
        return title
    
    def _generate_meta_description(
        self,
        content: str,
        keyword: str,
        style: str = "standard"
    ) -> str:
        """
        Generate SEO-optimized meta description based on SEO best practices.

        Rules:
        1. Length: 150-160 chars (never empty, never >160)
        2. Primary keyword in first 50 chars
        3. Compelling hook addressing user pain
        4. End with soft CTA

        Args:
            content: The article content
            keyword: Primary keyword
            style: Content style for context
        """
        # Load SEO config for CTA examples
        config_path = Path(__file__).parent.parent / 'config' / 'seo_optimization.json'
        cta_examples = ["Get started free", "See how", "Learn more", "Compare now"]
        hooks = ["Compare the best", "Find out which", "Discover why", "See how to"]

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    seo_config = json.load(f)
                    meta_rules = seo_config.get('meta_description_rules', {})
                    cta_examples = meta_rules.get('cta_examples', cta_examples)
                    hooks = meta_rules.get('hooks', hooks)
            except Exception:
                pass

        # Determine content style for hook selection
        is_comparison = style in ['comparison', 'top-compare', 'category']
        is_guide = style in ['guide']

        # Extract first meaningful paragraph (skip headings, frontmatter)
        first_para_match = re.search(r'^(?!#|\*\*|---)[A-Z][^#\n]{50,}', content.strip(), re.MULTILINE)

        if first_para_match:
            raw_description = first_para_match.group(0).strip()
            # Clean up markdown
            raw_description = re.sub(r'\*\*|__|\[|\]|\(|\)|`', '', raw_description)
            raw_description = re.sub(r'\s+', ' ', raw_description).strip()
        else:
            raw_description = ""

        # Build description with keyword in first 50 chars
        keyword_title = keyword.title() if len(keyword) < 30 else keyword[:30].title()

        # Select appropriate hook based on style
        if is_comparison:
            hook = f"Compare the best {keyword_title}."
        elif is_guide:
            hook = f"Learn how to {keyword.lower()}."
        else:
            hook = f"Discover {keyword_title}."

        # Ensure keyword is in first 50 chars
        if keyword.lower() in hook.lower()[:50]:
            description = hook
        else:
            description = f"{keyword_title}: {hook}"

        # Add value proposition from content
        if raw_description and len(raw_description) > 30:
            # Extract key value from first para
            value_snippet = raw_description[:80]
            # Cut at sentence or word boundary
            last_period = value_snippet.rfind('.')
            last_space = value_snippet.rfind(' ')
            if last_period > 40:
                value_snippet = value_snippet[:last_period + 1]
            elif last_space > 40:
                value_snippet = value_snippet[:last_space]

            # Add if space allows
            combined = f"{description} {value_snippet}".strip()
            if len(combined) <= 130:
                description = combined

        # Select CTA based on style
        if is_comparison:
            cta = "Compare now."
        elif is_guide:
            cta = "Get started free."
        else:
            cta = "See how."

        # Add CTA if room allows
        if len(description) + len(cta) + 1 <= 160:
            description = f"{description} {cta}"

        # Ensure minimum length (120 chars)
        if len(description) < 120:
            filler = " Expert insights and proven strategies."
            if len(description) + len(filler) <= 160:
                description = description.rstrip('.') + f".{filler}"

        # Ensure maximum length (160 chars)
        if len(description) > 160:
            # Cut at word boundary, leave room for ellipsis
            description = description[:157]
            last_space = description.rfind(' ')
            if last_space > 130:
                description = description[:last_space] + "..."
            else:
                description = description + "..."

        # Final validation: never empty
        if not description or len(description) < 50:
            description = f"{keyword_title}: Expert insights, practical tips, and proven strategies for {keyword.lower()}. Get started free."

        return description
    
    def _create_slug(self, title: str) -> str:
        """Create URL slug from title"""
        # Convert to lowercase and replace spaces
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        
        # Remove common words at end
        slug = re.sub(r'-(the|a|an|and|or|but|in|on|at|to|for)$', '', slug)

        # Ensure short length for filesystem compatibility (Astro/Windows)
        if len(slug) > 40:
            # Try to cut at word boundary
            slug = slug[:40]
            last_dash = slug.rfind('-')
            if last_dash > 25:
                slug = slug[:last_dash]

        return slug

    def _process_external_links(self, content: str) -> str:
        """
        Process external links for SEO based on best practices.

        Rules:
        1. For NEW content (this formatter is only used for new content):
           - Add rel="nofollow" to external links by default
           - Exception: Official partners, authority sites (academic, government)
        2. For EXISTING content (not handled here):
           - NEVER modify existing link attributes (handled at update time)

        This ensures we control link equity and protect backlink partnerships.
        """
        # Load exception domains from SEO config
        config_path = Path(__file__).parent.parent / 'config' / 'seo_optimization.json'
        dofollow_domains = [
            'acme.com',  # Internal links
            'github.com',  # Developer authority
            'docs.google.com',  # Official docs
            'wikipedia.org',  # Reference authority
            'anthropic.com',  # Partner
        ]

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    seo_config = json.load(f)
                    # Add any configured partner domains
                    ext_rules = seo_config.get('external_link_rules', {})
                    new_rules = ext_rules.get('new_articles', {})
                    # Could add partner domains from config here
            except Exception:
                pass

        # Pattern to match markdown links: [text](url)
        # This catches external links (http/https) but not internal (/)
        link_pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'

        def add_nofollow(match):
            text = match.group(1)
            url = match.group(2)

            # Check if this domain should keep dofollow
            for domain in dofollow_domains:
                if domain in url:
                    return match.group(0)  # Keep original

            # For all other external links, we note they should have nofollow
            # In Astro MDX, we use HTML anchor tags for nofollow
            # Return as HTML: <a href="url" target="_blank" rel="nofollow">text</a>
            return f'<a href="{url}" target="_blank" rel="nofollow">{text}</a>'

        # Process external links
        processed = re.sub(link_pattern, add_nofollow, content)

        return processed

    def _generate_feature_byline(self, keyword: str, content: str) -> str:
        """Generate a compelling byline for feature pages (Phase 6.3).

        Bylines are short, benefit-focused statements that appear below the title.
        Examples:
        - "Consolidate all your ad data in one dashboard"
        - "Stop wasting budget on underperforming ads"
        """
        # Extract first benefit-style statement from content
        benefit_patterns = [
            r"helps? (?:you |businesses? )?(.*?)[.\n]",
            r"enables? (?:you |businesses? )?(.*?)[.\n]",
            r"(?:Stop|Start|Finally) (.*?)[.\n]",
            r"Save (?:time|money|hours) (?:on |by )?(.*?)[.\n]"
        ]

        content_first_500 = content[:500].lower()
        for pattern in benefit_patterns:
            match = re.search(pattern, content_first_500, re.IGNORECASE)
            if match:
                byline = match.group(0).strip().rstrip('.')
                if 20 < len(byline) < 100:
                    return byline.capitalize()

        # Fallback to keyword-based byline
        keyword_words = keyword.split()
        if len(keyword_words) >= 2:
            return f"Master {keyword} with powerful automation"

        return f"Powerful {keyword} tools for growing businesses"

    def _extract_feature_list(self, content: str) -> List[Dict[str, str]]:
        """Extract feature list from content for frontmatter (Phase 6.3).

        Returns list of features with name and brief description.
        Used by Astro components for feature grids/cards.
        """
        features = []

        # Look for H3 feature sections
        h3_pattern = r"###\s*(?:Feature \d+:?\s*)?(.+?)[\n]"
        h3_matches = re.findall(h3_pattern, content)

        for match in h3_matches[:6]:  # Max 6 features
            feature_name = match.strip()
            # Skip if it's a generic section name
            if any(skip in feature_name.lower() for skip in ['faq', 'conclusion', 'get started', 'results']):
                continue

            # Try to find description after the heading
            desc_pattern = rf"###\s*(?:Feature \d+:?\s*)?{re.escape(feature_name)}[\n]+\*\*What it does:\*\*\s*(.+?)[\n]"
            desc_match = re.search(desc_pattern, content, re.IGNORECASE)

            description = ""
            if desc_match:
                description = desc_match.group(1).strip()
            else:
                # Fallback: get first sentence after heading
                section_pattern = rf"###\s*(?:Feature \d+:?\s*)?{re.escape(feature_name)}[\n]+([^#\n].+?)[.\n]"
                section_match = re.search(section_pattern, content)
                if section_match:
                    description = section_match.group(1).strip()

            if feature_name and len(feature_name) > 3:
                features.append({
                    'name': feature_name,
                    'description': description[:100] if description else ''
                })

        # If no H3 features found, extract from Key Features section
        if not features:
            key_features_match = re.search(
                r"##\s*Key Features.*?(?=##|$)",
                content,
                re.DOTALL | re.IGNORECASE
            )
            if key_features_match:
                section = key_features_match.group(0)
                bullet_pattern = r"[-*]\s*\*\*(.+?):\*\*\s*(.+?)[\n]"
                bullets = re.findall(bullet_pattern, section)
                for name, desc in bullets[:6]:
                    features.append({
                        'name': name.strip(),
                        'description': desc.strip()[:100]
                    })

        return features

    def _generate_tags(self, keyword: str, content: str, style: str) -> List[str]:
        """Generate SEO-optimized tags (max 5, Title Case, astro-site compliant)"""

        # Tag vocabulary from astro-site (Title Case)
        tag_vocab = {
            'Brand Methodology': 'Brand Methodology',
            'industry category': 'Industry Category',
            'attribution': 'Attribution',
            'automation': 'Automation',
            'crm integration': 'CRM Integration',
            'ad optimization': 'Ad Optimization',
            'media buying': 'Media Buying',
            'advertising': 'Advertising',
            'ai': 'AI',
            'analytics': 'Analytics',
            'strategy': 'Strategy',
            'guide': 'Guide',
            'product': 'Product',
            'engineering': 'Engineering'
        }

        # Start with Brand Methodology as primary tag (80% of content should have this)
        tags = ['Brand Methodology']

        # Extract relevant tags from keyword and content
        keyword_lower = keyword.lower()
        content_lower = content.lower()[:2000]

        # Check keyword matches
        for key, tag in tag_vocab.items():
            if tag not in tags and key in keyword_lower:
                tags.append(tag)
                if len(tags) >= 5:
                    break

        # Check content matches (prioritize by relevance)
        if len(tags) < 5:
            relevance_scores = {}
            for key, tag in tag_vocab.items():
                if tag not in tags:
                    count = content_lower.count(key)
                    if count > 2:  # Must appear at least 3 times
                        relevance_scores[tag] = count

            # Add top scoring tags
            for tag in sorted(relevance_scores, key=relevance_scores.get, reverse=True):
                if tag not in tags:
                    tags.append(tag)
                    if len(tags) >= 5:
                        break

        # Add style-based tag if space available
        style_tags = {
            'guide': 'Guide',
            'comparison': 'Strategy',
            'research': 'Analytics',
            'news': 'Product',
            'feature': 'Product'  # Feature pages are product-focused
        }
        if len(tags) < 5 and style in style_tags and style_tags[style] not in tags:
            tags.append(style_tags[style])

        return tags[:5]  # Max 5 tags
    
    def _extract_h2_sections(self, content: str) -> List[str]:
        """Extract H2 headings"""
        h2_matches = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
        return [h.strip() for h in h2_matches]
    
    def _strip_existing_frontmatter(self, content: str) -> str:
        """Strip any existing YAML frontmatter and imports from content (prevents duplicates)"""
        content = content.strip()

        # Strip frontmatter if present
        if content.startswith('---'):
            lines = content.split('\n')
            in_frontmatter = False
            frontmatter_end = 0

            for i, line in enumerate(lines):
                if line.strip() == '---':
                    if not in_frontmatter:
                        in_frontmatter = True
                    else:
                        frontmatter_end = i + 1
                        break

            if frontmatter_end > 0:
                content = '\n'.join(lines[frontmatter_end:]).lstrip('\n')
                logger.debug(f"Stripped existing frontmatter ({frontmatter_end} lines)")

        # Strip import statements (we add our own)
        lines = content.split('\n')
        content_lines = []
        for line in lines:
            # Skip import lines
            if line.strip().startswith('import ') or line.strip().startswith('import{'):
                continue
            # Skip lines that are just multiple imports joined with periods (malformed)
            if 'import {' in line and line.count('import') > 1:
                continue
            content_lines.append(line)

        return '\n'.join(content_lines).lstrip('\n')

    def _build_complete_mdx(self, frontmatter: Dict[str, Any], content: str,
                        keyword: str, h2_sections: List[str],
                        research_data: Optional[Dict] = None, style: str = "standard") -> str:
        """Build complete MDX file with all components - aligned with astro-site schema"""

        # Strip any existing frontmatter from content (Gemini sometimes includes it)
        content = self._strip_existing_frontmatter(content)

        # Generate slug and reading time
        slug = self._generate_slug(keyword)
        reading_time = self._calculate_reading_time(content)

        # Build FAQ array from PAA questions
        paa_questions = []
        if research_data:
            paa_questions = research_data.get('paa_questions', [])
        faq_items = self._build_faq_array(paa_questions, content)

        # Build imports based on style
        base_imports = [
            "import { Image } from 'astro:assets';",
            "import { Icon } from 'astro-icon/components';",
            "import FAQSection from '@/components/sections/FAQSectionAstro.astro';",
            "import ComparisonTable from '@/components/sections/ComparisonTable.astro';",
        ]

        # Add CitationsSection import if citations were added to content
        if 'CitationsSection' in content:
            base_imports.append("import CitationsSection from '@/components/content/CitationsSection.astro';")

        # Add top-compare specific imports
        if frontmatter.get('category') == 'Comparison' or 'top-compare' in str(frontmatter.get('tags', [])):
            base_imports.append("import { SolutionCard, ComparisonSummary, ServicesList, MetadataBadges } from '@/components/mdx';")

        # Escape quotes in frontmatter strings
        title_escaped = frontmatter['title'].replace("'", "''")
        desc_escaped = frontmatter['description'].replace("'", "''")
        seo_title = title_escaped[:60] if len(title_escaped) > 60 else title_escaped

        # Generate JSON-LD schema markup (BlogPosting + FAQPage + ClaimReview)
        canonical_url = f"https://www.acme.com/blog/{slug}"
        schema_markup = self.schema_generator.generate_complete_schema_markup(
            frontmatter=frontmatter,
            content=content
        )
        schema_json = json.dumps(schema_markup, separators=(',', ':'))  # Compact JSON

        # Build frontmatter YAML
        mdx_parts = [
            "---",
            f"title: '{title_escaped}'",
            f"publishDate: '{frontmatter['publishDate']}'",
            f"description: '{desc_escaped}'",
            f"author: '{frontmatter['author']}'",
            f"image: {json.dumps(frontmatter['image'])}",
            f"tags: {json.dumps(frontmatter['tags'])}",
            f"category: '{frontmatter['category']}'",
            f"categories: {json.dumps([frontmatter['category']])}",
            "featured: false",
            "draft: true",
            f"canonical: '{canonical_url}'",
            f"readingTime: '{reading_time}'",
            "seo:",
            f"  title: '{seo_title}'",
            f"  description: '{desc_escaped}'",
            f"  focusKeyword: '{keyword}'",
            "  schemaType: 'Article'",
            f"  jsonld: '{schema_json.replace(chr(39), chr(39) + chr(39))}'",  # Escape single quotes
        ]

        # Add FAQ block if we have items
        if faq_items:
            mdx_parts.append("faq:")
            for item in faq_items[:10]:
                q_escaped = item['question'].replace("'", "''").replace('"', '\\"')
                a_escaped = item['answer'].replace("'", "''").replace('"', '\\"')
                mdx_parts.append(f"  - question: \"{q_escaped}\"")
                mdx_parts.append(f"    answer: \"{a_escaped}\"")

        mdx_parts.extend([
            "---",
            "",
            *base_imports,
            "",
            content,
            ""
        ])

        return "\n".join(mdx_parts)
    
    def _extract_howto_steps(self, content: str) -> List[Dict[str, Any]]:
        """Extract HowTo steps from guide content"""
        steps = []
        
        # Find step patterns
        step_pattern = r'^##\s*Step\s*(\d+)[:\s]+(.+)$'
        matches = re.finditer(step_pattern, content, re.MULTILINE)
        
        for match in matches:
            step_num = match.group(1)
            step_name = match.group(2).strip()
            
            # Get step content
            start = match.end()
            next_heading = re.search(r'^#{1,6}\s', content[start:], re.MULTILINE)
            
            if next_heading:
                step_content = content[start:start + next_heading.start()].strip()
            else:
                step_content = content[start:start + 500].strip()
            
            steps.append({
                "@type": "HowToStep",
                "name": step_name,
                "text": step_content[:200] + "..." if len(step_content) > 200 else step_content,
                "position": int(step_num)
            })
        
        return steps[:10]  # Limit to 10 steps
    
    def _extract_faq_items_for_schema(self, content: str) -> List[Dict[str, Any]]:
        """Extract FAQ items from content for schema"""
        faq_items = []
        
        # Look for FAQ section
        faq_section_match = re.search(r'^##\s*(?:FAQ|Frequently Asked Questions)\s*$', 
                                     content, re.MULTILINE | re.IGNORECASE)
        
        if faq_section_match:
            faq_start = faq_section_match.end()
            # Find next H2 or end of content
            next_h2 = re.search(r'^##\s+(?!#)', content[faq_start:], re.MULTILINE)
            faq_end = faq_start + next_h2.start() if next_h2 else len(content)
            
            faq_content = content[faq_start:faq_end]
            
            # Extract questions (H3 headings)
            question_pattern = r'^###\s*([^#\n]+\?)\s*$'
            questions = re.finditer(question_pattern, faq_content, re.MULTILINE)
            
            for match in questions:
                question = match.group(1).strip()
                
                # Find the answer
                start = match.end()
                next_heading = re.search(r'^#{1,6}\s', faq_content[start:], re.MULTILINE)
                
                if next_heading:
                    answer = faq_content[start:start + next_heading.start()].strip()
                else:
                    answer = faq_content[start:].strip()
                
                if answer:
                    faq_items.append({
                        "@type": "Question",
                        "name": question,
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": answer[:500] + "..." if len(answer) > 500 else answer
                        }
                    })
        
        return faq_items[:15]  # Limit to 15 FAQ items