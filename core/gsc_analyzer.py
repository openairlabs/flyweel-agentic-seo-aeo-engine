"""
GSC Analyzer - Google Search Console integration for data-driven content decisions.

Based on advanced GSC analysis methodology:
- Cannibalization checking before content creation
- Keyword categorization (Rising Stars, Fading Giants, Striking Distance, High-Impact)
- Traffic Maximization Formula for quantitative keyword selection
- Real PAA question extraction from GSC queries

Usage:
    from core.gsc_analyzer import GSCAnalyzer

    async with GSCAnalyzer() as gsc:
        # Before creating new content
        result = await gsc.check_cannibalization("mcp servers for ad analytics")

        # Analyze existing page
        perf = await gsc.analyze_page("/blog/best-mcp-servers")

        # Get keyword opportunities
        keywords = await gsc.categorize_keywords(["mcp", "ad analytics", "claude integration"])
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load .env from project root with override to ensure fresh values
load_dotenv(Path(__file__).parent.parent / '.env', override=True)
logger = logging.getLogger(__name__)


class KeywordCategory(Enum):
    """Keyword categories for SEO prioritization"""
    RISING_STAR = "rising_star"           # Improving positions/impressions
    FADING_GIANT = "fading_giant"         # Declining performance (needs refresh)
    STRIKING_DISTANCE = "striking_distance"  # Positions 11-20 (page 1 opportunities)
    HIGH_IMPACT = "high_impact"           # Positions 4-10 (quick wins)
    OPPORTUNITY = "opportunity"           # High impressions, low CTR
    TOP_PERFORMER = "top_performer"       # Positions 1-3 (protect these)
    LONG_TAIL = "long_tail"               # 4+ words, specific intent


class ContentRecommendation(Enum):
    """Content action recommendations"""
    CREATE_NEW = "create_new"             # No existing content - safe to create
    OPTIMIZE_EXISTING = "optimize_existing"  # Existing content ranks - improve it
    ABORT = "abort"                       # Strong existing content - don't cannibalize
    CONSOLIDATE = "consolidate"           # Multiple pages - consider merging


@dataclass
class KeywordData:
    """Structured keyword performance data"""
    query: str
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0
    traffic_potential: float = 0.0
    category: Optional[KeywordCategory] = None
    is_question: bool = False
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.query.split())
        self.is_question = any(
            self.query.lower().startswith(q)
            for q in ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'can', 'does', 'is']
        )


@dataclass
class PagePerformance:
    """Page performance metrics from GSC"""
    url: str
    total_clicks: int = 0
    total_impressions: int = 0
    avg_ctr: float = 0.0
    avg_position: float = 0.0
    keywords: List[KeywordData] = field(default_factory=list)
    primary_keyword: Optional[KeywordData] = None
    rising_stars: List[KeywordData] = field(default_factory=list)
    opportunities: List[KeywordData] = field(default_factory=list)
    questions: List[KeywordData] = field(default_factory=list)


@dataclass
class CannibalizationResult:
    """Result of cannibalization check"""
    keyword: str
    existing_urls: List[Dict[str, Any]] = field(default_factory=list)
    recommendation: ContentRecommendation = ContentRecommendation.CREATE_NEW
    reason: str = ""
    best_existing_url: Optional[str] = None
    best_existing_position: Optional[float] = None


# CTR expectations by position (industry averages)
CTR_BY_POSITION = {
    1: 0.32,   # 30-35%
    2: 0.17,   # 15-18%
    3: 0.11,   # 10-12%
    4: 0.08,   # 6-8%
    5: 0.07,
    6: 0.05,   # 3-5%
    7: 0.04,
    8: 0.035,
    9: 0.03,
    10: 0.025,
}


def calculate_traffic_potential(impressions: int, position: float) -> float:
    """
    Traffic Maximization Formula for keyword prioritization.

    Traffic Potential = Impressions × Expected CTR at Target Position

    This quantifies keyword value beyond just impressions - a keyword
    with 1000 impressions at position 5 has more potential than one
    with 2000 impressions at position 20.
    """
    if position <= 0 or impressions <= 0:
        return 0.0

    pos_rounded = min(round(position), 20)

    if pos_rounded <= 10:
        expected_ctr = CTR_BY_POSITION.get(pos_rounded, 0.025)
    elif pos_rounded <= 20:
        expected_ctr = 0.015  # Page 2: 1-2%
    else:
        expected_ctr = 0.005  # Page 3+: <1%

    return impressions * expected_ctr


def categorize_keyword(kw: KeywordData, historical_data: Optional[Dict] = None) -> KeywordCategory:
    """
    Categorize keyword based on SEO prioritization methodology.

    Categories:
    - TOP_PERFORMER: Positions 1-3 (protect)
    - HIGH_IMPACT: Positions 4-10 (quick wins)
    - STRIKING_DISTANCE: Positions 11-20 (page 1 opportunities)
    - RISING_STAR: Improving trend (needs historical data)
    - FADING_GIANT: Declining trend (needs historical data)
    - OPPORTUNITY: High impressions, low CTR
    - LONG_TAIL: 4+ words (specific intent)
    """
    # Position-based categorization (primary)
    if kw.position <= 3:
        return KeywordCategory.TOP_PERFORMER
    elif kw.position <= 10:
        return KeywordCategory.HIGH_IMPACT
    elif kw.position <= 20:
        return KeywordCategory.STRIKING_DISTANCE

    # CTR-based opportunity detection
    expected_ctr = CTR_BY_POSITION.get(min(round(kw.position), 10), 0.015)
    if kw.impressions > 100 and kw.ctr < expected_ctr * 0.5:
        # High impressions but CTR is less than half expected
        return KeywordCategory.OPPORTUNITY

    # Long-tail detection
    if kw.word_count >= 4:
        return KeywordCategory.LONG_TAIL

    # Historical trend analysis (if data available)
    if historical_data:
        current_pos = kw.position
        historical_pos = historical_data.get('position', kw.position)

        if current_pos < historical_pos - 2:  # Position improved by 2+
            return KeywordCategory.RISING_STAR
        elif current_pos > historical_pos + 3:  # Position dropped by 3+
            return KeywordCategory.FADING_GIANT

    return KeywordCategory.LONG_TAIL  # Default for low-volume keywords


class GSCAnalyzer:
    """
    Google Search Console integration for data-driven content decisions.

    Implements advanced SEO methodology:
    - GSC-driven keyword selection
    - Cannibalization prevention
    - Traffic Maximization Formula
    - Keyword categorization
    """

    def __init__(self):
        self._service = None
        self._site_url = None
        self._initialized = False
        self._init_gsc()

    def _init_gsc(self):
        """Initialize Google Search Console API client"""
        creds_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')

        if not creds_path:
            logger.warning("GOOGLE_SERVICE_ACCOUNT_PATH not set - GSC features disabled")
            return

        if not os.path.exists(creds_path):
            logger.warning(f"GSC credentials file not found: {creds_path}")
            return

        try:
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
            self._service = build('searchconsole', 'v1', credentials=credentials)

            # Get site URL from env - support both domain property and URL prefix
            self._site_url = os.getenv('GSC_PROPERTY_URL', os.getenv('GSC_SITE_URL', 'https://acme.com'))

            self._initialized = True
            logger.debug(f"✅ GSC initialized for {self._site_url}")

        except Exception as e:
            logger.error(f"Failed to initialize GSC: {e}")
            self._service = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def is_available(self) -> bool:
        """Check if GSC is available and initialized"""
        return self._initialized and self._service is not None

    def _get_base_url(self) -> str:
        """
        Extract base URL from GSC property URL.
        Handles both domain property (sc-domain:acme.com) and URL prefix (https://acme.com).
        """
        if not self._site_url:
            return 'https://acme.com'

        # Handle domain property format: sc-domain:example.com -> https://example.com
        if self._site_url.startswith('sc-domain:'):
            domain = self._site_url.replace('sc-domain:', '')
            return f'https://{domain}'

        # Handle URL prefix format: https://example.com -> https://example.com
        if self._site_url.startswith('http'):
            return self._site_url

        # Fallback: prepend https://
        return f'https://{self._site_url}'

    async def check_cannibalization(
        self,
        keyword: str,
        days: int = 90,
        min_impressions: int = 10
    ) -> CannibalizationResult:
        """
        Check if existing Brand content already ranks for this keyword.

        CRITICAL: Run this before creating new content to avoid cannibalization.

        Based on SEO best practices:
        - If position 1-10 exists → recommend optimization, not new content
        - If position 11-20 exists → consider consolidation
        - If no ranking → safe to create new content

        Args:
            keyword: Target keyword to check
            days: Number of days to analyze (default 90)
            min_impressions: Minimum impressions threshold

        Returns:
            CannibalizationResult with recommendation
        """
        result = CannibalizationResult(keyword=keyword)

        if not self.is_available:
            logger.warning("GSC not available - skipping cannibalization check")
            result.reason = "GSC not available - proceed with caution"
            return result

        try:
            end_date = datetime.now() - timedelta(days=3)  # GSC has 3-day delay
            start_date = end_date - timedelta(days=days)

            request_body = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['page', 'query'],
                'dimensionFilterGroups': [{
                    'filters': [{
                        'dimension': 'query',
                        'expression': keyword.lower(),
                        'operator': 'contains'
                    }]
                }],
                'rowLimit': 100
            }

            response = await asyncio.to_thread(
                self._service.searchanalytics().query(
                    siteUrl=self._site_url,
                    body=request_body
                ).execute
            )

            if 'rows' not in response or not response['rows']:
                result.recommendation = ContentRecommendation.CREATE_NEW
                result.reason = f"No existing content ranks for '{keyword}' - safe to create"
                return result

            # Aggregate by page URL
            page_data = {}
            for row in response['rows']:
                page_url = row['keys'][0]
                query = row['keys'][1]

                if page_url not in page_data:
                    page_data[page_url] = {
                        'url': page_url,
                        'clicks': 0,
                        'impressions': 0,
                        'best_position': 100,
                        'queries': []
                    }

                page_data[page_url]['clicks'] += row.get('clicks', 0)
                page_data[page_url]['impressions'] += row.get('impressions', 0)
                page_data[page_url]['best_position'] = min(
                    page_data[page_url]['best_position'],
                    row.get('position', 100)
                )
                page_data[page_url]['queries'].append(query)

            # Filter by minimum impressions and sort by position
            ranking_pages = [
                p for p in page_data.values()
                if p['impressions'] >= min_impressions
            ]
            ranking_pages.sort(key=lambda x: x['best_position'])

            result.existing_urls = ranking_pages

            if not ranking_pages:
                result.recommendation = ContentRecommendation.CREATE_NEW
                result.reason = f"No pages with significant impressions for '{keyword}'"
                return result

            best_page = ranking_pages[0]
            result.best_existing_url = best_page['url']
            result.best_existing_position = best_page['best_position']

            # Decision logic based on SEO best practices
            if best_page['best_position'] <= 5:
                result.recommendation = ContentRecommendation.ABORT
                result.reason = (
                    f"Strong ranking exists at position {best_page['best_position']:.1f}. "
                    f"Optimize {best_page['url']} instead of creating new content."
                )
            elif best_page['best_position'] <= 10:
                result.recommendation = ContentRecommendation.OPTIMIZE_EXISTING
                result.reason = (
                    f"Page 1 ranking at position {best_page['best_position']:.1f}. "
                    f"Recommend optimizing {best_page['url']} for higher CTR."
                )
            elif len(ranking_pages) > 2:
                result.recommendation = ContentRecommendation.CONSOLIDATE
                result.reason = (
                    f"{len(ranking_pages)} pages compete for '{keyword}'. "
                    f"Consider consolidating into {best_page['url']}."
                )
            else:
                result.recommendation = ContentRecommendation.OPTIMIZE_EXISTING
                result.reason = (
                    f"Striking distance at position {best_page['best_position']:.1f}. "
                    f"Optimize {best_page['url']} for page 1."
                )

            return result

        except Exception as e:
            logger.error(f"Cannibalization check failed: {e}")
            result.reason = f"Check failed: {e} - proceed with caution"
            return result

    async def analyze_page(
        self,
        page_url: str,
        days: int = 90
    ) -> PagePerformance:
        """
        Get comprehensive performance data for an existing page.

        Use this when optimizing existing content to understand:
        - Which keywords drive traffic
        - Which keywords are underperforming (opportunities)
        - Which questions users ask (for FAQ section)

        Args:
            page_url: URL path (e.g., "/blog/best-mcp-servers") or full URL
            days: Number of days to analyze

        Returns:
            PagePerformance with categorized keywords
        """
        result = PagePerformance(url=page_url)

        if not self.is_available:
            logger.warning("GSC not available")
            return result

        try:
            end_date = datetime.now() - timedelta(days=3)
            start_date = end_date - timedelta(days=days)

            # Normalize URL for filter
            base_url = self._get_base_url()
            if page_url.startswith('/'):
                filter_url = f"{base_url}{page_url}"
            elif not page_url.startswith('http'):
                filter_url = f"{base_url}/{page_url}"
            else:
                filter_url = page_url

            request_body = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'dimensionFilterGroups': [{
                    'filters': [{
                        'dimension': 'page',
                        'expression': filter_url,
                        'operator': 'contains'
                    }]
                }],
                'rowLimit': 500  # Get more keywords for comprehensive analysis
            }

            response = await asyncio.to_thread(
                self._service.searchanalytics().query(
                    siteUrl=self._site_url,
                    body=request_body
                ).execute
            )

            if 'rows' not in response:
                return result

            # Process keywords
            for row in response['rows']:
                query = row['keys'][0]
                kw = KeywordData(
                    query=query,
                    clicks=row.get('clicks', 0),
                    impressions=row.get('impressions', 0),
                    ctr=row.get('ctr', 0),
                    position=row.get('position', 0)
                )
                kw.traffic_potential = calculate_traffic_potential(
                    kw.impressions,
                    kw.position
                )
                kw.category = categorize_keyword(kw)

                result.keywords.append(kw)
                result.total_clicks += kw.clicks
                result.total_impressions += kw.impressions

            if result.keywords:
                # Calculate averages
                result.avg_ctr = sum(k.ctr for k in result.keywords) / len(result.keywords)
                result.avg_position = sum(k.position for k in result.keywords) / len(result.keywords)

                # Find primary keyword (highest traffic potential)
                result.primary_keyword = max(
                    result.keywords,
                    key=lambda k: k.traffic_potential
                )

                # Categorize keywords
                result.rising_stars = [
                    k for k in result.keywords
                    if k.category == KeywordCategory.RISING_STAR
                ]
                result.opportunities = [
                    k for k in result.keywords
                    if k.category in [KeywordCategory.OPPORTUNITY, KeywordCategory.STRIKING_DISTANCE]
                ]
                result.questions = [
                    k for k in result.keywords
                    if k.is_question
                ]

            return result

        except Exception as e:
            logger.error(f"Page analysis failed for {page_url}: {e}")
            return result

    async def get_keyword_opportunities(
        self,
        base_keyword: str,
        days: int = 90,
        min_impressions: int = 50
    ) -> Dict[str, List[KeywordData]]:
        """
        Get keyword opportunities related to a base keyword.

        Returns keywords categorized by optimization priority:
        - rising_stars: Improving positions (capitalize on momentum)
        - high_impact: Positions 4-10 (quick wins to page 1 top)
        - striking_distance: Positions 11-20 (page 1 opportunities)
        - opportunities: High impressions, low CTR (title/meta fixes)
        - questions: User questions (FAQ content)

        Args:
            base_keyword: Core keyword to find related opportunities
            days: Number of days to analyze
            min_impressions: Minimum impressions threshold

        Returns:
            Dict with categorized KeywordData lists
        """
        result = {
            'top_performers': [],
            'high_impact': [],
            'striking_distance': [],
            'opportunities': [],
            'rising_stars': [],
            'fading_giants': [],
            'questions': [],
            'all_keywords': []
        }

        if not self.is_available:
            logger.warning("GSC not available")
            return result

        try:
            end_date = datetime.now() - timedelta(days=3)
            start_date = end_date - timedelta(days=days)

            request_body = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'dimensionFilterGroups': [{
                    'filters': [{
                        'dimension': 'query',
                        'expression': base_keyword.lower(),
                        'operator': 'contains'
                    }]
                }],
                'rowLimit': 500
            }

            response = await asyncio.to_thread(
                self._service.searchanalytics().query(
                    siteUrl=self._site_url,
                    body=request_body
                ).execute
            )

            if 'rows' not in response:
                return result

            for row in response['rows']:
                if row.get('impressions', 0) < min_impressions:
                    continue

                kw = KeywordData(
                    query=row['keys'][0],
                    clicks=row.get('clicks', 0),
                    impressions=row.get('impressions', 0),
                    ctr=row.get('ctr', 0),
                    position=row.get('position', 0)
                )
                kw.traffic_potential = calculate_traffic_potential(
                    kw.impressions,
                    kw.position
                )
                kw.category = categorize_keyword(kw)

                result['all_keywords'].append(kw)

                # Categorize
                if kw.category == KeywordCategory.TOP_PERFORMER:
                    result['top_performers'].append(kw)
                elif kw.category == KeywordCategory.HIGH_IMPACT:
                    result['high_impact'].append(kw)
                elif kw.category == KeywordCategory.STRIKING_DISTANCE:
                    result['striking_distance'].append(kw)
                elif kw.category == KeywordCategory.OPPORTUNITY:
                    result['opportunities'].append(kw)
                elif kw.category == KeywordCategory.RISING_STAR:
                    result['rising_stars'].append(kw)
                elif kw.category == KeywordCategory.FADING_GIANT:
                    result['fading_giants'].append(kw)

                if kw.is_question:
                    result['questions'].append(kw)

            # Sort each category by traffic potential
            for category in result.values():
                if isinstance(category, list):
                    category.sort(key=lambda k: k.traffic_potential, reverse=True)

            return result

        except Exception as e:
            logger.error(f"Keyword opportunity analysis failed: {e}")
            return result

    async def extract_paa_questions(
        self,
        keyword: str,
        days: int = 90,
        limit: int = 10
    ) -> List[str]:
        """
        Extract real People Also Ask questions from GSC query data.

        These are actual questions users searched and saw our content for,
        making them ideal for FAQ sections (better than AI-generated).

        Args:
            keyword: Base keyword to find related questions
            days: Number of days to analyze
            limit: Maximum questions to return

        Returns:
            List of question strings sorted by impressions
        """
        if not self.is_available:
            return []

        try:
            opportunities = await self.get_keyword_opportunities(
                keyword, days, min_impressions=5
            )

            questions = opportunities.get('questions', [])

            # Sort by impressions (most common questions first)
            questions.sort(key=lambda k: k.impressions, reverse=True)

            return [q.query for q in questions[:limit]]

        except Exception as e:
            logger.error(f"PAA extraction failed: {e}")
            return []

    async def get_primary_keyword(
        self,
        target_keyword: str,
        days: int = 90
    ) -> Optional[KeywordData]:
        """
        Get the #1 primary keyword for content optimization.

        Based on GSC-driven content methodology:
        - Find the highest-intent, best-performing keyword
        - Use EXACT keyword in title (not modified)

        Args:
            target_keyword: Base keyword to find primary
            days: Number of days to analyze

        Returns:
            KeywordData for the primary keyword, or None
        """
        opportunities = await self.get_keyword_opportunities(
            target_keyword, days, min_impressions=20
        )

        all_keywords = opportunities.get('all_keywords', [])

        if not all_keywords:
            return None

        # Find keyword with highest traffic potential that's 4+ words (high intent)
        high_intent = [k for k in all_keywords if k.word_count >= 4]

        if high_intent:
            return max(high_intent, key=lambda k: k.traffic_potential)

        # Fallback to highest traffic potential overall
        return max(all_keywords, key=lambda k: k.traffic_potential)

    async def get_content_recommendations(
        self,
        keyword: str,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Get comprehensive content recommendations based on GSC data.

        Returns actionable insights for content creation/optimization:
        - Primary keyword (use in title exactly)
        - Secondary keywords (use in H2s)
        - Questions (use in FAQ)
        - Cannibalization check result
        - Traffic potential estimate

        Args:
            keyword: Target keyword for content
            days: Number of days to analyze

        Returns:
            Dict with structured recommendations
        """
        # Run analyses in parallel
        cannibalization, opportunities = await asyncio.gather(
            self.check_cannibalization(keyword, days),
            self.get_keyword_opportunities(keyword, days)
        )

        all_keywords = opportunities.get('all_keywords', [])
        questions = opportunities.get('questions', [])

        # Find primary keyword
        primary = None
        if all_keywords:
            # Prefer high-intent (4+ words) with good traffic potential
            high_intent = [k for k in all_keywords if k.word_count >= 4]
            if high_intent:
                primary = max(high_intent, key=lambda k: k.traffic_potential)
            else:
                primary = max(all_keywords, key=lambda k: k.traffic_potential)

        # Get secondary keywords for H2s (top 4-5 by position)
        secondaries = sorted(
            [k for k in all_keywords if k != primary],
            key=lambda k: k.position
        )[:5]

        # Format recommendations
        return {
            'target_keyword': keyword,
            'cannibalization': {
                'recommendation': cannibalization.recommendation.value,
                'reason': cannibalization.reason,
                'existing_url': cannibalization.best_existing_url,
                'existing_position': cannibalization.best_existing_position
            },
            'primary_keyword': {
                'query': primary.query if primary else keyword,
                'position': primary.position if primary else None,
                'impressions': primary.impressions if primary else 0,
                'traffic_potential': primary.traffic_potential if primary else 0,
                'use_exact': True  # CRITICAL: Use exact keyword in title
            },
            'secondary_keywords': [
                {
                    'query': k.query,
                    'position': k.position,
                    'impressions': k.impressions,
                    'suggested_h2': True
                }
                for k in secondaries
            ],
            'faq_questions': [q.query for q in questions[:10]],
            'opportunities': {
                'striking_distance': len(opportunities.get('striking_distance', [])),
                'high_impact': len(opportunities.get('high_impact', [])),
                'total_keywords': len(all_keywords)
            },
            'meta': {
                'days_analyzed': days,
                'total_impressions': sum(k.impressions for k in all_keywords),
                'total_clicks': sum(k.clicks for k in all_keywords)
            }
        }


# Convenience function for CLI usage
async def analyze_keyword(keyword: str, days: int = 90) -> Dict[str, Any]:
    """
    Quick keyword analysis for CLI usage.

    Usage:
        python -c "import asyncio; from core.gsc_analyzer import analyze_keyword; print(asyncio.run(analyze_keyword('mcp servers')))"
    """
    async with GSCAnalyzer() as gsc:
        return await gsc.get_content_recommendations(keyword, days)


# CLI entry point
if __name__ == "__main__":
    import sys
    import json

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python gsc_analyzer.py <keyword> [--page <url>] [--days <n>]")
            print("\nExamples:")
            print("  python gsc_analyzer.py 'mcp servers'")
            print("  python gsc_analyzer.py --page '/blog/best-mcp-servers'")
            print("  python gsc_analyzer.py 'ad analytics' --days 30")
            sys.exit(1)

        keyword = None
        page_url = None
        days = 90

        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == '--page' and i + 1 < len(sys.argv):
                page_url = sys.argv[i + 1]
                i += 2
            elif arg == '--days' and i + 1 < len(sys.argv):
                days = int(sys.argv[i + 1])
                i += 2
            else:
                keyword = arg
                i += 1

        async with GSCAnalyzer() as gsc:
            if not gsc.is_available:
                print("❌ GSC not available. Check credentials and environment variables.")
                sys.exit(1)

            if page_url:
                print(f"📊 Analyzing page: {page_url}")
                result = await gsc.analyze_page(page_url, days)
                print(f"\n✅ Page Performance ({days} days):")
                print(f"   Clicks: {result.total_clicks:,}")
                print(f"   Impressions: {result.total_impressions:,}")
                print(f"   Avg CTR: {result.avg_ctr:.2%}")
                print(f"   Avg Position: {result.avg_position:.1f}")

                if result.primary_keyword:
                    print(f"\n🎯 Primary Keyword: '{result.primary_keyword.query}'")
                    print(f"   Traffic Potential: {result.primary_keyword.traffic_potential:.0f}")

                if result.questions:
                    print(f"\n❓ FAQ Questions ({len(result.questions)}):")
                    for q in result.questions[:5]:
                        print(f"   - {q.query}")

            elif keyword:
                print(f"🔍 Analyzing keyword: '{keyword}'")
                result = await gsc.get_content_recommendations(keyword, days)
                print(json.dumps(result, indent=2, default=str))

    asyncio.run(main())
