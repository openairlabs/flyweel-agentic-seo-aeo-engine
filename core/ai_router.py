"""Smart AI Router - Right model for each job, no BS"""
import os
import re
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI
import aiohttp
import json

logger = logging.getLogger(__name__)


def _load_seo_config() -> Dict[str, Any]:
    """Load SEO optimization rules from config"""
    config_path = Path(__file__).parent.parent / 'config' / 'seo_optimization.json'
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load SEO config: {e}")
    return {}


# Cache at module level
_SEO_CONFIG = _load_seo_config()


def _load_icp_context_for_research() -> str:
    """Load ICP context optimized for research prompts - business model buckets only"""
    return """
RELEVANCE FILTER - Prioritize insights from these BUSINESS MODELS:
- Sales-led businesses (ad spend → lead capture → sales team → close)
- Pipeline-led businesses (marketing → nurture → convert over time)
- Service businesses (enquiry → quote → job → invoice, 60-90 day cycles)

Key roles: Business owners, marketers, and media buyers dealing with operational challenges.

"""


# Cache at module level
_ICP_RESEARCH_CONTEXT = _load_icp_context_for_research()

class SmartAIRouter:
    async def _get_empty_list(self):
        """Coroutine that returns an empty list."""
        return []

    async def _get_none(self):
        """Coroutine that returns None."""
        return None
    def __init__(self):
        # Initialize only what we need
        self.perplexity_key = os.getenv('PERPLEXITY_API_KEY')
        self.gemini_key = os.getenv('GOOGLE_API_KEY')
        self.nebius_key = os.getenv('NEBIUS_API_KEY')

        # Load Astro MDX template for structure reference
        self.template_content = self._load_template()
        
        # Setup clients
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
            self.gemini_model = 'gemini-3-flash-preview'
        else:
            self.gemini_client = None
            self.gemini_model = None

        if self.nebius_key:
            # Nebius uses OpenAI-compatible API format
            self.nebius = AsyncOpenAI(
                api_key=self.nebius_key,
                base_url="https://api.studio.nebius.com/v1/"
            )
            # Token Factory API for embeddings (BGE-EN-ICL)
            self.nebius_embed = AsyncOpenAI(
                api_key=self.nebius_key,
                base_url="https://api.tokenfactory.nebius.com/v1/"
            )
        else:
            self.nebius = None
            self.nebius_embed = None

        self.session = None

        # Model assignments by task type (quality-optimized)
        # Creative/extraction: best Arena ELO + structured output
        self.model_creative = "moonshotai/Kimi-K2.5"
        # Precision editing: best instruction following + reasoning (tau2-Bench 87.4)
        self.model_precision = "zai-org/GLM-4.7-FP8"

        # Model fallback chain for Nebius (graceful degradation)
        self.nebius_models = [
            "moonshotai/Kimi-K2.5",                  # Primary — highest Arena ELO, best tool use
            "zai-org/GLM-4.7-FP8",                   # Fallback 1 — strongest benchmarks, top tau2
            "Qwen/Qwen3-235B-A22B-Instruct-2507",   # Fallback 2 — best prose quality
            "deepseek-ai/DeepSeek-V3.2",             # Fallback 3 — reliable all-rounder
        ]

    async def _nebius_with_fallback(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        purpose: str = "extraction"
    ) -> Optional[str]:
        """Make Nebius API call with automatic fallback through model chain.

        Args:
            messages: Chat messages for the API call
            temperature: Model temperature
            max_tokens: Maximum tokens to generate
            purpose: Description for logging

        Returns:
            Response content or None if all models fail
        """
        if not self.nebius:
            logger.warning("No Nebius client available")
            return None

        for model in self.nebius_models:
            try:
                response = await self.nebius.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                result = response.choices[0].message.content.strip()
                if result:
                    if model != self.nebius_models[0]:
                        logger.info(f"   ✓ {purpose} succeeded with fallback: {model}")
                    return result
            except Exception as e:
                logger.warning(f"   ⚠️  {model} failed for {purpose}: {e}")
                continue

        logger.error(f"   ✗ All Nebius models failed for {purpose}")
        return None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _build_brand_links_from_sitemap(self, site_context: Optional[Dict[str, Any]]) -> str:
        """Build brand link examples from real sitemap data

        Args:
            site_context: Site context with internal_links from live sitemap

        Returns:
            Formatted string with real brand links for prompt injection
        """
        if not site_context or 'internal_links' not in site_context:
            # Absolute fallback - just homepage
            return "- Brand → [Brand](https://acme.com)"

        links = site_context['internal_links']
        brand_links = []

        # 1. Homepage (highest priority)
        homepage = links.get('Brand') or links.get('Home') or links.get('Visit Website') or 'https://acme.com'
        brand_links.append(f"- Brand → [Brand]({homepage})")

        # 2. Brand Methodology (look for blog post or dedicated page)
        brand_methodology_link = None
        for text, url in links.items():
            if 'Brand Methodology' in url.lower():
                brand_methodology_link = url
                break
        if brand_methodology_link:
            brand_links.append(f"- Brand Methodology → [Brand Methodology]({brand_methodology_link})")

        # 3. Integrations page
        integrations = links.get('Integrations') or links.get('See CRM integrations') or links.get('Go to Integrations')
        if integrations:
            brand_links.append(f"- Integrations → [integrations]({integrations})")

        # 4. Pricing page
        pricing = links.get('Pricing') or links.get('See Pricing')
        if pricing:
            brand_links.append(f"- Pricing → [pricing]({pricing})")

        # 5. AI Agent page
        ai_agent = links.get('AI Agent') or links.get('Learn About Our Agent')
        if ai_agent:
            brand_links.append(f"- AI Agent → [AI Agent]({ai_agent})")

        # 6. Tools page
        tools = links.get('Tools') or links.get('Access free tools for ads.')
        if tools:
            brand_links.append(f"- Tools → [tools]({tools})")

        return '\n'.join(brand_links)

    def _load_template(self) -> str:
        """Load the Astro MDX template for structure reference"""
        template_path = os.path.join(os.path.dirname(__file__), '..', '_template.mdx')
        try:
            with open(template_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Template file not found at {template_path}")
            return ""

    async def research(self, query: str, search_type: str = "web") -> Dict[str, Any]:
        """Perplexity for web search - it's the best at this"""
        if not self.perplexity_key:
            return {"error": "No Perplexity key"}
            
        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json"
        }
        
        # Use the right model for the job
        model = "sonar-deep-research" if search_type == "deep" else "sonar-reasoning-pro"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": query}],
            "search_domain_filter": ["perplexity.ai"] if search_type == "citations" else None,
            "return_citations": True,
            "search_recency_filter": "month",
            "temperature": 0.2
        }
        
        async with self.session.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"error": f"Perplexity API error: {response.status}"}
    
    async def extract(self, text: str, extraction_type: str = "insights") -> str:
        """Nebius for extraction - fast and cheap"""
        if not self.nebius:
            return "No Nebius client"
            
        prompts = {
            "insights": "Extract key insights and pain points from this discussion:",
            "questions": "Extract all questions people are asking:",
            "citations": "Extract all factual claims with sources:"
        }
        
        response = await self.nebius.chat.completions.create(
            model=self.model_creative,
            messages=[{
                "role": "system",
                "content": prompts.get(extraction_type, prompts["insights"])
            }, {
                "role": "user",
                "content": text
            }],
            temperature=0.1,
            max_tokens=2000
        )

        return response.choices[0].message.content

    async def optimize_title_seo(
        self,
        content: str,
        keyword: str,
        style: str = "standard",
        gsc_primary_keyword: Optional[str] = None
    ) -> str:
        """
        Optimize H1 title for SEO/AEO using Gemini with enhanced SEO rules.

        Based on SEO best practices:
        1. Use EXACT #1 keyword from GSC (if provided)
        2. Include current year for freshness
        3. Add numbers for list/comparison content
        4. Add value indicators (Reviewed, Free, etc.)
        5. Stay under 60 chars ideal, max 70
        6. Avoid banned words

        Args:
            content: Full MDX content
            keyword: Target keyword
            style: Content style (comparison, guide, etc.)
            gsc_primary_keyword: Exact GSC primary keyword (use verbatim)
        """
        if not self.gemini_client:
            logger.warning("No Gemini client available for title optimization")
            return content

        # Extract frontmatter
        if not content.strip().startswith('---') or content.count('---') < 2:
            logger.warning("Invalid content structure for title optimization")
            return content

        parts = content.split('---', 2)
        if len(parts) < 3:
            return content

        frontmatter = parts[1]
        body = parts[2]

        # Extract current title from frontmatter
        title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
        if not title_match:
            logger.warning("No title found in frontmatter")
            return content

        current_title = title_match.group(1).strip('"\'')

        # Get SEO rules from config
        title_rules = _SEO_CONFIG.get('title_rules', {})
        banned_words = title_rules.get('banned_words', [
            "comprehensive", "ultimate", "guide to", "dive in", "delve",
            "leverage", "utilize", "optimize"
        ])
        value_indicators = title_rules.get('value_indicators', [
            "Reviewed", "Free", "For Beginners", "Step-by-Step", "Updated"
        ])
        max_length = title_rules.get('max_length', 70)
        ideal_length = title_rules.get('ideal_length', [50, 60])

        # Current year for freshness
        current_year = datetime.now().strftime("%Y")

        # Determine if this is list/comparison content (needs numbers)
        is_comparison = style in ['comparison', 'top-compare', 'category']
        is_guide = style in ['guide']
        is_informational = style in ['standard', 'research']

        # Build style-specific requirements
        style_requirements = ""
        if is_comparison:
            style_requirements = f"""
**COMPARISON CONTENT REQUIREMENTS (MANDATORY):**
- MUST start with a number ("10 Best", "Top 15", "12 Tools")
- MUST include year ({current_year})
- MUST include value indicator ("Reviewed", "Compared", "Tested")
- Format: "[Number] Best [Topic] ({current_year} Reviewed)"
- Example: "15 Best MCP Servers for Ad Analytics ({current_year} Reviewed)"
"""
        elif is_guide:
            style_requirements = f"""
**GUIDE CONTENT REQUIREMENTS:**
- Question format preferred: "How to...", "What is..."
- Include year if process/tech is time-sensitive
- Keep practical and action-oriented
- Example: "How to Connect Google Ads to Your CRM ({current_year})"
"""
        elif is_informational:
            style_requirements = f"""
**INFORMATIONAL CONTENT REQUIREMENTS:**
- Clear and direct
- Use "What is", "Why", or "Understanding" format
- Include year if topic evolves ({current_year})
- Example: "What is Model Context Protocol (MCP) and Why It Matters"
"""

        # Primary keyword instruction
        keyword_instruction = ""
        if gsc_primary_keyword:
            keyword_instruction = f"""
**CRITICAL - USE EXACT GSC KEYWORD:**
The following is the EXACT keyword users search for. Include it VERBATIM in the title:
→ "{gsc_primary_keyword}"
Do NOT modify, rephrase, or shorten this keyword.
"""
        else:
            keyword_instruction = f"""
**TARGET KEYWORD:** {keyword}
Include this keyword or a very close semantic variant.
"""

        # Extract first 500 words of content for context
        body_preview = ' '.join(body.split()[:500])

        title_prompt = f"""Optimize this blog post title for maximum CTR and SEO impact.
{keyword_instruction}
{style_requirements}
CURRENT TITLE ({len(current_title)} chars):
{current_title}

CONTENT PREVIEW:
{body_preview}

**SEO TITLE RULES:**
1. **Length**: {ideal_length[0]}-{ideal_length[1]} chars ideal, MAX {max_length} chars
2. **Year**: Include {current_year} for freshness signals
3. **Numbers**: Use specific numbers for lists ("10 Best" not "Best")
4. **Value Indicators**: Add one of: {', '.join(value_indicators[:5])}
5. **Natural Language**: Write like a real person

**BANNED WORDS (never use):**
{', '.join(banned_words)}

**GOOD EXAMPLES:**
✅ "10 Best Video Transcription Software ({current_year} Reviewed)" - number, year, value
✅ "How to Automate Lead Tracking in Your CRM ({current_year})" - question, year
✅ "What is MCP and Why Media Buyers Need It" - clear, direct

**BAD EXAMPLES:**
❌ "The Ultimate Comprehensive Guide to Marketing Tools" - banned words, vague
❌ "Top Tools" - too short, no specifics
❌ "Everything You Need to Know About..." - generic, overused

Return ONLY the optimized title (no quotes, no explanation):"""

        try:
            # Use Nebius Kimi-K2.5 for title optimization (creative task)
            if self.nebius:
                response = await self.nebius.chat.completions.create(
                    model=self.model_creative,
                    messages=[{
                        "role": "user",
                        "content": title_prompt
                    }],
                    temperature=0.7,
                    max_tokens=100
                )
                optimized_title = response.choices[0].message.content.strip().strip('"\'')
            elif self.gemini_client:
                # Fallback to Gemini if Nebius unavailable
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.gemini_model,
                    contents=title_prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=100,
                    )
                )
                optimized_title = response.text.strip().strip('"\'')
            else:
                logger.warning("No AI client available for title optimization")
                return current_title

            # Validation checks
            validation_issues = []

            # Length check
            if len(optimized_title) > max_length:
                validation_issues.append(f"Too long: {len(optimized_title)} chars (max {max_length})")

            if len(optimized_title) < 25:
                validation_issues.append(f"Too short: {len(optimized_title)} chars")

            # Banned words check
            title_lower = optimized_title.lower()
            for banned in banned_words:
                if banned.lower() in title_lower:
                    validation_issues.append(f"Contains banned word: '{banned}'")

            # Year check for comparison content
            if is_comparison and current_year not in optimized_title:
                # Try to add year if missing
                if len(optimized_title) + len(f" ({current_year})") <= max_length:
                    optimized_title = optimized_title.rstrip(')') + f" ({current_year})"
                    if not optimized_title.endswith(')'):
                        optimized_title += ')'
                    logger.info(f"   📅 Added year to title: {optimized_title}")

            # Number check for comparison content
            if is_comparison and not re.search(r'^\d+\s|Top\s+\d+', optimized_title):
                validation_issues.append("Missing number for comparison content")

            # Log any validation issues
            if validation_issues:
                logger.warning(f"   ⚠️  Title validation: {', '.join(validation_issues)}")
                # If critical issues, try to fix or keep original
                if any('banned word' in i or 'Too long' in i or 'Too short' in i for i in validation_issues):
                    logger.warning(f"   ⚠️  Keeping original title due to validation failures")
                    return content

            # Replace title in frontmatter
            new_frontmatter = re.sub(
                r'^title:\s*["\']?(.+?)["\']?\s*$',
                f'title: "{optimized_title}"',
                frontmatter,
                flags=re.MULTILINE
            )

            logger.info(f"   ✅ Title optimized: {len(current_title)} → {len(optimized_title)} chars")
            logger.info(f"      Old: {current_title}")
            logger.info(f"      New: {optimized_title}")

            return '---' + new_frontmatter + '---' + body

        except Exception as e:
            logger.warning(f"Title optimization failed: {e}, keeping original")
            return content

    async def _generate_multipart(self, full_prompt: str, keyword: str, is_custom_prompt: bool = False) -> str:
        """Generate content in 3 parts to avoid truncation while maintaining full context compliance

        Args:
            full_prompt: Complete prompt with all instructions
            keyword: The keyword/topic being written about
            is_custom_prompt: If True, uses generic guidance; if False, uses hardcoded section names
        """

        if is_custom_prompt:
            # For custom prompts, use generic guidance that respects the prompt's structure
            # Part 1: Frontmatter + Introduction + First ~40% of content
            part1_prompt = f"""{full_prompt}

GENERATION SCOPE FOR THIS PART (Part 1 of 3):
Generate the FIRST portion of content (target: 700-900 words):
1. YAML frontmatter (required fields: title, description, publishDate, author, image, tags, category)
2. Opening paragraph with direct PRIMARY ANSWER
3. The first 2-3 major sections as defined in your prompt structure

STOP after completing first 2-3 major sections. Do NOT generate all sections yet.
Remember: NO code fences around output. Start with --- frontmatter."""

        else:
            # For generic/keyword prompts, use explicit section names
            part1_prompt = f"""{full_prompt}

GENERATION SCOPE FOR THIS PART:
Generate ONLY the following sections (target: 500-600 words):
1. YAML frontmatter (required fields: title, description, publishDate, author, image, tags, category)
2. Opening paragraph with direct answer
3. Core Definition Section (## header)
4. How It Works Section (## header)

STOP after "How It Works" section. Do NOT generate remaining sections yet.
Remember: NO code fences around output. Start with --- frontmatter."""

        logger.info(f"🔹 Part 1/3: Generating frontmatter + intro + first sections...")
        part1_response = await self.gemini_client.aio.models.generate_content(
            model=self.gemini_model,
            contents=part1_prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.5,
            )
        )
        part1_content = part1_response.text.strip()

        # Remove code fences if present
        if part1_content.startswith('```'):
            first_newline = part1_content.find('\n')
            if first_newline > 0:
                part1_content = part1_content[first_newline+1:].strip()
                if part1_content.endswith('```'):
                    part1_content = part1_content[:-3].strip()

        part1_words = len(part1_content.split())
        logger.info(f"   ✓ Part 1 complete: {part1_words} words")

        # Part 2: Middle sections with full context
        if is_custom_prompt:
            part2_prompt = f"""{full_prompt}

PREVIOUS CONTENT GENERATED:
{part1_content}

GENERATION SCOPE FOR THIS PART (Part 2 of 3):
Generate the MIDDLE portion of content (target: 900-1200 words):
- Continue with the next 3-4 major sections as defined in your prompt structure
- Use same style, tone, and rigor as Part 1
- Do NOT regenerate frontmatter or earlier sections

STOP after completing middle sections. Leave final sections for Part 3."""

        else:
            part2_prompt = f"""{full_prompt}

PREVIOUS CONTENT GENERATED:
{part1_content}

GENERATION SCOPE FOR THIS PART:
Generate ONLY the following sections (target: 600-700 words):
1. Implementation Section (## header)
2. Benefits & Results Section (## header)
3. Tools & Resources Section (## header)

Continue naturally from previous content. Use same style and tone. Do NOT regenerate frontmatter or earlier sections.
STOP after "Tools & Resources" section."""

        logger.info(f"🔹 Part 2/3: Generating middle sections with context...")
        part2_response = await self.gemini_client.aio.models.generate_content(
            model=self.gemini_model,
            contents=part2_prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.55,
            )
        )
        part2_content = part2_response.text.strip()

        # Remove code fences if present
        if part2_content.startswith('```'):
            first_newline = part2_content.find('\n')
            if first_newline > 0:
                part2_content = part2_content[first_newline+1:].strip()
                if part2_content.endswith('```'):
                    part2_content = part2_content[:-3].strip()

        part2_words = len(part2_content.split())
        logger.info(f"   ✓ Part 2 complete: {part2_words} words")

        # Part 3: Final sections + FAQ with full context
        if is_custom_prompt:
            part3_prompt = f"""{full_prompt}

FULL CONTENT GENERATED SO FAR:
{part1_content}

{part2_content}

GENERATION SCOPE FOR THIS PART (Part 3 of 3 - FINAL):
Generate the FINAL portion of content (target: 900-1200 words):
- Complete ALL remaining sections as defined in your prompt structure
- MUST include FAQ section that addresses PAA questions naturally
- Maintain same rigor, data density, and style as Parts 1 & 2
- Include conclusion paragraph
- This COMPLETES the article - ensure all required sections are present

Do NOT regenerate any previous sections. This is the final part."""

        else:
            part3_prompt = f"""{full_prompt}

FULL CONTENT GENERATED SO FAR:
{part1_content}

{part2_content}

GENERATION SCOPE FOR THIS PART:
Generate ONLY the final sections (target: 500-600 words):
1. Common Challenges Section (## header)
2. FAQ Section (## header) - MUST address PAA questions
3. Conclusion paragraph

Continue naturally from previous content. Use same style and tone. This completes the article.
Do NOT regenerate any previous sections."""

        logger.info(f"🔹 Part 3/3: Generating final sections + FAQ...")
        part3_response = await self.gemini_client.aio.models.generate_content(
            model=self.gemini_model,
            contents=part3_prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.45,
            )
        )
        part3_content = part3_response.text.strip()

        # Remove code fences if present
        if part3_content.startswith('```'):
            first_newline = part3_content.find('\n')
            if first_newline > 0:
                part3_content = part3_content[first_newline+1:].strip()
                if part3_content.endswith('```'):
                    part3_content = part3_content[:-3].strip()

        part3_words = len(part3_content.split())
        logger.info(f"   ✓ Part 3 complete: {part3_words} words")

        # Combine all parts
        combined_content = f"{part1_content}\n\n{part2_content}\n\n{part3_content}"
        total_words = len(combined_content.split())
        logger.info(f"✅ Multi-part generation complete: {total_words} words total ({part1_words} + {part2_words} + {part3_words})")

        return combined_content

    async def _optimize_headings_seo(self, content: str, keyword: str) -> str:
        """Rewrite headings for SEO/AEO mastery - question format, keyword inclusion, user intent"""
        if not self.nebius:
            logger.warning("No Nebius client available for heading optimization")
            return content

        # Validate content structure
        if not content.strip().startswith('---') or content.count('---') < 2:
            logger.warning("Invalid content structure for heading optimization")
            return content

        # Extract frontmatter and body
        parts = content.split('---', 2)
        if len(parts) < 3:
            return content

        frontmatter_block = '---' + parts[1] + '---'
        body = parts[2]

        # Extract all H2 and H3 headings with their level AND context
        headings = re.findall(r'^(#{2,3})\s+(.+)$', body, re.MULTILINE)

        if not headings:
            logger.warning("No headings found to optimize")
            return content

        logger.info(f"🎯 Optimizing {len(headings)} headings for SEO/AEO mastery...")

        # Build heading list with section context (first 200 chars of content after each heading)
        sections = re.split(r'^#{2,3}\s+.+$', body, flags=re.MULTILINE)
        heading_list_with_context = []

        for i, (level, text) in enumerate(headings):
            # Get section content (next split after this heading)
            section_content = sections[i + 1] if i + 1 < len(sections) else ""
            section_preview = section_content.strip()[:200].replace('\n', ' ')
            heading_list_with_context.append(f"{level} {text.strip()}\n   Context: {section_preview}...")

        heading_list = "\n\n".join(heading_list_with_context)

        # Count H2s to determine if consolidation needed (optimal: 5-7 H2s)
        h2_count = sum(1 for level, _ in headings if level == "##")
        consolidation_note = ""
        if h2_count > 7:
            consolidation_note = f"""
⚠️  ARTICLE HAS {h2_count} H2 HEADINGS (too many - optimal is 5-7 for TOC scannability)

**CONSOLIDATION REQUIRED**:
- Target: 5-7 H2 sections maximum for clean table of contents
- Group related H2s under broader parent H2s
- Convert some H2s to H3s (subtopics under parent H2)
- Example:
  Before: ## What is X? | ## Why X matters? | ## When to use X?
  After:  ## Understanding X
          ### What is X?
          ### Why X Matters for Your Business
          ### When to Use X
"""
        elif h2_count < 5:
            consolidation_note = f"""
⚠️  ARTICLE HAS {h2_count} H2 HEADINGS (too few - optimal is 5-7)

**EXPANSION RECOMMENDED**:
- Target: 5-7 H2 sections for comprehensive TOC
- Consider splitting large sections into multiple focused H2s
"""

        optimization_prompt = f"""Rewrite these blog headings for maximum SEO/AEO optimization while preserving their hierarchy.

TARGET KEYWORD: {keyword}

CURRENT HEADINGS (with section context):
{heading_list}
{consolidation_note}
SEO/AEO MASTERY REQUIREMENTS:
1. **Conversational & Relatable Language**: Write like you're explaining to a friend over coffee
   - Use everyday words, not industry jargon
   - "Turn Your Ads Into Revenue" NOT "Optimize Conversion Funnels for Revenue Attribution"
   - "What Stage Is This Lead At?" NOT "Lead Lifecycle Stage Identification"
   - "Why This Matters for Your Team" NOT "Organizational Impact Assessment"

2. **Question Format Priority**: Transform 50-70% of headings into natural questions people actually ask:
   - Use the section context to understand what the heading is about
   - Rewrite as a genuine question someone would type into Google or ask a colleague
   - Vary your question starters naturally: "How...", "What...", "Why...", "When...", "Which..."
   - Don't force every heading into the same formula

3. **Keep It Simple & Human**:
   - Avoid technical jargon: "marketing qualified lead", "optimization process", "attribution model"
   - Use: "someone who's interested", "making it work better", "tracking where leads come from"
   - Sound like a real person talking, not a whitepaper

4. **H2 Word Limit (CRITICAL FOR TOC SCANNABILITY)**:
   - H2s: MAXIMUM 5 WORDS for clean table of contents
   - Examples: "Top Tools Available", "How to Choose", "Key Features Compared"
   - H3s can be slightly longer (5-8 words) for detail

5. **Natural Language First**:
   - BANNED WORDS: "leverage", "utilize", "optimization", "implementation", "methodology"
   - GOOD WORDS: "use", "make", "improve", "set up", "way to do it"

6. Maintain ## for H2 and ### for H3 structure

GOOD EXAMPLES (what TO do):
✅ ## How Does This Turn Ads Into Actual Revenue? (question, relatable)
✅ ## What Happens When You Match Ads to Lead Stages? (natural question)
✅ ## Why Your Current Setup Probably Isn't Working (conversational)
✅ ### The Simple Way to Set This Up (plain language)
✅ ### What to Do When Leads Don't Convert (action-oriented)

BAD EXAMPLES (what NOT to do):
❌ ## Attribution Methodology Implementation Strategies (jargon-heavy)
❌ ## Leveraging Advanced Analytics for Campaign Optimization (corporate speak)
❌ ### Optimizing Your Data Infrastructure Framework (technical jargon)
❌ ### Utilizing Multi-Touch Attribution Models (buzzwords)

Return ONLY the rewritten headings in the EXACT same format (## or ###), one per line, in the same order. Do NOT add explanations or extra text."""

        try:
            response = await self.nebius.chat.completions.create(
                model=self.model_creative,
                messages=[{
                    "role": "system",
                    "content": "You are a content editor who rewrites jargony, corporate headings into simple, conversational questions that sound like a real person talking. You avoid technical buzzwords and write like you're explaining something to a friend. Most headings should be questions people actually ask."
                }, {
                    "role": "user",
                    "content": optimization_prompt
                }],
                temperature=0.4,
                max_tokens=4000
            )

            optimized_headings_text = response.choices[0].message.content.strip()

            # Remove code fences if present
            if optimized_headings_text.startswith('```'):
                lines = optimized_headings_text.split('\n')
                # Remove first line (```markdown or ```), last line (```), and empty lines
                content_lines = [l for l in lines[1:] if l.strip() and not l.strip() == '```']
                optimized_headings_text = '\n'.join(content_lines)

            # Parse optimized headings - try multiple strategies
            optimized_headings = []

            # Strategy 1: Standard markdown format (## Heading)
            matches = re.findall(r'^(#{2,3})\s+(.+)$', optimized_headings_text, re.MULTILINE)
            if matches:
                optimized_headings = matches
                logger.info(f"   ✓ Parsed headings using markdown format")
            else:
                # Strategy 2: Numbered list or bullet format
                logger.info(f"   Trying fallback parsing (numbered/bullet list)...")
                lines = optimized_headings_text.split('\n')
                valid_lines = [l.strip() for l in lines if l.strip()]

                for i, line in enumerate(valid_lines):
                    if i >= len(headings):
                        break

                    # Remove common prefixes: "1. ", "1) ", "- ", "* ", etc.
                    cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
                    cleaned = re.sub(r'^[-\*•]\s*', '', cleaned)
                    cleaned = cleaned.strip()

                    if cleaned:
                        # Use original heading level from the source content
                        optimized_headings.append((headings[i][0], cleaned))

                if optimized_headings:
                    logger.info(f"   ✓ Parsed headings using fallback strategy")

            if len(optimized_headings) != len(headings):
                logger.warning(f"⚠️  Heading count mismatch ({len(optimized_headings)} vs {len(headings)}), using original")
                logger.warning(f"   Model response preview: {optimized_headings_text[:300]}")
                return content

            # Replace headings in content
            optimized_body = body
            for (old_level, old_text), (new_level, new_text) in zip(headings, optimized_headings):
                # Ensure hierarchy is preserved
                if old_level != new_level:
                    logger.warning(f"⚠️  Hierarchy mismatch for '{old_text}', keeping original level")
                    new_level = old_level

                # Replace old heading with optimized one
                old_heading = f"{old_level} {old_text}"
                new_heading = f"{new_level} {new_text.strip()}"
                optimized_body = optimized_body.replace(old_heading, new_heading, 1)

            logger.info(f"✅ Headings optimized for SEO/AEO")

            return frontmatter_block + '\n' + optimized_body

        except Exception as e:
            logger.warning(f"Heading optimization failed: {e}, using original headings")
            return content

    async def generate(self, prompt: str, context: Dict[str, Any]) -> str:
        """Gemini for generation - AI-optimized comprehensive content with schema markup

        Args:
            prompt: Either a full custom prompt (from style-specific builders) or just a keyword
            context: Research context with serp, reddit, quora data
        """
        if not self.gemini_client:
            return "No Gemini client"

        # Extract research data for enhanced prompting
        serp_data = context.get('serp', {})
        reddit_data = context.get('reddit', {})
        quora_data = context.get('quora', {})

        # Get PAA questions to explicitly address
        paa_questions = serp_data.get('paa_questions', [])[:8]
        paa_section = ""
        if paa_questions:
            paa_section = "\n\nCRITICAL: You MUST address these specific questions from search results:\n"
            for i, q in enumerate(paa_questions, 1):
                paa_section += f"{i}. {q}\n"
            paa_section += "\nIntegrate answers naturally within your sections - don't list them separately."

        # DETECT: Is this a full custom prompt or just a keyword?
        # Custom prompts contain style-specific structure markers
        is_custom_prompt = any(marker in prompt for marker in [
            "CRITICAL RESEARCH QUALITY STANDARDS",  # Research style
            "Brand way COMPARISON STRUCTURE",     # Guide style
            "COMPARISON FRAMEWORK",                  # Comparison style
            "TOPIC CLUSTERING APPROACH",             # All styles use this
            "BRAND VOICE & TONE"                     # All styles have this
        ])

        if is_custom_prompt:
            # This is a pre-built custom prompt from a style builder
            # Use it directly with minimal wrapping
            logger.info("📝 Using custom style-specific prompt")

            # Add only essential MDX format requirements and PAA questions
            full_prompt = f"""{prompt}

{paa_section}

CRITICAL OUTPUT FORMAT REQUIREMENTS (MUST FOLLOW EXACTLY):
1. MUST START WITH YAML FRONTMATTER:
---
title: "Your SEO-Optimized Title Here (Under 60 chars)"
description: "Compelling meta description 120-160 characters"
publishDate: "2025-01-15"
author: "Author Name"
image:
  src: "/src/assets/blog/placeholder.webp"
  alt: "Descriptive alt text"
tags: ["Brand Methodology", "Industry Category"]
category: "Industry Category"
---

2. AFTER FRONTMATTER, START CONTENT WITH PRIMARY ANSWER
3. USE PROPER MDX STRUCTURE (H2 ##, H3 ###, **bold**, bullets)
4. NO code fences (```) around output

RESEARCH DATA TO INTEGRATE:
Content Gaps: {serp_data.get('content_gaps', []) if serp_data.get('content_gaps') else 'None'}
Reddit Insights: {[insight[:150] for insight in reddit_data.get('insights', [])[:5]] if reddit_data.get('insights') else 'None'}
Quora Insights: {[insight[:150] for insight in quora_data.get('expert_insights', [])[:3]] if quora_data.get('expert_insights') else 'None'}

REMEMBER: Output must be valid Astro MDX starting with --- frontmatter. NO code fences wrapping the output."""

        else:
            # This is just a keyword - use generic standard structure
            logger.info("📝 Using generic prompt wrapper for keyword")

            # Build comprehensive AI-optimized prompt with MDX structure requirements
            full_prompt = f"""
        Create comprehensive, AI-readable Astro MDX blog content that answers 100+ related questions for: {prompt}

        CRITICAL OUTPUT FORMAT REQUIREMENTS (MUST FOLLOW EXACTLY):

        1. MUST START WITH YAML FRONTMATTER:
        ---
        title: "Your SEO-Optimized Title Here (Under 60 chars)"
        description: "Compelling meta description 120-160 characters"
        publishDate: "2025-01-15"
        author: "Author Name"
        image:
          src: "/src/assets/blog/placeholder.webp"
          alt: "Descriptive alt text"
        tags: ["Brand Methodology", "Industry Category"]
        category: "Industry Category"
        ---

        2. AFTER FRONTMATTER, START CONTENT WITH PRIMARY ANSWER:
        Begin first paragraph with direct answer to main question in 1-2 sentences.

        3. USE PROPER MDX STRUCTURE:
        - H2 headers (##) for main sections
        - H3 headers (###) for subsections
        - **Bold** for key concepts
        - Bullet lists with proper markdown
        - No code fences around content
        - No ```markdown or ```mdx wrappers

        CONTENT STRUCTURE (Organize into these thematic sections):

        ## Core Definition Section
        (Answers "what is" and foundational questions)
        - Lead with direct definition in first sentence
        - **Bold key concepts** for AI extraction
        - Address 3-5 related questions naturally
        - Include specific examples and use cases

        ## How It Works Section
        (Answers "how does" and process questions)
        - Step-by-step explanations with clear hierarchies
        - Bulleted subsections for multiple approaches
        - Include specific technical details
        - Real-world examples

        ## Implementation Section
        (Answers "how to" and practical questions)
        - Numbered steps with prerequisites clearly listed
        - Common challenges and prevention strategies
        - Pro tips and best practices with **bolded key advice**

        ## Benefits & Results Section
        (Answers "why" and outcome questions)
        - Quantifiable benefits with data points where possible
        - Expected results and realistic timelines
        - ROI improvements and efficiency gains

        ## Tools & Resources Section
        (Answers "what tools" questions)
        - Essential tools and resources needed
        - Clear evaluation criteria for selection
        - Integration considerations and compatibility

        ## Common Challenges Section
        (Answers troubleshooting questions)
        - Most frequent problems encountered
        - Prevention strategies and quick fixes
        - Troubleshooting guidance with **bolded solutions**
        {paa_section}

        RESEARCH DATA TO INTEGRATE:
        Content Gaps to Address: {serp_data.get('content_gaps', []) if serp_data.get('content_gaps') else 'None'}
        Reddit Pain Points: {[insight[:150] for insight in reddit_data.get('insights', [])[:5]] if reddit_data.get('insights') else 'None'}
        Quora Expert Insights: {[insight[:150] for insight in quora_data.get('expert_insights', [])[:3]] if quora_data.get('expert_insights') else 'None'}

        AI OPTIMIZATION REQUIREMENTS:
        - **Lead sentences**: Direct answers AI can extract verbatim
        - **Bulleted subsections**: For multiple specific points
        - **Bold key phrases**: Help AI identify important concepts
        - **Clear H2/H3 hierarchies**: Main topics and subtopics
        - **High answer density**: Every paragraph addresses 2-4 related questions
        - **Citation-ready facts**: Key data easily extractable by AI systems

        CONTENT SPECIFICATIONS:
        - 2000+ words minimum with comprehensive coverage
        - Natural keyword density (1-2%)
        - Actionable, expert-level insights
        - No AI markers or generic fluff
        - Citation-ready facts throughout
        - Address ALL PAA questions naturally in content flow

        NEGATIVE PROMPTS (AVOID COMPLETELY):
        - NO code fences (```) around output
        - NO generic fluff or obvious statements
        - Focus exclusively on the target audience and industry defined in the ICP configuration

        REMEMBER: Output must be valid Astro MDX starting with --- frontmatter and ending with content body. NO code fences wrapping the output.
        """

        # Use multi-part generation to avoid truncation
        content = await self._generate_multipart(full_prompt, prompt, is_custom_prompt)

        # Note: Heading optimization moved to generator.py after polish step
        # to prevent optimized headings from being overwritten by polish

        # Validate we got frontmatter
        if not content.startswith('---'):
            logger.error("Gemini output missing frontmatter - injecting minimal structure")
            # Extract any title from content or use keyword
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else prompt.title()

            # Inject minimal valid frontmatter
            minimal_frontmatter = f"""---
title: "{title[:60]}"
description: "Comprehensive guide to {prompt}"
publishDate: "2025-01-15"
author: "Author Name"
image:
  src: "/src/assets/blog/placeholder.webp"
  alt: "{title}"
tags: ["Brand Methodology", "Industry Category"]
category: "Industry Category"
---

"""
            content = minimal_frontmatter + content

        return content

    async def _edit_section(self, section: str, section_index: int, total_sections: int) -> str:
        """Edit a single section with targeted improvements (preserves word count, retries once if needed)"""
        if not self.nebius:
            return section

        section_words = len(section.split())

        section_prompt = f"""Make TARGETED improvements to this content section. DO NOT rewrite - only fix specific issues.

SECTION {section_index + 1} of {total_sections}:
{section}

CURRENT WORD COUNT: {section_words} words
TARGET WORD COUNT: {section_words} words (±10 words acceptable)

TARGETED IMPROVEMENTS ONLY:
1. Fix grammar/spelling errors
2. Remove AI phrases ("delve", "dive deep", "moreover", "furthermore")
3. Bold 2-3 key concepts with **bold**
4. Improve 1-2 weak sentences for clarity
5. Ensure first sentence directly answers the section topic

CRITICAL RULES:
- Return approximately {section_words} words (±25% tolerance)
- DO NOT remove examples, lists, or explanations
- DO NOT condense or shorten content
- DO NOT rewrite entire paragraphs - only targeted fixes
- PRESERVE all markdown structure (##, ###, bullets, etc.)
- If section is under target, expand examples slightly
- NO code fences around output

Return the improved section:"""

        # Try up to 3 times
        for attempt in range(3):
            response = await self.nebius.chat.completions.create(
                model=self.model_precision,
                messages=[{
                    "role": "system",
                    "content": "You are a precision editor who makes only targeted improvements without rewriting. You preserve word count exactly."
                }, {
                    "role": "user",
                    "content": section_prompt
                }],
                temperature=0.15,
                max_tokens=8000
            )

            raw = response.choices[0].message.content
            if not raw:
                logger.warning(f"   ⚠️  Section {section_index + 1} returned None response, retrying...")
                continue
            edited = raw.strip()
            edited_words = len(edited.split())

            # Check for empty/failed response (always retry)
            if edited_words < 50:
                logger.warning(f"   ⚠️  Section {section_index + 1} returned empty/truncated ({edited_words} words), retrying...")
                continue

            # Validate word count preserved (25% tolerance)
            word_diff = abs(edited_words - section_words)
            if word_diff > section_words * 0.25:
                if attempt < 2:
                    logger.warning(f"   ⚠️  Section {section_index + 1} word count changed too much ({section_words} → {edited_words}, diff: {word_diff}), retrying ({attempt + 1}/3)...")
                    continue
                else:
                    logger.warning(f"   ⚠️  Section {section_index + 1} word count still wrong after 3 retries ({section_words} → {edited_words}, diff: {word_diff}), using original")
                    return section

            # Success
            return edited

        # Fallback after all retries exhausted
        logger.warning(f"   ⚠️  Section {section_index + 1} failed all 3 retries, using original")
        return section

    async def _edit_multipart(self, content: str, progress_callback: Optional[Callable[[str, int], None]] = None) -> str:
        """Edit content in batches of 5 sections to prevent word chopping

        Args:
            content: Content to edit
            progress_callback: Optional callback(message, advance) for progress updates
        """
        if not self.nebius:
            return content

        # No-op callback if none provided
        progress = progress_callback or (lambda msg, adv=0: None)

        logger.info("✂️  Editing content in batches to preserve word count...")

        # Validate structure
        if not content.strip().startswith('---') or content.count('---') < 2:
            logger.warning("Invalid content structure for segmented editing")
            return content

        # Extract frontmatter and body
        parts = content.split('---', 2)
        frontmatter_block = '---' + parts[1] + '---'
        body = parts[2]

        # Split body by H2 headings (## Main Section)
        sections = re.split(r'(^## .+$)', body, flags=re.MULTILINE)

        # Combine heading with its content
        combined_sections = []
        i = 0
        while i < len(sections):
            if i == 0 and sections[i].strip():
                # Preamble before first H2
                combined_sections.append(sections[i])
                i += 1
            elif i < len(sections) - 1:
                # Heading + its content
                section_with_heading = sections[i] + (sections[i + 1] if i + 1 < len(sections) else '')
                combined_sections.append(section_with_heading)
                i += 2
            else:
                i += 1

        if not combined_sections:
            logger.warning("No sections found for editing")
            return content

        # Group sections into batches of 2 (tighter word count control)
        batched_sections = []
        for i in range(0, len(combined_sections), 2):
            batch = combined_sections[i:i+2]
            batched_sections.append('\n\n'.join(batch))

        logger.info(f"   📋 Split into {len(combined_sections)} sections, processing in {len(batched_sections)} batches (up to 2 sections per batch)")

        # Edit each batch with timing for ETA
        edited_sections = []
        batch_times = []
        for idx, batch in enumerate(batched_sections):
            if batch.strip():
                batch_start = datetime.now()

                # Calculate ETA if we have timing data
                if batch_times:
                    avg_time = sum(batch_times) / len(batch_times)
                    remaining = len(batched_sections) - idx
                    eta_seconds = avg_time * remaining
                    eta_msg = f" (ETA: {eta_seconds:.0f}s)" if eta_seconds > 5 else ""
                else:
                    eta_msg = ""

                logger.info(f"   🔹 Editing batch {idx + 1}/{len(batched_sections)}{eta_msg}...")
                progress(f"Editing batch {idx + 1}/{len(batched_sections)}{eta_msg}", 0)

                edited = await self._edit_section(batch, idx, len(batched_sections))
                edited_sections.append(edited)

                # Track timing
                batch_time = (datetime.now() - batch_start).total_seconds()
                batch_times.append(batch_time)

                # Warn if batch took too long
                if batch_time > 60:
                    logger.warning(f"   ⏱️  Batch {idx + 1} took {batch_time:.1f}s (timeout threshold: 60s)")

        # Combine back
        edited_body = '\n\n'.join(edited_sections)
        edited_content = frontmatter_block + '\n' + edited_body

        # Validate frontmatter is intact
        if not edited_content.startswith('---') or edited_content.count('---') < 2:
            logger.warning("   ⚠️  Frontmatter structure broken after editing, using original")
            return content

        original_words = len(content.split())
        edited_words = len(edited_content.split())
        logger.info(f"   ✅ Segmented editing complete: {original_words} → {edited_words} words ({edited_words - original_words:+d})")

        # Update progress to clear the editing status
        progress(f"✅ Editing complete ({edited_words:,} words)", 0)

        return edited_content

    async def edit(self, content: str, style_guide: Optional[str] = None, progress_callback: Optional[Callable[[str, int], None]] = None) -> str:
        """Final edit pass - using segmented editing to preserve word count

        Args:
            content: Content to edit
            style_guide: Optional style guide
            progress_callback: Optional callback(message, advance) for progress updates
        """
        if not self.nebius:
            return content

        # Use segmented editing to prevent word count chopping
        return await self._edit_multipart(content, progress_callback=progress_callback)

    async def edit_old_monolithic(self, content: str, style_guide: Optional[str] = None) -> str:
        """[DEPRECATED] Old monolithic edit - kept for reference"""
        if not self.nebius:
            return content

        edit_prompt = f"""Edit this Astro/MDX blog content for clarity, engagement, and SEO/AEO optimization.

CURRENT CONTENT:
{content}

TEMPLATE STRUCTURE REFERENCE (MUST MATCH THIS FORMAT):
{self.template_content[:500] if self.template_content else 'Template not loaded'}

CRITICAL STRUCTURAL REQUIREMENTS:
- MUST start with YAML frontmatter delimited by ---
- MUST include: title, publishDate, description, author, image, tags, category
- DO NOT wrap output in code fences (```) or backticks
- DO NOT add "```markdown" or "```mdx" wrappers
- ENSURE proper H2 (##) and H3 (###) heading hierarchy
- PRESERVE all schema markup (<script type="application/ld+json">)
- MAINTAIN all Astro component imports and usage (<CTASection />, etc.)

ASTRO/MDX TEMPLATE COMPLIANCE:
- PRESERVE all schema markup (QAPage, FAQPage, HowTo, Article schema)
- MAINTAIN all frontmatter and template variables
- KEEP all partial includes
- DO NOT break Astro/MDX template syntax
- VALIDATE FAQ sections have Q&A pairs for schema compliance
- CHECK HowTo sections have numbered/structured steps

SEO/AEO MASTERY REQUIREMENTS:
- **Primary Answer First**: Lead with direct answer in first 1-2 sentences of each section
- **Bold Key Concepts**: Use **bold** for important terms AI systems should extract
- **Clear H2/H3 Hierarchies**: Maintain semantic heading structure for topic clustering
- **Question-Answer Density**: Every paragraph should address 2-4 related questions naturally
- **Citation-Ready Facts**: Present data points in easily extractable format
- **Natural Keyword Flow**: 1-1.5% keyword density maximum, avoid repetition
- **AI-Readable Structure**: Bulleted lists, short paragraphs, scannable formatting

SCHEMA OPTIMIZATION:
- FAQ sections must have clear question headings (###) and answer paragraphs
- HowTo sections need numbered steps or clear step indicators
- Ensure schema variables (faq_items, howto_steps) can be extracted from content
- Include specific data points, timelines, and actionable advice

CONTENT QUALITY:
- Fix awkward phrasing and grammar errors
- Ensure consistent, professional tone
- Remove AI-sounding language ("delve", "dive deep", "moreover")
- Verify all claims are specific and actionable
- Maintain human-like burstiness (varied sentence length)
{f'- Follow style guide: {style_guide}' if style_guide else ''}

CRITICAL NEGATIVE ACTIONS (DO NOT):
- Wrap output in code fences or backticks
- Add markdown language tags (```markdown, ```mdx)
- Add new sections or restructure content
- Remove existing information or schema markup
- Change factual claims or key information
- Break MDX/template syntax

Return ONLY the edited MDX content (no code fences, no explanations)."""

        response = await self.nebius.chat.completions.create(
            model=self.model_precision,
            messages=[{
                "role": "system",
                "content": "You are an expert content editor specializing in Astro/MDX blogs, Schema.org markup, and SEO/AEO optimization. You ensure content is AI-readable, schema-compliant, and optimized for answer engines while preserving all template syntax."
            }, {
                "role": "user",
                "content": edit_prompt
            }],
            temperature=0.2,
            max_tokens=16384
        )

        result = response.choices[0].message.content
        if not result:
            logger.warning("⚠️  edit_content_segmented returned None response, returning original content")
            return content
        return result

    async def polish_frontmatter(self, content: str, use_llama: bool = False) -> Dict[str, str]:
        """Polish frontmatter to match template structure exactly using Qwen (default) or Llama (optional)

        Args:
            content: Content with frontmatter
            use_llama: If True, use Kimi K2; otherwise use Qwen3 235B
        """
        if not self.nebius:
            logger.warning("No Nebius API key configured, skipping frontmatter polish")
            return {"llama": content, "qwen": content}

        # Validate content has frontmatter before attempting polish
        if not content.strip().startswith('---'):
            logger.warning("Content missing frontmatter, skipping polish")
            return {"llama": content, "qwen": content}

        # Extract frontmatter and content using regex to avoid duplicate --- blocks
        import re
        match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not match:
            logger.warning("Invalid frontmatter structure, skipping frontmatter polish")
            return {"llama": content, "qwen": content}

        frontmatter = match.group(1)
        body = match.group(2)

        # Note: Body is already separated by regex above, no need for aggressive stripping
        # The previous regex r'\n---\n.*?\n---\n' with re.DOTALL was too aggressive
        # and would strip legitimate content if any --- markdown separators existed

        frontmatter_prompt = f"""Polish ONLY the YAML frontmatter below to match the Astro MDX template structure.

CURRENT FRONTMATTER:
---
{frontmatter}
---

TEMPLATE REFERENCE (follow this structure EXACTLY):
{self.template_content.split('---', 2)[1] if '---' in self.template_content else ''}

REQUIREMENTS (CRITICAL):
- MUST maintain YAML format (key: value)
- MUST include all required fields from template
- Fix any syntax errors or formatting issues
- Improve title and description for SEO (keep under 60 and 160 chars)
- Ensure proper quoting for strings with special characters
- DO NOT add triple backticks or code fences
- DO NOT change structure - only improve values
- DO NOT use em dashes (—) - use hyphens (-) instead
- DO NOT use semicolons (;) - use periods or commas instead
- Return ONLY the frontmatter content between --- markers

Return format:
---
[polished frontmatter here]
---"""

        # Use single model (Qwen by default, Kimi K2 if requested)
        try:
            model_name = "Kimi K2" if use_llama else "Qwen3 235B"
            model_id = "moonshotai/Kimi-K2-Instruct" if use_llama else "Qwen/Qwen3-235B-A22B-Instruct-2507"

            logger.info(f"✨ Polishing frontmatter with {model_name}...")

            response = await self.nebius.chat.completions.create(
                model=model_id,
                messages=[{
                    "role": "system",
                    "content": "You are an expert in Astro MDX frontmatter. You ensure YAML is valid and matches template structure exactly. You never add code fences or extra formatting. You NEVER use em dashes (—) or semicolons - use hyphens and periods instead."
                }, {
                    "role": "user",
                    "content": frontmatter_prompt
                }],
                temperature=0.2,
                max_tokens=2000
            )

            polished_frontmatter = response.choices[0].message.content.strip()

            # Filter out em dashes and semicolons from frontmatter (but protect import/export statements)
            polished_frontmatter = polished_frontmatter.replace('—', '-')  # Em dash → hyphen
            polished_frontmatter = polished_frontmatter.replace('–', '-')  # En dash → hyphen

            # Protect import/export statements from semicolon replacement
            # Split content into lines, preserve imports, apply regex to non-import lines only
            lines = polished_frontmatter.split('\n')
            processed_lines = []
            for line in lines:
                # Keep import/export statements untouched (they need semicolons)
                if line.strip().startswith(('import ', 'export ', 'import{', 'export{')):
                    processed_lines.append(line)
                else:
                    # Apply semicolon removal to prose only
                    processed_lines.append(re.sub(r';\s+', '. ', line))
            polished_frontmatter = '\n'.join(processed_lines)

            # Validate output
            is_valid = polished_frontmatter.startswith('---') and polished_frontmatter.count('---') >= 2

            if not is_valid:
                logger.warning(f"⚠️  {model_name} frontmatter invalid, using original")
                result = content
            else:
                result = polished_frontmatter + '\n' + body

            logger.info(f"✅ {model_name} frontmatter: {len(result)} chars")

            # Return in both keys for compatibility with existing code
            if use_llama:
                return {"llama": result, "qwen": content}
            else:
                return {"llama": content, "qwen": result}

        except Exception as e:
            logger.warning(f"Frontmatter polish failed: {e}, keeping original")
            return {"llama": content, "qwen": content}

    async def _polish_section(self, section: str, section_index: int, total_sections: int, model: str, site_context: Optional[Dict[str, Any]] = None, brand_mode: str = 'full') -> str:
        """Polish a single section while preserving word count (retries once if needed)"""
        section_words = len(section.split())

        # Build real brand links from sitemap (or disable based on mode)
        if brand_mode == 'none':
            brand_links = "DO NOT add any brand or internal links"
        elif brand_mode == 'limited':
            # Limited mode: Still provide links, but instruction to use sparingly
            brand_links = self._build_brand_links_from_sitemap(site_context)
            brand_links = f"{brand_links}\n\n⚠️ LIMITED MODE: Add brand links ONLY if highly natural (max 1-2 per section). Most sections should have ZERO links."
        else:  # full mode
            brand_links = self._build_brand_links_from_sitemap(site_context)

        section_prompt = f"""Polish this section to make it more human and relatable. Make TARGETED changes ONLY - change maximum 3-5 words per sentence.

SECTION {section_index + 1} of {total_sections}:
{section}

CURRENT WORD COUNT: {section_words} words
TARGET WORD COUNT: {section_words} words (±8% maximum)

READABILITY TARGET: Flesch Reading Ease Score 90-95+ (8th grade level or lower)
- Use SHORT sentences (avg 12-15 words)
- Use SIMPLE words (1-2 syllables preferred)
- Use ACTIVE voice ("we built" not "it was built")

ALLOWED CHANGES (and ONLY these):
1. **Replace 2-3 jargon terms** with everyday language:
   ✓ "leverage" → "use"  |  "optimize" → "improve"  |  "utilize" → "use"
   ✓ "implementation" → "setup"  |  "methodology" → "approach"
   ✓ "facilitate" → "help"  |  "subsequently" → "then"

2. **Add 1-2 brand links** where contextually relevant (ONLY use these real links from sitemap):
{brand_links}

3. **Fix grammar errors**: verb tense, subject-verb agreement, typos

4. **Shorten long sentences** (priority for readability):
   ✓ Split any sentence over 20 words into 2 shorter ones
   ✓ Replace complex clauses with simple statements

FORBIDDEN CHANGES (do NOT do these):
✗ Removing examples, data points, lists, or explanations
✗ Condensing or summarizing paragraphs
✗ Rewriting entire sentences from scratch
✗ Changing factual claims or statistics
✗ Nesting markdown links: [text](url[text2](url2)) is INVALID
✗ Using em dashes (—) - use hyphens (-) or split into sentences instead
✗ Using semicolons (;) - split into two sentences instead

CRITICAL RULES:
- Change MAXIMUM 3-5 words per sentence
- Return approximately {section_words} words (±25% tolerance)
- DO NOT include "CURRENT WORD COUNT" or word count markers in output
- PRESERVE all markdown (##, ###, bullets, **bold**, etc.)
- NO code fences around output
- ZERO em dashes (—) allowed
- Target Flesch 90-95+ readability
- This is POLISH not REWRITE

Return ONLY the polished section content (no word count labels):"""

        # Try up to 3 times
        for attempt in range(3):
            response = await self.nebius.chat.completions.create(
                model=model,
                messages=[{
                    "role": "system",
                    "content": "You are a content polisher who makes minimal, targeted improvements while preserving word count and structure. You never condense or shorten content. You target Flesch Reading Ease 90-95+ using short sentences and simple words. You NEVER use em dashes (—) or semicolons."
                }, {
                    "role": "user",
                    "content": section_prompt
                }],
                temperature=0.3,
                max_tokens=8000
            )

            polished = response.choices[0].message.content.strip()
            polished_words = len(polished.split())

            # Check for empty/failed response (always retry)
            if polished_words < 50:
                logger.warning(f"   ⚠️  Section {section_index + 1} returned empty/truncated ({polished_words} words), retrying...")
                continue

            # Validate word count - 25% tolerance
            word_diff = abs(polished_words - section_words)
            tolerance = max(int(section_words * 0.25), 25)  # 25% or minimum 25 words

            if word_diff > tolerance:
                if attempt < 2:
                    logger.warning(f"   ⚠️  Section {section_index + 1} word count changed too much ({section_words} → {polished_words}, diff: {word_diff}, tolerance: {tolerance}), retrying ({attempt + 1}/3)...")
                    continue
                else:
                    logger.warning(f"   ⚠️  Section {section_index + 1} word count still wrong after 3 retries ({section_words} → {polished_words}, diff: {word_diff}, tolerance: {tolerance}), using original")
                    return section

            # Remove any stray "CURRENT WORD COUNT" text that might have leaked through
            polished = re.sub(r'CURRENT WORD COUNT:?\s*\d+\s*words?', '', polished, flags=re.IGNORECASE)

            # Filter out em dashes and semicolons (replace with hyphens and periods, but protect imports)
            polished = polished.replace('—', '-')  # Em dash → hyphen
            polished = polished.replace('–', '-')  # En dash → hyphen

            # Protect import/export statements from semicolon replacement
            # Split content into lines, preserve imports, apply regex to non-import lines only
            lines = polished.split('\n')
            processed_lines = []
            for line in lines:
                # Keep import/export statements untouched (they need semicolons)
                if line.strip().startswith(('import ', 'export ', 'import{', 'export{')):
                    processed_lines.append(line)
                else:
                    # Apply semicolon removal to prose only
                    processed_lines.append(re.sub(r';\s+', '. ', line))
            polished = '\n'.join(processed_lines)

            # Success
            return polished

        # Fallback after all retries exhausted
        logger.warning(f"   ⚠️  Section {section_index + 1} failed all 3 retries, using original")
        return section

    async def _polish_multipart(self, content: str, model_name: str, model: str, site_context: Optional[Dict[str, Any]] = None, brand_mode: str = 'full', progress_callback: Optional[Callable[[str, int], None]] = None) -> str:
        """Polish content in batches of 2 sections to preserve word count and reduce API calls

        Args:
            content: Content to polish
            model_name: Human-readable model name
            model: Actual model identifier
            site_context: Site context for brand links
            brand_mode: Brand mention level
            progress_callback: Optional callback(message, advance) for progress updates
        """
        # No-op callback if none provided
        progress = progress_callback or (lambda msg, adv=0: None)

        logger.info(f"✨ Polishing content in batches with {model_name}...")

        # Extract frontmatter and body
        parts = content.split('---', 2)
        frontmatter_block = '---' + parts[1] + '---'
        body = parts[2]

        # Split by H2 headings
        sections = re.split(r'(^## .+$)', body, flags=re.MULTILINE)

        # Combine sections
        combined_sections = []
        i = 0
        while i < len(sections):
            if i == 0 and sections[i].strip():
                combined_sections.append(sections[i])
                i += 1
            elif i < len(sections) - 1:
                section_with_heading = sections[i] + (sections[i + 1] if i + 1 < len(sections) else '')
                combined_sections.append(section_with_heading)
                i += 2
            else:
                i += 1

        if not combined_sections:
            logger.warning(f"   No sections found for {model_name} polish")
            return content

        # Group sections into batches of 2
        batched_sections = []
        for i in range(0, len(combined_sections), 2):
            batch = combined_sections[i:i+2]
            batched_sections.append('\n\n'.join(batch))

        logger.info(f"   📋 Split into {len(combined_sections)} sections, processing in {len(batched_sections)} batches (2 sections per batch)")

        # Polish each batch with timing for ETA
        polished_sections = []
        batch_times = []
        for idx, batch in enumerate(batched_sections):
            if batch.strip():
                batch_start = datetime.now()

                # Calculate ETA if we have timing data
                if batch_times:
                    avg_time = sum(batch_times) / len(batch_times)
                    remaining = len(batched_sections) - idx
                    eta_seconds = avg_time * remaining
                    eta_msg = f" (ETA: {eta_seconds:.0f}s)" if eta_seconds > 5 else ""
                else:
                    eta_msg = ""

                logger.info(f"   🔹 Polishing batch {idx + 1}/{len(batched_sections)} with {model_name}{eta_msg}...")
                progress(f"Polishing batch {idx + 1}/{len(batched_sections)}{eta_msg}", 0)

                polished = await self._polish_section(batch, idx, len(batched_sections), model, site_context, brand_mode)
                polished_sections.append(polished)

                # Track timing
                batch_time = (datetime.now() - batch_start).total_seconds()
                batch_times.append(batch_time)

                # Warn if batch took too long
                if batch_time > 60:
                    logger.warning(f"   ⏱️  Batch {idx + 1} took {batch_time:.1f}s (timeout threshold: 60s)")

        # Combine back
        polished_body = '\n\n'.join(polished_sections)
        polished_content = frontmatter_block + '\n' + polished_body

        original_words = len(content.split())
        polished_words = len(polished_content.split())
        logger.info(f"   ✅ {model_name} polish complete: {original_words} → {polished_words} words ({polished_words - original_words:+d})")

        return polished_content

    async def polish_content(self, content: str, use_llama: bool = False, site_context: Optional[Dict[str, Any]] = None, brand_mode: str = 'full', progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, str]:
        """Polish content body for humanization and brand links using Qwen3 235B (default) or Kimi K2 (optional)

        Args:
            content: Content to polish
            use_llama: If True, use Kimi K2; otherwise use Qwen3 235B
            site_context: Site context with real internal_links from sitemap for brand link injection
            brand_mode: Brand mention level - 'none' (no links), 'limited' (sparse links), 'full' (natural integration)
        """
        if not self.nebius:
            logger.warning("No Nebius API key configured, skipping content polish")
            return {"llama": content, "qwen": content}

        # Validate content has frontmatter before attempting polish
        if not content.strip().startswith('---'):
            logger.warning("Content missing frontmatter, skipping content polish")
            return {"llama": content, "qwen": content}

        # Extract frontmatter and content
        parts = content.split('---', 2)
        if len(parts) < 3:
            logger.warning("Invalid frontmatter structure in polish_content")
            return {"llama": content, "qwen": content}

        frontmatter_block = '---' + parts[1] + '---'
        body = parts[2]

        # Validate body has content
        if len(body.strip()) < 100:
            logger.warning("Content body too short, skipping polish")
            return {"llama": content, "qwen": content}

        # Use single model polish (Qwen by default, Kimi K2 if requested)
        try:
            if use_llama:
                model_name = "Kimi K2"
                model_id = "moonshotai/Kimi-K2-Instruct"
                result = await self._polish_multipart(content, model_name, model_id, site_context, brand_mode, progress_callback=progress_callback)
                return {"llama": result, "qwen": content}
            else:
                model_name = "Qwen3 235B"
                model_id = "Qwen/Qwen3-235B-A22B-Instruct-2507"
                result = await self._polish_multipart(content, model_name, model_id, site_context, brand_mode, progress_callback=progress_callback)
                return {"llama": content, "qwen": result}

        except Exception as e:
            logger.warning(f"Segmented polish failed: {e}, using original")
            return {"llama": content, "qwen": content}

    async def polish_content_old_monolithic(self, content: str) -> Dict[str, str]:
        """[DEPRECATED] Old monolithic polish - kept for reference"""
        if not self.nebius:
            logger.warning("No Nebius API key configured, skipping content polish")
            return {"llama": content, "qwen": content}

        # Validate content has frontmatter before attempting polish
        if not content.strip().startswith('---'):
            logger.warning("Content missing frontmatter, skipping content polish")
            return {"llama": content, "qwen": content}

        # Extract frontmatter and content
        parts = content.split('---', 2)
        if len(parts) < 3:
            logger.warning("Invalid frontmatter structure in polish_content")
            return {"llama": content, "qwen": content}

        frontmatter_block = '---' + parts[1] + '---'
        body = parts[2]

        # Validate body has content
        if len(body.strip()) < 100:
            logger.warning("Content body too short, skipping polish")
            return {"llama": content, "qwen": content}

        content_prompt = f"""Polish ONLY the content body below (NOT the frontmatter). Make it more human, relatable, and naturally inject brand links.

CONTENT TO POLISH:
{body}

REQUIREMENTS (CRITICAL):
- Fix spelling and grammar errors
- Replace AI-sounding phrases with natural, human-like language
- Add subtle burstiness (vary sentence length naturally)
- **REWRITING FOR RELATABILITY**: Replace jargony terms with everyday language
- **BRAND LINK INJECTION**: Add natural hyperlinks to Brand brand pages where contextually relevant
- **MAINTAIN WORD COUNT**: Keep all sections and examples - only improve wording, do not shorten or condense
- **CRITICAL**: NEVER modify import/export statements - they must keep semicolons and line breaks
- PRESERVE all MDX structure, schema markup, and component imports exactly as-is
- Import statements must remain on separate lines ending with semicolons
- DO NOT modify any Astro components (<ComparisonTable />, <FAQSection />, etc.)
- DO NOT wrap output in code fences or backticks
- DO NOT add or remove headings or sections
- Focus on language polish only, not length reduction

BRAND LINKS TO INJECT NATURALLY:
- Brand → [Brand](https://acme.com)
- NOTE: This deprecated method uses hardcoded links. Use the new segmented polish for real sitemap links.

Return ONLY the polished content body (no frontmatter, no code fences). IMPORTANT: Maintain the same word count - do not shorten."""

        # A/B Test: Generate with both models in parallel
        try:
            logger.info("🔬 A/B Test: Generating content polish with Kimi K2 and Qwen3 235B...")

            # Run both models in parallel
            llama_task = self.nebius.chat.completions.create(
                model="moonshotai/Kimi-K2-Instruct",
                messages=[{
                    "role": "system",
                    "content": "You are an expert content editor specializing in making technical content relatable and human-like while preserving all structure and facts. You never add code fences or modify MDX components. CRITICAL: Never modify import/export statements - they must keep their semicolons and line breaks."
                }, {
                    "role": "user",
                    "content": content_prompt
                }],
                temperature=0.35,
                max_tokens=16384
            )

            qwen_task = self.nebius.chat.completions.create(
                model="Qwen/Qwen3-235B-A22B-Instruct-2507",
                messages=[{
                    "role": "system",
                    "content": "You are an expert content editor specializing in making technical content relatable and human-like while preserving all structure and facts. You never add code fences or modify MDX components. CRITICAL: Never modify import/export statements - they must keep their semicolons and line breaks."
                }, {
                    "role": "user",
                    "content": content_prompt
                }],
                temperature=0.35,
                max_tokens=16384
            )

            # Wait for both to complete
            llama_response, qwen_response = await asyncio.gather(llama_task, qwen_task)

            llama_body = llama_response.choices[0].message.content.strip()
            qwen_body = qwen_response.choices[0].message.content.strip()

            # Validate both outputs
            llama_valid = len(llama_body.strip()) >= 100
            qwen_valid = len(qwen_body.strip()) >= 100

            if not llama_valid:
                logger.warning("⚠️  Kimi K2 content too short, using original")
                llama_result = content
            else:
                llama_result = frontmatter_block + '\n' + llama_body
                if not llama_result.strip().startswith('---') or llama_result.count('---') < 2:
                    logger.warning("⚠️  Llama result invalid structure, using original")
                    llama_result = content

            if not qwen_valid:
                logger.warning("⚠️  Qwen content too short, using original")
                qwen_result = content
            else:
                qwen_result = frontmatter_block + '\n' + qwen_body
                if not qwen_result.strip().startswith('---') or qwen_result.count('---') < 2:
                    logger.warning("⚠️  Qwen result invalid structure, using original")
                    qwen_result = content

            llama_words = len(llama_result.split())
            qwen_words = len(qwen_result.split())

            logger.info(f"✅ Llama content: {llama_words} words")
            logger.info(f"✅ Qwen content: {qwen_words} words")
            logger.info(f"📊 Word count difference: {abs(llama_words - qwen_words)} words")

            return {
                "llama": llama_result,
                "qwen": qwen_result
            }

        except Exception as e:
            logger.warning(f"Content polish failed: {e}, keeping original")
            return {"llama": content, "qwen": content}

    def _repair_insight_json(self, json_str: str) -> str:
        """Repair common JSON malformations in insight responses"""
        import re

        # Remove markdown code fences
        if json_str.startswith('```'):
            json_str = json_str.split('```')[1]
            if json_str.startswith('json'):
                json_str = json_str[4:]
            json_str = json_str.strip()

        # Strategy 1 & 2: Fix ALL invalid escape sequences
        # Valid JSON escapes: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
        # Anything else (like \e, \s, \d, \w, \x, \-, etc.) needs to be double-escaped

        # First, temporarily protect valid escapes with unique markers
        protected = json_str
        protected = protected.replace('\\n', '\x00NEWLINE\x00')
        protected = protected.replace('\\t', '\x00TAB\x00')
        protected = protected.replace('\\r', '\x00RETURN\x00')
        protected = protected.replace('\\"', '\x00QUOTE\x00')
        protected = protected.replace('\\\\', '\x00BACKSLASH\x00')
        protected = protected.replace('\\/', '\x00SLASH\x00')
        protected = protected.replace('\\b', '\x00BSPACE\x00')
        protected = protected.replace('\\f', '\x00FORMFEED\x00')
        # Protect \uXXXX unicode escapes
        protected = re.sub(r'\\u([0-9a-fA-F]{4})', r'\x00UNICODE\1\x00', protected)

        # Now escape ALL remaining backslashes (these are invalid escapes)
        protected = protected.replace('\\', '\\\\')

        # Restore valid escapes
        protected = protected.replace('\x00NEWLINE\x00', '\\n')
        protected = protected.replace('\x00TAB\x00', '\\t')
        protected = protected.replace('\x00RETURN\x00', '\\r')
        protected = protected.replace('\x00QUOTE\x00', '\\"')
        protected = protected.replace('\x00BACKSLASH\x00', '\\\\')
        protected = protected.replace('\x00SLASH\x00', '\\/')
        protected = protected.replace('\x00BSPACE\x00', '\\b')
        protected = protected.replace('\x00FORMFEED\x00', '\\f')
        # Restore unicode escapes
        protected = re.sub(r'\x00UNICODE([0-9a-fA-F]{4})\x00', r'\\u\1', protected)

        json_str = protected

        # Strategy 3: Replace unescaped newlines in strings (but preserve JSON structure newlines)
        # Only replace newlines that appear inside quoted strings
        lines = json_str.split('\n')
        in_string = False
        fixed_lines = []

        for line in lines:
            # Count quotes to determine if we're in a string
            quote_count = line.count('"') - line.count('\\"')
            if quote_count % 2 == 1:
                in_string = not in_string

            if in_string and line.strip():
                # We're inside a string - this newline should be escaped
                fixed_lines.append(line + '\\n')
            else:
                fixed_lines.append(line)

        json_str = '\n'.join(fixed_lines)

        # Strategy 4: Remove trailing commas
        json_str = re.sub(r',\s*]', ']', json_str)
        json_str = re.sub(r',\s*}', '}', json_str)

        return json_str.strip()

    def _extract_insights_with_regex(self, text: str) -> List[str]:
        """Fallback: Extract insights using regex when JSON parsing fails"""
        import re
        # Try to find array-like patterns
        insights = []

        # Pattern 1: Match quoted strings in a list-like structure
        pattern1 = r'"([^"]{20,}?)"'
        matches = re.findall(pattern1, text)
        if matches:
            # Filter to only keep substantial text (likely insights, not keys)
            insights = [m for m in matches if len(m) > 30 and not m.startswith('http')]

        return insights[:20]  # Limit to reasonable number

    async def filter_research_insights(self, insights: List[str], keyword: str, context: str = "", source_type: str = "generic") -> List[str]:
        """Filter out irrelevant/out-of-context insights using Qwen for all sources

        Args:
            insights: List of insight strings to filter
            keyword: The keyword/topic to filter for relevance
            context: Context description (e.g., "Reddit discussions")
            source_type: Type of source (for logging)
        """
        if not insights:
            return []

        if not self.nebius:
            # No Nebius = no filtering, return insights as-is
            return insights

        # Use Qwen for all insight filtering (Kimi-K2.5 fallback via _filter_with_llama is dead code now)
        return await self._filter_with_qwen(insights, keyword, context)

    async def _filter_with_llama(self, insights: List[str], keyword: str, context: str) -> List[str]:
        """Filter insights using Kimi-K2.5 on Nebius (robust mode for complex/long insights)"""
        if not self.nebius:
            return insights

        logger.info(f"🔍 Filtering {len(insights)} {context} insights with Kimi-K2.5 (robust mode)...")
        logger.info(f"🎯 Kimi filter: ICP context injected for relevance scoring")

        # Prepare insights for filtering
        insights_json = json.dumps(insights, indent=2)

        # Get ICP context for filtering
        icp_filter_context = _ICP_RESEARCH_CONTEXT

        filter_prompt = f"""Review these research insights for the keyword: "{keyword}"

Context: {context or "General research"}
{icp_filter_context}
Your task: Filter out insights that are:
1. Completely off-topic or irrelevant to "{keyword}"
2. Generic/obvious statements with no real value (e.g., "it depends", "do your research")
3. Spam, promotional content, or self-promotion
4. Duplicate information (same point rephrased)
5. Too vague or unhelpful to be actionable

KEEP insights that are:
- Specific pain points or challenges related to "{keyword}"
- Concrete recommendations or solutions from practitioners
- Real user experiences or case studies
- Technical details or implementation advice
- Relevant to our target audience (business operators, not enterprise)

Insights to filter:
{insights_json}

CRITICAL JSON FORMATTING REQUIREMENTS:
- Return ONLY a valid JSON array: ["insight1", "insight2", "insight3"]
- Each insight MUST be on a single line (no line breaks within strings)
- Escape ALL quotes within insights using backslash: \\"
- Escape ALL backslashes: \\\\
- Do NOT include any text before or after the JSON array
- Do NOT use markdown code fences

Example format:
["Insight 1 that's relevant", "Insight 2 with \\"escaped quotes\\" works", "Insight 3 with specific details"]

Return ONLY the JSON array, no explanations, no code fences."""

        try:
            response = await self.nebius.chat.completions.create(
                model=self.model_creative,
                messages=[{
                    "role": "system",
                    "content": "You are a research quality filter. You identify and remove irrelevant, low-quality, or off-topic insights while preserving valuable, specific, actionable information. Return ONLY valid JSON arrays."
                }, {
                    "role": "user",
                    "content": filter_prompt
                }],
                temperature=0.1,
                max_tokens=6000
            )

            result = response.choices[0].message.content.strip()

            # Handle empty response
            if not result:
                logger.warning(f"⚠️  Kimi filter returned empty response, keeping all insights")
                return insights

            # Parse JSON response with repair strategies
            filtered_insights = None

            # Strategy 1: Try standard parse
            try:
                filtered_insights = json.loads(result)
            except json.JSONDecodeError as e1:
                logger.info(f"  Standard parse failed: {str(e1)[:100]}")

                # Strategy 2: Try with repair
                try:
                    repaired = self._repair_insight_json(result)
                    filtered_insights = json.loads(repaired)
                    logger.info(f"  ✓ Repair strategy succeeded")
                except json.JSONDecodeError as e2:
                    logger.info(f"  Repair parse failed: {str(e2)[:100]}")

                    # Strategy 3: Fallback to regex extraction
                    try:
                        extracted = self._extract_insights_with_regex(result)
                        if extracted and len(extracted) > 0:
                            filtered_insights = extracted
                            logger.info(f"  ✓ Regex extraction found {len(extracted)} insights")
                        else:
                            logger.warning(f"⚠️  All parsing strategies failed, keeping original insights")
                            return insights
                    except Exception as e3:
                        logger.warning(f"⚠️  Regex extraction failed: {e3}, keeping original insights")
                        return insights

            # Validate parsed result
            if isinstance(filtered_insights, list):
                if all(isinstance(item, str) for item in filtered_insights):
                    removed = len(insights) - len(filtered_insights)
                    logger.info(f"✅ Kimi filtered from {len(insights)} to {len(filtered_insights)} insights ({removed} removed)")
                    return filtered_insights
                else:
                    logger.warning(f"⚠️  Filter returned list with non-string items, keeping original")
                    return insights
            else:
                logger.warning(f"⚠️  Filter returned non-list: {type(filtered_insights)}, keeping original")
                return insights

        except Exception as e:
            logger.error(f"❌ Kimi insight filtering failed: {e}")
            return insights

    async def _filter_with_qwen(self, insights: List[str], keyword: str, context: str) -> List[str]:
        """Filter insights using Qwen3 235B (best quality for all insight types) with batching"""
        if not self.nebius:
            return insights

        # Batch processing for large insight sets
        batch_size = 50
        if len(insights) > batch_size:
            logger.info(f"🔍 Filtering {len(insights)} {context} insights with Qwen3 235B in batches of {batch_size}...")
            logger.info(f"🎯 Slightly stricter filtering (+5%) for batched processing")

            all_filtered = []
            num_batches = (len(insights) + batch_size - 1) // batch_size

            for batch_idx in range(num_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(insights))
                batch = insights[start_idx:end_idx]

                # Slightly stricter filtering for all batches (+5%)
                strictness_bonus = 5

                logger.info(f"  📦 Batch {batch_idx + 1}/{num_batches}: {len(batch)} insights")

                filtered_batch = await self._filter_batch_with_qwen(batch, keyword, context, strictness_bonus)
                all_filtered.extend(filtered_batch)

            logger.info(f"✅ Qwen batched filtering: {len(insights)} → {len(all_filtered)} insights ({len(insights) - len(all_filtered)} removed)")
            return all_filtered
        else:
            # Small batch - process directly
            logger.info(f"🔍 Filtering {len(insights)} {context} insights with Qwen3 235B (highest quality)...")
            logger.info(f"🎯 Qwen filter: ICP context injected for relevance scoring")
            return await self._filter_batch_with_qwen(insights, keyword, context, strictness_bonus=0)

    async def _filter_batch_with_qwen(self, insights: List[str], keyword: str, context: str, strictness_bonus: int = 0) -> List[str]:
        """Filter a single batch of insights with Qwen3 235B"""
        # Prepare insights for filtering
        insights_json = json.dumps(insights, indent=2)

        # Get ICP context for filtering
        icp_filter_context = _ICP_RESEARCH_CONTEXT

        # Progressive strictness instructions
        strictness_note = ""
        if strictness_bonus > 0:
            strictness_note = f"\n⚡ STRICTNESS LEVEL: +{strictness_bonus}% - Be {strictness_bonus}% more selective. Prioritize only the MOST valuable, specific, and actionable insights.\n"

        filter_prompt = f"""Review these research insights for the keyword: "{keyword}"

Context: {context or "General research"}
{icp_filter_context}{strictness_note}
Your task: Filter out insights that are:
1. Completely off-topic or irrelevant to "{keyword}"
2. Generic/obvious statements with no real value (e.g., "it depends", "do your research")
3. Spam, promotional content, or self-promotion
4. Duplicate information (same point rephrased)
5. Too vague or unhelpful to be actionable

KEEP insights that are:
- Specific pain points or challenges related to "{keyword}"
- Concrete recommendations or solutions from practitioners
- Real user experiences or case studies
- Technical details or implementation advice
- Relevant to our target audience (business operators, not enterprise)

Insights to filter:
{insights_json}

CRITICAL JSON FORMATTING REQUIREMENTS:
- Return ONLY a valid JSON array: ["insight1", "insight2", "insight3"]
- Each insight MUST be on a single line (no line breaks within strings)
- Do NOT use ANY escape sequences - keep text raw and simple
- Replace problematic characters with spaces or remove them
- Do NOT include any text before or after the JSON array
- Do NOT use markdown code fences

Example format:
["Insight 1 that is relevant", "Insight 2 with quotes works fine", "Insight 3 with specific details"]

Return ONLY the JSON array, no explanations, no code fences."""

        try:
            response = await self.nebius.chat.completions.create(
                model="Qwen/Qwen3-235B-A22B-Instruct-2507",
                messages=[{
                    "role": "system",
                    "content": "You are a research quality filter. You identify and remove irrelevant, low-quality, or off-topic insights while preserving valuable, specific, actionable information. Return ONLY valid JSON arrays with no escape sequences."
                }, {
                    "role": "user",
                    "content": filter_prompt
                }],
                temperature=0.1,
                max_tokens=8000
            )

            result = response.choices[0].message.content.strip()

            # Handle empty response
            if not result:
                logger.warning(f"⚠️  Qwen filter returned empty response, keeping all insights")
                return insights

            # Parse JSON response with repair strategies
            filtered_insights = None

            # Strategy 1: Try standard parse
            try:
                filtered_insights = json.loads(result)
            except json.JSONDecodeError as e1:
                logger.info(f"  Standard parse failed: {str(e1)[:100]}")

                # Strategy 2: Try with repair
                try:
                    repaired = self._repair_insight_json(result)
                    filtered_insights = json.loads(repaired)
                    logger.info(f"  ✓ Repair strategy succeeded")
                except json.JSONDecodeError as e2:
                    logger.info(f"  Repair parse failed: {str(e2)[:100]}")

                    # Strategy 3: Fallback to regex extraction
                    try:
                        extracted = self._extract_insights_with_regex(result)
                        if extracted and len(extracted) > 0:
                            filtered_insights = extracted
                            logger.info(f"  ✓ Regex extraction found {len(extracted)} insights")
                        else:
                            logger.warning(f"⚠️  All parsing strategies failed, keeping original insights")
                            return insights
                    except Exception as e3:
                        logger.warning(f"⚠️  Regex extraction failed: {e3}, keeping original insights")
                        return insights

            # Validate parsed result
            if isinstance(filtered_insights, list):
                if all(isinstance(item, str) for item in filtered_insights):
                    removed = len(insights) - len(filtered_insights)
                    logger.info(f"✅ Qwen filtered from {len(insights)} to {len(filtered_insights)} insights ({removed} removed)")
                    return filtered_insights
                else:
                    logger.warning(f"⚠️  Filter returned list with non-string items, keeping original")
                    return insights
            else:
                logger.warning(f"⚠️  Filter returned non-list: {type(filtered_insights)}, keeping original")
                return insights

        except Exception as e:
            logger.error(f"❌ Qwen insight filtering failed: {e}")
            return insights

    async def _filter_with_oss(self, insights: List[str], keyword: str, context: str) -> List[str]:
        """Filter insights using OSS-120B via Nebius (fast, good for shorter insights)"""
        if not self.nebius:
            return insights

        logger.info(f"🔍 Filtering {len(insights)} {context} insights with OSS-120B (fast mode)...")
        logger.info(f"🎯 OSS filter: ICP context injected for relevance scoring")

        # Prepare insights for filtering
        insights_json = json.dumps(insights, indent=2)

        # Get ICP context for filtering
        icp_filter_context = _ICP_RESEARCH_CONTEXT

        filter_prompt = f"""Review these research insights for the keyword: "{keyword}"

Context: {context or "General research"}
{icp_filter_context}
Your task: Filter out insights that are:
1. Completely off-topic or irrelevant to "{keyword}"
2. Out of context for the keyword's domain
3. Generic/obvious statements with no real value (e.g., "it depends", "do your research")
4. Spam, promotional content, or self-promotion
5. Duplicate information (same point rephrased)
6. Too vague or unhelpful to be actionable

KEEP insights that are:
- Specific pain points or challenges related to "{keyword}"
- Concrete recommendations or solutions from practitioners
- Real user experiences or case studies
- Technical details or implementation advice
- Relevant to our target audience (business operators, not enterprise)

Insights to filter:
{insights_json}

CRITICAL JSON FORMATTING REQUIREMENTS:
- Return ONLY a valid JSON array: ["insight1", "insight2", "insight3"]
- Each insight MUST be on a single line (no line breaks within strings)
- Escape ALL quotes within insights using backslash: \\"
- Escape ALL backslashes: \\\\
- Do NOT include any text before or after the JSON array
- Do NOT use markdown code fences

Example format:
["Insight 1 that's relevant", "Insight 2 with \\"escaped quotes\\" works", "Insight 3 with specific details"]

Return ONLY the JSON array, no explanations, no code fences."""

        try:
            response = await self.nebius.chat.completions.create(
                model=self.model_creative,
                messages=[{
                    "role": "system",
                    "content": "You are a research quality filter. You identify and remove irrelevant, low-quality, or off-topic insights while preserving valuable, specific, actionable information."
                }, {
                    "role": "user",
                    "content": filter_prompt
                }],
                temperature=0.1,
                max_tokens=4000
            )

            result = response.choices[0].message.content.strip()

            # Handle empty response
            if not result:
                logger.warning(f"⚠️  Filter returned empty response, keeping all insights")
                return insights

            # Parse JSON response with repair strategies
            filtered_insights = None

            # Strategy 1: Try standard parse
            try:
                filtered_insights = json.loads(result)
            except json.JSONDecodeError as e1:
                logger.info(f"  Standard parse failed: {str(e1)[:100]}")

                # Strategy 2: Try with repair
                try:
                    repaired = self._repair_insight_json(result)
                    filtered_insights = json.loads(repaired)
                    logger.info(f"  ✓ Repair strategy succeeded")
                except json.JSONDecodeError as e2:
                    logger.info(f"  Repair parse failed: {str(e2)[:100]}")

                    # Strategy 3: Fallback to regex extraction
                    try:
                        extracted = self._extract_insights_with_regex(result)
                        if extracted and len(extracted) > 0:
                            filtered_insights = extracted
                            logger.info(f"  ✓ Regex extraction found {len(extracted)} insights")
                        else:
                            logger.warning(f"⚠️  All parsing strategies failed, keeping original insights")
                            return insights
                    except Exception as e3:
                        logger.warning(f"⚠️  Regex extraction failed: {e3}, keeping original insights")
                        return insights

            # Validate parsed result
            if isinstance(filtered_insights, list):
                # Validate that list contains strings
                if all(isinstance(item, str) for item in filtered_insights):
                    removed = len(insights) - len(filtered_insights)
                    logger.info(f"✅ Filtered from {len(insights)} to {len(filtered_insights)} insights ({removed} removed)")
                    return filtered_insights
                else:
                    logger.warning(f"⚠️  Filter returned list with non-string items, keeping original")
                    return insights
            else:
                logger.warning(f"⚠️  Filter returned non-list: {type(filtered_insights)}, keeping original")
                return insights

        except Exception as e:
            logger.error(f"❌ Insight filtering failed: {e}")
            # Return original insights on error
            return insights

    def _filter_platform_questions(self, questions: List[str]) -> List[str]:
        """Filter out questions that contain platform names"""
        # Platform names to exclude from questions
        platform_names = [
            # CRMs
            "capsulecrm", "copper crm", "gohighlevel", "attio", "close", "zoho crm",
            "salesforce", "monday.com", "hubspot",
            # Advertising platforms
            "outbrain", "taboola", "applovin", "youtube ads", "facebook ads",
            "instagram ads", "x ads", "tiktok ads", "snapchat ads", "reddit ads",
            "pinterest ads", "linkedin ads", "microsoft ads",
            # Analytics & tracking
            "google analytics", "google tag manager", "google sheets",
            # Distribution
            "databowl", "leadspedia", "leadbyte", "phonexa", "clickpoint leadexec",
            # Finance
            "xero",
            # Competitors
            "supermetrics", "adverity", "funnel.io", "triple whale", "domo",
            "tableau", "revealbot", "northbeam", "rockerbox"
        ]

        filtered_questions = []
        for question in questions:
            question_lower = question.lower()
            # Check if question contains any platform name
            contains_platform = any(platform in question_lower for platform in platform_names)
            if not contains_platform:
                filtered_questions.append(question)

        return filtered_questions

    # =========================================================================
    # EMBEDDING FILTER: Nebius BGE-EN-ICL for semantic relevance filtering
    # =========================================================================

    async def embed_text(self, text: str) -> List[float]:
        """Get embedding from Nebius BGE-EN-ICL model via Token Factory API.

        Args:
            text: Text to embed (max 32K context)

        Returns:
            4096-dimensional embedding vector
        """
        if not self.nebius_embed:
            logger.warning("   ⚠️  No Nebius Token Factory client for embeddings")
            return []

        try:
            response = await self.nebius_embed.embeddings.create(
                model="BAAI/bge-en-icl",
                input=text[:8000],  # Limit input length (32K context available)
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"   ✗ Embedding failed: {e}")
            return []

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts in batch via Token Factory API.

        Args:
            texts: List of texts to embed

        Returns:
            List of 4096-dimensional embedding vectors
        """
        if not self.nebius_embed or not texts:
            return []

        try:
            # Truncate each text
            truncated = [t[:8000] for t in texts]

            response = await self.nebius_embed.embeddings.create(
                model="BAAI/bge-en-icl",
                input=truncated,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"   ✗ Batch embedding failed: {e}")
            return []

    async def filter_by_embedding_relevance(
        self,
        query: str,
        items: List[str],
        threshold: float = 0.60
    ) -> List[Dict[str, Any]]:
        """Filter items by semantic relevance to query using BGE-EN-ICL embeddings.

        Args:
            query: Reference query (e.g., "CRM integration for lead sellers")
            items: List of text items to filter
            threshold: Minimum cosine similarity (0.0-1.0)

        Returns:
            List of {content, relevance_score, rank} for items above threshold
        """
        import numpy as np

        if not items:
            return []

        logger.info(f"   🔍 Embedding filter: {len(items)} items, threshold {threshold}")

        # Get embeddings
        query_embedding = await self.embed_text(query)
        if not query_embedding:
            # Return all items if embedding fails
            return [{"content": item, "relevance_score": 1.0, "rank": i+1} for i, item in enumerate(items)]

        item_embeddings = await self._embed_batch(items)
        if not item_embeddings:
            return [{"content": item, "relevance_score": 1.0, "rank": i+1} for i, item in enumerate(items)]

        # Calculate cosine similarities and filter
        results = []
        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)

        for i, (item, embedding) in enumerate(zip(items, item_embeddings)):
            if not embedding:
                continue

            item_vec = np.array(embedding)
            item_norm = np.linalg.norm(item_vec)

            # Cosine similarity = dot(a, b) / (norm(a) * norm(b))
            if query_norm > 0 and item_norm > 0:
                similarity = np.dot(query_vec, item_vec) / (query_norm * item_norm)
            else:
                similarity = 0.0

            if similarity >= threshold:
                results.append({
                    "content": item,
                    "relevance_score": float(similarity),
                    "rank": len(results) + 1
                })

        # Sort by relevance
        results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)

        # Update ranks after sorting
        for i, item in enumerate(results):
            item["rank"] = i + 1

        removed = len(items) - len(results)
        logger.info(f"   ✓ Embedding filter: {len(results)} kept, {removed} removed")

        return results

    # ═══════════════════════════════════════════════════════════════════════════════
    # SOLUTION EXTRACTION & DISCOVERY SYSTEM
    # ═══════════════════════════════════════════════════════════════════════════════

    async def extract_solutions_from_research(
        self,
        keyword: str,
        serp_data: Dict[str, Any],
        reddit_data: Dict[str, Any],
        quora_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Hyper-intelligent solution extraction from research data.

        Uses Gemini to semantically parse research and extract ONLY solutions
        that are genuinely relevant to the keyword's core intent.

        Returns list of: {name, url, source, confidence, why_relevant}
        """
        if not self.gemini_client:
            logger.warning("No Gemini client available for solution extraction")
            return []

        # Compile all research text
        serp_text = serp_data.get('serp_analysis', {}).get('analysis', '') if isinstance(serp_data.get('serp_analysis'), dict) else str(serp_data.get('serp_analysis', ''))
        citations = serp_data.get('serp_analysis', {}).get('citations', []) if isinstance(serp_data.get('serp_analysis'), dict) else []

        reddit_insights = reddit_data.get('insights', []) if reddit_data else []
        quora_insights = quora_data.get('expert_insights', []) if quora_data else []

        # Build comprehensive prompt for intelligent extraction
        prompt = f"""You are a HYPER-INTELLIGENT solution extraction system. Your job is to find REAL products/tools/solutions mentioned in research data.

═══════════════════════════════════════════════════════════════════════════════
KEYWORD BEING RESEARCHED: "{keyword}"
═══════════════════════════════════════════════════════════════════════════════

STEP 1: SEMANTIC DECOMPOSITION
First, analyze the keyword to understand EXACTLY what category of solution is being sought:
- What is the CORE NOUN (the thing being sought)?
- What are the QUALIFYING MODIFIERS (constraints, platforms, niches)?
- What FUNCTION must solutions perform to satisfy this search?

STEP 2: RESEARCH DATA TO PARSE

### SERP ANALYSIS:
{serp_text[:8000] if serp_text else "No SERP data available"}

### SERP CITATIONS:
{json.dumps(citations[:20], indent=2) if citations else "No citations"}

### REDDIT COMMUNITY INSIGHTS:
{chr(10).join(f'- {insight}' for insight in reddit_insights[:15]) if reddit_insights else "No Reddit insights"}

### QUORA EXPERT INSIGHTS:
{chr(10).join(f'- {insight}' for insight in quora_insights[:10]) if quora_insights else "No Quora insights"}

═══════════════════════════════════════════════════════════════════════════════
EXTRACTION RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════════════

1. ONLY extract solutions that DIRECTLY match the keyword's semantic intent
2. Each solution must be a REAL product/tool/service with a verifiable URL
3. Solutions must be SUBSTITUTES for each other (same category), not complementary tools
4. Assign confidence scores based on:
   - 0.9+: Explicitly mentioned as a solution for this exact use case
   - 0.7-0.9: Mentioned in relevant context, likely a match
   - 0.5-0.7: Tangentially mentioned, may or may not be relevant
   - <0.5: Don't include - too uncertain

ANTI-HALLUCINATION RULES:
- NEVER invent solutions not mentioned in the research
- NEVER include generic tools that happen to be famous (e.g., Zapier, HubSpot) unless they're SPECIFICALLY mentioned as solutions for THIS keyword
- If the keyword asks for "X for Y platform" (e.g., MCPs for Google Ads), solutions MUST specifically work with Y platform
- If unsure, DON'T include it - quality over quantity

OUTPUT FORMAT (JSON array):
[
  {{
    "name": "Exact Product Name",
    "url": "https://official-website.com",
    "source": "SERP|Reddit|Quora",
    "confidence": 0.85,
    "why_relevant": "1 sentence explaining why this matches the keyword"
  }}
]

If NO genuinely relevant solutions are found, return an empty array: []
This is better than padding with irrelevant results.
"""

        try:
            response = await self.gemini_client.aio.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,  # Very low for factual extraction
                    max_output_tokens=4000,
                )
            )

            content = response.text

            # Parse JSON from response
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                solutions = json.loads(match.group(0))

                # Validate and clean solutions
                valid_solutions = []
                seen_names = set()

                for sol in solutions:
                    if not isinstance(sol, dict):
                        continue

                    name = sol.get('name', '').strip()
                    if not name or name.lower() in seen_names:
                        continue

                    # Skip obviously irrelevant generic tools unless high confidence
                    generic_tools = {'zapier', 'hubspot', 'salesforce', 'airtable', 'notion',
                                   'google sheets', 'excel', 'slack', 'trello', 'asana',
                                   'monday.com', 'clickup', 'jira', 'confluence'}
                    if name.lower() in generic_tools and sol.get('confidence', 0) < 0.85:
                        continue

                    seen_names.add(name.lower())
                    valid_solutions.append({
                        'name': name,
                        'url': sol.get('url', ''),
                        'source': sol.get('source', 'Unknown'),
                        'confidence': min(1.0, max(0.0, float(sol.get('confidence', 0.5)))),
                        'why_relevant': sol.get('why_relevant', '')
                    })

                # Sort by confidence
                valid_solutions.sort(key=lambda x: x['confidence'], reverse=True)

                logger.info(f"   ✓ Extracted {len(valid_solutions)} solutions from research")
                return valid_solutions

        except Exception as e:
            logger.error(f"Solution extraction failed: {e}")

        return []

    async def discover_solutions_grounded(
        self,
        keyword: str,
        rejected_solutions: List[str],
        approved_solutions: List[str],
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Use Gemini with Google Search grounding to discover REAL, RELEVANT solutions
        that the initial research missed.

        This is hyper-intelligent: it learns from what the user approved/rejected
        to understand the EXACT category and find similar solutions.
        """
        if not self.gemini_client:
            logger.warning("No Gemini client available for grounded discovery")
            return []

        # Build context-aware discovery prompt
        prompt = f"""You are a WORLD-CLASS solution discovery system with real-time web search.

═══════════════════════════════════════════════════════════════════════════════
MISSION: Find {count} REAL solutions for: "{keyword}"
═══════════════════════════════════════════════════════════════════════════════

CRITICAL LEARNING CONTEXT:
The user has already reviewed initial research results. Learn from their decisions:

✅ APPROVED AS RELEVANT (these define the correct category):
{chr(10).join(f'   - {sol}' for sol in approved_solutions) if approved_solutions else '   (none yet)'}

❌ REJECTED AS IRRELEVANT (avoid solutions like these):
{chr(10).join(f'   - {sol}' for sol in rejected_solutions) if rejected_solutions else '   (none rejected)'}

═══════════════════════════════════════════════════════════════════════════════
SEMANTIC ANALYSIS (DO THIS FIRST)
═══════════════════════════════════════════════════════════════════════════════

1. KEYWORD DECOMPOSITION:
   - Core noun: What TYPE of thing is being sought?
   - Modifiers: What constraints/platforms/niches apply?
   - Function: What must solutions DO to satisfy this search?

2. CATEGORY INFERENCE FROM APPROVALS:
   If approved solutions exist, they define the EXACT category.
   New solutions must be DIRECT SUBSTITUTES (same market category).

3. ANTI-PATTERN FROM REJECTIONS:
   If rejections exist, understand WHY they were wrong.
   Avoid similar mistakes (e.g., if Zapier was rejected for an "MCP" search,
   don't suggest other automation platforms - they're the wrong category).

═══════════════════════════════════════════════════════════════════════════════
DISCOVERY REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

1. SEARCH THE WEB for real products matching "{keyword}"
2. Prefer LESSER-KNOWN but highly-relevant solutions over famous but tangential ones
3. Each solution MUST have a real, verifiable website (check it exists)
4. Solutions must be ACTUAL PRODUCTS/TOOLS, not articles or tutorials
5. Don't repeat any solutions from the approved or rejected lists

QUALITY STANDARDS:
- Every solution must pass the "searcher satisfaction" test
- If someone Googled "{keyword}", would they be SATISFIED finding this?
- If unsure, don't include it - quality over quantity

OUTPUT FORMAT (JSON array):
[
  {{
    "name": "Solution Name",
    "url": "https://official-website.com",
    "source": "Web Search",
    "confidence": 0.85,
    "why_relevant": "1 sentence explaining exact match to keyword"
  }}
]

SEARCH NOW and find {count} genuinely relevant solutions.
If you can't find {count} truly relevant ones, return fewer - don't pad with garbage.
"""

        try:
            # Use grounding with Google Search for real-time discovery
            grounding_tool = genai_types.Tool(
                google_search=genai_types.GoogleSearch()
            )

            response = await self.gemini_client.aio.models.generate_content(
                model="gemini-3-pro-preview",  # Pro for better reasoning + grounding
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    tools=[grounding_tool],
                    temperature=0.2,  # Low for factual accuracy
                    max_output_tokens=4000,
                )
            )

            content = response.text

            # Parse JSON from response
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                solutions = json.loads(match.group(0))

                # Validate discovered solutions
                valid_solutions = []
                seen_names = set()
                existing_names = set(s.lower() for s in approved_solutions + rejected_solutions)

                for sol in solutions:
                    if not isinstance(sol, dict):
                        continue

                    name = sol.get('name', '').strip()
                    if not name or name.lower() in seen_names or name.lower() in existing_names:
                        continue

                    seen_names.add(name.lower())
                    valid_solutions.append({
                        'name': name,
                        'url': sol.get('url', ''),
                        'source': 'Web Search',
                        'confidence': min(1.0, max(0.0, float(sol.get('confidence', 0.7)))),
                        'why_relevant': sol.get('why_relevant', '')
                    })

                # Sort by confidence
                valid_solutions.sort(key=lambda x: x['confidence'], reverse=True)

                logger.info(f"   ✓ Discovered {len(valid_solutions)} new solutions via web search")
                return valid_solutions

        except Exception as e:
            logger.error(f"Grounded solution discovery failed: {e}")

        return []

    # ═══════════════════════════════════════════════════════════════════════════
    # INTELLIGENT COMPETITOR DISCOVERY (v2 - Perplexity + Gemini Grounded)
    # ═══════════════════════════════════════════════════════════════════════════

    async def discover_competitors_intelligent(
        self,
        keyword: str,
        existing_competitors: List[str] = None,
        count: int = 8
    ) -> List[Dict[str, Any]]:
        """Hyper-intelligent competitor discovery using multiple AI sources.

        Strategy:
        1. Perplexity SERP analysis for top-ranking competitors
        2. Gemini grounded search for lesser-known alternatives
        3. Merge, deduplicate, and rank by relevance

        Args:
            keyword: The target keyword
            existing_competitors: Already-known competitors (to avoid duplicates)
            count: Target number of competitors to find

        Returns:
            List of: {name, source, confidence, url, why_relevant}
        """
        existing = existing_competitors or []
        all_competitors = []

        # ─────────────────────────────────────────────────────────────────────
        # Source 1: Perplexity SERP Analysis
        # ─────────────────────────────────────────────────────────────────────
        try:
            logger.info(f"🔍 Discovering competitors via Perplexity SERP...")
            perplexity_competitors = await self._discover_via_perplexity(keyword, existing)
            all_competitors.extend(perplexity_competitors)
            logger.info(f"   ✓ Perplexity found {len(perplexity_competitors)} competitors")
        except Exception as e:
            logger.warning(f"Perplexity discovery failed: {e}")

        # ─────────────────────────────────────────────────────────────────────
        # Source 2: Gemini Grounded Web Search (lesser-known alternatives)
        # ─────────────────────────────────────────────────────────────────────
        try:
            # Only search for more if Perplexity didn't find enough
            remaining = count - len(all_competitors)
            if remaining > 0:
                logger.info(f"🔍 Finding {remaining} more via Gemini grounded search...")
                known_names = [c['name'] for c in all_competitors] + existing
                gemini_competitors = await self._discover_via_gemini_grounded_competitors(
                    keyword,
                    known_names,
                    count=remaining
                )
                all_competitors.extend(gemini_competitors)
                logger.info(f"   ✓ Gemini found {len(gemini_competitors)} more competitors")
        except Exception as e:
            logger.warning(f"Gemini grounded discovery failed: {e}")

        # Deduplicate by name (case-insensitive)
        seen = set()
        unique = []
        for comp in all_competitors:
            name_lower = comp['name'].lower()
            if name_lower not in seen and name_lower not in [e.lower() for e in existing]:
                seen.add(name_lower)
                unique.append(comp)

        logger.info(f"✓ Total unique competitors found: {len(unique)}")
        return unique[:count]

    async def _discover_via_perplexity(
        self,
        keyword: str,
        exclude: List[str]
    ) -> List[Dict[str, Any]]:
        """Use Perplexity to find competitors from SERP analysis.

        Args:
            keyword: Target keyword
            exclude: Already-known competitors to exclude

        Returns:
            List of competitor dicts with {name, url, source, confidence, why_relevant}
        """
        if not self.perplexity_key:
            logger.warning("No Perplexity API key - skipping SERP discovery")
            return []

        if not self.session:
            self.session = aiohttp.ClientSession()

        exclude_str = ', '.join(exclude) if exclude else '(none)'

        prompt = f"""Analyze the search results for "{keyword}" and extract ALL
tools/products/solutions that compete in this EXACT category.

EXCLUDE these (already known): {exclude_str}

For EACH competitor found, you MUST provide:
1. name: The official product/tool name
2. url: The official website URL
3. why_relevant: One sentence explaining why it's a DIRECT competitor

CRITICAL REQUIREMENTS:
- Only include tools that are DIRECT substitutes for what the keyword describes
- Prefer specialized/niche solutions over generic enterprise tools
- Each competitor must actually exist and be publicly available
- Include both well-known and lesser-known alternatives

Return ONLY a valid JSON array in this exact format:
[
  {{"name": "Product Name", "url": "https://example.com", "why_relevant": "Explanation"}}
]

Be exhaustive - include at least 8-10 competitors if they exist."""

        try:
            async with self.session.post(
                "https://api.perplexity.ai/chat/completions",
                json={
                    "model": "sonar-reasoning-pro",
                    "messages": [{"role": "user", "content": prompt}],
                    "search_context_size": "large"
                },
                headers={
                    "Authorization": f"Bearer {self.perplexity_key}",
                    "Content-Type": "application/json"
                }
            ) as response:
                if response.status != 200:
                    logger.warning(f"Perplexity API returned status {response.status}")
                    return []

                data = await response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

                # Parse JSON from response
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    competitors = json.loads(match.group(0))

                    result = []
                    seen_names = set()

                    for comp in competitors:
                        if not isinstance(comp, dict):
                            continue

                        name = comp.get('name', '').strip()
                        if not name or name.lower() in seen_names or name.lower() in [e.lower() for e in exclude]:
                            continue

                        seen_names.add(name.lower())
                        result.append({
                            'name': name,
                            'url': comp.get('url', ''),
                            'source': 'SERP',
                            'confidence': 0.85,  # SERP results are high confidence
                            'why_relevant': comp.get('why_relevant', '')
                        })

                    return result

        except Exception as e:
            logger.error(f"Perplexity competitor discovery failed: {e}")

        return []

    async def _discover_via_gemini_grounded_competitors(
        self,
        keyword: str,
        exclude: List[str],
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Use Gemini with Google Search grounding to find lesser-known competitors.

        Args:
            keyword: Target keyword
            exclude: Already-known competitors to exclude
            count: Number of competitors to find

        Returns:
            List of competitor dicts
        """
        if not self.gemini_client:
            logger.warning("No Gemini client available for grounded discovery")
            return []

        exclude_str = ', '.join(exclude) if exclude else '(none)'

        prompt = f"""You are a HYPER-INTELLIGENT competitor discovery agent with web search.

═══════════════════════════════════════════════════════════════════════════════
MISSION: Find {count} LESSER-KNOWN but HIGHLY-RELEVANT competitors for: "{keyword}"
═══════════════════════════════════════════════════════════════════════════════

CRITICAL CONSTRAINTS:
1. EXCLUDE these (already known): {exclude_str}
2. Focus on NICHE, SPECIALIZED solutions that larger research might miss
3. Each competitor MUST be a DIRECT substitute - not tangentially related
4. Verify each has a real, active website (search to confirm)
5. Prefer newer/smaller players over well-known incumbents

SEMANTIC ANALYSIS (do this first):
- Parse "{keyword}" to understand the EXACT category
- Identify the core function/purpose being sought
- Only include tools that fulfill this EXACT purpose

QUALITY OVER QUANTITY:
- Only return solutions you're CONFIDENT are relevant
- If you can't find {count} truly relevant ones, return fewer
- Don't pad with famous but irrelevant tools

OUTPUT FORMAT (JSON array):
[
  {{
    "name": "Product Name",
    "url": "https://official-website.com",
    "why_relevant": "One sentence explaining EXACT relevance to keyword"
  }}
]

SEARCH NOW for real products matching "{keyword}" that aren't in the exclude list."""

        try:
            grounding_tool = genai_types.Tool(
                google_search=genai_types.GoogleSearch()
            )

            response = await self.gemini_client.aio.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",  # Fast + grounded
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    tools=[grounding_tool],
                    temperature=0.2,
                    max_output_tokens=2000
                )
            )

            content = response.text

            # Parse JSON from response
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                competitors = json.loads(match.group(0))

                result = []
                seen_names = set()

                for comp in competitors:
                    if not isinstance(comp, dict):
                        continue

                    name = comp.get('name', '').strip()
                    if not name or name.lower() in seen_names or name.lower() in [e.lower() for e in exclude]:
                        continue

                    seen_names.add(name.lower())
                    result.append({
                        'name': name,
                        'url': comp.get('url', ''),
                        'source': 'Web Search',
                        'confidence': 0.75,  # Slightly lower than SERP
                        'why_relevant': comp.get('why_relevant', '')
                    })

                return result

        except Exception as e:
            logger.error(f"Gemini grounded competitor discovery failed: {e}")

        return []

    async def generate_questions(self, keyword: str, count: int = 100, context_questions: Optional[List[str]] = None, platform: Optional[str] = None, style: Optional[str] = None) -> List[str]:
        """Generate natural language questions from keyword using Gemini 3 Flash

        Args:
            keyword: Target keyword to generate questions for
            count: Number of questions to generate
            context_questions: Optional PAA questions for context
            platform: Optional platform optimization ('reddit', 'quora', or None for mixed)
            style: Optional content style for question type optimization ('research' for data-driven questions)
        """
        if not self.gemini_client and not self.nebius:
            # Generate fallback questions with long-tail focus (service businesses)
            fallback_templates = [
                f"What is {keyword} and how does it work?",
                f"How do I implement {keyword} in my business?",
                f"What are the best {keyword} tools for 2025?",
                f"How much does {keyword} cost for small businesses?",
                f"What are common {keyword} mistakes to avoid?",
                f"How to get started with {keyword} integration?",
                f"What are {keyword} best practices for beginners?",
                f"Who should use {keyword} and when?",
                f"Why is {keyword} important for marketing?",
                f"What problems does {keyword} solve for sales teams?",
                f"How to choose the right {keyword} solution?",
                f"What are the benefits of {keyword} automation?",
                f"How does {keyword} improve customer relationships?",
                f"What are {keyword} security considerations?",
                f"How to troubleshoot {keyword} connection issues?"
            ]
            # Filter platform names from fallback questions too
            filtered_fallback = self._filter_platform_questions(fallback_templates)
            return (filtered_fallback * (count // len(filtered_fallback) + 1))[:count]
        
        all_questions = []
        batch_size = 10  # Reduced batch size to prevent truncation issues
        
        while len(all_questions) < count:
            remaining = count - len(all_questions)
            current_batch_size = min(batch_size, remaining)
            
            context_str = ""
            if context_questions:
                context_str = f"""

Use these related questions as inspiration for similar topics and angles:
{chr(10).join(f"- {q}" for q in context_questions[:3])}
"""

            prompt = f"""You are a world-class semantic intelligence system. Generate {current_batch_size} community research questions.

═══════════════════════════════════════════════════════════════════════════════
TARGET KEYWORD: "{keyword}"
═══════════════════════════════════════════════════════════════════════════════

PHASE 1 — KEYWORD DECOMPOSITION & SENTIMENT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyze each word/phrase in the keyword for:

A) CORE ENTITIES (nouns/noun phrases):
   - What THING(S) is the searcher looking for? (products, tools, methods, concepts)
   - Extract the primary subject vs modifiers

B) INTENT SIGNALS (verbs, adjectives, numbers):
   - "Top", "Best", numbers → COMPARISON/RANKING intent
   - "How to", "Guide" → IMPLEMENTATION/LEARNING intent
   - "vs", "or", "difference" → EVALUATION/DECISION intent
   - "Why", "Problem", "Issue" → TROUBLESHOOTING/VALIDATION intent
   - "2025", "2026", "new" → RECENCY/FRESHNESS intent

C) SCOPE INDICATORS:
   - Platform names → NARROW scope (specific ecosystem)
   - "for [use case]" → MODERATE scope (specific application)
   - Generic terms → BROAD scope (exploratory)

D) EMOTIONAL UNDERTONES:
   - Frustration signals: "still", "can't", "won't work"
   - Curiosity signals: "what is", "how does"
   - Urgency signals: "now", "quickly", "ASAP"
   - Skepticism signals: "really", "actually", "worth it"
{context_str}"""

            # Add domain-specific term expansion
            domain_expansions = {
                'ads': ['advertising', 'paid media', 'industry category', 'direct response', 'paid acquisition', 'media buying'],
                'ad': ['advertising', 'paid media', 'industry category'],
            }

            # Detect if keyword contains domain trigger words (word boundary check)
            expansion_terms = []
            keyword_lower = keyword.lower()
            keyword_words = keyword_lower.split()
            for trigger, alternatives in domain_expansions.items():
                if trigger in keyword_words:  # Word boundary check
                    expansion_terms.extend(alternatives)
                    break  # Only apply one domain expansion

            # If expansion terms found, inject into prompt
            if expansion_terms:
                prompt += f"""

🎯 DOMAIN TERM EXPANSION:
When generating questions, also use these highly relevant alternatives: {', '.join(expansion_terms[:4])}

Example: If generating "best ads platform", also generate "best performance marketing platform", "best paid media platform", etc.
"""

            prompt += """

PHASE 2 — MULTI-LEVEL QUESTION GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate questions at VARYING SPECIFICITY LEVELS:

🔹 BROAD QUESTIONS (cast a wide net):
   - "What's everyone using for [core entity]?"
   - "Any recommendations for [core entity] in [year]?"

🔸 MODERATE QUESTIONS (refine the search):
   - Questions about specific features/capabilities
   - Comparison between options within the category
   - Use case validation questions

🔺 NARROW QUESTIONS (precise answers):
   - Technical implementation details
   - Specific problem/solution pairs
   - Integration with specific platforms mentioned

PHASE 3 — QUESTION TYPE DIVERSITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            # Add style-specific question types optimized for each content style
            if style == "research":
                prompt += """
Include a MIX of these DATA-DRIVEN types (optimized for research content):

1. QUANTITATIVE_BENCHMARKS (25%): "What percentage of...", "Average ROI for...", "Industry benchmark for...", "Typical conversion rates..."
2. CASE_STUDY_MINING (20%): "Companies that achieved...", "Before/after results from...", "Success stories with...", "Real examples of..."
3. EXPERT_CONSENSUS (15%): "What do experts recommend...", "Best practices according to...", "Industry leaders' approach to...", "Professional consensus on..."
4. MARKET_ANALYSIS (15%): "Market size for...", "Adoption rate of...", "Growth trends in...", "Industry statistics on..."
5. COMPARATIVE_PERFORMANCE (10%): "Performance difference between...", "Top quartile vs median...", "Manual vs automated...", "X vs Y effectiveness..."
6. ROI_VALIDATION (10%): "Actual ROI from...", "Payback period for...", "Cost vs benefit of...", "Return on investment for..."
7. IMPLEMENTATION_INSIGHTS (5%): "How long does implementation take...", "Resources needed for...", "Common mistakes when...", "Timeline for..."
8. TREND_FORECASTING (5%): "Where is [X] heading...", "Emerging technologies in...", "Future of...", "What's coming next in..."
"""

            elif style == "guide":
                prompt += """
Include a MIX of these STEP-BY-STEP types (optimized for tutorial content):

1. STEP_SPECIFIC (30%): "How do I do [specific step]...", "What's the first thing to do with...", "What comes after...", "Best way to handle step X..."
2. PAIN_POINT (25%): "What's the hardest part of...", "What problems happen at [X] stage...", "Why is [X] so hard...", "Where do people get stuck with..."
3. OPTIMIZATION_TIPS (20%): "What's the fastest way to...", "Any shortcuts for...", "Pro tips for...", "How to do [X] more efficiently..."
4. TROUBLESHOOTING (15%): "What if [X] goes wrong...", "How do I fix [X] error...", "Why isn't [X] working...", "Common mistakes when..."
5. TIME_COST (10%): "How long does [X] take...", "Cost of doing [X] manually...", "Time saved with automation...", "Effort required for..."
"""

            elif style == "comparison":
                prompt += """
Include a MIX of these COMPARISON types (optimized for product/solution comparison):

1. COMPARATIVE (30%): "What's the difference between X and Y...", "Which is better for...", "X vs Y for my use case...", "How does X stack up against Y..."
2. SELECTION_CRITERIA (25%): "How do I choose between...", "Which one should I use...", "What matters most when picking...", "Decision factors for..."
3. FEATURE_SPECIFIC (20%): "Does X have feature Y...", "Can X integrate with...", "How easy is X to set up...", "Which has better [feature]..."
4. PRICING (15%): "Which is cheapest...", "What's included in [X] plan...", "Any hidden costs with...", "Best value for money..."
5. USE_CASE (10%): "Best for small teams...", "Which if I need [X] feature...", "Best for budget-conscious buyers...", "Right choice for [scenario]..."
"""

            elif style == "top-compare":
                prompt += """
Include a MIX of these RANKING types (optimized for "Top X Best" listicles):

1. RANKING (25%): "What's the best [X]...", "Top [X] tools for...", "Which [X] ranks highest...", "Highest rated [X]..."
2. ALTERNATIVE_SEARCH (25%): "What's better than [X]...", "Alternatives to [X]...", "Options similar to [X]...", "Competitors to [X]..."
3. SPECIFIC_USE_CASE (20%): "Best [X] for small teams...", "Best [X] for enterprise...", "Best [X] for beginners...", "Top [X] for [segment]..."
4. FEATURE_SELECTION (20%): "Which [X] has feature Y...", "[X] with best integration...", "Easiest [X] to use...", "Most powerful [X]..."
5. DECISION_SUPPORT (10%): "How do I pick from these...", "What features matter most...", "Should I switch from X to Y...", "How to decide between..."
"""

            elif style == "news":
                prompt += """
Include a MIX of these TRENDING types (optimized for news/developments coverage):

1. RECENCY (30%): "What's new with [X]...", "Latest [X] developments...", "Recent [X] changes...", "What happened with [X] recently..."
2. IMPACT (25%): "Why does this matter...", "How does [X] affect my business...", "Impact of [X] announcement...", "What does [X] mean for..."
3. TIMELINE (20%): "When did [X] happen...", "What's the history of [X]...", "What changed about [X]...", "Timeline of [X] evolution..."
4. EXPERT_VIEW (15%): "What do experts say about [X]...", "Industry reaction to [X]...", "Predictions for [X]...", "Professional opinions on..."
5. PRACTICAL_APPLICATION (10%): "How do I benefit from [X]...", "How to take advantage of [X]...", "Who should care about [X]...", "What should I do about..."
"""

            elif style == "category":
                prompt += """
Include a MIX of these CATEGORY types (optimized for category overviews):

1. CATEGORY_SCOPE (20%): "What's included in [X] category...", "What defines [X]...", "Difference between [X] and [Y] categories...", "Boundaries of [X]..."
2. SOLUTION_DISCOVERY (25%): "What are my options in [X] category...", "List of [X] solutions...", "Examples of [X]...", "Players in the [X] space..."
3. SELECTION (20%): "How do I pick a [X] solution...", "Which [X] is best for me...", "What should I look for in [X]...", "Criteria for choosing [X]..."
4. COMPARISON (20%): "How does [X] compare to [Y]...", "Difference between solutions...", "Should I upgrade from X to Y...", "Which solution wins for..."
5. MARKET_TRENDS (15%): "What's trending in [X]...", "Which [X] solutions are growing...", "Future of [X] category...", "Emerging players in [X]..."
"""

            elif style == "feature":
                prompt += """
Include a MIX of these CONVERSION types (optimized for product feature pages):

1. PROBLEM_VALIDATION (25%): "Is [X] a real problem...", "Am I the only one struggling with [X]...", "Why is [X] so frustrating...", "Anyone else dealing with..."
2. SOLUTION_FIT (25%): "Does this solve my problem...", "Will feature [X] help with [Y]...", "Is this solution right for me...", "Can this handle [use case]..."
3. OUTCOME_FOCUS (20%): "What results can I expect...", "How much time will I save...", "What's the ROI...", "Actual outcomes from using..."
4. IMPLEMENTATION (15%): "How quickly can I start...", "What's the learning curve...", "How much effort to set up...", "Time to see results..."
5. SOCIAL_PROOF (15%): "Who else uses this...", "Does this work for companies like mine...", "Success stories...", "Real examples of people using..."
"""

            elif style == "standard":
                prompt += """
Include a MIX of these COMPREHENSIVE types (optimized for overview content):

1. DEFINITIONAL (20%): "What is [X] and how does it work...", "Key components of [X]...", "What defines [X]...", "Fundamentals of [X]..."
2. EXPLORATORY (25%): "Different ways to approach [X]...", "Variations of [X]...", "What are my options with [X]...", "Landscape of [X]..."
3. IMPLEMENTATION (25%): "How do I get started with [X]...", "What's required to implement [X]...", "First steps with [X]...", "How to begin using..."
4. OPTIMIZATION (20%): "Best practices for [X]...", "How to improve my [X] approach...", "Getting better results from [X]...", "Advanced techniques for..."
5. TROUBLESHOOTING (10%): "Common [X] mistakes...", "How to fix [X] issues...", "What to avoid with [X]...", "Pitfalls to watch for..."
"""

            else:
                # Fallback to generic question types for unknown styles
                prompt += """
Include a MIX of these types:

1. EXPLORATORY: "What are people's experiences with..."
2. COMPARATIVE: "Has anyone compared X vs Y..."
3. VALIDATION: "Is it actually worth..."
4. TROUBLESHOOTING: "Why isn't my [X] working..."
5. IMPLEMENTATION: "How do I set up..."
6. OPTIMIZATION: "What's the best way to improve..."
7. SOCIAL PROOF: "Anyone here successfully using..."
"""

            prompt += """

═══════════════════════════════════════════════════════════════════════════════
OUTPUT REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

✓ Questions MUST be about the CORE ENTITIES in "{keyword}"
✓ Include questions at DIFFERENT specificity levels
✓ Match the INTENT SIGNALS detected in the keyword

LENGTH VARIETY (critical):
- ~40% SHORT punchy questions (5-12 words) — quick, direct, scannable
- ~40% MEDIUM questions (12-20 words) — adds context while staying focused
- ~20% LONGER detailed questions (20-30 words) — nuanced, multi-part scenarios

PHRASING (critical — type like a real person):
- Always use contractions naturally
- Casual tone as if texting a colleague who knows the space
- Open-ended endings that invite discussion
- ZERO corporate/formal/stiff language

✗ NEVER mention: HubSpot, Salesforce, Zoho, Pipedrive, or other CRM names

Return ONLY a JSON array of questions:
["question 1", "question 2", ...]
"""

            # Add platform-specific optimization
            if platform == "reddit":
                prompt += """

═══════════════════════════════════════════════════════════════════════════════
🔴 REDDIT SEARCH OPTIMIZATION
═══════════════════════════════════════════════════════════════════════════════

Reddit's search is WEAK — optimize for how it actually works:

- SHORTER queries find more threads (5-10 words ideal)
- Keyword phrases > full questions (Reddit indexes titles + body text)
- Topic fragments catch discussion threads: "MCP recommendations 2026"
- Problem descriptions match rant posts: "attribution not working"
- Subreddit-style casual: "anyone else struggling with..."

DISTRIBUTION for Reddit:
- 60% SHORT keyword-focused phrases (5-10 words)
- 30% MEDIUM casual questions (10-15 words)
- 10% LONGER specific scenarios (15-20 words)

Example Reddit-optimized queries:
- "best MCP for Meta ads" (keyword phrase)
- "Google attribution broken again" (problem phrase)
- "MCP recommendations small agency" (use case phrase)
"""
            elif platform == "quora":
                prompt += """

═══════════════════════════════════════════════════════════════════════════════
🟠 QUORA SEARCH OPTIMIZATION
═══════════════════════════════════════════════════════════════════════════════

Quora's search is QUESTION-MATCHING — optimize for how it actually works:

- FULL QUESTIONS match Quora's Q&A structure perfectly
- Specific, detailed questions find expert answers
- "What is the best..." format is Quora's bread and butter
- Professional tone matches Quora's expert audience
- Longer queries work BETTER on Quora (unlike Reddit)

DISTRIBUTION for Quora:
- 20% SHORT direct questions (8-12 words)
- 50% MEDIUM specific questions (12-20 words)
- 30% LONGER detailed scenarios (20-30 words)

Example Quora-optimized queries:
- "What is the best MCP for Google and Meta Ads in 2026?"
- "How do marketing agencies handle cross-platform attribution?"
- "Which Model Context Protocol provides the most reliable data sync between advertising platforms?"
"""

            try:
                # Use Gemini 3 Flash for hyper-intelligent topic understanding
                if self.gemini_client:
                    response = await self.gemini_client.aio.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=0.3,
                            max_output_tokens=6000,
                        )
                    )
                    content = response.text
                else:
                    # Fallback to Nebius if Gemini unavailable
                    response = await self.nebius.chat.completions.create(
                        model=self.model_creative,
                        messages=[{
                            "role": "system",

                        }, {
                            "role": "user",
                            "content": prompt
                        }],
                        temperature=0.6,
                        max_tokens=6000
                    )
                    content = response.choices[0].message.content
                # Extract JSON array from response (greedy match to capture full array)
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    questions = json.loads(match.group(0))
                    # Validate questions meet length requirements (no keyword forcing)
                    valid_questions = []
                    for q in questions:
                        if isinstance(q, str) and len(q) > 8 and len(q) < 300:
                            valid_questions.append(q)

                    # Filter out questions containing platform names
                    filtered_questions = self._filter_platform_questions(valid_questions)
                    all_questions.extend(filtered_questions)
                    
            except Exception as e:
                print(f"Question generation error in batch: {e}")
                # Add some fallback questions with long-tail focus
                fallback_questions = [
                    f"What are the top {keyword} solutions for 2025?",
                    f"How to troubleshoot {keyword} connection issues?",
                    f"What's the difference between {keyword} platforms?",
                    f"Is {keyword} suitable for my small business?",
                    f"How to optimize {keyword} performance and ROI?"
                ]
                # Filter platform names from fallback questions
                filtered_fallback = self._filter_platform_questions(fallback_questions)
                all_questions.extend(filtered_fallback)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_questions = []
        for q in all_questions:
            if q not in seen:
                seen.add(q)
                unique_questions.append(q)
        
        return unique_questions[:count]
    
    async def research_with_compound(self, questions: List[str], platform: str = "reddit") -> Dict[str, Any]:
        """Search Reddit/Quora using Perplexity (primary) with Gemini grounded fallback.

        Uses Perplexity sonar-pro with domain filtering for precise community
        search. Falls back to Gemini Google Search grounding if Perplexity fails.
        """
        # Get ICP context for targeted research
        icp_context = _ICP_RESEARCH_CONTEXT
        logger.info(f"🎯 {platform.title()} research: ICP context injected ({len(icp_context)} chars)")

        # Try Perplexity first (native domain filtering)
        if self.perplexity_key and self.session:
            result = await self._research_with_perplexity(questions, platform, icp_context)
            if result and result.get("insights"):
                return result
            logger.warning(f"⚠️  Perplexity {platform} search returned no insights, trying Gemini fallback...")

        # Fallback to Gemini grounded search
        if self.gemini_client:
            result = await self._research_with_gemini_grounding(questions, platform, icp_context)
            if result:
                return result

        logger.error(f"No search provider available for {platform} community research")
        return {"insights": [], "questions": questions, "citations": []}

    async def _research_with_perplexity(self, questions: List[str], platform: str, icp_context: str) -> Optional[Dict[str, Any]]:
        """Search community platforms using Perplexity sonar-pro with domain filtering."""
        domain = f"{platform}.com"
        search_prompt = f"""Find real user discussions on {domain} about:

{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}
{icp_context}
Extract from actual {platform} threads:
- Specific pain points and frustrations users describe
- Solutions and recommendations that got upvoted/endorsed
- Common mistakes and warnings from experienced users
- Real-world results and case studies shared

Return bullet points with one actionable insight per line. Be specific — quote real user language. Skip generic advice."""

        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "sonar-reasoning-pro",
            "messages": [{"role": "user", "content": search_prompt}],
            "search_domain_filter": [domain],
            "return_citations": True,
            "search_recency_filter": "year",
            "temperature": 0.2
        }

        try:
            logger.debug(f"Sending to Perplexity for {platform} research (domain: {domain})")

            async with self.session.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    logger.warning(f"⚠️  Perplexity {platform} search failed: HTTP {response.status}")
                    return None

                data = await response.json()

            content = ""
            if data.get("choices"):
                content = data["choices"][0].get("message", {}).get("content", "")

            if not content:
                return None

            logger.debug(f"Got Perplexity response, content length: {len(content)}")

            # Extract insights from response
            insights = self._extract_compound_insights(content)

            # Extract citations from Perplexity response
            citations = []
            pplx_citations = data.get("citations", [])
            for url in pplx_citations:
                if isinstance(url, str) and f'{platform}.com' in url:
                    citations.append({
                        "url": url,
                        "platform": platform.title(),
                        "type": "perplexity_search"
                    })

            # Also extract URLs from content text
            text_citations = self._extract_compound_citations(content, [])
            seen_urls = {c['url'] for c in citations}
            for c in text_citations:
                if c['url'] not in seen_urls:
                    seen_urls.add(c['url'])
                    citations.append(c)

            logger.info(f"✅ Perplexity {platform} search: {len(insights)} insights, {len(citations)} citations")

            return {
                "insights": insights[:15],
                "questions": questions,
                "citations": citations[:10],
                "raw_content": content,
            }

        except Exception as e:
            logger.error(f"Perplexity {platform} research failed: {e}")
            return None

    async def _research_with_gemini_grounding(self, questions: List[str], platform: str, icp_context: str) -> Optional[Dict[str, Any]]:
        """Fallback: search community platforms using Gemini with Google Search grounding."""
        search_prompt = f"""Search {platform}.com for real user discussions about:

{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}
{icp_context}
IMPORTANT: Only use results from {platform}.com. Ignore results from other sites.

For each discussion you find, extract:
- The specific pain point or question the user raised
- Any solutions or recommendations from replies
- Common mistakes or warnings mentioned
- Expert advice or real-world experience shared

Format your response as:
- Bullet points with one actionable insight per line
- Include the {platform} URL for each discussion found
- Be specific — quote real user language where possible
- Skip generic advice, only include insights with real substance"""

        try:
            logger.debug(f"Sending to Gemini grounded search for {platform} research")

            grounding_tool = genai_types.Tool(
                google_search=genai_types.GoogleSearch()
            )

            response = await self.gemini_client.aio.models.generate_content(
                model="gemini-3-flash-preview",
                contents=search_prompt,
                config=genai_types.GenerateContentConfig(
                    tools=[grounding_tool],
                    temperature=0.2,
                    max_output_tokens=4000,
                )
            )

            content = response.text if response.text else ""
            if not content:
                return None

            logger.debug(f"Got Gemini grounded response, content length: {len(content)}")

            # Extract grounding metadata (URLs from Google Search)
            grounding_citations = []
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                grounding_meta = getattr(candidate, 'grounding_metadata', None)
                if grounding_meta:
                    chunks = getattr(grounding_meta, 'grounding_chunks', None) or []
                    for chunk in chunks:
                        web = getattr(chunk, 'web', None)
                        if web and hasattr(web, 'uri'):
                            url = web.uri
                            if f'{platform}.com' in url:
                                grounding_citations.append({
                                    "url": url,
                                    "platform": platform.title(),
                                    "title": getattr(web, 'title', ''),
                                    "type": "grounded_search"
                                })

            # Extract insights and text citations
            insights = self._extract_compound_insights(content)
            text_citations = self._extract_compound_citations(content, [])

            # Merge citations
            all_citations = grounding_citations + text_citations
            seen_urls = set()
            unique_citations = []
            for c in all_citations:
                if c['url'] not in seen_urls:
                    seen_urls.add(c['url'])
                    unique_citations.append(c)

            logger.info(f"✅ Gemini grounded {platform} search: {len(insights)} insights, {len(unique_citations)} citations")

            return {
                "insights": insights[:15],
                "questions": questions,
                "citations": unique_citations[:10],
                "raw_content": content,
            }

        except Exception as e:
            logger.error(f"Gemini grounded {platform} research failed: {e}")
            return None
    
    def _extract_compound_insights(self, content: str) -> List[str]:
        """Extract insights from community research response"""
        insights = []
        
        # Look for bullet points, numbered lists, or key phrases
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Look for bullet points or numbered items
            if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+\.\s+', line):
                cleaned = re.sub(r'^[-•*\d.]\s+', '', line)
                if len(cleaned) > 20:
                    insights.append(cleaned)
            # Look for sentences with insight indicators
            elif any(indicator in line.lower() for indicator in ['users report', 'people say', 'common issue', 'many find', 'often mentioned']):
                insights.append(line)
        
        return insights
    
    def _extract_compound_citations(self, content: str, executed_tools: List[Any]) -> List[Dict[str, str]]:
        """Extract citations from community research response"""
        citations = []
        
        # Extract URLs from content
        url_pattern = r'https?://(?:www\.)?(?:reddit\.com|quora\.com)[^\s\)]*'
        urls = re.findall(url_pattern, content)
        
        for url in urls:
            # Clean up URL
            url = url.rstrip('.,;:')
            # Determine platform
            platform = "Reddit" if "reddit.com" in url else "Quora"
            citations.append({
                "url": url,
                "platform": platform,
                "type": "discussion"
            })
        
        # Also check executed tools for search results
        if executed_tools:
            for tool in executed_tools:
                if isinstance(tool, dict) and tool.get('name') == 'web_search':
                    results = tool.get('results', [])
                    for result in results:
                        if isinstance(result, dict) and result.get('url'):
                            url = result['url']
                            if 'reddit.com' in url or 'quora.com' in url:
                                platform = "Reddit" if "reddit.com" in url else "Quora"
                                citations.append({
                                    "url": url,
                                    "platform": platform,
                                    "title": result.get('title', ''),
                                    "type": "search_result"
                                })
        
        # Deduplicate citations
        seen_urls = set()
        unique_citations = []
        for citation in citations:
            if citation['url'] not in seen_urls:
                seen_urls.add(citation['url'])
                unique_citations.append(citation)
        
        return unique_citations[:10]  # Limit to 10 citations