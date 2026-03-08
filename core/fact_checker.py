"""
Fact Checker - Claim Extraction and Source Verification

Extracts citation-worthy claims from content and verifies against research sources.
Generates inline citations and confidence scoring for E-E-A-T and ClaimReview schema.

Integrates with:
- seo_optimization.json (source confidence levels)
- research.py (SERP, Reddit, Quora insights)
- schema_generator.py (ClaimReview schema)
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Claim:
    """Represents a citation-worthy claim extracted from content."""

    def __init__(
        self,
        text: str,
        sentence: str,
        position: int,
        claim_type: str
    ):
        """
        Initialize claim.

        Args:
            text: The specific claim text (e.g., "65% faster")
            sentence: Full sentence containing the claim
            position: Character position in content
            claim_type: Type of claim (statistical, expert, research, etc.)
        """
        self.text = text
        self.sentence = sentence
        self.position = position
        self.claim_type = claim_type
        self.source: Optional[str] = None
        self.confidence: str = 'OBSERVATIONAL'
        self.date_published: Optional[str] = None
        self.verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for schema generation."""
        return {
            'claim': self.sentence,
            'text': self.text,
            'source': self.source or 'research',
            'confidence': self.confidence,
            'date_published': self.date_published or datetime.now().isoformat(),
            'verified': self.verified
        }


class FactChecker:
    """Extract and verify claims from research content."""

    # Citation-worthy patterns (24 patterns for comprehensive coverage)
    CITATION_PATTERNS = [
        # Statistical claims
        (r'((?:data|research|analysis|study|survey|report)\s+(?:shows?|reveals?|demonstrates?|indicates?|suggests?)[^.!?]{10,150})', 'statistical'),
        (r'(\d+(?:\.\d+)?%\s+(?:of|increase|decrease|reduction|improvement|growth)[^.!?]{5,100})', 'statistical'),
        (r'(averaging?\s+\$?\d+[^.!?]{5,100})', 'statistical'),
        (r'(\d+x\s+(?:faster|more|better|higher|improvement)[^.!?]{5,100})', 'statistical'),

        # Expert attribution
        (r'(according\s+to\s+[A-Z][^.!?]{10,150})', 'expert'),
        (r'((?:Gartner|Forrester|McKinsey|HubSpot|Salesforce|Harvard|MIT)\s+[^.!?]{10,150})', 'research'),
        (r'(experts?\s+(?:recommend|suggest|indicate|note|observe)[^.!?]{10,150})', 'expert'),

        # Research findings
        (r'((?:our|the)\s+analysis\s+(?:reveals?|shows?|demonstrates?)[^.!?]{10,150})', 'research'),
        (r'(findings?\s+(?:show|indicate|suggest|reveal|demonstrate)[^.!?]{10,150})', 'research'),
        (r'(industry\s+(?:data|benchmarks?|standards?)\s+(?:shows?|indicates?)[^.!?]{10,150})', 'industry'),

        # Comparative claims
        (r'(\d+%\s+(?:more|less|faster|slower|higher|lower)\s+than[^.!?]{5,100})', 'comparative'),
        (r'(compared\s+to[^.!?]{10,150})', 'comparative'),

        # Time/cost savings
        (r'(saves?\s+(?:up\s+to\s+)?\d+\s*(?:hours?|days?|weeks?)[^.!?]{5,100})', 'benefit'),
        (r'(reduces?\s+(?:costs?|time|effort)\s+by\s+\d+%[^.!?]{5,100})', 'benefit'),

        # Market/industry facts
        (r'(market\s+(?:size|growth|share|value)\s+(?:of|is|reached?)[^.!?]{10,150})', 'market'),
        (r'((?:adoption|usage)\s+rate\s+of\s+\d+%[^.!?]{5,100})', 'market'),

        # ROI/performance claims
        (r'(ROI\s+of\s+\d+[^.!?]{5,100})', 'performance'),
        (r'((?:achieves?|delivers?)\s+\d+%\s+(?:improvement|increase|reduction)[^.!?]{5,100})', 'performance'),

        # Best practices
        (r'((?:best|top|leading)\s+practices?\s+include[^.!?]{10,150})', 'guideline'),
        (r'((?:recommended|proven)\s+(?:approach|method|strategy)[^.!?]{10,150})', 'guideline'),

        # Trend observations
        (r'((?:trend|shift|change)\s+towards?[^.!?]{10,150})', 'trend'),
        (r'((?:increasing|growing|declining)\s+(?:adoption|usage|demand)[^.!?]{10,150})', 'trend'),

        # Specific metrics
        (r'(conversion\s+rate\s+of\s+\d+%[^.!?]{5,100})', 'metric'),
        (r'(average\s+(?:cost|price|spend)\s+of\s+\$\d+[^.!?]{5,100})', 'metric'),
    ]

    def __init__(self, seo_config_path: Optional[Path] = None):
        """
        Initialize fact checker with source confidence config.

        Args:
            seo_config_path: Path to seo_optimization.json (optional)
        """
        if seo_config_path is None:
            seo_config_path = Path(__file__).parent.parent / 'config' / 'seo_optimization.json'

        self.confidence_levels = self._load_confidence_config(seo_config_path)

    def _load_confidence_config(self, path: Path) -> Dict[str, Any]:
        """Load source confidence levels from SEO config."""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                confidence = config.get('source_confidence_levels', {})
                logger.debug(f"✅ Loaded source confidence config ({len(confidence)} levels)")
                return confidence
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"⚠️  Could not load SEO config: {e}, using defaults")
            return {
                'research': {
                    'indicators': ['.edu', '.gov', 'gartner', 'forrester', 'mckinsey'],
                    'label': 'RESEARCH-GRADE'
                },
                'industry': {
                    'indicators': ['hubspot', 'salesforce', 'google', 'meta'],
                    'label': 'INDUSTRY'
                },
                'observational': {
                    'label': 'OBSERVATIONAL'
                }
            }

    def extract_claims(self, content: str) -> List[Claim]:
        """
        Extract citation-worthy claims from content using pattern matching.

        Args:
            content: Full MDX content

        Returns:
            List of Claim objects

        Extracts:
        - Statistical claims (percentages, metrics, data points)
        - Expert attributions (according to, experts say)
        - Research findings (analysis reveals, study shows)
        - Comparative claims (X% more than Y)
        - Market facts (market size, adoption rates)
        """
        claims = []
        seen_sentences = set()  # Avoid duplicates

        for pattern, claim_type in self.CITATION_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                sentence = match.group(1).strip()

                # Skip if already extracted
                if sentence.lower() in seen_sentences:
                    continue

                # Extract the core claim (stat, percentage, etc.)
                claim_text = self._extract_core_claim(sentence)

                claim = Claim(
                    text=claim_text,
                    sentence=sentence,
                    position=match.start(),
                    claim_type=claim_type
                )

                claims.append(claim)
                seen_sentences.add(sentence.lower())

        logger.info(f"📊 Extracted {len(claims)} claims ({len(set(c.claim_type for c in claims))} types)")
        return claims

    def _extract_core_claim(self, sentence: str) -> str:
        """Extract the core data point from a claim sentence."""
        # Try to extract the key metric/stat
        patterns = [
            r'\d+(?:\.\d+)?%',  # Percentages
            r'\$\d+(?:,\d{3})*(?:\.\d+)?[KMB]?',  # Dollar amounts
            r'\d+x',  # Multipliers
            r'\d+\s*(?:hours?|days?|weeks?|months?)',  # Time periods
            r'\d+(?:,\d{3})*\s*(?:companies|businesses|users?)',  # Counts
        ]

        for pattern in patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                return match.group(0)

        # Fallback: first 50 chars
        return sentence[:50] + '...' if len(sentence) > 50 else sentence

    def verify_against_research(
        self,
        claims: List[Claim],
        research_context: Dict[str, Any]
    ) -> List[Claim]:
        """
        Verify claims against research sources and assign confidence scores.

        Args:
            claims: List of extracted claims
            research_context: Dict with 'serp', 'reddit', 'quora', 'topical_insights'

        Returns:
            List of claims with verified=True and confidence assigned

        Confidence levels (from seo_optimization.json):
        - RESEARCH: Peer-reviewed, .edu/.gov, Gartner/Forrester/McKinsey
        - INDUSTRY: HubSpot, Salesforce, Google, Meta, established pubs
        - OBSERVATIONAL: Community discussions, practitioner sources
        """
        serp = research_context.get('serp', {})
        reddit = research_context.get('reddit', {})
        quora = research_context.get('quora', {})
        topical = research_context.get('topical_insights', {})

        # Build source lookup from research
        sources = self._build_source_lookup(serp, reddit, quora, topical)

        verified_count = 0
        for claim in claims:
            # Try to match claim to a source
            matched_source = self._match_claim_to_source(claim, sources)

            if matched_source:
                claim.source = matched_source['name']
                claim.confidence = matched_source['confidence']
                claim.date_published = matched_source.get('date')
                claim.verified = True
                verified_count += 1
            else:
                # Default to OBSERVATIONAL if no source match
                claim.source = 'research'
                claim.confidence = 'OBSERVATIONAL'
                claim.verified = False

        logger.info(f"✅ Verified {verified_count}/{len(claims)} claims against research sources")
        return claims

    def _build_source_lookup(
        self,
        serp: Dict,
        reddit: Dict,
        quora: Dict,
        topical: Dict
    ) -> List[Dict[str, Any]]:
        """Build source lookup table from research data."""
        sources = []

        # SERP sources
        for result in serp.get('search_results', []):
            url = result.get('url', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')

            confidence = self._classify_source_confidence(url, title)

            sources.append({
                'name': self._extract_source_name(url, title),
                'url': url,
                'text': f"{title}. {snippet}",
                'confidence': confidence,
                'type': 'serp'
            })

        # Topical insights
        for insight in topical.get('insights', []):
            if isinstance(insight, dict):
                source_url = insight.get('source', insight.get('url', ''))
                text = insight.get('text', insight.get('insight', ''))

                confidence = self._classify_source_confidence(source_url, text)

                sources.append({
                    'name': self._extract_source_name(source_url, text[:50]),
                    'url': source_url,
                    'text': text,
                    'confidence': confidence,
                    'type': 'topical'
                })

        # Reddit (OBSERVATIONAL)
        for insight in reddit.get('insights', []):
            text = insight.get('text', insight.get('insight', '')) if isinstance(insight, dict) else insight
            sources.append({
                'name': 'Reddit Community',
                'text': text,
                'confidence': 'OBSERVATIONAL',
                'type': 'reddit'
            })

        # Quora (OBSERVATIONAL)
        for insight in quora.get('expert_insights', []):
            text = insight.get('text', insight.get('insight', '')) if isinstance(insight, dict) else insight
            sources.append({
                'name': 'Quora Experts',
                'text': text,
                'confidence': 'OBSERVATIONAL',
                'type': 'quora'
            })

        logger.debug(f"📚 Built source lookup with {len(sources)} sources")
        return sources

    def _classify_source_confidence(self, url: str, text: str) -> str:
        """
        Classify source confidence level based on URL and content.

        Uses indicators from seo_optimization.json:
        - RESEARCH: .edu, .gov, gartner, forrester, mckinsey, harvard, etc.
        - INDUSTRY: hubspot, salesforce, google, meta, forbes, techcrunch
        - OBSERVATIONAL: everything else
        """
        url_lower = url.lower()
        text_lower = text.lower()

        # Check RESEARCH indicators
        research_indicators = self.confidence_levels.get('research', {}).get('indicators', [])
        for indicator in research_indicators:
            if indicator in url_lower or indicator in text_lower:
                return 'RESEARCH'

        # Check INDUSTRY indicators
        industry_indicators = self.confidence_levels.get('industry', {}).get('indicators', [])
        for indicator in industry_indicators:
            if indicator in url_lower or indicator in text_lower:
                return 'INDUSTRY'

        # Default to OBSERVATIONAL
        return 'OBSERVATIONAL'

    def _extract_source_name(self, url: str, fallback_text: str) -> str:
        """Extract clean source name from URL or text."""
        if not url:
            return fallback_text[:30]

        # Extract domain
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            # Clean up (remove .com, .org, etc.)
            domain = re.sub(r'\.(com|org|net|edu|gov|io)$', '', domain)
            # Capitalize
            return domain.replace('-', ' ').replace('.', ' ').title()

        return fallback_text[:30]

    def _match_claim_to_source(
        self,
        claim: Claim,
        sources: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Match a claim to the best research source using fuzzy text matching.

        Args:
            claim: Claim object
            sources: List of source dicts

        Returns:
            Best matching source dict or None
        """
        # Extract key terms from claim
        claim_terms = set(re.findall(r'\b\w{4,}\b', claim.sentence.lower()))

        best_match = None
        best_score = 0

        for source in sources:
            source_text = source.get('text', '').lower()

            # Count matching terms
            matches = sum(1 for term in claim_terms if term in source_text)

            # Bonus for exact claim substring match
            if claim.text.lower() in source_text:
                matches += 5

            if matches > best_score:
                best_score = matches
                best_match = source

        # Require at least 2 matching terms for verification
        if best_score >= 2:
            return best_match

        return None

    def check_data_freshness(
        self,
        claims: List[Claim],
        max_age_months: int = 18
    ) -> Dict[str, Any]:
        """
        Check freshness of data points in claims.

        Args:
            claims: List of verified claims
            max_age_months: Maximum acceptable age in months (default: 18)

        Returns:
            Freshness report with counts and recommendations
        """
        current_year = datetime.now().year
        cutoff_date = datetime.now() - timedelta(days=max_age_months * 30)

        outdated_claims = []
        year_pattern = r'\b(20\d{2})\b'

        for claim in claims:
            # Look for year mentions in claim
            years = re.findall(year_pattern, claim.sentence)

            for year_str in years:
                year = int(year_str)
                claim_date = datetime(year, 1, 1)

                if claim_date < cutoff_date:
                    outdated_claims.append({
                        'claim': claim.sentence[:80],
                        'year': year,
                        'age_months': (datetime.now() - claim_date).days // 30
                    })

        freshness_ratio = 1 - (len(outdated_claims) / max(len(claims), 1))

        report = {
            'total_claims': len(claims),
            'outdated_count': len(outdated_claims),
            'freshness_ratio': freshness_ratio,
            'freshness_score': int(freshness_ratio * 100),
            'recommendation': 'REFRESH' if len(outdated_claims) > 5 else 'OK',
            'outdated_examples': outdated_claims[:5]
        }

        if outdated_claims:
            logger.warning(f"⚠️  {len(outdated_claims)} claims have data >{max_age_months} months old")
        else:
            logger.info(f"✅ All claims have fresh data (<{max_age_months} months)")

        return report

    def generate_inline_citations(
        self,
        content: str,
        verified_claims: List[Claim]
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Add inline citations [1], [2] to content for verified claims.

        Args:
            content: Original MDX content
            verified_claims: List of verified claims with sources

        Returns:
            Tuple of (content_with_citations, bibliography)

        Format:
        - Inline: "Data shows 65% improvement [1]."
        - Bibliography: [1] HubSpot: 2024 Marketing Trends Report (INDUSTRY)
        """
        # Sort claims by position (reverse to avoid offset issues)
        sorted_claims = sorted(
            [c for c in verified_claims if c.verified],
            key=lambda x: x.position,
            reverse=True
        )

        bibliography = []
        citation_map = {}  # Track unique sources
        citation_num = 1

        # Build bibliography and citation map
        for claim in sorted_claims:
            source_key = f"{claim.source}_{claim.confidence}"

            if source_key not in citation_map:
                citation_map[source_key] = citation_num
                bibliography.append({
                    'number': citation_num,
                    'source': claim.source,
                    'confidence': claim.confidence
                })
                citation_num += 1

        # Add inline citations to content
        modified_content = content
        for claim in sorted_claims:
            source_key = f"{claim.source}_{claim.confidence}"
            citation_number = citation_map.get(source_key, 0)

            if citation_number:
                # Find the claim sentence in content
                sentence_pattern = re.escape(claim.sentence[:50])  # Match first 50 chars
                match = re.search(sentence_pattern, modified_content)

                if match:
                    # Insert citation before period/end
                    insert_pos = match.end()
                    # Find sentence end
                    sentence_end = re.search(r'[.!?]', modified_content[insert_pos:])
                    if sentence_end:
                        citation_pos = insert_pos + sentence_end.start()
                        citation = f" [{citation_number}]"
                        modified_content = modified_content[:citation_pos] + citation + modified_content[citation_pos:]

        logger.info(f"📝 Added {len(bibliography)} inline citations to content")
        return modified_content, bibliography

    def get_verified_claims_for_schema(
        self,
        claims: List[Claim],
        min_confidence: str = 'INDUSTRY'
    ) -> List[Dict[str, Any]]:
        """
        Get verified claims formatted for ClaimReview schema.

        Args:
            claims: List of all claims
            min_confidence: Minimum confidence level (RESEARCH, INDUSTRY, OBSERVATIONAL)

        Returns:
            List of claim dicts for schema_generator.generate_claim_review_schema()
        """
        confidence_order = ['RESEARCH', 'INDUSTRY', 'OBSERVATIONAL']
        min_index = confidence_order.index(min_confidence) if min_confidence in confidence_order else 2

        filtered_claims = [
            c.to_dict()
            for c in claims
            if c.verified and confidence_order.index(c.confidence) <= min_index
        ]

        logger.debug(f"🎯 Filtered {len(filtered_claims)}/{len(claims)} claims for schema (≥{min_confidence})")
        return filtered_claims
