"""
Intelligent Context Builder - Dynamic ICP context from research extraction.

Replaces hardcoded pain phrases with actual customer language extracted from
Reddit/Quora research. Uses three-tier fallback based on research availability.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntelligentContextBuilder:
    """
    Builds dynamic ICP context by extracting pain language from research.

    Instead of injecting static phrases like "45-60 minutes every morning",
    extracts actual customer language from Reddit/Quora discussions.

    Three-tier fallback:
    - Rich: ≥5 Reddit + ≥3 Quora insights → Use extracted patterns only
    - Partial: 1-4 insights → Extract + minimal business model buckets
    - Minimal: No research → Intent-based defaults (no specific phrases)
    """

    # Regex patterns for extracting pain categories from insight text
    PAIN_PATTERNS = {
        'time_waste': [
            r'\d+\s*(hours?|hrs?|mins?|minutes?)\s*(every|each|per|a)\s*(day|morning|week)',
            r'(every|each)\s+(morning|day|week)\s+\w+\s+(pulling|checking|reconciling)',
            r'(spend|waste|lose)\s+\d+\s*(hours?|mins?)',
            r'(spreadsheet|excel)\s+(hell|nightmare|chaos)',
            r'manual(ly)?\s+(reconcil|match|check|pull)',
        ],
        'money_blindness': [
            r"can'?t\s+(see|tell|know|track)\s+\w*\s*(profit|ROI|ROAS|revenue)",
            r'(no|zero|lack\s+of)\s+(visibility|insight)\s+(into|on)\s+\w*\s*(profit|spend|revenue)',
            r'(flying|going)\s+blind',
            r'(have\s+)?no\s+idea\s+(which|what|if)',
            r"don'?t\s+know\s+(which|what|if)\s+\w+\s+(is\s+)?(profitable|making\s+money|working)",
        ],
        'silo_problems': [
            r'(different|separate|multiple)\s+(system|tool|platform|spreadsheet)s?',
            r'(data\s+)?silo(s|ed)?',
            r"(don'?t|doesn'?t)\s+(talk|connect|sync)\s+(to\s+each\s+other)?",
            r'(disconnect|gap)\s+(between|from)',
            r'(one|this)\s+(system|tool)\s+.{0,20}(another|different)\s+(system|tool)',
        ],
        'blame_game': [
            r'(marketing|sales)\s+(blames?|points?\s+fingers?)',
            r'no\s+(one|body)\s+(knows?|owns?|can\s+prove)',
            r"can'?t\s+prove\s+(anything|it|ROI|results)",
            r'(finger\s+pointing|blame\s+game)',
        ],
        'cash_flow_pain': [
            r'(cash\s+flow|cash\-?flow)\s+(problem|issue|gap|crunch)',
            r'(self[\-\s]?fund|out\s+of\s+pocket)',
            r'\d+[\-\s](day|week)\s+(gap|wait|delay)',
            r"(bank|lender)s?\s+(won'?t|don'?t|refuse)",
            r'(credit\s+limit|line\s+of\s+credit)',
        ],
    }

    def __init__(
        self,
        research_data: Dict[str, Any],
        intent_classification: Dict[str, Any],
        brand_voice: Dict[str, Any],
        minimal_defaults_path: Optional[Path] = None,
    ):
        """
        Initialize context builder with research results.

        Args:
            research_data: Dict with 'reddit', 'quora', 'topical_insights' keys
            intent_classification: Intent classification from classify_keyword_intent()
            brand_voice: Brand voice configuration for guardrails
            minimal_defaults_path: Path to minimal_defaults.json (optional)
        """
        self.reddit = research_data.get('reddit', {})
        self.quora = research_data.get('quora', {})
        self.topical_insights = research_data.get('topical_insights', {})
        self.intent = intent_classification
        self.brand_voice = brand_voice

        # Load minimal defaults for fallback
        if minimal_defaults_path is None:
            minimal_defaults_path = Path(__file__).parent.parent / 'config' / 'minimal_defaults.json'

        try:
            with open(minimal_defaults_path, 'r') as f:
                self.minimal_defaults = json.load(f)
        except FileNotFoundError:
            logger.warning(f"⚠️  minimal_defaults.json not found at {minimal_defaults_path}")
            self.minimal_defaults = self._get_hardcoded_minimal_defaults()

        # Extract patterns on init
        self._extracted_pains = None
        self._extracted_data_points = None
        self._context_tier = None

    def _get_hardcoded_minimal_defaults(self) -> Dict[str, Any]:
        """Fallback minimal defaults if config file not found."""
        return {
            "business_model_buckets": [
                "Sales-led: ad spend → lead capture → sales → close",
                "Pipeline-led: marketing → nurture → convert",
                "Service: enquiry → quote → job → invoice"
            ],
            "tone_anchor": "Write for operators who wear multiple hats"
        }

    def _count_insights(self) -> tuple:
        """Count available insights from research."""
        reddit_count = len(self.reddit.get('insights', []))
        quora_count = len(self.quora.get('expert_insights', []))
        topical_count = len(self.topical_insights.get('insights', []))
        return reddit_count, quora_count, topical_count

    def _determine_context_tier(self) -> str:
        """
        Determine which context tier to use based on research availability.

        Returns:
            'rich': ≥5 Reddit + ≥3 Quora → extracted patterns only
            'partial': 1-4 total insights → extract + minimal business buckets
            'minimal': No research → intent-based defaults only
        """
        if self._context_tier is not None:
            return self._context_tier

        reddit_count, quora_count, topical_count = self._count_insights()
        total_insights = reddit_count + quora_count

        if reddit_count >= 5 and quora_count >= 3:
            self._context_tier = 'rich'
            logger.debug(f"🎯 Context tier: RICH ({reddit_count} Reddit + {quora_count} Quora)")
        elif total_insights >= 1:
            self._context_tier = 'partial'
            logger.debug(f"🎯 Context tier: PARTIAL ({reddit_count} Reddit + {quora_count} Quora)")
        else:
            self._context_tier = 'minimal'
            logger.debug(f"🎯 Context tier: MINIMAL (no community research)")

        return self._context_tier

    def extract_pain_language(self) -> Dict[str, List[str]]:
        """
        Extract actual customer pain phrases from Reddit/Quora research.

        Uses regex patterns to categorize extracted text into pain categories:
        - time_waste: Time spent on manual tasks
        - money_blindness: Lack of visibility into profitability
        - silo_problems: Data fragmentation across systems
        - blame_game: Attribution conflicts between teams
        - cash_flow_pain: Working capital and payment timing issues

        Returns:
            Dict mapping pain category to list of extracted phrases
        """
        if self._extracted_pains is not None:
            return self._extracted_pains

        extracted = {category: [] for category in self.PAIN_PATTERNS.keys()}

        # Collect all insight text
        all_insights = []

        # Reddit insights
        for insight in self.reddit.get('insights', []):
            if isinstance(insight, dict):
                all_insights.append(insight.get('text', insight.get('insight', '')))
            elif isinstance(insight, str):
                all_insights.append(insight)

        # Quora insights
        for insight in self.quora.get('expert_insights', []):
            if isinstance(insight, dict):
                all_insights.append(insight.get('text', insight.get('insight', '')))
            elif isinstance(insight, str):
                all_insights.append(insight)

        # Reddit pain points (if present)
        for pain in self.reddit.get('pain_points', []):
            if isinstance(pain, str):
                all_insights.append(pain)

        # Match patterns against collected text
        for text in all_insights:
            if not text:
                continue
            text_lower = text.lower()

            for category, patterns in self.PAIN_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        # Extract the relevant sentence containing the match
                        sentences = re.split(r'[.!?]', text)
                        for sentence in sentences:
                            if re.search(pattern, sentence.lower(), re.IGNORECASE):
                                clean_sentence = sentence.strip()
                                if clean_sentence and len(clean_sentence) > 10:
                                    # Avoid duplicates
                                    if clean_sentence not in extracted[category]:
                                        extracted[category].append(clean_sentence)
                                    break

        # Limit to top 5 per category
        for category in extracted:
            extracted[category] = extracted[category][:5]

        self._extracted_pains = extracted

        total_extracted = sum(len(v) for v in extracted.values())
        logger.debug(f"💬 Extracted {total_extracted} pain phrases across {len([k for k, v in extracted.items() if v])} categories")

        return extracted

    def extract_data_points(self) -> List[Dict[str, str]]:
        """
        Extract citable data points from topical insights.

        Looks for statistics, percentages, and specific claims that can
        be cited in content for authority.

        Returns:
            List of dicts with 'claim' and 'source' keys
        """
        if self._extracted_data_points is not None:
            return self._extracted_data_points

        data_points = []

        # Patterns for citable claims
        stat_patterns = [
            r'\d+%',  # Percentages
            r'\$\d+',  # Dollar amounts
            r'\d+x',  # Multipliers
            r'\d+\s*(hours?|days?|weeks?|months?)',  # Time periods
            r'\d+\s*(companies|businesses|marketers|users)',  # Counts
        ]

        for insight in self.topical_insights.get('insights', []):
            if isinstance(insight, dict):
                text = insight.get('text', insight.get('insight', ''))
                source = insight.get('source', insight.get('url', 'research'))
            elif isinstance(insight, str):
                text = insight
                source = 'research'
            else:
                continue

            if not text:
                continue

            # Check if text contains citable data
            for pattern in stat_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    data_points.append({
                        'claim': text.strip(),
                        'source': source
                    })
                    break

        # Limit to top 10 data points
        self._extracted_data_points = data_points[:10]

        logger.debug(f"📊 Extracted {len(self._extracted_data_points)} citable data points")

        return self._extracted_data_points

    def _format_extracted_pains_for_prompt(self, pains: Dict[str, List[str]]) -> str:
        """Format extracted pains into prompt-ready text."""
        if not any(pains.values()):
            return ""

        lines = ["PAIN LANGUAGE EXTRACTED FROM RESEARCH:"]

        category_labels = {
            'time_waste': 'Time/effort frustrations',
            'money_blindness': 'Visibility/tracking gaps',
            'silo_problems': 'System fragmentation',
            'blame_game': 'Attribution conflicts',
            'cash_flow_pain': 'Cash flow challenges',
        }

        for category, phrases in pains.items():
            if phrases:
                label = category_labels.get(category, category)
                lines.append(f"\n{label}:")
                for phrase in phrases[:3]:
                    lines.append(f'- "{phrase}"')

        return '\n'.join(lines)

    def _get_intent_based_defaults(self) -> str:
        """Get minimal context based on keyword intent."""
        intent_type = self.intent.get('intent', 'informational')

        if intent_type == 'commercial':
            return """
TARGET AUDIENCE:
- Decision-makers evaluating and comparing solutions
- Focus: Practical comparison with actionable insights
- Tone: Expert advisor, objective but helpful
"""
        elif intent_type == 'transactional':
            return """
TARGET AUDIENCE:
- Ready-to-buy professionals seeking the right solution
- Focus: Clear value proposition and next steps
- Tone: Confident, direct, solution-oriented
"""
        else:  # informational or navigational
            return """
TARGET AUDIENCE:
- Business professionals seeking practical knowledge
- Focus: Educational, actionable insights
- Tone: Expert friend explaining clearly
"""

    def build_icp_context(self, light_mode: bool = False, skip_icp: bool = False) -> str:
        """
        Build ICP context from extracted research (not hardcoded phrases).

        Args:
            light_mode: If True, return minimal context for comparison styles
            skip_icp: If True, return generic audience context

        Returns:
            Formatted ICP context string for prompt injection
        """
        # Skip ICP entirely - use generic audience
        if skip_icp:
            logger.debug("🎯 ICP context: SKIPPED (generic audience)")
            return """
TARGET AUDIENCE:
- Business professionals and decision-makers
- Marketing and operations teams
- Focus: Practical, actionable insights
- Tone: Expert advisor, professional but accessible
"""

        # Light mode for comparison styles
        if light_mode:
            logger.debug("🎯 ICP context: light mode (comparison style)")
            return """
TARGET AUDIENCE:
- Target audience evaluating solutions
- Decision-makers comparing options for their marketing/sales stack
- Focus: Objective comparison with practical insights
- Tone: Expert advisor helping with informed decisions
"""

        tier = self._determine_context_tier()
        extracted_pains = self.extract_pain_language()

        # Build context based on tier
        if tier == 'rich':
            # Rich tier: Use only extracted patterns
            pain_section = self._format_extracted_pains_for_prompt(extracted_pains)

            context = f"""
TARGET AUDIENCE - RESEARCH-DERIVED CONTEXT:

{pain_section}

CONTENT APPROACH:
- Echo the exact language patterns found in research above
- Write FOR operators who wear multiple hats
- Avoid enterprise jargon - these are real business owners
- Tone: One founder talking to another
"""
            logger.debug("🎯 ICP context injected: research-derived (RICH tier)")

        elif tier == 'partial':
            # Partial tier: Extract + minimal business model buckets
            pain_section = self._format_extracted_pains_for_prompt(extracted_pains)
            buckets = self.minimal_defaults.get('business_model_buckets', [])

            context = f"""
TARGET AUDIENCE - PARTIAL RESEARCH CONTEXT:

BUSINESS MODEL BUCKETS:
{chr(10).join(f'- {bucket}' for bucket in buckets)}

{pain_section if pain_section else ''}

CONTENT APPROACH:
- {self.minimal_defaults.get('tone_anchor', 'Write for operators who wear multiple hats')}
- Avoid enterprise jargon - these are real business owners
- Tone: One founder talking to another
"""
            logger.debug("🎯 ICP context injected: partial research + business buckets")

        else:
            # Minimal tier: Intent-based defaults only
            context = self._get_intent_based_defaults()

            # Add minimal business model context
            buckets = self.minimal_defaults.get('business_model_buckets', [])

            context += f"""
BUSINESS MODEL CONTEXT:
{chr(10).join(f'- {bucket}' for bucket in buckets)}

CONTENT APPROACH:
- {self.minimal_defaults.get('tone_anchor', 'Write for operators who wear multiple hats')}
- Focus on the problem being solved, not specific pain phrases
"""
            logger.debug("🎯 ICP context injected: minimal (intent-based defaults)")

        return context

    def build_customer_language_context(self) -> str:
        """
        Build customer language context from research extraction.

        Instead of using static pain_language from config, extracts
        terms and phrases from actual research.

        Returns:
            Formatted customer language context for prompt injection
        """
        tier = self._determine_context_tier()

        if tier == 'minimal':
            # No research - return minimal guidance
            return """
LANGUAGE GUIDANCE:
- Use conversational, jargon-free language
- Focus on practical business outcomes
- Avoid marketing buzzwords
"""

        # Extract terms from research
        extracted_terms = set()

        # From Reddit insights
        for insight in self.reddit.get('insights', []):
            text = insight.get('text', insight.get('insight', '')) if isinstance(insight, dict) else insight
            if text:
                # Extract quoted phrases or specific terms
                quotes = re.findall(r'"([^"]+)"', text)
                extracted_terms.update(quotes)

        # From language_they_use in research
        for term in self.reddit.get('language_they_use', []):
            extracted_terms.add(term)

        # Limit and format
        terms_list = list(extracted_terms)[:15]

        if not terms_list:
            return """
LANGUAGE GUIDANCE:
- Use conversational, jargon-free language
- Echo customer pain points naturally
- Avoid marketing buzzwords
"""

        pains = self.extract_pain_language()

        # Build context with extracted content
        context_parts = [
            "LANGUAGE EXTRACTED FROM RESEARCH:",
            f"Terms customers use: {', '.join(terms_list[:10])}" if terms_list else "",
        ]

        # Add sample pain phrases (different from ICP context)
        if pains.get('time_waste'):
            context_parts.append(f"\nTime frustrations to echo: {'; '.join(pains['time_waste'][:2])}")
        if pains.get('silo_problems'):
            context_parts.append(f"System pain to echo: {'; '.join(pains['silo_problems'][:2])}")

        return '\n'.join(filter(None, context_parts))

    def get_data_points_for_content(self) -> str:
        """
        Format extracted data points for content generation.

        Returns:
            Formatted string with citable claims and sources
        """
        data_points = self.extract_data_points()

        if not data_points:
            return ""

        lines = ["CITABLE DATA POINTS FROM RESEARCH:"]
        for dp in data_points[:5]:
            lines.append(f"- {dp['claim']}")
            if dp.get('source') and dp['source'] != 'research':
                lines.append(f"  (Source: {dp['source']})")

        return '\n'.join(lines)
