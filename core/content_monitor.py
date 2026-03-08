"""
Content Monitor - GSC-driven content refresh trigger system.

Based on SEO best practices:
- Monitors keyword position changes
- Detects declining performance (Fading Giants)
- Identifies refresh opportunities
- Tracks CTR underperformance

Usage:
    from core.content_monitor import ContentMonitor

    async with ContentMonitor() as monitor:
        # Check if content needs refresh
        needs_refresh, reasons = await monitor.check_refresh_needed("/blog/best-crm-tools")

        # Get all content needing refresh
        refresh_list = await monitor.get_refresh_candidates()
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import json

from .gsc_analyzer import (
    GSCAnalyzer,
    KeywordData,
    PagePerformance,
    KeywordCategory,
    calculate_traffic_potential,
    CTR_BY_POSITION
)

logger = logging.getLogger(__name__)


@dataclass
class RefreshTrigger:
    """Represents a content refresh trigger"""
    trigger_type: str  # position_drop, ctr_underperform, impressions_spike, annual_refresh
    severity: str  # critical, warning, info
    message: str
    data: Dict[str, Any]


@dataclass
class ContentRefreshResult:
    """Result of content refresh analysis"""
    url: str
    needs_refresh: bool
    triggers: List[RefreshTrigger]
    priority: int  # 1 = highest, 3 = lowest
    primary_keyword: Optional[str] = None
    current_position: Optional[float] = None
    traffic_potential: float = 0.0


def _load_refresh_config() -> Dict[str, Any]:
    """Load refresh trigger configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'seo_optimization.json'
    defaults = {
        'ranking_drop_threshold': 5,  # Refresh if position drops below 5
        'impressions_increase_threshold': 0.5,  # 50% increase triggers review
        'ctr_underperform_ratio': 0.5,  # Refresh if CTR is <50% of expected
        'annual_refresh_months': [1, 7],  # January and July
        'max_days_without_update': 180  # 6 months
    }

    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                triggers = config.get('content_refresh_triggers', {})
                return {
                    'ranking_drop_threshold': triggers.get('ranking_drop_threshold', 5),
                    'impressions_increase_threshold': triggers.get('impressions_increase_threshold', 0.5),
                    'ctr_underperform_ratio': 0.5,
                    'annual_refresh_months': triggers.get('annual_refresh_months', [1, 7]),
                    'max_days_without_update': 180
                }
        except Exception:
            pass

    return defaults


class ContentMonitor:
    """
    Monitor content performance and identify refresh opportunities.

    Implements refresh trigger methodology:
    - Position drops (keyword falling out of top 5)
    - CTR underperformance (below expected for position)
    - Impressions spikes (opportunity to capitalize)
    - Annual refresh schedule (January/July)
    """

    def __init__(self):
        self._gsc = None
        self._config = _load_refresh_config()

    async def __aenter__(self):
        self._gsc = GSCAnalyzer()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def is_available(self) -> bool:
        """Check if GSC is available"""
        return self._gsc is not None and self._gsc.is_available

    async def check_refresh_needed(
        self,
        page_url: str,
        last_updated: Optional[datetime] = None
    ) -> Tuple[bool, List[RefreshTrigger]]:
        """
        Check if a specific page needs content refresh.

        Args:
            page_url: URL path to check (e.g., "/blog/best-crm-tools")
            last_updated: Optional last update date for staleness check

        Returns:
            Tuple of (needs_refresh, list of triggers)
        """
        triggers = []

        if not self.is_available:
            logger.warning("GSC not available for refresh check")
            return (False, triggers)

        try:
            # Get current page performance
            current_perf = await self._gsc.analyze_page(page_url, days=30)

            # Get historical performance (60-90 days ago)
            # Note: We'd need historical data storage for true trend analysis
            # For now, use longer period as baseline
            baseline_perf = await self._gsc.analyze_page(page_url, days=90)

            if not current_perf.keywords:
                logger.info(f"No keyword data for {page_url}")
                return (False, triggers)

            # Check 1: Position drop trigger
            if current_perf.primary_keyword:
                pk = current_perf.primary_keyword
                threshold = self._config['ranking_drop_threshold']

                if pk.position > threshold and pk.impressions > 100:
                    triggers.append(RefreshTrigger(
                        trigger_type='position_drop',
                        severity='critical' if pk.position > 10 else 'warning',
                        message=f"Primary keyword '{pk.query}' dropped to position {pk.position:.1f} (threshold: {threshold})",
                        data={
                            'keyword': pk.query,
                            'position': pk.position,
                            'threshold': threshold,
                            'impressions': pk.impressions
                        }
                    ))

            # Check 2: CTR underperformance
            for kw in current_perf.keywords[:5]:  # Top 5 keywords
                if kw.impressions < 50:
                    continue

                pos_rounded = min(round(kw.position), 10)
                expected_ctr = CTR_BY_POSITION.get(pos_rounded, 0.025)
                actual_ctr = kw.ctr

                if actual_ctr < expected_ctr * self._config['ctr_underperform_ratio']:
                    triggers.append(RefreshTrigger(
                        trigger_type='ctr_underperform',
                        severity='warning',
                        message=f"CTR for '{kw.query}' is {actual_ctr:.1%} (expected {expected_ctr:.1%} at position {pos_rounded})",
                        data={
                            'keyword': kw.query,
                            'actual_ctr': actual_ctr,
                            'expected_ctr': expected_ctr,
                            'position': kw.position
                        }
                    ))
                    break  # One CTR warning is enough

            # Check 3: Impressions spike (opportunity)
            if baseline_perf.total_impressions > 0:
                impressions_change = (current_perf.total_impressions - baseline_perf.total_impressions) / baseline_perf.total_impressions

                if impressions_change > self._config['impressions_increase_threshold']:
                    triggers.append(RefreshTrigger(
                        trigger_type='impressions_spike',
                        severity='info',
                        message=f"Impressions increased by {impressions_change:.0%} - opportunity to optimize",
                        data={
                            'current_impressions': current_perf.total_impressions,
                            'baseline_impressions': baseline_perf.total_impressions,
                            'change_percent': impressions_change
                        }
                    ))

            # Check 4: Annual refresh trigger
            current_month = datetime.now().month
            if current_month in self._config['annual_refresh_months']:
                triggers.append(RefreshTrigger(
                    trigger_type='annual_refresh',
                    severity='info',
                    message=f"Scheduled annual content refresh (month {current_month})",
                    data={'refresh_months': self._config['annual_refresh_months']}
                ))

            # Check 5: Staleness trigger
            if last_updated:
                days_since_update = (datetime.now() - last_updated).days
                max_days = self._config['max_days_without_update']

                if days_since_update > max_days:
                    triggers.append(RefreshTrigger(
                        trigger_type='staleness',
                        severity='warning',
                        message=f"Content not updated in {days_since_update} days (max: {max_days})",
                        data={
                            'days_since_update': days_since_update,
                            'max_days': max_days,
                            'last_updated': last_updated.isoformat()
                        }
                    ))

            needs_refresh = any(t.severity in ['critical', 'warning'] for t in triggers)

            return (needs_refresh, triggers)

        except Exception as e:
            logger.error(f"Refresh check failed for {page_url}: {e}")
            return (False, [])

    async def get_refresh_candidates(
        self,
        base_url: str = "/blog/",
        limit: int = 20
    ) -> List[ContentRefreshResult]:
        """
        Get all content pages that need refresh, prioritized by urgency.

        Args:
            base_url: URL prefix to filter (e.g., "/blog/")
            limit: Maximum pages to return

        Returns:
            List of ContentRefreshResult sorted by priority
        """
        candidates = []

        if not self.is_available:
            logger.warning("GSC not available for refresh candidates")
            return candidates

        try:
            # Get all pages under base_url
            # Note: This would require a GSC pages query which is different from keyword query
            # For now, we'll provide a helper that works with known URLs

            logger.info(f"Refresh candidate check requires specific page URLs")
            logger.info(f"Use check_refresh_needed() with specific page URLs")

            return candidates

        except Exception as e:
            logger.error(f"Failed to get refresh candidates: {e}")
            return candidates

    async def analyze_content_health(
        self,
        page_urls: List[str]
    ) -> Dict[str, ContentRefreshResult]:
        """
        Analyze content health for multiple pages.

        Args:
            page_urls: List of page URLs to analyze

        Returns:
            Dict mapping URL to ContentRefreshResult
        """
        results = {}

        for url in page_urls:
            needs_refresh, triggers = await self.check_refresh_needed(url)

            # Determine priority
            if any(t.severity == 'critical' for t in triggers):
                priority = 1
            elif any(t.severity == 'warning' for t in triggers):
                priority = 2
            else:
                priority = 3

            # Get additional metrics
            perf = await self._gsc.analyze_page(url, days=30)

            results[url] = ContentRefreshResult(
                url=url,
                needs_refresh=needs_refresh,
                triggers=triggers,
                priority=priority,
                primary_keyword=perf.primary_keyword.query if perf.primary_keyword else None,
                current_position=perf.primary_keyword.position if perf.primary_keyword else None,
                traffic_potential=perf.primary_keyword.traffic_potential if perf.primary_keyword else 0
            )

        return results

    def generate_refresh_report(
        self,
        results: Dict[str, ContentRefreshResult]
    ) -> str:
        """
        Generate a human-readable refresh report.

        Args:
            results: Dict from analyze_content_health

        Returns:
            Formatted report string
        """
        lines = [
            "=" * 60,
            "CONTENT REFRESH REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
            ""
        ]

        # Group by priority
        critical = [r for r in results.values() if r.priority == 1]
        warning = [r for r in results.values() if r.priority == 2]
        info = [r for r in results.values() if r.priority == 3 and r.triggers]

        if critical:
            lines.append("🚨 CRITICAL (Refresh Immediately)")
            lines.append("-" * 40)
            for r in critical:
                lines.append(f"  {r.url}")
                for t in r.triggers:
                    lines.append(f"    → {t.message}")
            lines.append("")

        if warning:
            lines.append("⚠️  WARNING (Schedule Refresh)")
            lines.append("-" * 40)
            for r in warning:
                lines.append(f"  {r.url}")
                for t in r.triggers:
                    lines.append(f"    → {t.message}")
            lines.append("")

        if info:
            lines.append("ℹ️  INFO (Opportunities)")
            lines.append("-" * 40)
            for r in info:
                lines.append(f"  {r.url}")
                for t in r.triggers:
                    lines.append(f"    → {t.message}")
            lines.append("")

        # Summary
        lines.append("=" * 60)
        lines.append("SUMMARY")
        lines.append(f"  Total analyzed: {len(results)}")
        lines.append(f"  Critical: {len(critical)}")
        lines.append(f"  Warning: {len(warning)}")
        lines.append(f"  Info: {len(info)}")
        lines.append("=" * 60)

        return "\n".join(lines)


# CLI entry point
if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python content_monitor.py <page_url> [page_url2 ...]")
            print("\nExamples:")
            print("  python content_monitor.py /blog/best-mcp-servers")
            print("  python content_monitor.py /blog/crm-tools /blog/ad-analytics")
            sys.exit(1)

        page_urls = sys.argv[1:]

        async with ContentMonitor() as monitor:
            if not monitor.is_available:
                print("❌ GSC not available. Check credentials.")
                sys.exit(1)

            print(f"🔍 Analyzing {len(page_urls)} page(s)...")
            results = await monitor.analyze_content_health(page_urls)

            report = monitor.generate_refresh_report(results)
            print(report)

    asyncio.run(main())
