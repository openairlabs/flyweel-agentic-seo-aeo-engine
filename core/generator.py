"""Lean Content Generator - Fast, focused, with ALL content styles"""
import asyncio
import re
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
import logging
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from .ai_router import SmartAIRouter
from .research import WebResearcher, CommunityResearcher, classify_keyword_intent
from .site_extractor import SiteContextExtractor
from .formatter import AstroFormatter
from .insight_formatter import SERPInsightFormatter
from .gsc_analyzer import GSCAnalyzer, ContentRecommendation
from .context_builder import IntelligentContextBuilder
from .intelligent_benchmark_extractor import IntelligentBenchmarkExtractor
from .cli.live_display import LiveStatusDisplay

def configure_logging(verbose: bool = False):
    """Configure logging to suppress noise and show only user-relevant messages

    Args:
        verbose: If True, show all debug logs (for troubleshooting)
    """
    from rich.logging import RichHandler

    # Set up Rich handler for clean output (no timestamps, no module names)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(message)s",  # Clean format - message only
        handlers=[RichHandler(
            rich_tracebacks=True,
            show_path=False,
            show_time=False,
            show_level=False,
            markup=True
        )]
    )

    # Suppress noisy third-party loggers
    logging.getLogger('google_genai.models').setLevel(logging.ERROR)
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    # Suppress internal technical logs (only show in verbose mode)
    if not verbose:
        logging.getLogger('core.repo_extractor').setLevel(logging.WARNING)
        logging.getLogger('core.site_extractor').setLevel(logging.WARNING)
        logging.getLogger('core.context_builder').setLevel(logging.WARNING)

# Initialize logger (will be configured by CLI)
logger = logging.getLogger(__name__)

class ContentGenerator:
    """Main content generator - all styles, all features, no BS"""

    def __init__(self, site_context: Optional[Dict[str, Any]] = None):
        """Initialize generator with optional pre-loaded site context

        Args:
            site_context: Optional pre-extracted context (from RepoContextExtractor).
                         If provided, skips live site scraping.
        """
        self.site_extractor = SiteContextExtractor()
        self._injected_context = site_context  # For CLI mode with repo context
        self.site_context = None  # Will be populated on first use
        self._skip_icp = False  # Will be set by generate() - controls ICP context injection
        self._context_builder = None  # Will be instantiated after research completes
        self.brand_voice = self._load_brand_voice()
        self.icp_config = self._load_icp_config()
        self.customer_language = self._load_customer_language()
        self.product_registry = self._load_product_registry()
        self.insight_formatter = SERPInsightFormatter()

        # Content style templates
        self.style_prompts = {
            'standard': self._get_standard_prompt,
            'comparison': self._get_comparison_prompt,
            'guide': self._get_guide_prompt,
            'research': self._get_research_prompt,
            'news': self._get_news_prompt,
            'category': self._get_category_prompt,
            'top-compare': self._get_top_compare_prompt,
            'feature': self._get_feature_prompt  # Phase 6.1: Conversion-focused feature pages
        }

    def _load_brand_voice(self) -> Dict[str, Any]:
        """Load unified brand voice configuration"""
        config_path = Path(__file__).parent.parent / 'config' / 'brand_voice_config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {
            "tone": "conversational, relatable, jargon-free",
            "banned_words": ["leverage", "utilize", "optimize"],
            "good_words": ["use", "make", "improve"],
            "style_rules": ["Write like explaining to a friend"]
        }

    def _load_icp_config(self) -> Dict[str, Any]:
        """Load ICP (Ideal Customer Profile) configuration"""
        config_path = Path(__file__).parent.parent / 'config' / 'icp_config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}

    def _load_customer_language(self) -> Dict[str, Any]:
        """Load customer language patterns"""
        config_path = Path(__file__).parent.parent / 'config' / 'customer-language.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}

    def _load_product_registry(self) -> Dict[str, Any]:
        """Load Brand product registry with keyword mappings and disambiguation

        This registry enables the generator to:
        1. Detect when a keyword relates to a Brand product
        2. Provide correct terminology disambiguation (e.g., MCP = Model Context Protocol)
        3. Inject accurate product context into prompts
        """
        config_path = Path(__file__).parent.parent / 'config' / 'products.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                registry = json.load(f)
                logger.info(f"📦 Loaded product registry: {len(registry.get('products', {}))} products, "
                           f"{len(registry.get('keyword_mapping', {}))} keyword mappings")
                return registry
        logger.warning("⚠️  No product registry found at config/products.json")
        return {}

    def _detect_relevant_product(self, keyword: str) -> Optional[Dict[str, Any]]:
        """Detect if keyword relates to a Brand product

        Args:
            keyword: Target keyword for content generation

        Returns:
            Product definition dict if keyword matches, None otherwise
        """
        if not self.product_registry:
            return None

        keyword_lower = keyword.lower()

        # Check keyword mapping for matches
        for trigger, product_id in self.product_registry.get('keyword_mapping', {}).items():
            if trigger.lower() in keyword_lower:
                product = self.product_registry.get('products', {}).get(product_id)
                if product:
                    logger.info(f"🎯 Detected relevant product: {product.get('name')} (trigger: '{trigger}')")
                    return product

        return None

    def _get_disambiguation_context(self, keyword: str) -> str:
        """Get disambiguation hints for ambiguous terms in keyword

        For terms like "MCP" that could mean multiple things, provides
        explicit definition in the AI/LLM context to avoid misinterpretation.

        Args:
            keyword: Target keyword

        Returns:
            Disambiguation context string for prompt injection
        """
        if not self.product_registry:
            return ""

        hints = []
        disambiguation = self.product_registry.get('disambiguation', {})

        for term, info in disambiguation.items():
            if term.lower() in keyword.lower():
                hints.append(f"""
## CRITICAL TERMINOLOGY DISAMBIGUATION

**"{term}" in this context means:** {info.get('means', '')}

**NOT:** {info.get('not', '')}

**Context indicators:** {', '.join(info.get('in_context', []))}

**Examples of {term} solutions:**
{chr(10).join(f'- {ex}' for ex in info.get('examples', [])[:4])}

You MUST interpret "{term}" according to this definition throughout the entire article.
""")
                logger.info(f"📖 Disambiguation added for term: {term}")

        return '\n'.join(hints)

    def _get_product_context(self, keyword: str, brand_mode: str = 'full') -> str:
        """Get Brand product context for injection into prompts

        When a keyword relates to a Brand product, injects detailed
        product information to position it as #1 in comparisons.

        Args:
            keyword: Target keyword
            brand_mode: Brand mention level - 'none', 'limited', 'full'

        Returns:
            Product context string for prompt injection
        """
        if brand_mode == 'none':
            return ""

        product = self._detect_relevant_product(keyword)
        if not product:
            return ""

        # Minimal product context - AI figures out the rest from keyword + SERP
        features_list = '\n'.join(f'- {f}' for f in product.get('features', []))
        use_cases_list = '\n'.join(f'- {uc}' for uc in product.get('use_cases', []))

        return f"""
## RELEVANT BRAND PRODUCT

**Product:** {product.get('name', '')}
**URL:** {product.get('url', '')}
**Tagline:** {product.get('tagline', '')}

{product.get('description', '')}

{f"{product.get('what_is_mcp', '')}" if product.get('what_is_mcp') else ""}

**Features:**
{features_list}

**Use Cases:**
{use_cases_list}

{f"**Works With:** {', '.join(product.get('supported_tools', []))}" if product.get('supported_tools') else ""}
{f"**Platforms:** {', '.join(product.get('supported_platforms', []))}" if product.get('supported_platforms') else ""}

**Why It Matters:** {product.get('positioning', '')}
"""

    def _format_icp_context(self, light_mode: bool = False, skip_icp: bool = False) -> str:
        """Format ICP context for injection into content prompts.

        Delegates to IntelligentContextBuilder if available (research-derived context),
        otherwise falls back to minimal defaults.

        Args:
            light_mode: If True, return minimal ICP context for comparison/top-compare styles
                       to avoid over-injection of ICP-specific language
            skip_icp: If True, return generic audience context (no industry specifics)
        """
        # Use intelligent context builder if available (instantiated after research)
        if self._context_builder is not None:
            return self._context_builder.build_icp_context(
                light_mode=light_mode,
                skip_icp=skip_icp
            )

        # Fallback for cases where context builder not yet instantiated
        if skip_icp:
            logger.info("🎯 ICP context: SKIPPED (generic audience)")
            return """
TARGET AUDIENCE:
- Business professionals and decision-makers
- Marketing and operations teams
- Focus: Practical, actionable insights
- Tone: Expert advisor, professional but accessible
"""

        if light_mode:
            logger.info("🎯 ICP context: light mode (comparison style)")
            return """
TARGET AUDIENCE:
- Target audience evaluating solutions
- Decision-makers comparing options for their marketing/sales stack
- Focus: Objective comparison with practical insights
- Tone: Expert advisor helping with informed decisions
"""

        # Minimal fallback - no hardcoded phrases
        logger.info("🎯 ICP context: minimal fallback (no context builder)")
        return """
TARGET AUDIENCE:
- Business professionals and decision-makers
- Focus: Practical, actionable insights
- Tone: Expert advisor, conversational

CONTENT APPROACH:
- Write for operators who wear multiple hats
- Avoid enterprise jargon
- Focus on the problem being solved
"""

    def _detect_research_intent(self, keyword: str, serp: Dict[str, Any]) -> str:
        """Detect research intent from keyword and SERP context.

        Returns one of: 'benchmarking', 'roi_analysis', 'market_research', 'comparison', 'performance_analysis'
        """
        keyword_lower = keyword.lower()

        # Check keyword patterns
        if any(term in keyword_lower for term in ['benchmark', 'industry standard', 'performance metric', 'average']):
            return 'benchmarking'

        if any(term in keyword_lower for term in ['roi', 'return on investment', 'cost benefit', 'payback', 'contribution margin']):
            return 'roi_analysis'

        if any(term in keyword_lower for term in ['market size', 'industry analysis', 'adoption rate', 'market share']):
            return 'market_research'

        if any(term in keyword_lower for term in ['vs', 'versus', 'comparison', 'compare', 'alternative', 'best']):
            return 'comparison'

        if any(term in keyword_lower for term in ['performance', 'results', 'metrics', 'kpi', 'outcomes']):
            return 'performance_analysis'

        # Default to benchmarking for research content
        return 'benchmarking'

    def _format_customer_language(self) -> str:
        """Format customer language patterns for authentic voice.

        Delegates to IntelligentContextBuilder if available (research-derived language),
        otherwise falls back to term seeds only (no hardcoded pain phrases).
        """
        # Use intelligent context builder if available (research-extracted language)
        if self._context_builder is not None:
            return self._context_builder.build_customer_language_context()

        # Fallback: Use term seeds only, no hardcoded pain phrases
        if not self.customer_language:
            logger.warning("⚠️  No customer language loaded - using default voice")
            return """
LANGUAGE GUIDANCE:
- Use conversational, jargon-free language
- Focus on practical business outcomes
"""

        terms = self.customer_language.get('customer_language', [])
        logger.info(f"💬 Customer language: {len(terms)} terms (fallback mode)")

        return f"""
LANGUAGE OUR AUDIENCE ACTUALLY USES:
Terms they say: {', '.join(terms[:10])}

LANGUAGE GUIDANCE:
- Echo customer terminology naturally
- Use conversational, jargon-free language
- Focus on practical business outcomes
"""

    def _format_brand_voice_prompt(self, brand_mode: str = 'full') -> str:
        """Format brand voice config into prompt text

        Args:
            brand_mode: Brand mention level - 'none', 'limited', 'full'
        """
        if brand_mode == 'none':
            # Educational mode - no brand mentions, only use ICP context for relevance
            return """
CONTENT APPROACH (NO BRAND MODE):
- Write 100% educational, problem-solving content
- Focus entirely on user's challenges and solutions
- DO NOT mention Brand, DO NOT include brand links, DO NOT sell
- Use brand context ONLY for understanding target audience pain points
- Conversational, helpful tone like explaining to a friend
- Avoid all banned jargon: leverage, utilize, optimize, implement, comprehensive
- Use everyday language: use, make, improve, set up, approach

TARGET AUDIENCE CONTEXT (for content alignment only):
- Lead generation companies and service businesses
- Pain points: manual data reconciliation, wasted ad spend, attribution gaps
- Subject matter expertise: CRM integration, ad attribution, spend optimization
"""
        elif brand_mode == 'limited':
            # Limited mode - 2-3 highly natural mentions only, maximum restraint
            return f"""
BRAND VOICE & TONE:
{', '.join(self.brand_voice['style_rules'])}

BANNED WORDS (avoid): {', '.join(self.brand_voice['banned_words'][:10])}
PREFERRED WORDS (use): {', '.join(self.brand_voice['good_words'])}

KEYWORD USAGE: {self.brand_voice.get('keyword_usage', {}).get('density', '1-1.5%')} density maximum
BRAND MENTIONS (LIMITED MODE): Maximum 2-3 times per article - ONLY where genuinely perfect fit exists
DISTRIBUTION: 95% problem-focused, 5% solution-focused (even more restraint than standard)
APPROACH: Quality over quantity - each mention must feel completely natural and helpful, never forced. If uncertain, skip the mention.
"""
        else:
            # Full mode - natural brand mentions (up to 10, 90/10 problem-solution)
            return f"""
BRAND VOICE & TONE:
{', '.join(self.brand_voice['style_rules'])}

BANNED WORDS (avoid): {', '.join(self.brand_voice['banned_words'][:10])}
PREFERRED WORDS (use): {', '.join(self.brand_voice['good_words'])}

KEYWORD USAGE: {self.brand_voice.get('keyword_usage', {}).get('density', '1-1.5%')} density maximum
BRAND MENTIONS: Up to {self.brand_voice.get('brand_mentions', {}).get('max_per_article', '10')} times per article (ONLY where naturally fits problem-solution flow)
DISTRIBUTION: {self.brand_voice.get('brand_mentions', {}).get('distribution', '90% problem-focused, 10% solution-focused')}
APPROACH: {self.brand_voice.get('brand_mentions', {}).get('approach', 'conversational, never salesy, maximum restraint')}
"""
    
    async def generate(self, keyword: str, style: str = "standard", augment_serp: bool = False, skip_community: bool = False, limit_community: bool = False, use_llama_polish: bool = False, brand_mode: str = 'full', skip_icp: bool = False, solution_count: int = 8, gsc_check: bool = False, gsc_keywords: bool = False, approved_solutions: Optional[List[str]] = None, progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        """Generate complete SEO-optimized content in any style

        Args:
            keyword: Target keyword
            style: Content style (standard/guide/comparison/research/news/category/top-compare)
            augment_serp: Whether to augment with SERP data
            skip_community: Skip Reddit/Quora research entirely (--nr flag)
            limit_community: Limit to 3 Reddit + 1 Quora highest relevance (--nrl flag)
            use_llama_polish: Use Llama 3.1 405B for polish instead of Qwen3 235B (legacy option)
            brand_mode: Brand mention level - 'none' (--nb), 'limited' (--lb), 'full' (default)
            skip_icp: Skip ICP context injection (no industry-specific audience targeting) (--no-icp flag)
            solution_count: Number of solutions for top-compare style (5/8/10/15)
            gsc_check: Run pre-generation cannibalization check using GSC data (--gsc-check flag)
            gsc_keywords: Use GSC-derived keywords for title/H2 optimization (--gsc-keywords flag)
            approved_solutions: User-approved solutions for comparison content (from interactive selection)
            progress_callback: Optional callback(message: str, advance: int = 0) for progress updates
        """
        logger.debug(f"Starting {style} generation for: {keyword}")
        logger.debug(f"Keyword: '{keyword}' | Style: '{style}' | Augment SERP: {augment_serp}")

        # Store progress callback (use no-op if none provided)
        def _no_op_progress(message: str, advance: int = 0) -> None:
            """No-op progress callback when none provided"""
            pass

        self._progress = progress_callback or _no_op_progress

        # Store skip_icp as instance variable for prompt builders
        self._skip_icp = skip_icp

        if skip_community:
            logger.debug("Community research: DISABLED (--nr)")
        elif limit_community:
            logger.debug("Community research: LIMITED MODE (3 Reddit + 1 Quora) (--nrl)")

        # Log Brand mention mode
        mode_labels = {
            'none': 'NO BRAND (Educational content only, no brand selling)',
            'limited': 'LIMITED BRAND (2-3 highly natural mentions only)',
            'full': 'FULL INTEGRATION (Natural mentions where it fits, max 10)'
        }
        logger.debug(f"Mode: {mode_labels.get(brand_mode, 'FULL INTEGRATION')}")

        if skip_icp:
            logger.debug("ICP: SKIPPED (generic audience targeting)")
        else:
            logger.debug("ICP: ENABLED (industry-specific audience)")

        polish_model = "Llama 3.1 405B" if use_llama_polish else "Qwen3 235B"
        logger.debug(f"Polish model: {polish_model}")

        start_time = datetime.now()
        
        # Validate style
        if style not in self.style_prompts:
            logger.warning(f"⚠️  Unknown style '{style}', using 'standard'")
            style = 'standard'

        # GSC-driven keyword recommendations (stored for later use)
        gsc_recommendations = None

        # Pre-generation cannibalization check (Phase 4.1)
        if gsc_check or gsc_keywords:
            logger.debug("Running GSC analysis...")
            try:
                async with GSCAnalyzer() as gsc:
                    if gsc.is_available:
                        # Get comprehensive recommendations
                        gsc_recommendations = await gsc.get_content_recommendations(keyword)

                        # Cannibalization check
                        if gsc_check:
                            cannibalization = gsc_recommendations.get('cannibalization', {})
                            recommendation = cannibalization.get('recommendation', 'create_new')

                            if recommendation == 'abort':
                                logger.warning(f"🚫 CANNIBALIZATION DETECTED!")
                                logger.warning(f"   {cannibalization.get('reason', 'Existing content ranks well')}")
                                logger.warning(f"   Existing URL: {cannibalization.get('existing_url', 'N/A')}")
                                logger.warning(f"   Position: {cannibalization.get('existing_position', 'N/A')}")
                                return {
                                    'success': False,
                                    'error': f"Cannibalization check failed: {cannibalization.get('reason')}",
                                    'recommendation': 'optimize_existing',
                                    'existing_url': cannibalization.get('existing_url'),
                                    'existing_position': cannibalization.get('existing_position')
                                }
                            elif recommendation == 'optimize_existing':
                                logger.warning(f"⚠️  Page 1 ranking detected - consider optimizing existing content")
                                logger.warning(f"   {cannibalization.get('reason', '')}")
                                # Continue but warn user
                            elif recommendation == 'consolidate':
                                logger.warning(f"⚠️  Multiple pages compete for this keyword")
                                logger.warning(f"   {cannibalization.get('reason', '')}")
                                # Continue but warn user
                            else:
                                logger.debug("Cannibalization check passed - safe to create new content")

                        # Log GSC keyword insights
                        if gsc_keywords:
                            primary = gsc_recommendations.get('primary_keyword', {})
                            if primary.get('query'):
                                logger.debug(f"GSC Primary Keyword: '{primary['query']}'")
                                logger.debug(f"Traffic Potential: {primary.get('traffic_potential', 0):.0f}")
                                logger.debug(f"Position: {primary.get('position', 'N/A')}")

                            secondaries = gsc_recommendations.get('secondary_keywords', [])
                            if secondaries:
                                logger.debug(f"GSC Secondary Keywords: {len(secondaries)} found for H2 distribution")

                    else:
                        logger.warning("⚠️  GSC not available - skipping GSC analysis")
            except Exception as e:
                logger.warning(f"⚠️  GSC analysis failed: {e}")

        # Get Brand context (from injected repo context or live site)
        if self._injected_context:
            logger.debug("Using injected repo context")
            site_context = self._injected_context
            self.site_context = site_context
        else:
            logger.debug("Extracting Brand site context")
            async with self.site_extractor as extractor:
                site_context = await extractor.get_context(force_refresh=True)
                self.site_context = site_context  # Store for later use

        logger.debug(f"Site context loaded: {len(site_context.get('features', []))} features, "
                   f"{len(site_context.get('internal_links', {}))} internal links")
        
        # Run all research in parallel
        async with SmartAIRouter() as ai, WebResearcher() as web, CommunityResearcher() as community:
            # Pre-flight validation: Check AI router has required clients
            if not ai.gemini_client:
                logger.error("❌ Gemini client not initialized - check GOOGLE_API_KEY")
                return {
                    'success': False,
                    'error': "Generation failed: Gemini API not available (check GOOGLE_API_KEY)"
                }

            if not ai.nebius:
                logger.warning("⚠️  Nebius client not initialized (NEBIUS_API_KEY missing) — extraction, editing, filtering, and polish will be skipped")

            # Log research phase with Reddit query targets
            reddit_query_info = " (25-30 Reddit queries for research style)" if style == "research" and not skip_community and not limit_community else ""
            logger.debug(f"Phase 1: Research - SERP analysis, Reddit mining, Quora insights{reddit_query_info}")
            self._progress("Analyzing search landscape...", 0)

            # Create live status display for research (if in TTY mode)
            use_live_display = sys.stdout.isatty()
            if use_live_display:
                research_display = LiveStatusDisplay()
                research_display.set_phase("Research")
                research_display.add_task("SERP Analysis")
                if not skip_community:
                    research_display.add_task("Reddit Mining")
                    research_display.add_task("Quora Extraction")
                    research_display.add_task("Quality Filter")

                live = research_display.start_live(refresh_per_second=2)
                live.start()

            # Build research tasks based on flags
            research_tasks = [web.analyze_serp(keyword, augment_serp, style=style)]

            if not skip_community:
                # Research style gets 30 Reddit queries for comprehensive ICP segment coverage
                reddit_limit = 30 if style == "research" and not limit_community else (3 if limit_community else None)
                quora_limit = 1 if limit_community else None

                research_tasks.extend([
                    community.mine_reddit(keyword, limit=reddit_limit, style=style),
                    community.mine_quora(keyword, limit=quora_limit, style=style)
                ])

            # Add topical insights for all styles EXCEPT research (research uses sonar-deep-research)
            include_topical = style != "research"
            if style == "research":
                logger.debug("Research style: Using Perplexity sonar-deep-research")
            if include_topical:
                # Map content style to topic scope
                scope_mapping = {
                    'standard': 'broad',
                    'guide': 'broad',
                    'comparison': 'narrow',
                    'top-compare': 'narrow',
                    'news': 'industry',
                    'category': 'broad',
                    'feature': 'narrow'
                }
                topic_scope = scope_mapping.get(style, 'broad')
                research_tasks.append(web._discover_topical_insights(keyword, topic_scope=topic_scope))
                logger.debug(f"Adding topical insights discovery (scope: {topic_scope})")

            # Mark SERP as running
            if use_live_display:
                serp_model = "sonar-deep-research" if style == "research" else "sonar-reasoning-pro"
                research_display.start_task("SERP Analysis", f"Perplexity {serp_model}")
                research_display.refresh()

            # Execute research
            research_start = datetime.now()
            results = await asyncio.gather(*research_tasks)
            research_elapsed = (datetime.now() - research_start).total_seconds()

            # Extract results based on what was included
            result_idx = 0
            serp = results[result_idx]
            result_idx += 1

            if skip_community:
                reddit = {'insights': [], 'pain_points': []}
                quora = {'expert_insights': [], 'discussions': []}
            else:
                reddit = results[result_idx]
                result_idx += 1
                quora = results[result_idx]
                result_idx += 1

            # Extract topical insights if included
            if include_topical:
                topical_insights = results[result_idx]
            else:
                topical_insights = {'insights': [], 'sources': [], 'enabled': False}

            # Handle any errors in research
            serp = self._validate_research_result(serp, 'serp')
            reddit = self._validate_research_result(reddit, 'reddit')
            quora = self._validate_research_result(quora, 'quora')
            topical_insights = self._validate_research_result(topical_insights, 'topical')

            # Validate minimum research data collected
            paa_count = len(serp.get('paa_questions', []))
            reddit_count = len(reddit.get('insights', []))
            quora_count = len(quora.get('expert_insights', []))

            # Update live display: SERP complete
            if use_live_display:
                serp_sources = len(serp.get('serp_analysis', {}).get('citations', [])) if augment_serp else 0
                serp_detail = f"{paa_count} questions"
                if serp_sources > 0:
                    serp_detail += f", {serp_sources} sources"
                research_display.complete_task("SERP Analysis", serp_detail, f"{research_elapsed:.1f}s")

                # Mark community tasks as running
                if not skip_community:
                    research_display.start_task("Reddit Mining", "Perplexity + Gemini")
                    research_display.start_task("Quora Extraction", "Perplexity + Gemini")
                research_display.refresh()

            if paa_count == 0 and reddit_count == 0 and quora_count == 0:
                logger.warning("⚠️  No research data collected - generation quality may be lower")

            reddit_before = len(reddit.get('insights', []))
            quora_before = len(quora.get('expert_insights', []))

            # Filter research insights - use appropriate model based on source
            if reddit.get('insights'):
                reddit['insights'] = await ai.filter_research_insights(
                    reddit['insights'],
                    keyword,
                    context="Reddit discussions",
                    source_type="reddit"  # Use Llama 3.3 70B for robust filtering
                )

            if quora.get('expert_insights'):
                quora['expert_insights'] = await ai.filter_research_insights(
                    quora['expert_insights'],
                    keyword,
                    context="Quora expert answers",
                    source_type="reddit"  # Use Llama 3.3 70B for robust filtering
                )

            reddit_after = len(reddit.get('insights', []))
            quora_after = len(quora.get('expert_insights', []))

            # Update live display: Community complete, start filtering
            if use_live_display and not skip_community:
                research_display.complete_task("Reddit Mining", f"{reddit_after} insights", "...")
                research_display.complete_task("Quora Extraction", f"{quora_after} insights", "...")
                research_display.start_task("Quality Filter", "Filtering with Qwen3 235B")
                research_display.refresh()

            # Small delay for better UX (let user see the completion)
            if use_live_display:
                if not skip_community:
                    await asyncio.sleep(0.5)
                    research_display.complete_task("Quality Filter", f"{reddit_after + quora_after} insights filtered", "✓")
                    research_display.refresh()
                await asyncio.sleep(0.3)  # Brief pause before closing
                live.stop()

            # Log topical insights if available
            topical_count = len(topical_insights.get('insights', []))
            topical_filtered = topical_insights.get('filtered_count', 0)
            topical_raw = topical_insights.get('raw_count', 0)

            logger.debug(f"Research complete: {len(serp.get('paa_questions', []))} PAA questions, "
                       f"{reddit_after}/{reddit_before} Reddit insights, {quora_after}/{quora_before} Quora insights")

            # Log GSC intelligence availability
            gsc_data = serp.get('gsc_data')
            if gsc_data and gsc_data.get('primary_keyword'):
                primary_kw = gsc_data['primary_keyword'].get('query', 'N/A')
                secondary_count = len(gsc_data.get('secondary_keywords', []))
                question_count = len(gsc_data.get('questions', []))
                logger.debug(f"GSC Intelligence: Primary '{primary_kw}', {secondary_count} secondary keywords, {question_count} question keywords")
            else:
                logger.debug("GSC Intelligence: Not available (will continue without GSC optimization)")

            # Progress update: Research complete with summary
            research_summary = f"✓ Research complete: {paa_count} questions"
            if not skip_community:
                research_summary += f", {reddit_after} Reddit + {quora_after} Quora insights"
            self._progress(research_summary, advance=1)

            # Display Rich panel summary (only in TTY mode)
            if sys.stdout.isatty():
                console = Console()
                table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
                table.add_column("Source", style="dim", width=20)
                table.add_column("Model", style="yellow", width=25)
                table.add_column("Data Collected", style="green")

                # SERP row
                serp_model = "sonar-deep-research" if style == "research" else "sonar-reasoning-pro"
                serp_sources = len(serp.get('serp_analysis', {}).get('citations', [])) if augment_serp else 0
                serp_data = f"{paa_count} questions" + (f", {serp_sources} sources" if serp_sources > 0 else "")
                table.add_row("SERP Analysis", serp_model, serp_data)

                # Community rows
                if not skip_community:
                    reddit_data = f"{reddit_after} insights"
                    if style == "research" and not limit_community:
                        reddit_data += " (25-30 queries)"
                    elif limit_community:
                        reddit_data += " (limited: 3 queries)"
                    table.add_row("Reddit", "Perplexity + Gemini", reddit_data)
                    table.add_row("Quora", "Perplexity + Gemini", f"{quora_after} insights")

                # Topical insights row
                if topical_insights.get('enabled'):
                    table.add_row("Topical Insights", "sonar-reasoning-pro", f"{topical_count} insights")

                console.print()
                console.print(Panel(table, title="[bold]Research Summary[/bold]", border_style="blue"))
                console.print()

            if style == "research" and (reddit_after > 0 or quora_after > 0):
                logger.debug(f"Community data will be injected into research prompt: "
                           f"{reddit_after} Reddit + {quora_after} Quora insights")

            if topical_insights.get('enabled'):
                logger.debug(f"Topical insights: {topical_filtered}/{topical_raw} passed relevance filter")

            # Log SERP insights if available
            if augment_serp:
                serp_stats = self.insight_formatter.get_stats(serp)
                if serp_stats['enabled']:
                    logger.debug(f"SERP insights: {serp_stats['citation_count']} sources, "
                               f"~{serp_stats['estimated_tokens']} tokens")

            # Extract research quality metadata for prompting
            research_quality = {
                'has_academic_sources': False,
                'source_quality': 'standard',
                'citation_count': 0
            }

            if style == "research" and serp.get('serp_analysis'):
                analysis_text = serp['serp_analysis'].get('analysis', '').lower()
                citations = serp['serp_analysis'].get('citations', [])

                # Detect academic sources in citations
                academic_indicators = ['.edu', '.gov', 'gartner', 'forrester', 'pew', 'mckinsey',
                                      'harvard', 'mit', 'research', 'study', 'survey']
                academic_count = sum(1 for c in citations if any(ind in str(c).lower() for ind in academic_indicators))

                if academic_count >= 3:
                    research_quality['has_academic_sources'] = True
                    research_quality['source_quality'] = 'research-grade'
                    research_quality['citation_count'] = len(citations)
                    logger.debug(f"Research quality: research-grade ({academic_count} academic sources detected)")

            # Build comprehensive context
            # Note: 'style' and 'brand_mode' are passed separately to prompt builders,
            # so we don't duplicate them in context (they were never accessed via context)

            # Expose citations from community research (previously collected but unused)
            community_citations = reddit.get('citations', []) + quora.get('citations', [])

            context = {
                'serp': serp,
                'reddit': reddit,
                'quora': quora,
                'topical_insights': topical_insights,  # Industry insights from sonar-reasoning-pro
                'site_context': site_context,
                'research_quality': research_quality,
                'approved_solutions': approved_solutions,  # User-approved solutions from interactive selection
                'citations': community_citations  # Combined citations from Reddit + Quora for factual sourcing
            }

            # Instantiate intelligent context builder with research data
            self._context_builder = IntelligentContextBuilder(
                research_data={
                    'reddit': reddit,
                    'quora': quora,
                    'topical_insights': topical_insights
                },
                intent_classification=serp.get('intent_classification', {}),
                brand_voice=self.brand_voice
            )

            # Generate content using style-specific prompt
            logger.debug(f"Phase 2: Generation - Creating {style} content with Gemini 3.0 Pro")
            self._progress(f"Generating {style} content with Gemini 3.0 Pro...", 0)

            prompt_builder = self.style_prompts[style]

            # Build prompt kwargs based on style
            prompt_kwargs = {'brand_mode': brand_mode}
            if style == 'top-compare':
                prompt_kwargs['solution_count'] = solution_count
                logger.debug(f"Top-compare style: {solution_count} solutions")

            prompt = prompt_builder(keyword, context, **prompt_kwargs)

            # Log research data sources for research style
            if style == "research":
                serp_sources = len(context['serp'].get('search_results', []))
                reddit_insights = len(context['reddit'].get('insights', []))
                quora_insights = len(context['quora'].get('expert_insights', []))
                logger.debug("Research prompt data sources:")
                logger.debug(f"Perplexity SERP: {serp_sources} authoritative sources")
                logger.debug(f"Reddit insights: {reddit_insights} community discussions")
                logger.debug(f"Quora insights: {quora_insights} expert perspectives")
                if context['research_quality'].get('has_academic_sources'):
                    logger.debug(f"Research-grade sources detected: {context['research_quality']['citation_count']} academic citations")

            raw_content = await ai.generate(prompt, context)
            raw_words = len(raw_content.split())

            # Validate raw Gemini output before proceeding
            raw_validation = self._validate_mdx_structure(raw_content)
            if not raw_validation['valid']:
                logger.warning(f"⚠️  Raw content validation issues: {raw_validation['issues']}")
                # Attempt auto-repair
                raw_content = raw_validation['repaired_content']
                # Check if repair worked
                if not raw_content.strip().startswith('---'):
                    logger.error("❌ Gemini output invalid and could not be repaired")
                    return {
                        'success': False,
                        'error': f"Generation failed: Invalid MDX structure - {raw_validation['issues']}"
                    }

            # Validate minimum word count
            if raw_words < 1000:
                logger.error(f"❌ Generated content too short: {raw_words} words (minimum 1000)")
                return {
                    'success': False,
                    'error': f"Generation failed: Content too short ({raw_words} words, need 1000+)"
                }

            logger.debug(f"Generated {raw_words} words")
            self._progress(f"✓ Generated {raw_words:,} words", advance=1)

            # Format for Astro with all features
            research_data = {'serp': serp, 'community': {'reddit': reddit, 'quora': quora}}
            formatter = AstroFormatter(site_context, brand_mode=brand_mode)
            formatted = formatter.format(raw_content, keyword, style, research_data)

            # Refinement phase
            polish_model = "Llama 3.1 405B" if use_llama_polish else "Qwen3 235B"
            logger.debug(f"Phase 3: Refinement - Edit (GLM-4.7-FP8) + Polish ({polish_model})")
            self._progress(f"Polishing with {polish_model}...", 0)

            # Create live status display for refinement (if in TTY mode)
            if use_live_display:
                refinement_display = LiveStatusDisplay()
                refinement_display.set_phase("Refinement")
                refinement_display.add_task("Edit Pass")
                refinement_display.add_task("Polish Pass")
                refinement_display.add_task("Heading SEO")
                refinement_display.add_task("Title SEO")

                live = refinement_display.start_live(refresh_per_second=2)
                live.start()
                refinement_display.start_task("Edit Pass", "GLM-4.7-FP8")
                refinement_display.refresh()

            final_content = await ai.edit(formatted['content'], progress_callback=self._progress)

            # Validate edit didn't break structure
            edit_validation = self._validate_mdx_structure(final_content)
            if not edit_validation['valid']:
                logger.warning(f"⚠️  Edit step broke structure, using pre-edit version")
                final_content = formatted['content']
            else:
                formatted['content'] = final_content

            # Update live display: Edit complete
            if use_live_display:
                edit_words = len(final_content.split())
                refinement_display.complete_task("Edit Pass", f"{edit_words:,} words", "✓")
                refinement_display.refresh()

            # Verify citation accuracy and factual correctness (BEFORE polishing)
            logger.debug("Phase 3.5: Citation Verification - Checking links and factual accuracy")
            citation_verification = await self._verify_citations(final_content, ai, web, progress_callback=self._progress)

            # Auto-correct citation issues if found (skip micro sub-agent if no issues)
            if citation_verification.get('verification_status') == 'issues_found':
                logger.debug("Phase 3.6: Auto-correcting citation issues with micro sub-agent")
                corrected_content = await self._auto_correct_citations(
                    final_content,
                    citation_verification,
                    ai,
                    web
                )
                if corrected_content != final_content:
                    final_content = corrected_content
                    formatted['content'] = final_content
                    logger.info("✅ Citation auto-corrections applied")
            elif citation_verification.get('verification_status') == 'verified':
                logger.debug("✓ All citations verified - skipping micro sub-agent correction")
            else:
                logger.debug("ℹ️  Citation verification skipped or no citations found")

            # Update live display: Start polish
            if use_live_display:
                refinement_display.start_task("Polish Pass", polish_model)
                refinement_display.refresh()

            # Single polish step using Qwen3 235B (default) or Llama 3.1 405B (optional)
            # Polish frontmatter with chosen model
            frontmatter_polished = await ai.polish_frontmatter(final_content, use_llama=use_llama_polish)

            # Polish content body with chosen model
            if use_llama_polish:
                logger.debug("Using Llama 3.1 405B for polish (legacy mode)")
                polished_content = await ai.polish_content(frontmatter_polished["llama"], use_llama=True, site_context=self.site_context, brand_mode=brand_mode, progress_callback=self._progress)
                polished_final = polished_content["llama"]
            else:
                logger.debug("Using Qwen3 235B for polish (default)")
                polished_content = await ai.polish_content(frontmatter_polished["qwen"], use_llama=False, site_context=self.site_context, brand_mode=brand_mode, progress_callback=self._progress)
                polished_final = polished_content["qwen"]

            # Validate polish result
            polished_words = len(polished_final.split())

            if polished_words < 100:
                logger.warning(f"⚠️  Polish too short ({polished_words} words), using pre-polish")
                polished_final = final_content
            else:
                polish_validation = self._validate_mdx_structure(polished_final)
                if not polish_validation['valid']:
                    logger.warning(f"⚠️  Polish broke structure: {polish_validation['issues']}, using pre-polish")
                    polished_final = final_content

            polished_words = len(polished_final.split())
            logger.debug(f"Polish complete: {polished_words} words")
            self._progress(f"✓ Polished to {polished_words:,} words", advance=1)

            # Update live display: Polish complete
            if use_live_display:
                refinement_display.complete_task("Polish Pass", f"{polished_words:,} words", "✓")
                refinement_display.start_task("Heading SEO", "Optimizing headings")
                refinement_display.refresh()

            # Optimize headings for SEO/AEO
            logger.debug("Phase 4: Heading SEO/AEO Optimization")
            self._progress("Optimizing headings for SEO/AEO...", 0)
            polished_final = await ai._optimize_headings_seo(polished_final, keyword)
            logger.debug("Heading optimization complete")
            self._progress("✓ Headings optimized", advance=1)

            # Update live display: Heading SEO complete
            if use_live_display:
                refinement_display.complete_task("Heading SEO", "Optimized", "✓")
                refinement_display.start_task("Title SEO", "Gemini 3.0 Pro")
                refinement_display.refresh()

            # Optimize title for SEO/AEO (FINAL step - Gemini 3.0 Pro)
            # Uses enhanced SEO rules: year, numbers for lists, exact GSC keyword
            logger.debug("Phase 5: Title SEO/AEO Optimization (Gemini 3.0 Pro)")
            polished_final = await ai.optimize_title_seo(
                polished_final,
                keyword,
                style=style,
                gsc_primary_keyword=None  # TODO: Pass from GSC analyzer when integrated
            )

            # Update live display: Title SEO complete and close
            if use_live_display:
                refinement_display.complete_task("Title SEO", "Optimized", "✓")
                refinement_display.refresh()
                await asyncio.sleep(0.3)  # Brief pause before closing
                live.stop()

            # Set as final content
            formatted['content'] = polished_final

            # Analyze citations (basic counts)
            citation_analysis = await community.analyze_citations(polished_final)

            # Calculate metrics
            word_count = len(polished_final.split())
            generation_time = (datetime.now() - start_time).total_seconds()

            logger.debug(f"Complete! {word_count} words | {generation_time:.1f}s")
            self._progress(f"✓ Content complete! {word_count:,} words in {generation_time:.1f}s", advance=1)

            # Display completion summary panel (only in TTY mode)
            if sys.stdout.isatty():
                console = Console()
                summary_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
                summary_table.add_column("Metric", style="dim")
                summary_table.add_column("Value", style="bold green")

                summary_table.add_row("Final Word Count", f"{word_count:,} words")
                summary_table.add_row("Generation Time", f"{generation_time:.1f}s")
                summary_table.add_row("Title", formatted['title'])
                summary_table.add_row("Style", style.title())

                paa_answered = self._count_paa_answered(serp.get('paa_questions', []), polished_final)
                if paa_answered > 0:
                    summary_table.add_row("PAA Questions Answered", str(paa_answered))

                reddit_used = self._count_insights_used(reddit.get('insights', []), polished_final)
                if reddit_used > 0:
                    summary_table.add_row("Reddit Insights Used", str(reddit_used))

                console.print()
                console.print(Panel(summary_table, title="[bold green]✓ Generation Complete[/bold green]", border_style="green"))
                console.print()

            return {
                'success': True,
                'keyword': keyword,
                'style': style,
                'title': formatted['title'],
                'meta_description': formatted['meta_description'],
                'slug': formatted['slug'],
                'content': formatted['content'],
                'raw_content': raw_content,  # Raw content before any editing
                'edited_content': final_content,  # Content after edit pass
                'metrics': {
                    'word_count': word_count,
                    'generation_time': generation_time,
                    'paa_questions_answered': self._count_paa_answered(serp.get('paa_questions', []), polished_final),
                    'reddit_insights_used': self._count_insights_used(reddit.get('insights', []), polished_final),
                    'citation_ratio': citation_analysis['citation_ratio'],
                    'content_gaps_addressed': len(serp.get('content_gaps', [])),
                    'h2_sections': len(formatted.get('h2_sections', []))
                },
                'research_data': research_data,
                'generated_at': datetime.now().isoformat()
            }
    
    def _validate_mdx_structure(self, content: str) -> Dict[str, Any]:
        """Validate MDX structure and attempt auto-repair if needed"""
        issues = []

        # Check 1: Starts with YAML frontmatter
        if not content.strip().startswith('---'):
            issues.append("Missing YAML frontmatter (should start with ---)")

        # Check 2: No triple backticks wrapping entire content
        if content.strip().startswith('```') and content.strip().endswith('```'):
            issues.append("Content wrapped in code fences (backticks)")
            # Auto-repair: remove code fences
            content = content.strip()[3:-3].strip()
            logger.info("Auto-repaired: Removed code fence wrapping")

        # Check 3: Has valid frontmatter block
        parts = content.split('---')
        if len(parts) < 3:
            issues.append("Invalid frontmatter structure (needs --- delimiters)")
        else:
            # Check frontmatter has required fields
            frontmatter = parts[1]
            required_fields = ['title', 'publishDate', 'description', 'author']
            for field in required_fields:
                if f'{field}:' not in frontmatter:
                    issues.append(f"Missing required frontmatter field: {field}")

        # Check 4: Has content after frontmatter
        if len(parts) >= 3:
            body = '---'.join(parts[2:]).strip()
            if len(body) < 100:
                issues.append("Content body is too short or missing")

            # Check 5: Validate import statement syntax
            # Look for import statements in the body
            import_lines = [line for line in body.split('\n') if line.strip().startswith('import ')]

            for i, line in enumerate(import_lines):
                # Check 1: Import should end with semicolon
                if line.strip() and not line.strip().endswith(';'):
                    issues.append(f"Import statement {i+1} missing semicolon: {line[:50]}")
                    # Auto-repair: add semicolon
                    body = body.replace(line, line.rstrip() + ';')
                    logger.info(f"Auto-repaired: Added semicolon to import statement")

                # Check 2: Import should not contain periods before end (malformed concatenation)
                if '. import ' in line:
                    issues.append(f"Import statement {i+1} contains malformed periods: {line[:50]}")
                    # Auto-repair: split concatenated imports
                    fixed = line.replace('. import ', ';\nimport ')
                    body = body.replace(line, fixed)
                    logger.info(f"Auto-repaired: Split concatenated import statements")

            # Update content with repaired body
            if import_lines:
                content = '---'.join(parts[:2]) + '---\n' + body

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'repaired_content': content
        }

    def _validate_research_result(self, result: Any, source: str) -> Dict:
        """Validate and normalize research results"""
        if isinstance(result, dict):
            return result

        logger.warning(f"⚠️  {source} returned invalid data, using defaults")

        # Return appropriate defaults
        if source == 'serp':
            return {
                'keyword': '',
                'search_results': [],
                'paa_questions': [],
                'gsc_data': None,
                'content_gaps': [],
                'recommended_length': 2500
            }
        elif source == 'reddit':
            return {
                'insights': [],
                'questions': [],
                'citations': []
            }
        elif source == 'quora':
            return {
                'questions': [],
                'expert_insights': [],
                'citations': []
            }

        return {}

    def _format_community_insights_for_research(self, reddit: Dict, quora: Dict) -> str:
        """Format Reddit/Quora insights specifically for research-style content.

        Research mode emphasizes academic rigor but benefits from practitioner validation
        and real-world user experiences to complement industry analysis.

        Args:
            reddit: Reddit mining results with 'insights' list
            quora: Quora mining results with 'expert_insights' list

        Returns:
            Formatted community intelligence section for research prompt injection
        """
        reddit_insights = reddit.get('insights', [])[:30]  # Limit to 30 for comprehensive ICP segment coverage
        quora_insights = quora.get('expert_insights', [])[:10]  # Limit to 10 expert perspectives

        # Skip section entirely if no community data available
        if not reddit_insights and not quora_insights:
            logger.debug("   ℹ️  No community insights available for research prompt injection")
            return ""

        logger.debug(f"   📝 Formatting community insights for research: {len(reddit_insights)} Reddit + {len(quora_insights)} Quora")

        sections = []

        if reddit_insights:
            reddit_section = "**From Reddit Community Discussions:**\n"
            reddit_section += '\n'.join(f'  • {insight}' for insight in reddit_insights)
            sections.append(reddit_section)

        if quora_insights:
            quora_section = "**From Quora Expert Perspectives:**\n"
            quora_section += '\n'.join(f'  • {insight}' for insight in quora_insights)
            sections.append(quora_section)

        community_block = f"""
═══════════════════════════════════════════════════════════════
💬 COMMUNITY INTELLIGENCE (Real User Experiences)
═══════════════════════════════════════════════════════════════

{chr(10).join(sections)}

**How to Use This Data:**
- Validate academic findings with real-world practitioner experiences
- Surface practical implementation challenges not covered in formal research
- Include diverse perspectives: researchers, practitioners, and end-users
- Cross-reference community patterns with industry data for credibility

⚠️ Attribution: When using community insights, cite as "according to practitioner discussions" or "as reported by users in [platform]"
═══════════════════════════════════════════════════════════════
"""

        return community_block

    def _format_gsc_intelligence(self, gsc_data: Optional[Dict[str, Any]]) -> str:
        """Format GSC data for prompt injection across all content styles.

        Args:
            gsc_data: GSC data from serp context (may be None if unavailable)

        Returns:
            Formatted GSC intelligence block for prompt injection
        """
        if not gsc_data or not gsc_data.get('primary_keyword'):
            return ""

        primary = gsc_data.get('primary_keyword', {})
        secondaries = gsc_data.get('secondary_keywords', [])
        questions = gsc_data.get('questions', [])

        gsc_block = f"""
═══════════════════════════════════════════════════════════════
📊 GOOGLE SEARCH CONSOLE INTELLIGENCE (Real Search Data)
═══════════════════════════════════════════════════════════════

**Primary Keyword (MUST use EXACT in title):**
{primary.get('query', '')}
- Current Position: {primary.get('position', 'N/A')}
- Monthly Impressions: {primary.get('impressions', 0):,}
- Traffic Potential: {primary.get('traffic_potential', 0):.0f}
- Current CTR: {primary.get('ctr', 0):.2%}

**Secondary Keywords (distribute across H2 headings):**
"""
        for i, kw in enumerate(secondaries[:5], 1):
            gsc_block += f"{i}. {kw.get('query', '')} (Position: {kw.get('position', 'N/A'):.1f}, Impressions: {kw.get('impressions', 0):,})\n"

        if questions:
            gsc_block += f"\n**Question Keywords for FAQ (from real search data):**\n"
            for q in questions[:8]:
                gsc_block += f"- {q.get('query', '')} (Position: {q.get('position', 'N/A'):.1f})\n"

        gsc_block += f"""
**How to Use This Data:**
- Use primary keyword EXACTLY as shown in title (it's proven to get impressions)
- Weave secondary keywords naturally into H2 headings where relevant
- Use question keywords to inform FAQ section structure
- This is REAL search demand data from Google - prioritize these over speculation
═══════════════════════════════════════════════════════════════
"""
        return gsc_block

    def _get_brand_positioning_prompt(self, brand_mode: str) -> str:
        """Generate mode-specific Brand positioning instructions

        Args:
            brand_mode: 'none', 'limited', or 'full'

        Returns:
            Positioning prompt text for the generation model
        """
        if brand_mode == 'none':
            return ""

        elif brand_mode == 'limited':
            return '''
⚠️ LIMITED BRAND MODE - MAXIMUM RESTRAINT:
- Mention Brand ONLY 2-3 times total in entire article
- ONLY where it's a genuinely perfect fit for the problem discussed
- Each mention must feel completely natural and helpful, never forced
- 95% problem-focused, 5% solution
- If it doesn't feel natural, DON'T mention it
- Quality over quantity - better 2 perfect mentions than 5 awkward ones
'''

        else:  # full mode
            return '''
BRAND AS NATURAL FIT (Refined for Natural Integration):
- Weave Brand naturally where it genuinely fits the problem-solution flow
- Maximum 10 mentions total, but only use what feels natural (8-10 is fine, 4-5 is also fine)
- 90% problem-focused, 10% solution-focused
- Every mention should feel helpful and conversational, never salesy
- If a section doesn't naturally call for Brand, skip it
- Prioritize reader value over mention count
'''

    def _get_standard_prompt(self, keyword: str, context: Dict[str, Any], brand_mode: str = 'full') -> str:
        """Standard content prompt"""
        serp = context['serp']
        reddit = context['reddit']
        quora = context['quora']
        site_context = context['site_context']

        # Calculate target length based on SERP with guardrails (increased by 500 words)
        serp_recommended = serp.get('recommended_length', 2500)
        target_length = max(2000, min(3000, serp_recommended))

        # Filter PAA questions to avoid platform-specific questions
        paa_questions = self._filter_paa_questions(serp.get('paa_questions', []))

        # Format SERP insights for injection
        serp_insights = self.insight_formatter.format_for_prompt(serp, 'standard')

        # Format GSC intelligence if available
        gsc_intelligence = self._format_gsc_intelligence(serp.get('gsc_data'))

        return f"""Create comprehensive, AI-optimized content that answers 100+ related questions for "{keyword}".

PRIMARY ANSWER FIRST: Start with direct answers to the main question in the first 1-2 sentences.

Target length: {target_length} words (min 1500, max 2500)
SERP recommendation: {serp_recommended} words
{self._format_icp_context(skip_icp=self._skip_icp)}
{self._format_customer_language()}
TOPIC CLUSTERING APPROACH (AI-optimized structure):

## Core Definition Section
**Lead with direct definition in first sentence**
- **Bold key concepts** for AI extraction
- Address foundational "what is" questions naturally
- Include specific examples and use cases
- Cover 3-5 related questions per paragraph

## How It Works Section
**Direct explanations of core processes**
- Step-by-step breakdowns with clear hierarchies
- Bulleted subsections for multiple approaches
- **Bold key phrases** for important mechanisms
- Address "how does" questions conversationally

## Implementation Section
**Practical guidance for getting started**
- Numbered steps with prerequisites clearly listed
- Common challenges and prevention strategies
- Pro tips and best practices with **bolded key advice**
- Address "how to" questions with actionable detail

## Benefits & Results Section
**Specific outcomes and advantages**
- Quantifiable benefits with data points where possible
- Expected results and realistic timelines
- ROI improvements and efficiency gains
- Address "why" and results questions directly

## Tools & Resources Section
**Essential tools and evaluation criteria**
- Must-have resources and tools for success
- Clear evaluation criteria for selection
- Integration considerations and compatibility
- Address "what tools" questions comprehensively

## Common Challenges Section
**Frequent problems and solutions**
- Most common issues encountered
- Prevention strategies and quick fixes
- Troubleshooting guidance with **bolded solutions**
- Address pain points from community discussions

{self._get_brand_positioning_prompt(brand_mode)}
NEGATIVE PROMPTS (AVOID COMPLETELY):
- NEVER discuss product catalogs, inventory management, shopping carts, or customer purchases
- NEVER mention order fulfillment, shipping, online marketplaces, or digital commerce
- Focus exclusively on the target audience and industry defined in the ICP configuration

EXPERT ANALYSIS FRAMING:
- Frame comprehensive coverage as expert analysis
- Include specific examples, data points, actionable advice
- Ensure logical flow between sections (coherence check)
- Maintain scannable readability with clear takeaways
- Signal expertise through detailed explanations and insights
- High answer density: Every paragraph addresses 2-4 related questions
- Citation-ready facts easily extractable by AI systems
{self._format_brand_voice_prompt(brand_mode)}
SERP Intelligence (AEO 2026 - Target 90% AI Visibility):
- Address these natural language questions conversationally: {', '.join(paa_questions[:15]) if paa_questions else 'None found'}
- Fill these content gaps: {', '.join(serp.get('content_gaps', [])) if serp.get('content_gaps') else 'None identified'}
- Competitor count: {len(serp.get('search_results', []))}

{serp_insights}

{gsc_intelligence}

Community Pain Points (Reddit):
{self._format_insights(reddit.get('insights', [])[:5])}

Expert Knowledge (Quora):
{self._format_insights(quora.get('expert_insights', [])[:3])}

{self._format_topical_insights(context.get('topical_insights'))}

{self._get_brand_positioning_prompt(brand_mode)}
AI OPTIMIZATION REQUIREMENTS:
- **Lead sentences**: Direct answers AI can extract verbatim
- **Bulleted subsections**: For multiple specific points
- **Bold key phrases**: Help AI identify important concepts
- **Clear H2/H3 hierarchies**: Main topics and subtopics
- **High answer density**: 2-4 questions addressed per paragraph
- **Citation-ready facts**: Key data easily extractable

Create content that dominates search results while positioning Brand as a leading solution."""

    def _has_competitors(self, keyword: str, serp: Dict[str, Any]) -> bool:
        """Strictly detect if keyword explicitly compares specific competitor products with problem-solution fit"""
        keyword_lower = keyword.lower()

        # Only detect competitors if keyword has EXPLICIT comparison pattern with a brand name
        # E.g., "HubSpot vs Salesforce", "Zapier or Segment", "Google Analytics alternative"
        competitor_patterns = [' vs ', ' vs. ', ' versus ', ' compared to ', ' compare ', ' or ']

        # Must have comparison pattern AND exclude generic terms
        has_comparison_pattern = any(pattern in keyword_lower for pattern in competitor_patterns)

        if not has_comparison_pattern:
            return False  # No comparison pattern = no competitors

        # Exclude keywords comparing generic terms (these should use Manual vs Brand)
        generic_exclusions = [
            'manual', 'automation', 'automated', 'tools', 'software', 'platforms',
            'solutions', 'methods', 'approaches', 'strategies', 'techniques',
            'process', 'system', 'way', 'methods'
        ]

        # If keyword contains generic terms around comparison pattern, NOT a competitor comparison
        for generic in generic_exclusions:
            for pattern in competitor_patterns:
                if f"{pattern}{generic}" in keyword_lower or f"{generic}{pattern}" in keyword_lower:
                    return False  # Generic comparison, use Manual vs Brand

        # Direct competitors to Brand
        try:
            with open(os.path.join(os.path.dirname(__file__), '..', 'config', 'competitors.json'), 'r') as f:
                competitors_data = json.load(f)
                direct_competitors = [c.lower() for c in competitors_data.get('main_competitors', [])]
        except Exception:
            direct_competitors = []

        # Check if keyword mentions direct competitors
        if any(comp in keyword_lower for comp in direct_competitors):
            return True  # Clear competitor comparison

        return False  # Default: Use Manual vs Brand for most guide content

    def _verify_brand_features(self, site_context: Dict[str, Any], required_features: List[str]) -> bool:
        """Verify that Brand actually has the claimed features based on site extraction"""
        if not site_context or 'features' not in site_context:
            return False

        # Get all confirmed features from site extraction
        confirmed_features = site_context.get('features', [])
        confirmed_text = ' '.join(confirmed_features).lower()

        # Check if all required features are mentioned in site content
        for feature in required_features:
            feature_lower = feature.lower()
            if feature_lower not in confirmed_text:
                logger.warning(f"⚠️  Feature not verified in site content: {feature}")
                return False

        logger.info(f"✅ All {len(required_features)} features verified in site content")
        return True

    def _get_comparison_prompt(self, keyword: str, context: Dict[str, Any], brand_mode: str = 'full') -> str:
        """Comparison content prompt"""
        serp = context['serp']
        reddit = context['reddit']
        site_context = context['site_context']

        # Calculate target length based on SERP with guardrails (increased by 500 words)
        serp_recommended = serp.get('recommended_length', 2500)
        target_length = max(2000, min(3000, serp_recommended))

        # Format SERP insights for injection
        serp_insights = self.insight_formatter.format_for_prompt(serp, 'comparison')

        # Format GSC intelligence if available
        gsc_intelligence = self._format_gsc_intelligence(serp.get('gsc_data'))

        # Get disambiguation context for ambiguous terms (e.g., MCP)
        disambiguation_context = self._get_disambiguation_context(keyword)

        # Get relevant Brand product context
        product_context = self._get_product_context(keyword, brand_mode)

        return f"""Create a comprehensive, AI-optimized comparison that answers 100+ related questions for "{keyword}".

{disambiguation_context}

{product_context}

PRIMARY ANSWER FIRST: Start with direct answers to the main comparison question in the first 1-2 sentences.

Target length: {target_length} words (min 2000, max 3000)
SERP recommendation: {serp_recommended} words
{self._format_icp_context(light_mode=True, skip_icp=self._skip_icp)}
{self._format_customer_language()}
TOPIC CLUSTERING APPROACH (AI-optimized comparison structure):

## Quick Comparison Table (REQUIRED - IMMEDIATELY AFTER INTRO)
**Scannable summary for readers who want quick answers**

Create a markdown comparison table with 4-5 columns:
| Feature/Solution | Option A | Option B | Option C | Brand |
|-----------------|----------|----------|----------|---------|
| Best For | [use case] | [use case] | [use case] | [use case] |
| Pricing | [range] | [range] | [range] | [range] |
| Key Strength | [strength] | [strength] | [strength] | [strength] |
| Overall Score | X/10 | X/10 | X/10 | X/10 |

This table MUST appear immediately after the opening hook/intro.

## Core Definition Section
**What this comparison covers and key decision factors**
- **Bold key evaluation criteria** for AI extraction
- Address foundational "what to compare" questions
- Set clear framework for evaluation

## Overview of Options Section
**High-level summary of each solution**
- **Option 1: [Name]** - Direct description first
  - **Key strengths:** Bulleted advantages
  - **Best for:** Specific use cases
  - Address 2-3 related questions per option
- **Option 2: [Name]** - Continue pattern
- Include Brand as optimization layer, not direct competitor

## Feature Comparison Section
**Detailed side-by-side analysis**
- **Core Features:** Essential capabilities compared
  - **Integration:** How easily it connects with other tools
  - **Ease of Use:** Learning curve and user experience
  - **Scalability:** Growth and performance considerations
- **Advanced Features:** Specialized capabilities
- **Brand Advantage:** Show as enhancement layer

## Pricing & Value Section
**Cost analysis and ROI considerations**
- **Pricing Models:** Breakdown of costs and structures
  - **Free tiers:** What's included and limitations
  - **Paid plans:** Feature differences and value
  - **Enterprise options:** Advanced pricing considerations
- **Total Cost of Ownership:** Hidden costs and long-term value
- **Brand Positioning:** Competitive value proposition

## Use Cases & Scenarios Section
**Specific applications and when to choose each**
- **Scenario 1: [Use Case]** - Direct application description
  - **Best option:** Which solution excels here
  - **Why it works:** Specific advantages
  - **Brand enhancement:** How it improves outcomes
- **Scenario 2: [Use Case]** - Continue pattern
- Address "when to use" questions comprehensively

## Implementation & Setup Section
**Getting started and integration considerations**
- **Ease of Implementation:** Setup complexity and time
  - **Technical requirements:** Prerequisites and dependencies
  - **Learning curve:** Training and adoption challenges
  - **Support quality:** Available resources and assistance
- **Integration Capabilities:** How well it works with existing tools
- **Brand Advantage:** Zero technical expertise required

## Pros, Cons & Limitations Section
**Balanced analysis of strengths and weaknesses**
- **Strengths:** What each does exceptionally well
- **Limitations:** Where each falls short
- **Common Challenges:** Real-world issues encountered
- Address community pain points and user feedback

EXPERT ANALYSIS FRAMING:
- Frame as comprehensive expert comparison
- Include specific examples and real-world scenarios
- Ensure logical flow between evaluation criteria
- High answer density: 2-4 questions per section
- Citation-ready facts and data points
- Signal expertise through detailed, nuanced analysis
{self._format_brand_voice_prompt(brand_mode)}
{self._get_brand_positioning_prompt(brand_mode)}
SEMANTIC INTELLIGENCE: SOLUTION RELEVANCE FILTER
Before including ANY option/solution in this comparison, verify:
1. Does this solution's PRIMARY PURPOSE match what "{keyword}" is asking for?
2. Would solutions in this comparison be SUBSTITUTES for each other (same category)?
3. Would a searcher typing "{keyword}" expect to find this solution?
If a solution fails these checks, DO NOT INCLUDE IT — even to pad out the comparison.
Quality over quantity. Honesty over comprehensiveness.

{self._format_approved_solutions(context.get('approved_solutions'))}

NEGATIVE PROMPTS (AVOID COMPLETELY):
- NEVER include solutions from unrelated categories just to have more options
- NEVER discuss product catalogs, inventory management, shopping carts, or customer purchases
- NEVER mention order fulfillment, shipping, online marketplaces, or digital commerce
- Focus exclusively on the target audience and industry defined in the ICP configuration

SERP Intelligence (AEO 2026 - 12-15 questions for 90% AI visibility):
- Address these comparison questions: {', '.join(serp.get('paa_questions', [])[:15])}
- Fill these content gaps: {', '.join(serp.get('content_gaps', []))}
- Key comparison factors from search analysis

{serp_insights}

{gsc_intelligence}

Community Insights & User Feedback:
{self._format_insights(reddit.get('insights', [])[:6])}

{self._format_topical_insights(context.get('topical_insights'))}

{"" if brand_mode == 'none' else f'''Brand's Competitive Advantages:
- Features: {', '.join(site_context.get('features', [])[:4])}
- Benefits: {', '.join(site_context.get('customer_benefits', [])[:3])}
- Use cases: {', '.join(site_context.get('use_cases', [])[:3])}

⚠️ CRITICAL FEATURE CONSTRAINT:
- ONLY mention Brand features explicitly listed here: {', '.join(site_context.get('features', []))}
- NEVER invent, assume, or extrapolate features not in this verified list
- If a feature isn't confirmed, DO NOT claim Brand can do it
- Focus on verified differentiators: {', '.join(site_context.get('key_differentiators', []))}
'''}
AI OPTIMIZATION REQUIREMENTS:
- **Lead sentences**: Direct answers AI can extract
- **Bulleted subsections**: For detailed comparisons
- **Bold key phrases**: Important features and criteria
- **Clear H2/H3 hierarchies**: Main topics and sub-details
- **Comparison tables**: Structured data for AI parsing
- **Citation-ready facts**: Key data easily extractable

Create an objective comparison that naturally positions Brand as the optimization layer that enhances all other solutions."""

    def _get_guide_prompt(self, keyword: str, context: Dict[str, Any], brand_mode: str = 'full') -> str:
        """Guide/How-to content prompt"""
        serp = context['serp']
        reddit = context['reddit']
        site_context = context['site_context']

        # Calculate target length based on SERP with guardrails (increased by 500 words)
        serp_recommended = serp.get('recommended_length', 2500)
        target_length = max(2000, min(3000, serp_recommended))

        # Format SERP insights for injection
        serp_insights = self.insight_formatter.format_for_prompt(serp, 'guide')

        # Format GSC intelligence if available
        gsc_intelligence = self._format_gsc_intelligence(serp.get('gsc_data'))

        # Determine if we should include Manual vs Brand comparison
        has_competitors = self._has_competitors(keyword, serp)
        manual_vs_brand_section = ""

        if not has_competitors and brand_mode != 'none':
            # Always include detailed Manual Way section
            manual_section = """

## The Manual Way vs The Automated Way Section (INCLUDE THIS - CRITICAL)

### The Manual Way (Traditional Approach) - HIGHLY DETAILED
**The painful, time-consuming reality of doing this manually**

INSTRUCTION TO AI: Generate 5-7 highly detailed, realistic steps showing exactly how someone would solve this problem manually without specialized tools.
- Focus strictly on the specific pain points defined in the ICP and the current keyword.
- Include estimated hours per week wasted on each step.
- Include realistic "Pro hacks" or "Time-saving tips" that people try (which usually fall short).
- Include "Reality checks" or "Watch outs" highlighting the fragility of the manual process.
- End with a summary of total manual time investment, expertise required, risk level, and scalability limitations.
**HIDDEN COSTS:**
- $750-2,300/week in labor costs (15-23 hours at $50-100/hour)
- Opportunity cost of strategic work not being done
- Lost revenue from delayed optimization decisions
- Stress and burnout from repetitive manual work
"""

            # Only add Brand section if we can verify the features actually exist
            brand_features = ['integration', 'sync', 'real-time', 'dashboard']
            has_verified_features = self._verify_brand_features(site_context, brand_features)

            if has_verified_features:
                # Build Brand section dynamically based on CONFIRMED features only
                confirmed_features = site_context.get('features', [])
                confirmed_text = ' '.join(confirmed_features).lower()

                brand_section = "\n### The Brand way (Automated Solution)\n**Modern, effortless automation that eliminates 95% of manual work:**\n\n"

                # Only mention features we've confirmed exist
                if 'integration' in confirmed_text:
                    brand_section += """- **One-Time Setup (5-10 minutes):** Connect all platforms with no-code integrations
  - Single-click authentication for CRM and ad platforms
  - Brand handles all API connections automatically
  - Zero technical expertise required\n"""

                if 'sync' in confirmed_text or 'real-time' in confirmed_text:
                    brand_section += """- **Automatic Data Syncing:** All data flows automatically 24/7
  - No more manual exports or CSV wrangling
  - Real-time data updates across all platforms
  - Always working with current data\n"""

                if 'dashboard' in confirmed_text or 'report' in confirmed_text:
                    brand_section += """- **Unified Dashboard:** Single view of all performance
  - Compare campaigns across platforms side-by-side
  - Real-time visibility into what's working
  - Custom reporting delivered automatically\n"""

                brand_section += """\n**TOTAL TIME INVESTMENT: 0-1 hours per week (review only)**
**EXPERTISE REQUIRED: NONE - completely no-code**
**RISK LEVEL: LOW - automated validation, zero human error**
**SCALABILITY: EXCELLENT - add unlimited campaigns with no additional work**
"""

                manual_vs_brand_section = manual_section + brand_section
            else:
                # If we can't verify Brand features, ONLY show manual guide
                logger.info("⚠️  Could not verify Brand features - showing manual guide only")
                manual_vs_brand_section = manual_section
        elif not has_competitors and brand_mode == 'none':
            # No Brand mode: Show detailed manual way ONLY (educational value, no brand selling)
            manual_vs_brand_section = """

## The Manual Way Section (HIGHLY DETAILED - EDUCATIONAL GUIDE)

### Traditional Manual Approach
**The detailed reality of doing this manually:**

#### Step 1: Manual Data Export & Collection (2-3 hours/week)
**The tedious process of gathering data from multiple sources:**
- Log into each platform separately (Google Ads, Facebook Ads Manager, LinkedIn Campaign Manager, CRM)
- Navigate to reporting sections and select date ranges manually (often inconsistent across platforms)
- Export CSVs one platform at a time, dealing with different export formats
- Download files to local machine, organize in folders with naming conventions
- **Pro hack:** Create a master folder structure organized by week/month to avoid file chaos
- **Common issue:** Export limits force you to download data in chunks for large accounts
- **Time-saving tip:** Set up scheduled reports where available, but these often arrive at inconsistent times
- **Reality check:** Miss one export and your entire analysis has gaps

**TOTAL MANUAL TIME INVESTMENT: 15-23 hours per week**
**EXPERTISE REQUIRED: Advanced Excel, data analysis, understanding of each ad platform**
**RISK LEVEL: VERY HIGH - Human error, data staleness, missed opportunities, formula errors**
**SCALABILITY: POOR - Each additional channel doubles the workload**
"""

        return f"""Create a comprehensive, AI-optimized step-by-step guide that answers 100+ related questions for "{keyword}".

PRIMARY ANSWER FIRST: Start with direct answers to the main "how to" question in the first 1-2 sentences.

Target length: {target_length} words (min 2000, max 3000)
SERP recommendation: {serp_recommended} words
{self._format_icp_context(skip_icp=self._skip_icp)}
{self._format_customer_language()}
TOPIC CLUSTERING APPROACH (AI-optimized guide structure):

## Core Definition Section
**What this guide covers and expected outcomes**
- **Bold key objectives** and deliverables
- Address foundational "what is" questions
- Set clear expectations for readers

## Prerequisites & Requirements Section
**Everything needed before starting**
- Essential tools and resources clearly listed
- Technical requirements and prerequisites
- Time and resource estimates
- Address "what do I need" questions directly

## Step-by-Step Implementation Section
**Detailed numbered steps with sub-bullets**
- **Step 1: [Action]** - Direct instruction first
  - Substep details with **bolded key actions**
  - Common variations and alternatives
  - Brand integration points highlighted
- **Step 2: [Action]** - Continue with clear progression
  - Include screenshots/examples where helpful
  - Show Brand features that simplify each step
- Address 3-5 related questions per major step
{manual_vs_brand_section}
## Common Challenges & Solutions Section
**Most frequent problems and how to solve them**
- **Challenge 1: [Problem]** - Direct description
  - **Solution:** Step-by-step fix with **bolded key advice**
  - Prevention strategies
- **Challenge 2: [Problem]** - Continue pattern
- Address troubleshooting questions from community

## Pro Tips & Best Practices Section
**Advanced strategies and optimization**
- **Tip 1: [Strategy]** - Specific actionable advice
- **Tip 2: [Strategy]** - Continue with expert insights
- Time-saving shortcuts and efficiency hacks
- Brand-specific optimizations highlighted

## Tools & Resources Section
**Complete toolkit for success**
- Essential tools with evaluation criteria
- Recommended resources and further reading
- Integration considerations
- Address "what tools do I need" questions

## Expected Results & Timeline Section
**What to expect and when**
- Realistic timelines for each phase
- Success metrics and milestones
- Common results and outcomes
- Address "how long does it take" questions

EXPERT ANALYSIS FRAMING:
- Frame as comprehensive expert guide
- Include specific examples and real-world scenarios
- Ensure logical flow between sections
- High answer density: 2-4 questions per paragraph
- Citation-ready facts and data points
- Signal expertise through detailed, actionable guidance
{self._format_brand_voice_prompt(brand_mode)}
SERP Intelligence (AEO 2026 - 12-15 questions for 90% AI visibility):
- Address these how-to questions: {', '.join([q for q in serp.get('paa_questions', []) if 'how' in q.lower()][:15])}
- Fill these content gaps: {', '.join(serp.get('content_gaps', []))}
- Missing implementation details from competitors

{serp_insights}

{gsc_intelligence}

Community Challenges & Pain Points:
{self._format_insights(reddit.get('insights', [])[:6])}

{self._format_topical_insights(context.get('topical_insights'))}

{self._get_brand_positioning_prompt(brand_mode)}

{"" if brand_mode == 'none' else f'''⚠️ CRITICAL FEATURE CONSTRAINT:
- Verified Brand features: {', '.join(site_context.get('features', []))}
- Verified differentiators: {', '.join(site_context.get('key_differentiators', []))}
- ONLY mention these verified features - NEVER invent or assume capabilities not listed
- If troubleshooting requires a feature Brand doesn't have, focus on manual solutions
'''}
NEGATIVE PROMPTS (AVOID COMPLETELY):
- NEVER discuss product catalogs, inventory management, shopping carts, or customer purchases
- NEVER mention order fulfillment, shipping, online marketplaces, or digital commerce
- Focus exclusively on the target audience and industry defined in the ICP configuration

AI OPTIMIZATION REQUIREMENTS:
- **Lead sentences**: Direct answers AI can extract
- **Bulleted subsections**: For multiple approaches/options
- **Bold key phrases**: Important actions and concepts
- **Clear H2/H3 hierarchies**: Main steps and sub-details
- **Numbered steps**: For sequential processes
- **Citation-ready facts**: Key data easily extractable

Create a guide so comprehensive that readers succeed{"" if brand_mode == 'none' else ", while naturally showcasing Brand ONLY where it genuinely fits"}."""

    def _format_research_quality_prompt(self, context: Dict[str, Any]) -> str:
        """Format research quality guidance for generation"""
        quality = context.get('research_quality', {})

        if quality.get('has_academic_sources'):
            return f"""
RESEARCH QUALITY DIRECTIVE:
This analysis leveraged {quality.get('citation_count', 0)} research-grade sources including academic journals, market research firms, and government data.

GENERATION REQUIREMENTS:
✓ Cite specific data points from research sources
✓ Reference studies, surveys, and published research
✓ Use phrases: "According to [source]...", "Research shows...", "Studies indicate..."
✓ Include statistics with context (sample sizes, time periods, methodologies)
✓ Maintain academic tone while staying accessible
✓ Prioritize peer-reviewed insights over anecdotal evidence
"""
        else:
            return """
CONTENT QUALITY DIRECTIVE:
Use available research data to support claims with specific examples and industry insights.
"""

    def _get_research_prompt(self, keyword: str, context: Dict[str, Any], brand_mode: str = 'full') -> str:
        """Research/data-driven content prompt with intelligent benchmark extraction"""
        serp = context['serp']
        reddit = context['reddit']
        quora = context['quora']
        site_context = context['site_context']

        # Research style gets HIGHEST limits - enforce longer, more authoritative content
        serp_recommended = serp.get('recommended_length', 4000)
        target_length = max(3500, min(5000, serp_recommended))

        # Format SERP insights for injection (research gets highest token budget)
        serp_insights = self.insight_formatter.format_for_prompt(serp, 'research')

        # Format GSC intelligence if available
        gsc_intelligence = self._format_gsc_intelligence(serp.get('gsc_data'))

        # INTELLIGENT BENCHMARK EXTRACTION (NO HARDCODED METRICS)
        extractor = IntelligentBenchmarkExtractor()

        # Detect relevant metrics from actual research data
        relevant_metrics = extractor.detect_relevant_metrics(keyword, serp, reddit)

        # Discover relevant industry segments intelligently
        research_context = {'serp': serp, 'reddit': reddit, 'quora': quora}
        industry_segments = extractor.discover_industry_segments(keyword, self.icp_config, research_context)

        # Detect research intent for intelligent table generation
        research_intent = self._detect_research_intent(keyword, serp)

        # Generate dynamic table requirements (NO HARDCODED TEMPLATES)
        intelligent_table_prompt = extractor.build_intelligent_table_requirements(
            keyword=keyword,
            metrics=relevant_metrics,
            segments=industry_segments,
            research_intent=research_intent
        )

        return f"""Create a comprehensive, AI-optimized research article that answers 100+ related questions for "{keyword}".

PRIMARY ANSWER FIRST: Start with direct answers to the main research question in the first 1-2 sentences.

Target length: {target_length} words (CRITICAL MINIMUM: 3500 words for research-grade content - aim for 4000-4500)
SERP recommendation: {serp_recommended} words
{self._format_icp_context(skip_icp=self._skip_icp)}
{self._format_customer_language()}
TOPIC CLUSTERING APPROACH (AI-optimized research structure):

## Executive Summary Section (200-300 words)
**Key findings and takeaways upfront**
- **Bold critical insights** for AI extraction
- Address "what did we find" questions directly
- Include 3-5 major conclusions with specific data points and percentages
- Set expectations for detailed analysis to follow
- Frame with executive language: "This research reveals...", "Our analysis demonstrates..."

## Quick Findings Summary Table (REQUIRED - immediately after executive summary)
**Scannable overview for quick reference**
| Finding | Key Metric | Objective Industry Impact | Confidence |
|---------|------------|---------------------------|------------|
| [Finding 1] | [Specific stat with %] | [Objective Industry Impact] | [RESEARCH/INDUSTRY/OBSERVATIONAL] |
| [Finding 2] | [Specific stat with %] | [Objective Industry Impact] | [RESEARCH/INDUSTRY/OBSERVATIONAL] |
| [Finding 3] | [Specific stat with %] | [Objective Industry Impact] | [RESEARCH/INDUSTRY/OBSERVATIONAL] |
| ... | ... | ... | ... |

**Impact Column Requirements (OBJECTIVE - NO ADVISORY LANGUAGE):**
- ✅ GOOD: "Affects $127B global ad spend market" (market sizing)
- ✅ GOOD: "Represents 23% of total industry budgets" (market share)
- ✅ GOOD: "Standard deviation ±0.8x indicates high variability" (statistical significance)
- ✅ GOOD: "42% of marketers cite this as top challenge" (industry observation)
- ❌ BAD: "Helps businesses plan budgets effectively" (advisory/prescriptive)
- ❌ BAD: "Enables faster break-even timelines" (internal benefit)
- ❌ BAD: "Prevents under-investing in nurture" (recommendation)

**Focus on:**
1. Market size/share implications
2. Statistical significance or variance
3. Industry-wide adoption/prevalence rates
4. Competitive landscape positioning
5. Economic impact at industry level

**Avoid:**
- How businesses should use this insight
- Internal planning implications
- Strategic recommendations
- Problem-solving framing

Requirements:
- 5-8 findings minimum in table format
- Each finding links to a detailed section below
- Confidence levels indicate source quality:
  - RESEARCH: Peer-reviewed, .edu/.gov, Gartner/Forrester/McKinsey
  - INDUSTRY: Established publications, vendor reports
  - OBSERVATIONAL: Community insights, user testimonials

## Research Methodology Section (REQUIRED FOR CREDIBILITY - 300-400 words)
**Professional, authoritative research framework**
- **Data Collection Approach:** "Industry analysis of leading solutions across multiple segments and market verticals from {datetime.now().year}"
  - Scope of analysis: define what was examined (platforms, companies, industries)
  - Time period covered: specify research timeframe
  - Data source types: "authoritative industry sources, verified case studies, performance benchmarks"
- **Analysis Framework:** "Comparative evaluation using quantitative and qualitative metrics across 50+ data points"
  - Key evaluation criteria used
  - How solutions/approaches were scored or ranked
  - Weighting methodology for different factors
- **Quality Validation Process:** "Cross-referenced data from multiple authoritative industry sources for accuracy"
  - How data accuracy was ensured
  - Conflict resolution when sources disagreed
  - Verification methods for claims and statistics
- **Scope & Limitations:** Define research boundaries clearly
  - What was included vs. excluded from analysis
  - Geographic or industry limitations
  - Time period constraints
  - Acknowledging gaps or areas requiring future research
- **Source Confidence Classification Framework:**
  - **RESEARCH-GRADE:** Peer-reviewed journals, .edu/.gov sources, Gartner/Forrester/McKinsey, academic studies with methodology disclosure
  - **INDUSTRY:** Established industry publications, vendor reports from recognized companies, trade associations, analyst firms
  - **OBSERVATIONAL:** Community discussions, user testimonials, practitioner blogs, case studies without peer review
  - Tag each major data point with its confidence level throughout the article
- **DO NOT expose internal tools:** Keep methodology high-level, professional, third-party research language
- **Frame as authoritative:** "comprehensive market analysis", "systematic evaluation", "data-driven assessment"

## Current State Analysis Section (500-600 words)
**Where the market stands today**
- **Market Overview:** Size, growth, key players (include specific numbers)
  - **Market size:** Specific dollar amounts, TAM/SAM data points and trends
  - **Growth rate:** Year-over-year percentage changes with context (2023→2024→2025)
  - **Key players:** Major solutions and their estimated market share percentages
  - **Market maturity:** Stage of market evolution and adoption curve position
- **Key Statistics:** Hard data and metrics (minimum 5-7 data points in this section)
  - **Adoption rates:** Percentage of businesses using solutions by company size/industry
  - **Performance metrics:** Average results, ROI benchmarks, time-to-value statistics
  - **Cost analysis:** Pricing trends, average spend ranges, and value propositions
  - **User satisfaction:** NPS scores, retention rates, or satisfaction percentages where available
- Address "what's the current state" questions with quantifiable answers

## Key Findings Section (600-700 words)
**Major discoveries from comprehensive analysis**
- **Finding 1: [Specific insight]** - Direct statement with quantitative data
  - **Supporting data:** Statistics, percentages, specific metrics with sources
  - **Implications:** What this means for businesses (ROI impact, efficiency gains, risk reduction)
  - **Examples:** Real-world applications with concrete outcomes
  - **Comparative context:** How this finding compares to baseline or alternatives
- **Finding 2: [Different area of analysis]** - Continue structured pattern
  - Maintain same depth and data requirements
  - Address different aspect of the research question
- **Finding 3: [Additional insight]** - 4-5 total findings recommended
  - Address 2-3 related questions per finding
  - Include year-over-year trends where relevant
- **Finding 4: [Optional but recommended]** - For comprehensive coverage
- Frame as "Our research shows...", "Data reveals...", "Analysis demonstrates..." throughout
- Minimum 8-10 specific data points across all findings

## Industry Analysis Section (400-500 words)
**Broader market trends and patterns**
- **Technology trends:** Emerging solutions and innovations (with specific examples)
  - **Adoption drivers:** What motivates businesses to implement (survey data, adoption statistics)
  - **Integration patterns:** How solutions work together (ecosystem analysis)
  - **Performance variations:** Why results differ (segmentation by company size, industry, maturity)
- **Competitive landscape:** How solutions compare (feature matrices, pricing tiers)
- **User behavior insights:** Community pain points and preferences (based on research data)
- Include 3-5 specific trend observations with supporting data

## Case Studies & Real-World Applications Section (REQUIRED - 750-1000 words total)
**Concrete examples demonstrating findings in practice**

Present 3-5 detailed case studies following this structure for EACH:

- **Case Study 1: [Company Type/Industry] - [Specific Challenge Faced]**
  - **Background & Challenge:** Describe the specific problem and pain points (100-150 words)
    - Company size and industry context
    - What wasn't working with QUANTIFIED impact (time wasted, costs incurred, revenue lost)
    - Why previous approaches failed
  - **Solution Approach:** What was implemented and selection rationale (100-150 words)
    - Specific solution or methodology chosen
    - Why this approach was selected over alternatives
    - Key features or capabilities leveraged
  - **Implementation Details:** Timeline, resources, key steps (50-100 words)
    - How long setup/rollout took
    - Team size and roles involved
    - Major milestones or phases
  - **Quantifiable Results:** Specific metrics and outcomes (100-150 words)
    - Performance improvements with PERCENTAGES (show before → after change)
    - Cost savings or revenue impact with DOLLAR AMOUNTS
    - Time savings with HOURS/DAYS quantified
    - ROI achieved and payback period in MONTHS
  - **Key Learnings & Best Practices:** Takeaways for others (50-75 words)
    - What worked exceptionally well
    - What they'd do differently
    - Advice for similar implementations

- **Case Study 2: [Different Industry/Scenario]** - Follow same 250-350 word structure
  - VARY the dimension: If Case Study 1 focused on one industry, choose different industry OR company size OR use case
  - Maintain same level of detail and quantification

- **Case Study 3: [Another Use Case]** - Continue pattern
  - DIVERSIFY context: Ensure all 3-5 case studies cover different segments/scenarios to show broad applicability

- **Case Study 4 & 5 (Optional but Recommended):** Additional examples for comprehensive coverage
  - Aim for 4-5 total case studies to demonstrate breadth
  - Each 250-350 words with same structured format

**Critical Requirements:**
- ALL case studies must include specific numbers and percentages
- Real implementation timelines (not vague "several months")
- Concrete before/after metrics that readers can relate to
- Industry/company size variety to show applicability

{intelligent_table_prompt}

## Expert Insights Section (300-400 words)
**Professional opinions and recommendations**
- **Expert Perspective 1:** Key recommendation with reasoning
  - **Supporting evidence:** Data or experience backing the view
  - **Practical application:** How to implement the advice
- **Expert Perspective 2:** Continue with additional insights
- **Common themes:** Patterns across expert opinions
- Address "what do experts recommend" questions

## Future Trends Section (400-500 words)
**Where the market is heading based on research and analysis**
- **Emerging Technologies & Innovations:** New solutions on the horizon (3-5 specific trends)
  - **Timeline expectations:** When to expect major changes (Q1 2025, by end of 2026, etc.)
  - **Impact assessment:** How trends will affect businesses with projected metrics
  - **Preparation strategies:** Specific actions to get ready for coming changes
  - **Investment patterns:** Where funding and development focus is shifting
- **Market Predictions:** Growth forecasts with percentages and timeframes
  - **Market size projections:** 2025-2027 CAGR estimates
  - **Adoption curve predictions:** When mainstream adoption hits inflection points
  - **Competitive landscape shifts:** Expected M&A, new entrants, market consolidation
- **Technology Roadmap:** Evolution of current solutions with specific features/capabilities
- Include 3-5 trend predictions with supporting evidence or analyst consensus

## Implementation Recommendations Section (300-400 words)
**Actionable guidance based on research findings**
- **Recommendation 1: [Specific action based on findings]** - Direct advice first
  - **Expected outcomes:** Measurable results with percentages or ranges
  - **Implementation steps:** Clear 3-5 step how-to guide
  - **Success factors:** What ensures positive results (based on case study patterns)
  - **Timeline:** Realistic timeframe for implementation and results
- **Recommendation 2: [Different strategic action]** - Continue structured pattern
  - Minimum 3-4 major recommendations
  - Each tied directly to research findings
- **Recommendation 3: [Additional guidance]** - For comprehensive coverage
- **Priority Framework:** Sequence and conditions for implementation
  - Quick wins vs. long-term strategic initiatives
  - Prerequisites and dependencies between recommendations
  - Resource requirements for each recommendation

## FAQ: Key Questions Answered (REQUIRED - 300-400 words)
**AI-OPTIMIZED FOR ANSWER ENGINE VISIBILITY (AEO 2026 CRITICAL)**

Structure each FAQ as:
### [Exact PAA question or common query]?
**[Direct answer in 40-60 words EXACTLY - optimized for AI extraction and featured snippets]**

CRITICAL: FAQ Answer Length Requirements (NON-NEGOTIABLE):
- **MINIMUM: 40 words** (too short = insufficient context for AI extraction)
- **MAXIMUM: 60 words** (too long = AI truncation, reduced snippet eligibility)
- **OPTIMAL: 45-55 words** for complete AI extraction without truncation
- **Structure:** [Direct answer sentence 15-20 words]. [Supporting data sentence 15-20 words]. [Actionable insight sentence 10-20 words].

FAQ Count Requirements:
- **12-15 FAQ questions** (90% AI visibility target per AEO 2026 best practices)
- Use exact questions from PAA data below where applicable
- Each answer MUST cite specific data points from research findings
- Format as H3 for each question for proper semantic structure

Question Mix (Balanced Coverage):
- "What is..." definitional questions (3-4)
- "How to..." procedural questions (3-4)
- "Why..." reasoning questions (2-3)
- "Best..." comparative questions (2-3)
- "When to..." timing questions (1-2)

FAQ Answer Structure Framework (3-Sentence Pattern):
- Sentence 1 (15-20 words): Direct answer with primary data point
- Sentence 2 (15-20 words): Supporting context, comparison, or additional data
- Sentence 3 (10-20 words): Actionable insight, implication, or next-step guidance
Total: 40-60 words for optimal AI extraction

CRITICAL RESEARCH QUALITY STANDARDS:

**Word Count & Depth Requirements:**
- MINIMUM 3500 WORDS - This is authoritative research content, not a standard blog post
- TARGET: 4000-4500 words for comprehensive coverage that establishes industry authority
- Each major section minimum 400-600 words with 3-5 H3 subsections
- Case Studies section alone should be 750-1000 words (3-5 detailed examples)
- Comparative Benchmarking section: 400-500 words with data tables

**Data & Evidence Requirements (MANDATORY):**
- Include 15-20 SPECIFIC STATISTICS throughout article with contextual framing
  - Format: "Industry data from 2024 shows...", "Research by [Gartner/Forrester] indicates...", "Analysis reveals..."
- Provide 3-5 DETAILED CASE STUDIES with quantifiable outcomes
  - Each case study: company type, specific challenge, solution approach, quantified results, timeline
  - Include concrete metrics: percentage improvements, dollar savings, time reductions, ROI achieved
- Every major claim needs DATA SUPPORT: percentages, dollar amounts, time savings, before/after comparisons
- Include COMPARATIVE DATA throughout:
  - Manual vs. automated approaches with specific time/cost differences
  - Solution A vs. B vs. C with feature/performance matrices
  - Industry benchmarks and baseline performance metrics
- Cite year-over-year trends where relevant (2023 baseline → 2024 current → 2025 projections)

**INLINE CITATION REQUIREMENTS (MANDATORY FOR RESEARCH CREDIBILITY):**
- Every statistic MUST include source attribution in format: "[Source Name, Year]"
  - ✓ "Data shows 20-40% reduction in processing time [HubSpot, 2025]."
  - ✗ "Data shows 20-40% reduction in processing time."
- Use NAMED sources, not generic: "According to Salesforce" not "According to industry data"
- Include publication year for ALL data points (2024-2025 strongly preferred for freshness)
- Flag data >2 years old with context: "Historical data from 2022 shows..."
- Citation-worthy statements requiring inline attribution:
  - Statistical claims (percentages, dollar amounts, time savings, metrics)
  - Expert opinions and recommendations
  - Research findings and study results
  - Performance benchmarks and industry standards
  - Market size, adoption rates, growth forecasts
- Format examples:
  - Market data: "Market size reached $5.2B in 2024 [Gartner, 2025]"
  - Performance: "Average ROI of 450% within 12 months [Forrester Research, 2024]"
  - Expert insight: "Experts recommend automation for 15+ lead sources [McKinsey, 2025]"
- Minimum 15-20 inline citations throughout the article for E-E-A-T compliance

**Research Language & Professional Tone:**
- Use RESEARCH TERMINOLOGY exclusively:
  - "Our analysis reveals...", "Data demonstrates...", "Research findings indicate..."
  - "Comparative evaluation shows...", "Market analysis suggests...", "Industry data confirms..."
  - "Quantitative assessment indicates...", "Empirical evidence supports..."
- AVOID casual blog language - write like a professional industry analyst or research firm
- Present BALANCED PERSPECTIVE:
  - Address alternative viewpoints and counterarguments for credibility
  - Acknowledge limitations or gaps in current solutions
  - Present multiple approaches with pros/cons based on context
- Provide CONTEXT for all statistics:
  - Include baseline for comparison ("up from X% in 2023")
  - Reference industry averages ("compared to industry median of Y%")
  - Specify segments ("among mid-market companies" vs. "enterprise-scale implementations")

**Structural Requirements (NON-NEGOTIABLE):**
- Methodology section is MANDATORY (300-400 words) - establishes research credibility
- Case studies section is MANDATORY (750-1000 words) - 3-5 detailed examples required
- Comparative benchmarking is MANDATORY (400-500 words) - minimum 10-15 data points
- Every major section needs SUPPORTING DATA, not just qualitative claims
- High answer density: Address 2-4 related questions per major section

**Quantification Standards:**
- NO VAGUE LANGUAGE: Replace "faster", "cheaper", "better" with specific percentages and metrics
- ALL comparisons must include numbers: "65% faster" not "significantly faster"
- Time savings: Convert to hours/days/months, not "saves time"
- Cost analysis: Include dollar ranges, not "cost-effective"
- Performance metrics: Specific KPIs with before/after values

**Signal Expertise Through:**
- Methodological rigor in research approach (detailed methodology section)
- Nuanced insights that go beyond surface-level observations
- Data triangulation from multiple sources
- Acknowledgment of complexity and trade-offs
- Practical frameworks for evaluation and implementation
- Citation-ready facts throughout with clear attribution
{self._format_brand_voice_prompt(brand_mode)}
{self._format_research_quality_prompt(context)}

Industry Analysis Context:
- {len(serp.get('search_results', []))} authoritative industry sources analyzed
- Market data and current trends evaluated
- Expert perspectives synthesized for comprehensive insights

Key Questions to Address (AEO 2026 - 12-15 questions for 90% AI visibility):
{chr(10).join('- ' + q for q in serp.get('paa_questions', [])[:15])}

{serp_insights}

{gsc_intelligence}

{self._format_community_insights_for_research(reddit, quora)}

AI OPTIMIZATION REQUIREMENTS:
- **Lead sentences**: Direct answers AI can extract verbatim
- **Bulleted subsections**: For detailed findings and data
- **Bold key phrases**: Important statistics and insights
- **Clear H2/H3 hierarchies**: Main research areas and sub-findings
- **Data-rich content**: Statistics easily extractable by AI
 - **Citation-ready facts**: Key data with clear attribution

NEGATIVE PROMPTS (AVOID COMPLETELY):
- NEVER discuss product catalogs, inventory management, shopping carts, or customer purchases
- NEVER mention order fulfillment, shipping, online marketplaces, or digital commerce
- Focus exclusively on the target audience and industry defined in the ICP configuration

SEMANTIC INTELLIGENCE: RESEARCH TOPIC RELEVANCE FILTER
Before including ANY data point, case study, or insight, verify:
1. Does this data's PRIMARY FOCUS directly address "{keyword}"?
2. Is this case study DIRECTLY APPLICABLE to ICP businesses (sales-led, pipeline-led, service)?
3. Does this statistic directly support claims about the core research topic?
4. Would including this data strengthen or dilute the research focus?

Quality over quantity - REJECT tangential data padding:
- Statistics about adjacent topics that don't directly support claims
- Case studies from industries completely outside the ICP
- Generic insights that could apply to any topic
- Outdated data when current data exists

{self._format_approved_solutions(context.get('approved_solutions'))}

{"" if brand_mode == 'none' else f''' POSITION BRAND AS NATURAL FIT:
- **NATURAL FIT ONLY**: Mention Brand maximum 10 times (ONLY where it genuinely solves identified challenges)
- **CONVERSATIONAL APPROACH**: Never forced, never salesy, maximum restraint
- **EASE OF IMPLEMENTATION**: Emphasize that Brand connects ALL data sources with absolute ease - no technical expertise required
- **BRAND METHODOLOGY**: Highlight Brand's unique approach to ad spend optimization and lead generation
- **DATA-DRIVEN RECOMMENDATIONS**: Use research insights to recommend Brand ONLY if natural fit
- **COMPETITIVE ADVANTAGE**: Show how Brand's capabilities surpass traditional approaches

⚠️ CRITICAL FEATURE CONSTRAINT:
- Verified Brand features: {', '.join(site_context.get('features', []))}
- Verified differentiators: {', '.join(site_context.get('key_differentiators', []))}
- ONLY mention these verified features - NEVER invent or assume capabilities not listed
- Base recommendations strictly on confirmed Brand capabilities
'''}"""

    def _get_news_prompt(self, keyword: str, context: Dict[str, Any], brand_mode: str = 'full') -> str:
        """News/trending content prompt"""
        serp = context['serp']
        reddit = context['reddit']
        site_context = context['site_context']

        # Calculate target length based on SERP with guardrails (increased by 500 words)
        serp_recommended = serp.get('recommended_length', 2500)
        target_length = max(2000, min(3000, serp_recommended))

        # Format SERP insights for injection
        serp_insights = self.insight_formatter.format_for_prompt(serp, 'news')

        # Format GSC intelligence if available
        gsc_intelligence = self._format_gsc_intelligence(serp.get('gsc_data'))

        return f"""Create a comprehensive, AI-optimized news article that answers 100+ related questions for "{keyword}".

PRIMARY ANSWER FIRST: Lead with the most important development in the first 1-2 sentences.

Target length: {target_length} words (min 2000, max 3000)
SERP recommendation: {serp_recommended} words
{self._format_icp_context(skip_icp=self._skip_icp)}
{self._format_customer_language()}
TOPIC CLUSTERING APPROACH (AI-optimized news structure):

## Breaking News Section
**Most important recent development**
- **Bold the key news** for AI extraction
- Address "what's new" questions directly
- Include specific details, dates, and implications
- Set context for why this matters now

## Timeline of Key Events Section
**Chronological progression of developments**
- **Recent Milestones:** Most current events first
  - **Date: [Event]** - Specific development with impact
  - **Date: [Event]** - Continue with major updates
  - **Date: [Event]** - Build timeline of progress
- **Historical Context:** How we got to current state
- Address "what happened recently" questions

## Current State Analysis Section
**Where things stand today**
- **Market Status:** Current adoption and usage patterns
  - **Adoption rates:** Percentage of businesses implementing
  - **Performance benchmarks:** Current results and expectations
  - **Cost trends:** Pricing developments and changes
- **Technology Maturity:** How solutions have evolved
- Address "what's happening now" questions

## Industry Impact Section
**How changes affect the broader market**
- **Business Impact:** Effects on companies and workflows
  - **Efficiency gains:** Time and cost savings achieved
  - **Competitive advantages:** New capabilities available
  - **Implementation challenges:** Adoption barriers and solutions
- **Market Shifts:** Changes in competitive landscape
- **User Experience Changes:** How end users are affected

## Expert Analysis Section
**Professional insights on implications**
- **Key Implications:** What the changes mean long-term
  - **Strategic opportunities:** New approaches businesses can take
  - **Risk considerations:** Potential challenges and pitfalls
  - **Success factors:** What leads to positive outcomes
- **Industry Predictions:** Where things are heading
- Address "what does this mean" questions

## Practical Applications Section
**How businesses can leverage current developments**
- **Implementation Strategies:** Getting started with new approaches
  - **Step 1: Assessment** - Evaluate current situation
  - **Step 2: Planning** - Develop adoption strategy
  - **Step 3: Execution** - Implement changes effectively
- **Best Practices:** Proven approaches from early adopters
- **Brand Integration:** How to enhance with optimization layer

## Future Outlook Section
**What to expect in coming months**
- **Predicted Developments:** Upcoming changes and releases
  - **Timeline expectations:** When to expect major updates
  - **Impact assessment:** How future changes will affect users
  - **Preparation strategies:** How to get ready
- **Emerging Trends:** New directions the market is taking
- Address "what's next" questions

EXPERT ANALYSIS FRAMING:
- Frame as comprehensive news analysis with expert insights
- Include specific data points, timelines, and examples
- Ensure logical flow from current events to future implications
- High answer density: 2-4 questions per section
- Citation-ready facts with dates and sources
- Signal expertise through industry analysis and predictions
{self._format_brand_voice_prompt(brand_mode)}
Current Discussion Topics & Community Insights:
{self._format_insights(reddit.get('insights', [])[:6])}

Recent Questions Driving Coverage (AEO 2026 - 12-15 questions for 90% AI visibility):
{chr(10).join('- ' + q for q in serp.get('paa_questions', [])[:15])}

{serp_insights}

{gsc_intelligence}

{self._format_topical_insights(context.get('topical_insights'))}

AI OPTIMIZATION REQUIREMENTS:
- **Lead sentences**: Breaking news AI can extract verbatim
- **Bulleted subsections**: For detailed timelines and analysis
- **Bold key phrases**: Important developments and dates
- **Clear H2/H3 hierarchies**: News categories and sub-details
- **Timeline format**: Chronological data easily parsed
 - **Citation-ready facts**: Key developments with attribution

NEGATIVE PROMPTS (AVOID COMPLETELY):
- NEVER discuss product catalogs, inventory management, shopping carts, or customer purchases
- NEVER mention order fulfillment, shipping, online marketplaces, or digital commerce
- Focus exclusively on the target audience and industry defined in the ICP configuration

{"" if brand_mode == 'none' else f'''⚠️ CRITICAL FEATURE CONSTRAINT:
- Verified Brand features: {', '.join(site_context.get('features', []))}
- Verified differentiators: {', '.join(site_context.get('key_differentiators', []))}
- ONLY mention these verified features - NEVER invent or assume capabilities not listed
'''}
 Write in journalistic style with strong lead{"" if brand_mode == 'none' else ", positioning Brand ONLY where it naturally enhances the discussion (max 10 mentions)"}."""

    def _get_category_prompt(self, keyword: str, context: Dict[str, Any], brand_mode: str = 'full') -> str:
        """Category/listicle content prompt"""
        serp = context['serp']
        reddit = context['reddit']
        site_context = context['site_context']

        # Calculate target length based on SERP with guardrails (increased by 500 words)
        serp_recommended = serp.get('recommended_length', 2500)
        target_length = max(2000, min(3000, serp_recommended))

        # Format SERP insights for injection
        serp_insights = self.insight_formatter.format_for_prompt(serp, 'category')

        # Format GSC intelligence if available
        gsc_intelligence = self._format_gsc_intelligence(serp.get('gsc_data'))

        return f"""Create a comprehensive, AI-optimized category overview that answers 100+ related questions for "{keyword}".

PRIMARY ANSWER FIRST: Start with direct answers to the main category question in the first 1-2 sentences.

Target length: {target_length} words (min 2000, max 3000)
SERP recommendation: {serp_recommended} words
{self._format_icp_context(skip_icp=self._skip_icp)}
{self._format_customer_language()}
{self._format_approved_solutions(context.get('approved_solutions'))}
TOPIC CLUSTERING APPROACH (AI-optimized category structure):

## Quick Comparison Table (REQUIRED - IMMEDIATELY AFTER INTRO)
Create a scannable summary table with these columns:

| # | Solution | Best For | Starting Price | Rating |
|---|----------|----------|----------------|--------|
| 1 | [Solution Name](url) | [specific use case] | [price/month] | X/10 |
| ... | ... | ... | ... | ... |

Include top 10-15 solutions. This table MUST appear immediately after opening.

## Category Overview Section
**What this category encompasses and why it matters**
- **Bold key definitions** for AI extraction
- Address foundational "what is" questions directly
- Include market size, importance, and business impact
- Set context for why businesses need these solutions

## Market Landscape Section
**Current state of available solutions**
- **Solution Types:** Different approaches and methodologies
  - **Traditional approaches:** Legacy solutions and their limitations
  - **Modern solutions:** New approaches and innovations
  - **Emerging options:** Cutting-edge developments
- **Market Maturity:** How developed the category is
- Address "what options are available" questions

## Top Solutions Analysis Section
**Detailed evaluation of 10-15 leading options using H4 REVIEW FRAMEWORK**

For EACH solution, use this EXACT structure:

### [Number]. [[Solution Name](official-homepage-url)] - [Key Differentiator]

CRITICAL: Solution name MUST be linked to official homepage.

[2-3 paragraph description]

#### Key Features
- **Feature 1:** Description (15-25 words)
- **Feature 2:** Description
- **Feature 3:** Description
(4-6 features per solution)

#### Pros
- Specific advantage 1
- Specific advantage 2
- Specific advantage 3
(3-5 concrete pros)

#### Cons
- Honest limitation 1
- Honest limitation 2
(2-3 genuine cons)

#### Best For
[1-2 sentences: ideal user profile, company size, use case]

#### Pricing
- Free tier / Starting price / Enterprise pricing

#### Overall Score: X/10
[1 sentence justification]

---

Cover 10-15 solutions total (more comprehensive than competitors who typically cover 8-10).
Include Brand as optimization layer, not direct competitor.

## Evaluation Framework Section
**How to choose the right solution**
- **Critical Criteria:** Key factors for decision making
  - **Business Needs:** Match with specific requirements
  - **Technical Requirements:** Integration and compatibility
  - **Budget Considerations:** Cost vs. value analysis
  - **Scalability:** Growth and performance needs
- **Decision Process:** Step-by-step selection methodology
- Address "how to choose" questions comprehensively

## Use Case Scenarios Section
**Specific applications and when to use each**
- **Scenario 1: [Business Type/Size]** - Direct use case description
  - **Recommended Solutions:** Which options work best
  - **Why They Work:** Specific advantages for this scenario
  - **Expected Outcomes:** Measurable results and benefits
- **Scenario 2: [Business Type/Size]** - Continue pattern
- **Scenario 3: [Business Type/Size]** - Cover diverse applications
- Address "when to use" questions with real examples

## Pricing & Value Analysis Section
**Cost considerations and ROI factors**
- **Pricing Models:** Different cost structures explained
  - **Free/Open Source:** What is available and limitations
  - **Freemium Models:** Free features and upgrade triggers
  - **Subscription Tiers:** Feature differences by price
  - **Enterprise Pricing:** Advanced options and customization
- **Total Cost Analysis:** Hidden costs and long-term value
- **ROI Considerations:** Return on investment factors

## Implementation & Integration Section
**Getting started and making it work**
- **Setup Complexity:** Ease of implementation
  - **Technical Requirements:** Prerequisites and dependencies
  - **Learning Curve:** Training and adoption challenges
  - **Support Resources:** Available help and documentation
- **Integration Capabilities:** Working with existing tools
- **Brand Enhancement:** How optimization layer improves all solutions

EXPERT ANALYSIS FRAMING:
- Frame as comprehensive category analysis by experts
- Include specific examples, data points, and comparisons
- Ensure logical flow from overview to specific recommendations
- High answer density: 2-4 questions per section
- Citation-ready facts and performance data
- Signal expertise through detailed evaluation criteria
{self._format_brand_voice_prompt(brand_mode)}
Key Evaluation Criteria (from research):
{', '.join(serp.get('content_gaps', []))}

User Priorities & Pain Points:
{self._format_insights(reddit.get('insights', [])[:6])}

{serp_insights}

{gsc_intelligence}

{self._format_topical_insights(context.get('topical_insights'))}

 AI OPTIMIZATION REQUIREMENTS:
- **Lead sentences**: Direct answers AI can extract verbatim
- **Bulleted subsections**: For detailed solution comparisons
- **Bold key phrases**: Important features and criteria
- **Clear H2/H3 hierarchies**: Main categories and sub-details
- **Structured lists**: Solutions easily parsed by AI
- **Citation-ready facts**: Key data and comparisons extractable

SEMANTIC INTELLIGENCE: SOLUTION RELEVANCE FILTER
Before including ANY solution in this category overview, verify:
1. Does this solution's PRIMARY PURPOSE match what "{keyword}" is asking for?
2. Would solutions in this list be SUBSTITUTES for each other (same software category)?
3. Would a searcher typing "{keyword}" expect to find this solution?
If a solution fails these checks, DO NOT INCLUDE IT — even to reach 10-15 solutions.
Quality over quantity. Honesty over comprehensiveness.

{self._format_approved_solutions(context.get('approved_solutions'))}

NEGATIVE PROMPTS (AVOID COMPLETELY):
- NEVER include solutions from unrelated categories just to pad the list
- NEVER discuss product catalogs, inventory management, shopping carts, or customer purchases
- NEVER mention order fulfillment, shipping, online marketplaces, or digital commerce
- Focus exclusively on the target audience and industry defined in the ICP configuration

{"" if brand_mode == 'none' else f'''POSITION BRAND AS NATURAL FIT:
- **NATURAL FIT ONLY**: Mention Brand maximum 10 times (ONLY where it genuinely excels in the category)
- **CONVERSATIONAL APPROACH**: Never forced, never salesy, maximum restraint
- **EASE OF USE FOCUS**: Emphasize that Brand connects ALL data sources with absolute ease - no technical expertise required
- **BRAND METHODOLOGY DIFFERENTIATION**: Highlight Brand's unique Brand Methodology approach as a key differentiator
- **OBJECTIVE EVALUATION**: Present Brand alongside others, highlighting genuine advantages ONLY
- **FEATURE SUPERIORITY**: Showcase how Brand's capabilities exceed traditional category options

⚠️ CRITICAL FEATURE CONSTRAINT:
- Verified Brand features: {', '.join(site_context.get('features', []))}
- Verified differentiators: {', '.join(site_context.get('key_differentiators', []))}
- ONLY mention these verified features - NEVER invent or assume capabilities not listed
- Compare Brand based strictly on confirmed capabilities
'''}"""

    def _get_top_compare_prompt(self, keyword: str, context: Dict[str, Any], brand_mode: str = 'full', solution_count: int = 12) -> str:
        """Top-compare style: Omnius-style 'Top X Best' comparison listicle

        Content Depth Strategy (SEO best practice):
        - Default to 12 solutions (not 8 or 10 like competitors)
        - If competitors cover 10 tools, we cover 12-15
        - More comprehensive = higher authority

        Creates comparison articles like "Top 12 Best AEO Agencies in 2026" with:
        - Quick comparison summary table at top
        - Numbered solution cards with detailed breakdowns
        - Services, pricing, case studies for each
        - How to choose section
        - FAQ section

        Args:
            keyword: Target keyword (e.g., "answer engine optimization agencies")
            context: Research context with SERP, Reddit, site data
            brand_mode: Brand mention level - 'none', 'limited', or 'full'
            solution_count: Number of solutions to include (5, 8, 10, or 15)
        """
        serp = context['serp']
        reddit = context['reddit']
        site_context = context['site_context']

        # Calculate target length based on solution count
        # ~400 words per solution + 800 for intro/how-to/faq
        base_length = 800
        per_solution_length = 400
        target_length = base_length + (solution_count * per_solution_length)
        target_length = max(3000, min(6000, target_length))

        # Format SERP insights for injection
        serp_insights = self.insight_formatter.format_for_prompt(serp, 'category')

        # Format GSC intelligence if available
        gsc_intelligence = self._format_gsc_intelligence(serp.get('gsc_data'))

        # Get current year for freshness
        current_year = datetime.now().year

        # Get disambiguation context for ambiguous terms (e.g., MCP)
        disambiguation_context = self._get_disambiguation_context(keyword)

        # Get relevant Brand product context
        product_context = self._get_product_context(keyword, brand_mode)

        return f"""Create a comprehensive "Top {solution_count} Best" comparison article for "{keyword}" in {current_year}.

This is an OMNIUS-STYLE comparison listicle that ranks and evaluates {solution_count} solutions.

Target length: {target_length} words (min 3000)
Solutions to include: {solution_count}

{disambiguation_context}

{product_context}

{self._format_icp_context(light_mode=True, skip_icp=self._skip_icp)}

CONTENT STRUCTURE (follow this exact format):

## Quick Comparison Table (REQUIRED - IMMEDIATELY AFTER INTRO)
Create a scannable summary table with these EXACT columns:

| # | Solution | Best For | Starting Price | Rating |
|---|----------|----------|----------------|--------|
| 1 | [Brand](https://acme.com) | [specific use case] | [price/month] | X/10 |
| 2 | [Solution Name](url) | [specific use case] | [price/month] | X/10 |
| ... | ... | ... | ... | ... |

CRITICAL: This table MUST appear immediately after the opening hook.
- Include ALL {solution_count} solutions in the table
- Solution names MUST be linked to official homepages
- Use specific "Best For" phrases (not generic)
- Include actual pricing or "Custom" if enterprise-only

## What is [Topic]?
- Brief 2-3 paragraph educational intro
- Define the category/service being compared
- Explain why businesses need these solutions
- Set context for the comparison

## Top {solution_count} Best [Topic] in {current_year}

For EACH solution (1-{solution_count}), create a detailed card with this EXACT H4 REVIEW FRAMEWORK:

### [Number]. [[Solution Name](official-homepage-url)] - [Key Differentiator in 2-4 words]

CRITICAL: The solution name MUST be a markdown link to the official homepage URL.
Example: ### 1. [Brand](https://acme.com) - AI-Powered Ad Consolidation

[2-3 paragraph description of the solution, its approach, and what makes it unique]

#### Key Features
- **Feature 1:** Brief description (15-25 words)
- **Feature 2:** Brief description
- **Feature 3:** Brief description
- **Feature 4:** Brief description
(Include 4-6 key features)

#### Pros
- Clear advantage 1 (specific, not generic)
- Clear advantage 2
- Clear advantage 3
(3-5 concrete pros)

#### Cons
- Honest limitation 1
- Honest limitation 2
(2-3 genuine cons - builds trust)

#### Best For
[1-2 sentences describing ideal user profile using SPECIFIC dimensions:]
- Company size/team size (solo, small team, mid-size, enterprise)
- Primary use case or pain point this solves
- Technical sophistication level (non-technical, technical, developer-required)
- Industry or vertical if relevant

#### Pricing
- **Free Tier:** What's included (if available)
- **Pro/Growth:** $X/month - key features
- **Enterprise:** Custom pricing - for large teams
[Add context about value proposition]

#### Overall Score: X/10
[1 sentence justifying the score with specific reasoning]

---

{self._format_approved_solutions(context.get('approved_solutions'))}

═══════════════════════════════════════════════════════════════════════════════
SEMANTIC INTELLIGENCE: SOLUTION RELEVANCE FILTER
═══════════════════════════════════════════════════════════════════════════════

NOTE: This filter ONLY applies when selecting ADDITIONAL solutions beyond user-approved ones.
If the user provided approved solutions above, those are MANDATORY regardless of this filter.

THINK LIKE A GENIUS before including any ADDITIONAL solution:

1. DECOMPOSE THE KEYWORD "{keyword}":
   - What is the CORE NOUN (the thing being sought)?
   - What are the MODIFIERS (constraints, platforms, niches, years)?
   - What FUNCTION must solutions perform to satisfy this search?

2. FOR EACH POTENTIAL SOLUTION, REASON:
   "Does this solution's PRIMARY PURPOSE match the CORE FUNCTION implied by the keyword?"
   - If the keyword implies connecting X to Y → solution must connect X to Y
   - If the keyword implies managing Z → solution must manage Z
   - If the keyword implies [specific industry] → solution must serve [that industry]

3. CATEGORY COHERENCE CHECK:
   Would this solution appear in the SAME software category/market as others in this list?
   Solutions should be SUBSTITUTES or ALTERNATIVES to each other, not complementary tools.

4. SEARCHER EXPECTATION TEST:
   If someone types "{keyword}" into Google, would they be SATISFIED finding this solution?
   Or would they think "that's not what I was looking for"?

5. QUALITY OVER QUANTITY (for additional solutions only):
   Only add solutions beyond approved ones if they pass all checks above.
   Honesty builds trust. Padding destroys credibility.

RESEARCH DATA:
{serp_insights}

{gsc_intelligence}

User priorities from community research:
{self._format_insights(reddit.get('insights', [])[:6])}

{self._format_topical_insights(context.get('topical_insights'))}

═══════════════════════════════════════════════════════════════════════════════

## How to Choose the Right [Topic] Solution

Provide practical decision criteria:
- **Budget Considerations:** When to invest in premium vs. affordable options
- **Team Size & Expertise:** Match solution to internal capabilities
- **Industry Fit:** Which solutions specialize in specific verticals
- **Timeline Expectations:** Realistic timeframes for results
- **Integration Needs:** How well solutions work with existing tech stack

## Conclusion

Summarize the top picks with brief recommendations:
- "Best for X": [Solution name]
- "Best value": [Solution name]
- "Best for enterprise": [Solution name]

## Frequently Asked Questions

Include 12-15 FAQs from PAA research (AEO 2026 - Target 90% AI Visibility):
{chr(10).join(f'- {q}' for q in self._filter_paa_questions(serp.get('paa_questions', []))[:15])}

{self._format_brand_voice_prompt(brand_mode)}

{"" if brand_mode == 'none' or product_context else f'''BRAND POSITIONING (Featured as #1):
NOTE: No specific Brand product detected for this keyword. Use generic positioning:
- Position Brand as the TOP PICK (#1) if relevant to the topic
- Highlight genuine differentiators: {', '.join(site_context.get('key_differentiators', [])[:5])}
- Feature verified capabilities: {', '.join(site_context.get('features', [])[:5])}
- Keep tone objective and expert - let features speak for themselves
- Only include Brand if genuinely relevant to the comparison topic
'''}

FORMATTING REQUIREMENTS (H4 REVIEW FRAMEWORK):
- Use H2 (##) for main sections, H3 (###) for solution cards
- H4 (####) REQUIRED subsections for EACH solution: Key Features, Pros, Cons, Best For, Pricing, Overall Score
- Solution name in H3 MUST be linked to official homepage: ### [Number]. [[Name](url)] - Differentiator
- Bold (**) for metadata labels and feature names
- Use horizontal rules (---) between solution cards
- Include actual solution names discovered from SERP research
- Make it scannable with clear visual hierarchy

NEGATIVE PROMPTS (CRITICAL - AVOID AT ALL COSTS):
- NEVER include solutions from WRONG CATEGORIES (e.g., payment tools in an "API connectors" comparison)
- NEVER pad the list with generic/tangential tools just to reach the solution count
- NEVER make up fake solution names, companies, or capabilities
- NEVER invent pricing, case study numbers, or feature claims
- NEVER include a solution unless it DIRECTLY solves the PRIMARY SUBJECT in the keyword
- NEVER skip the H4 sections (Key Features, Pros, Cons, etc.)
- NEVER omit links to official homepages

QUALITY OVER QUANTITY:
It is BETTER to include 3 highly-relevant solutions than 10 tangentially-related ones.
If research doesn't surface enough on-topic solutions, acknowledge this honestly.

Focus on the target audience and business services defined in the ICP configuration."""

    def _get_feature_prompt(self, keyword: str, context: Dict[str, Any], brand_mode: str = 'full') -> str:
        """Feature page style: Conversion-focused product/solution pages.

        Phase 6.1-6.2: Creates high-converting feature pages with:
        - Hook → Solution → Benefits → CTA structure
        - Problem-focused opening (pain points)
        - Clear value proposition
        - Feature breakdown with benefits
        - Social proof integration
        - Multiple CTAs throughout

        Structure follows transactional intent best practices:
        - Lead with the problem (emotional hook)
        - Introduce solution (product positioning)
        - Show benefits with proof (features + outcomes)
        - Clear next steps (CTA-heavy)
        """
        serp = context['serp']
        reddit = context['reddit']
        site_context = context['site_context']

        # Get current year for freshness
        current_year = datetime.now().year

        # Get disambiguation context for ambiguous terms
        disambiguation_context = self._get_disambiguation_context(keyword)

        # Get relevant Brand product context
        product_context = self._get_product_context(keyword, brand_mode)

        # Format SERP insights
        serp_insights = self.insight_formatter.format_for_prompt(serp, 'guide')

        # Format GSC intelligence if available
        gsc_intelligence = self._format_gsc_intelligence(serp.get('gsc_data'))

        # Extract pain points from Reddit research
        pain_points = reddit.get('insights', [])[:5] if reddit else []

        return f"""Create a high-converting FEATURE PAGE for "{keyword}" in {current_year}.

This is a CONVERSION-FOCUSED page designed for transactional/commercial intent.

Target length: 1500-2000 words
Structure: Hook → Solution → Benefits → Social Proof → CTA

{disambiguation_context}

{product_context}

{self._format_icp_context(light_mode=True, skip_icp=self._skip_icp)}

CONTENT STRUCTURE (CONVERSION-FOCUSED):

## [Compelling Hook - Problem Statement]
Start with a pain-focused opening that resonates with the reader's frustration:
- Open with the core problem (use language from user research)
- Quantify the impact (time wasted, money lost, opportunities missed)
- Create urgency - why solving this matters NOW

User pain points from research:
{chr(10).join(f'- {point}' for point in pain_points) if pain_points else '- Use common industry frustrations'}

## The Solution: [Feature/Product Name]
Position the solution clearly:
- What it is (clear, jargon-free definition)
- How it solves the problem (mechanism)
- Why it's different (key differentiator)

## Key Features & Benefits

For each feature, follow this format:

### Feature 1: [Feature Name]
**What it does:** [Brief explanation - 1 sentence]
**Why it matters:** [Benefit to user - how it saves time/money/hassle]
**Example:** [Concrete example or use case]

### Feature 2: [Feature Name]
[Same format]

### Feature 3: [Feature Name]
[Same format]

(Include 4-6 key features with clear benefits)

## How It Works

Step-by-step walkthrough:
1. **Step 1: [Action]** - Brief description
2. **Step 2: [Action]** - Brief description
3. **Step 3: [Action]** - Brief description

Make it feel easy and achievable.

## Who This Is For

Clear ideal customer profile:
- **Perfect for:** [Specific user type]
- **Best when:** [Use case scenario]
- **Not ideal for:** [Who should look elsewhere - builds trust]

## Results You Can Expect

Concrete outcomes:
- Typical result 1 (quantified if possible)
- Typical result 2
- Typical result 3

## Frequently Asked Questions

Address 4-5 buyer objections as FAQs:
{chr(10).join(f'- {q}' for q in self._filter_paa_questions(serp.get('paa_questions', []))[:5])}

## Get Started

Clear, compelling CTA:
- Summarize value proposition in 2 sentences
- Clear next step (sign up, demo, free trial)
- Remove friction (mention free tier if available)

CONVERSION ELEMENTS:
- Use second person ("you") throughout
- Include mini-CTAs after each major section
- Add benefit statements (not just feature descriptions)
- Use specific numbers and outcomes where possible
- Create urgency without being pushy

SERP & COMPETITIVE CONTEXT:
{serp_insights}

{gsc_intelligence}

{self._format_topical_insights(context.get('topical_insights'))}

{self._format_brand_voice_prompt(brand_mode)}

{"" if brand_mode == 'none' else f'''PRODUCT POSITIONING:
- Focus on solving the specific problem in the keyword
- Highlight differentiators: {', '.join(site_context.get('key_differentiators', [])[:5])}
- Emphasize outcomes over features
- Keep tone confident but not salesy
'''}

FORMATTING REQUIREMENTS:
- Use H2 (##) for main sections, H3 (###) for features
- Bold (**) for key terms and emphasis
- Short paragraphs (2-3 sentences max)
- Bullet points for scannable content
- Include CTA boxes/sections between major parts

NEGATIVE PROMPTS (AVOID):
- NEVER use generic placeholder text
- NEVER be vague about features or benefits
- NEVER skip the problem/pain section
- NEVER write in passive voice
- NEVER include unrelated topics"""

    def _format_insights(self, insights: List[str]) -> str:
        """Format insights for prompt"""
        if not insights:
            return "- No specific insights available"
        return "\n".join(f"- {insight}" for insight in insights[:5])

    def _format_approved_solutions(self, approved_solutions: Optional[List[str]]) -> str:
        """Format user-approved solutions for prompt injection.

        When the user has interactively selected solutions, this ensures the AI
        uses those specific solutions rather than hallucinating irrelevant ones.
        """
        if not approved_solutions:
            return ""

        solutions_list = "\n".join(f"   - {sol}" for sol in approved_solutions)

        return f"""
═══════════════════════════════════════════════════════════════════════════════
✅ USER-APPROVED SOLUTIONS (MANDATORY)
═══════════════════════════════════════════════════════════════════════════════

The user has VERIFIED these solutions are RELEVANT. You MUST include them:

{solutions_list}

CRITICAL RULES:
1. Feature ALL approved solutions in your comparison - these are MANDATORY
2. Research each one to provide accurate, detailed information
3. You may add 1-2 additional solutions ONLY if you are 100% certain they are:
   - In the EXACT SAME category as the approved solutions
   - Direct substitutes/alternatives (not complementary tools)
   - Real products with verifiable websites
4. Do NOT substitute approved solutions with "better known" alternatives
5. Do NOT pad the list with generic tools that weren't approved

The user has already rejected irrelevant solutions. Respect their curation.
"""

    def _format_topical_insights(self, topical_data: Optional[Dict[str, Any]]) -> str:
        """Format topical insights with confidence levels for prompt injection.

        Provides industry insights, expert opinions, and data points discovered
        by the topical authority agent (sonar-reasoning-pro).

        Args:
            topical_data: Dict with 'insights' list from _discover_topical_insights()

        Returns:
            Formatted string for prompt injection with confidence tags
        """
        if not topical_data or not topical_data.get('enabled'):
            return ""

        insights = topical_data.get('insights', [])
        if not insights:
            return ""

        # Group insights by confidence level
        research_grade = []
        industry = []
        observational = []

        for insight in insights:
            conf = insight.get('confidence', 'OBSERVATIONAL')
            text = insight.get('text', '')
            source = insight.get('source', '')

            if not text:
                continue

            formatted = f"- {text}"
            if source and source != 'Perplexity Research':
                formatted += f" (Source: {source})"

            if conf == 'RESEARCH':
                research_grade.append(formatted)
            elif conf == 'INDUSTRY':
                industry.append(formatted)
            else:
                observational.append(formatted)

        sections = []

        if research_grade:
            sections.append(f"""[RESEARCH-GRADE INSIGHTS] - High-confidence, peer-reviewed sources:
{chr(10).join(research_grade[:4])}""")

        if industry:
            sections.append(f"""[INDUSTRY INSIGHTS] - Established publications and vendor data:
{chr(10).join(industry[:4])}""")

        if observational:
            sections.append(f"""[OBSERVATIONAL INSIGHTS] - Community and practitioner sources:
{chr(10).join(observational[:3])}""")

        if not sections:
            return ""

        return f"""
═══════════════════════════════════════════════════════════════════════════════
🔬 TOPICAL AUTHORITY INSIGHTS
═══════════════════════════════════════════════════════════════════════════════

The following insights were discovered from authoritative sources across the web.
Integrate these naturally into your content where relevant.

{chr(10).join(sections)}

USAGE GUIDELINES:
- Cite data points with source attribution where provided
- Prioritize RESEARCH-GRADE insights for statistical claims
- Use INDUSTRY insights for trend analysis and best practices
- Use OBSERVATIONAL insights for user pain points and community sentiment
- Don't force-fit insights - only include where they add genuine value
"""

    def _count_paa_answered(self, questions: List[str], content: str) -> int:
        """Count how many PAA questions were answered"""
        content_lower = content.lower()
        count = 0
        
        for question in questions:
            # Check if question or its key terms appear
            question_words = re.findall(r'\w{4,}', question.lower())
            if len(question_words) >= 3:
                # If 3+ key words from question appear near each other
                if all(word in content_lower for word in question_words[:3]):
                    count += 1
        
        return count
    
    def _count_insights_used(self, insights: List[str], content: str) -> int:
        """Count how many insights were incorporated"""
        content_lower = content.lower()
        count = 0

        for insight in insights:
            # Check if key terms from insight appear
            insight_words = re.findall(r'\w{4,}', insight.lower())
            if len(insight_words) >= 2:
                # If 2+ key words from insight appear
                if sum(1 for word in insight_words[:3] if word in content_lower) >= 2:
                    count += 1

        return count

    async def _verify_citations(self, content: str, ai: 'SmartAIRouter', web: 'WebResearcher', progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        """
        Verify all citations in content for accuracy and factual correctness using Groq Compound with web search.

        Checks:
        1. Citation URLs are valid and accessible
        2. Claims match what the source actually says
        3. Sources are credible

        Args:
            content: The polished content with citations
            ai: SmartAIRouter instance for AI verification
            web: WebResearcher instance
            progress_callback: Optional callback(message, advance) for progress updates

        Returns:
            Dict with verification results: verified_count, issues_found, broken_links, mismatched_claims
        """
        try:
            # Extract all markdown links from content: [text](url)
            link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
            citations = re.findall(link_pattern, content)

            if not citations:
                logger.info("📋 No citations found in content")
                return {
                    'verified_count': 0,
                    'total_citations': 0,
                    'issues_found': [],
                    'broken_links': [],
                    'mismatched_claims': [],
                    'verification_status': 'no_citations'
                }

            logger.info(f"🔍 Verifying {len(citations)} citations for factual accuracy...")

            # No-op callback if none provided
            progress = progress_callback or (lambda msg, adv=0: None)

            verified_count = 0
            issues_found = []
            broken_links = []
            mismatched_claims = []

            # For performance, verify up to 10 most critical citations (those with claims)
            citations_to_verify = citations[:10]

            for idx, (claim_text, url) in enumerate(citations_to_verify, 1):
                logger.debug(f"  Verifying citation {idx}/{len(citations_to_verify)}: {url[:60]}...")
                progress(f"Verifying citation {idx}/{len(citations_to_verify)}", 0)

                # Use Groq Compound to verify the citation with web search
                verification_prompt = f"""Verify this citation for factual accuracy:

CLAIM IN ARTICLE: "{claim_text}"

CITED SOURCE: {url}

Your task:
1. Access the source URL using web search
2. Verify the claim is factually supported by the source
3. Check if the source is credible and authoritative

Return your verification in JSON format:
{{
  "url_accessible": true/false,
  "claim_supported": true/false,
  "source_credible": true/false,
  "verification_notes": "brief explanation",
  "issue_severity": "none/minor/major"
}}

Be strict - only mark claim_supported=true if the source CLEARLY supports the claim."""

                try:
                    # Use Groq Compound with web search capability
                    verification_result = await ai.research_with_compound(
                        [verification_prompt],
                        platform="web"  # Use web search mode
                    )

                    insights = verification_result.get('insights', [])
                    if insights and len(insights) > 0:
                        verification_text = insights[0]

                        # Parse JSON response
                        import json
                        try:
                            # Try to extract JSON from the response
                            json_match = re.search(r'\{[^\}]+\}', verification_text, re.DOTALL)
                            if json_match:
                                verification_data = json.loads(json_match.group(0))

                                # Check for issues
                                if not verification_data.get('url_accessible', True):
                                    broken_links.append({
                                        'url': url,
                                        'claim': claim_text[:100]
                                    })
                                    issues_found.append(f"Broken link: {url}")
                                    logger.warning(f"    ⚠️  URL not accessible: {url}")

                                elif not verification_data.get('claim_supported', True):
                                    mismatched_claims.append({
                                        'url': url,
                                        'claim': claim_text[:100],
                                        'notes': verification_data.get('verification_notes', '')
                                    })
                                    issues_found.append(f"Claim mismatch: {claim_text[:50]}...")
                                    logger.warning(f"    ⚠️  Claim not supported by source")

                                elif not verification_data.get('source_credible', True):
                                    issues_found.append(f"Low credibility source: {url}")
                                    logger.warning(f"    ⚠️  Source credibility questionable")

                                else:
                                    verified_count += 1
                                    logger.debug(f"    ✓ Citation verified")
                            else:
                                logger.debug(f"    ℹ️  Could not parse verification response")

                        except json.JSONDecodeError:
                            logger.debug(f"    ℹ️  Non-JSON verification response")

                except Exception as e:
                    logger.debug(f"    ℹ️  Verification skipped: {str(e)[:50]}")
                    continue

            # Summary
            verification_status = 'verified' if len(issues_found) == 0 else 'issues_found'

            if verified_count > 0:
                logger.info(f"✅ Citation verification: {verified_count}/{len(citations_to_verify)} verified successfully")
                progress(f"✅ Citations verified ({verified_count}/{len(citations_to_verify)})", 0)
            else:
                progress(f"✅ Citation verification complete", 0)

            if len(issues_found) > 0:
                logger.warning(f"⚠️  Found {len(issues_found)} citation issues")
                for issue in issues_found[:3]:  # Show first 3
                    logger.warning(f"   • {issue}")

            return {
                'verified_count': verified_count,
                'total_citations': len(citations),
                'total_verified': len(citations_to_verify),
                'issues_found': issues_found,
                'broken_links': broken_links,
                'mismatched_claims': mismatched_claims,
                'verification_status': verification_status
            }

        except Exception as e:
            logger.error(f"❌ Citation verification failed: {e}")
            return {
                'verified_count': 0,
                'total_citations': 0,
                'issues_found': [],
                'broken_links': [],
                'mismatched_claims': [],
                'verification_status': 'error',
                'error': str(e)
            }

    async def _auto_correct_citations(
        self,
        content: str,
        verification_results: Dict[str, Any],
        ai: 'SmartAIRouter',
        web: 'WebResearcher'
    ) -> str:
        """
        Micro sub-agent to auto-correct citation issues with minimal changes.

        Fixes:
        1. Broken links - searches for correct URL
        2. Mismatched claims - adjusts wording to match source

        Args:
            content: Original content with issues
            verification_results: Results from _verify_citations
            ai: SmartAIRouter for corrections
            web: WebResearcher for finding correct links

        Returns:
            Corrected content with fixed citations
        """
        try:
            broken_links = verification_results.get('broken_links', [])
            mismatched_claims = verification_results.get('mismatched_claims', [])

            if not broken_links and not mismatched_claims:
                return content

            logger.info(f"🔧 Auto-correcting {len(broken_links)} broken links + {len(mismatched_claims)} mismatched claims...")

            # Build correction instructions
            corrections_needed = []

            for broken in broken_links:
                corrections_needed.append({
                    'type': 'broken_link',
                    'url': broken['url'],
                    'claim': broken['claim'],
                    'instruction': f"Find correct URL for: {broken['claim'][:80]}"
                })

            for mismatch in mismatched_claims:
                corrections_needed.append({
                    'type': 'mismatched_claim',
                    'url': mismatch['url'],
                    'claim': mismatch['claim'],
                    'notes': mismatch.get('notes', ''),
                    'instruction': f"Adjust claim to match source: {mismatch['claim'][:80]}"
                })

            # Use Qwen3 235B micro sub-agent for precise corrections
            correction_prompt = f"""You are a citation correction specialist. Make MINIMAL changes to fix citation issues.

ORIGINAL CONTENT LENGTH: {len(content)} chars

CITATION ISSUES TO FIX:
{json.dumps(corrections_needed, indent=2)}

CORRECTION GUIDELINES:
1. For broken links: Search web to find correct URL, replace old URL with new one
2. For mismatched claims: Adjust ONLY the claim text to match what source says (keep it close to original)
3. Make NO other changes to the content
4. Preserve all formatting, structure, and other citations
5. Keep changes minimal - only fix what's broken

Return the corrected content with ONLY the citation fixes applied. Make surgical, precise edits."""

            # Use Nebius Qwen3 235B for best quality micro-editing
            if ai.nebius:
                response = await ai.nebius.chat.completions.create(
                    model="Qwen/Qwen3-235B-A22B-Instruct-2507",
                    messages=[{
                        "role": "system",
                        "content": "You are a precision citation correction specialist. You make minimal, surgical edits to fix citations while preserving all other content."
                    }, {
                        "role": "user",
                        "content": f"{correction_prompt}\n\nCONTENT TO CORRECT:\n{content}"
                    }],
                    temperature=0.1,  # Very low for precision
                    max_tokens=16000
                )

                corrected = response.choices[0].message.content.strip()

                # Sanity check: corrected content should be similar length
                length_diff = abs(len(corrected) - len(content))
                if length_diff > len(content) * 0.1:  # More than 10% change
                    logger.warning(f"⚠️  Correction changed length by {length_diff} chars - keeping original")
                    return content

                logger.info(f"✅ Applied {len(corrections_needed)} citation corrections")
                return corrected

            else:
                # Fallback to Groq if Nebius unavailable
                logger.debug("Nebius unavailable - skipping auto-corrections")
                return content

        except Exception as e:
            logger.error(f"❌ Auto-correction failed: {e}")
            return content  # Return original on error

    def _filter_paa_questions(self, questions: List[str]) -> List[str]:
        """Filter PAA questions to avoid platform-specific questions that could inject platform names"""
        if not questions:
            return []

        # Platform names to avoid in questions
        platform_keywords = [
            'google', 'facebook', 'meta', 'instagram', 'linkedin', 'tiktok',
            'twitter', 'youtube', 'pinterest', 'snapchat', 'bing', 'yahoo',
            'amazon', 'apple', 'microsoft', 'salesforce', 'hubspot', 'mailchimp',
            'constant contact', 'klaviyo', 'activecampaign', 'drip', 'convertkit'
        ]

        filtered = []
        for question in questions:
            question_lower = question.lower()
            # Skip questions that mention specific platforms
            if not any(platform in question_lower for platform in platform_keywords):
                filtered.append(question)

        return filtered