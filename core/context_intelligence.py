"""
Context Intelligence - Hyper-Relevant Table Generation

Understands research intent from keywords and SERP context to generate
context-aware table templates with intelligent breakdowns (company size,
industry, geography, maturity level).

Instead of generic tables, generates hyper-specific breakdowns:
- "marketing automation benchmarks" → tables by company size, industry, maturity
- "CRM pricing" → tables by tier, features, company size
- "lead gen performance" → tables by channel, industry, optimization level

Integrates with:
- research_config.json (intent patterns and table requirements)
- core/generator.py (inject table templates into research prompt)
- core/content_validator.py (validate table presence and quality)
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ContextIntelligence:
    """Understand research topic context to generate hyper-relevant data breakdowns."""

    def __init__(self, research_config_path: Optional[Path] = None, icp_config_path: Optional[Path] = None):
        """
        Initialize context intelligence with research intent patterns AND ICP industry data.

        Args:
            research_config_path: Path to research_config.json (optional)
            icp_config_path: Path to icp_config.json (optional)
        """
        if research_config_path is None:
            research_config_path = Path(__file__).parent.parent / 'config' / 'research_config.json'
        if icp_config_path is None:
            icp_config_path = Path(__file__).parent.parent / 'config' / 'icp_config.json'

        self.intent_patterns = self._load_intent_patterns(research_config_path)
        self.icp_industries = self._load_icp_industries(icp_config_path)

    def _load_intent_patterns(self, path: Path) -> Dict[str, Any]:
        """Load research intent patterns from config."""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                patterns = config.get('research_intent_patterns', {})
                logger.debug(f"✅ Loaded {len(patterns)} research intent patterns")
                return patterns
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"⚠️  Could not load research_config.json: {e}, using defaults")
            return self._get_default_patterns()

    def _get_default_patterns(self) -> Dict[str, Any]:
        """Fallback default intent patterns."""
        return {
            'benchmarking': {
                'keywords': ['benchmark', 'benchmarks', 'industry standards'],
                'required_breakdowns': ['company_size', 'industry'],
                'table_types': ['performance_metrics', 'cost_analysis'],
                'min_tables': 3
            },
            'market_research': {
                'keywords': ['market size', 'market analysis', 'adoption rate'],
                'required_breakdowns': ['market_segment', 'geography'],
                'table_types': ['market_size', 'adoption_rates'],
                'min_tables': 3
            }
        }

    def _load_icp_industries(self, path: Path) -> Dict[str, List[str]]:
        """
        Load ICP industry taxonomy from config.

        Returns dict with industry categories as keys and list of sub-industries as values.
        Example: {'home_services': ['solar installers', 'HVAC', ...], ...}
        """
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                # Extract industries from sales_led_services
                industries_raw = config.get('primary_icps', {}).get('sales_led_services', {}).get('industries', {})

                # Flatten to: {'home_services': ['solar installers', 'HVAC', ...], ...}
                industries = {}
                for category, items in industries_raw.items():
                    industries[category] = items if isinstance(items, list) else []

                total_sub_industries = sum(len(v) for v in industries.values())
                logger.debug(f"✅ Loaded {len(industries)} ICP industry categories with {total_sub_industries} sub-industries")
                return industries
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"⚠️  Could not load icp_config.json: {e}, using generic industries")
            return {}

    def _format_category_name(self, category: str) -> str:
        """
        Format category name for display.

        Example: 'home_services' → 'Home Services'
        """
        return category.replace('_', ' ').title()

    def detect_research_intent(
        self,
        keyword: str,
        serp_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        """
        Classify research type from keyword and SERP context.

        Args:
            keyword: Primary keyword being researched
            serp_context: Optional SERP data for additional context

        Returns:
            Tuple of (intent_type, confidence_score)

        Intent types:
        - benchmarking: Performance metrics, cost comparisons
        - market_research: Market size, adoption rates, trends
        - comparison: Feature matrices, pricing comparisons
        - performance_analysis: Before/after, optimization results
        - roi_analysis: Cost/benefit, payback, TCO
        """
        keyword_lower = keyword.lower()
        scores = {}

        # Score each intent type based on keyword matches
        for intent_type, config in self.intent_patterns.items():
            keywords = config.get('keywords', [])
            score = 0

            # Exact keyword matches
            for kw in keywords:
                if kw in keyword_lower:
                    score += 10

            # Partial matches
            keyword_terms = set(keyword_lower.split())
            for kw in keywords:
                kw_terms = set(kw.split())
                overlap = keyword_terms & kw_terms
                score += len(overlap)

            scores[intent_type] = score

        # Get best match
        if not scores or max(scores.values()) == 0:
            # Fallback to benchmarking
            return 'benchmarking', 0.5

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]
        confidence = min(1.0, max_score / 20)  # Normalize to 0-1

        logger.info(f"🎯 Detected research intent: {best_intent} (confidence: {confidence:.2f})")
        return best_intent, confidence

    def get_required_breakdowns(
        self,
        research_intent: str
    ) -> List[str]:
        """
        Get required data breakdowns for research intent.

        Args:
            research_intent: Detected intent type

        Returns:
            List of required breakdown dimensions

        Examples:
        - benchmarking → ['company_size', 'industry', 'geography', 'maturity_level']
        - roi_analysis → ['investment_level', 'payback_period', 'company_size', 'industry']
        """
        config = self.intent_patterns.get(research_intent, {})
        breakdowns = config.get('required_breakdowns', ['company_size', 'industry'])

        logger.debug(f"📊 Required breakdowns for {research_intent}: {len(breakdowns)} dimensions")
        return breakdowns

    def generate_table_templates(
        self,
        research_intent: str,
        keyword: str
    ) -> List[Dict[str, Any]]:
        """
        Create table structure templates based on intent.

        Args:
            research_intent: Detected intent type (benchmarking, market_research, etc.)
            keyword: Primary research keyword for customization

        Returns:
            List of table template dicts with structure and examples

        Each template includes:
        - title: Table title/heading
        - columns: List of column headers
        - rows: List of row dimensions (breakdowns)
        - example_data: Sample cell values for guidance
        - requirements: Specific requirements (ranges, alignment, etc.)
        """
        config = self.intent_patterns.get(research_intent, {})
        table_types = config.get('table_types', [])
        breakdowns = config.get('required_breakdowns', [])

        templates = []

        # Generate templates based on table types
        if 'performance_metrics' in table_types:
            templates.append(self._generate_performance_metrics_table(keyword, breakdowns))

        if 'cost_analysis' in table_types or 'pricing_comparison' in table_types:
            templates.append(self._generate_cost_analysis_table(keyword, breakdowns))

        if 'roi_comparison' in table_types or 'cost_benefit' in table_types:
            templates.append(self._generate_roi_table(keyword, breakdowns))

        if 'market_size' in table_types:
            templates.append(self._generate_market_size_table(keyword, breakdowns))

        if 'adoption_rates' in table_types:
            templates.append(self._generate_adoption_table(keyword, breakdowns))

        if 'feature_matrix' in table_types:
            templates.append(self._generate_feature_matrix_table(keyword, breakdowns))

        logger.info(f"📋 Generated {len(templates)} table templates for {research_intent}")
        return templates

    def _generate_performance_metrics_table(
        self,
        keyword: str,
        breakdowns: List[str]
    ) -> Dict[str, Any]:
        """Generate performance metrics comparison table."""
        # Primary breakdown dimension (company size or maturity level)
        primary_dimension = 'company_size' if 'company_size' in breakdowns else 'maturity_level'

        if primary_dimension == 'company_size':
            rows = ['SMB (1-50)', 'Mid-Market (51-500)', 'Enterprise (500+)']
        else:
            rows = ['Basic', 'Intermediate', 'Advanced', 'Best-in-Class']

        return {
            'title': f'Performance Metrics by {primary_dimension.replace("_", " ").title()}',
            'columns': ['Segment', 'Baseline Performance', 'Average Performance', 'Top Quartile', 'Best-in-Class'],
            'rows': rows,
            'example_data': {
                'Baseline Performance': '[metric range]',
                'Average Performance': '[metric range]',
                'Top Quartile': '[metric range]',
                'Best-in-Class': '[metric range]'
            },
            'requirements': [
                'Use ranges for all metrics (e.g., "$50-$100" not "$75")',
                'Include units (%, $, hours, etc.)',
                'Right-align numerical columns',
                'Bold the "Best-in-Class" column for emphasis'
            ],
            'guidance': f'Populate with real data from research about {keyword} performance across different {primary_dimension.replace("_", " ")}.'
        }

    def _generate_cost_analysis_table(
        self,
        keyword: str,
        breakdowns: List[str]
    ) -> Dict[str, Any]:
        """Generate cost/pricing analysis table."""
        primary_dimension = 'company_size' if 'company_size' in breakdowns else 'pricing_tier'

        if primary_dimension == 'company_size':
            rows = ['SMB (1-50 employees)', 'Mid-Market (51-500)', 'Enterprise (500+)']
        else:
            rows = ['Starter/Basic', 'Professional', 'Business/Premium', 'Enterprise']

        return {
            'title': f'Pricing Breakdown by {primary_dimension.replace("_", " ").title()}',
            'columns': ['Tier/Size', 'Setup Cost', 'Monthly Cost', 'Annual Spend', 'Cost per User/Lead'],
            'rows': rows,
            'example_data': {
                'Setup Cost': '$500-$1,500',
                'Monthly Cost': '$100-$300',
                'Annual Spend': '$1,200-$3,600',
                'Cost per User/Lead': '$5-$15'
            },
            'requirements': [
                'ALL costs must be ranges (e.g., "$100-$300" not "$200")',
                'Include both one-time and recurring costs',
                'Right-align all currency columns',
                'Note hidden costs or additional fees in context'
            ],
            'guidance': f'Extract real pricing data for {keyword} from research sources. Include setup, monthly, and per-unit costs.'
        }

    def _generate_roi_table(
        self,
        keyword: str,
        breakdowns: List[str]
    ) -> Dict[str, Any]:
        """Generate ROI/payback analysis table with support for industry breakdowns."""
        # Determine primary dimension: industry, investment_level, or company_size
        if 'industry' in breakdowns:
            primary_dimension = 'industry'
        elif 'investment_level' in breakdowns:
            primary_dimension = 'investment_level'
        else:
            primary_dimension = 'company_size'

        if primary_dimension == 'industry':
            # Use REAL ICP industries if available (user's requirement: exhaustive industry coverage)
            if self.icp_industries:
                # EXHAUSTIVE: Show ALL industry categories for thorough breakdown
                rows = []
                for category, sub_industries in self.icp_industries.items():
                    formatted_category = self._format_category_name(category)
                    # Include category with top 2 sub-industry examples
                    example_businesses = ', '.join(sub_industries[:2]) if sub_industries else ''
                    if example_businesses:
                        rows.append(f'{formatted_category} ({example_businesses})')
                    else:
                        rows.append(formatted_category)

                # If no ICP industries loaded, fallback to generic
                if not rows:
                    rows = ['Technology/SaaS', 'Professional Services', 'Healthcare', 'Finance/Insurance']
            else:
                rows = ['Technology/SaaS', 'Professional Services', 'Healthcare', 'Finance/Insurance']
        elif primary_dimension == 'investment_level':
            rows = ['Low ($0-$5K)', 'Medium ($5K-$20K)', 'High ($20K-$100K)', 'Enterprise ($100K+)']
        else:
            rows = ['SMB', 'Mid-Market', 'Enterprise']

        return {
            'title': f'ROI Analysis by {primary_dimension.replace("_", " ").title()}',
            'columns': ['Segment/Level', 'Initial Cost', 'Annual Savings', 'Payback Period', '3-Year ROI'],
            'rows': rows,
            'example_data': {
                'Initial Cost': '$500-$1,500',
                'Annual Savings': '$12,000-$24,000',
                'Payback Period': '2-4 months',
                '3-Year ROI': '450-600%'
            },
            'requirements': [
                'Use ranges for all values',
                'Payback period in months or years',
                'ROI as percentage (e.g., "450-600%")',
                'Right-align numerical columns'
            ],
            'guidance': f'Calculate ROI metrics for {keyword} based on research data. Show clear value proposition across segments. Use REAL ICP industries from icp_config.json for exhaustive industry coverage.'
        }

    def _generate_market_size_table(
        self,
        keyword: str,
        breakdowns: List[str]
    ) -> Dict[str, Any]:
        """Generate market size/segmentation table with REAL ICP industries when available."""
        # Determine primary dimension: industry, geography, or market_segment
        if 'industry' in breakdowns:
            primary_dimension = 'industry'
        elif 'geography' in breakdowns:
            primary_dimension = 'geography'
        else:
            primary_dimension = 'market_segment'

        if primary_dimension == 'industry':
            # Use REAL ICP industries if available (user's requirement: exhaustive industry coverage)
            if self.icp_industries:
                # EXHAUSTIVE: Show ALL industry categories for thorough breakdown
                rows = []
                for category, sub_industries in self.icp_industries.items():
                    formatted_category = self._format_category_name(category)
                    # Include category with top 2 sub-industry examples
                    example_businesses = ', '.join(sub_industries[:2]) if sub_industries else ''
                    if example_businesses:
                        rows.append(f'{formatted_category} ({example_businesses})')
                    else:
                        rows.append(formatted_category)

                # If no ICP industries loaded, fallback to generic
                if not rows:
                    rows = ['Technology/SaaS', 'Professional Services', 'Healthcare', 'Finance/Insurance', 'Manufacturing']
            else:
                rows = ['Technology/SaaS', 'Professional Services', 'Healthcare', 'Finance/Insurance', 'Manufacturing']
        elif primary_dimension == 'geography':
            rows = ['North America', 'Europe', 'Asia-Pacific', 'Latin America', 'Global']
        else:
            rows = ['SMB Segment', 'Mid-Market', 'Enterprise', 'Total Market']

        return {
            'title': f'Market Size by {primary_dimension.replace("_", " ").title()}',
            'columns': ['Region/Segment', '2024 Market Size', 'YoY Growth', '2025 Projection', '2025-2027 CAGR'],
            'rows': rows,
            'example_data': {
                '2024 Market Size': '$5.2B-$6.8B',
                'YoY Growth': '15-18%',
                '2025 Projection': '$6.0B-$8.0B',
                '2025-2027 CAGR': '12-16%'
            },
            'requirements': [
                'Use ranges for market sizes',
                'Include specific years (2024, 2025, 2026)',
                'CAGR (Compound Annual Growth Rate) as percentage',
                'Right-align all numerical columns'
            ],
            'guidance': f'Extract market sizing data for {keyword} from industry reports and analyst forecasts. Use REAL ICP industries from icp_config.json for exhaustive industry coverage.'
        }

    def _generate_adoption_table(
        self,
        keyword: str,
        breakdowns: List[str]
    ) -> Dict[str, Any]:
        """Generate adoption rate/maturity table with REAL ICP industries when available."""
        primary_dimension = 'industry' if 'industry' in breakdowns else 'company_size'

        if primary_dimension == 'industry':
            # Use REAL ICP industries if available (user's requirement: exhaustive industry coverage)
            if self.icp_industries:
                # EXHAUSTIVE: Show ALL industry categories for thorough breakdown
                rows = []
                for category, sub_industries in self.icp_industries.items():
                    formatted_category = self._format_category_name(category)
                    # Include category with top 2 sub-industry examples
                    example_businesses = ', '.join(sub_industries[:2]) if sub_industries else ''
                    if example_businesses:
                        rows.append(f'{formatted_category} ({example_businesses})')
                    else:
                        rows.append(formatted_category)

                # If no ICP industries loaded, fallback to generic
                if not rows:
                    rows = ['Technology/SaaS', 'Professional Services', 'Healthcare', 'Finance/Insurance', 'Manufacturing']
            else:
                rows = ['Technology/SaaS', 'Professional Services', 'Healthcare', 'Finance/Insurance', 'Manufacturing']
        else:
            rows = ['SMB (1-50)', 'Mid-Market (51-500)', 'Enterprise (500+)']

        return {
            'title': f'Adoption Rate by {primary_dimension.replace("_", " ").title()}',
            'columns': ['Industry/Segment', 'Current Adoption', 'YoY Growth', 'Market Maturity', 'Avg Investment'],
            'rows': rows,
            'example_data': {
                'Current Adoption': '65-72%',
                'YoY Growth': '+12%',
                'Market Maturity': 'Mature/Growing/Emerging',
                'Avg Investment': '$600-$1,200/mo'
            },
            'requirements': [
                'Adoption as percentage range',
                'Maturity as categorical (Emerging/Growing/Mature)',
                'Include average spend ranges',
                'Bold the highest adoption segment'
            ],
            'guidance': f'Show adoption patterns for {keyword} across different {primary_dimension.replace("_", " ")}. Use REAL ICP industries from icp_config.json for exhaustive coverage.'
        }

    def _generate_feature_matrix_table(
        self,
        keyword: str,
        breakdowns: List[str]
    ) -> Dict[str, Any]:
        """Generate feature comparison matrix."""
        return {
            'title': 'Feature Comparison Matrix',
            'columns': ['Feature Category', 'Basic Tier', 'Professional', 'Business', 'Enterprise'],
            'rows': [
                'Core Features',
                'Advanced Analytics',
                'Integration Options',
                'Support Level',
                'User Limits'
            ],
            'example_data': {
                'Basic Tier': 'Limited / ✗ / ✓',
                'Professional': '✓ / Limited / ✓',
                'Business': '✓ / ✓ / Advanced',
                'Enterprise': '✓ / ✓ / Unlimited'
            },
            'requirements': [
                'Use ✓ for included, ✗ for not included',
                'Use "Limited" or specific caps (e.g., "Up to 10 users")',
                'Highlight differentiators with bold text',
                'Include footnotes for complex features'
            ],
            'guidance': f'Compare feature availability for {keyword} across pricing tiers or product options.'
        }

    def format_table_requirements_for_prompt(
        self,
        templates: List[Dict[str, Any]]
    ) -> str:
        """
        Format table templates into prompt-ready text.

        Args:
            templates: List of table template dicts

        Returns:
            Formatted string to inject into research prompt

        Output format:
        ```
        ## Required Tables (Context-Intelligent for [keyword])

        ### Table 1: [Title]
        | Column 1 | Column 2 | Column 3 |
        |----------|----------|----------|
        | Row 1    | [data]   | [data]   |
        ...

        Requirements:
        - [requirement 1]
        - [requirement 2]

        ### Table 2: ...
        ```
        """
        if not templates:
            return ""

        lines = ["## CONTEXT-INTELLIGENT TABLE REQUIREMENTS (CRITICAL):\n"]

        for i, template in enumerate(templates, 1):
            lines.append(f"### Table {i}: {template['title']}\n")

            # Generate table skeleton
            columns = template['columns']
            lines.append(f"| {' | '.join(columns)} |")
            lines.append(f"| {' | '.join(['---' for _ in columns])} |")

            # Add example rows
            for row_label in template['rows'][:3]:  # First 3 rows as examples
                row_data = [row_label]
                example_data = template.get('example_data', {})
                for col in columns[1:]:  # Skip first column (row labels)
                    cell_value = example_data.get(col, '[data]')
                    row_data.append(cell_value)
                lines.append(f"| {' | '.join(row_data)} |")

            lines.append(f"| {'... | ' * len(columns)}|\n")

            # Add requirements
            requirements = template.get('requirements', [])
            if requirements:
                lines.append("**Requirements:**")
                for req in requirements:
                    lines.append(f"- {req}")

            # Add guidance
            guidance = template.get('guidance', '')
            if guidance:
                lines.append(f"\n**Guidance:** {guidance}\n")

            lines.append("")  # Blank line between tables

        return '\n'.join(lines)

    def validate_table_coverage(
        self,
        content: str,
        research_intent: str,
        templates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate that content includes required context-intelligent tables.

        Args:
            content: Generated MDX content
            templates: Expected table templates
            research_intent: Detected research intent

        Returns:
            Validation report dict

        Checks:
        - Are required tables present?
        - Do tables have correct breakdowns?
        - Are numerical values ranges (not single points)?
        - Are tables properly formatted?
        """
        # Extract tables from content
        table_pattern = r'(\|.+\|\n\|[-:\s|]+\|\n(?:\|.+\|\n)+)'
        found_tables = re.findall(table_pattern, content)

        config = self.intent_patterns.get(research_intent, {})
        min_tables = config.get('min_tables', 2)
        required_breakdowns = set(config.get('required_breakdowns', []))

        report = {
            'tables_found': len(found_tables),
            'tables_required': min_tables,
            'table_count_met': len(found_tables) >= min_tables,
            'breakdown_coverage': 0.0,
            'range_compliance': 0.0,
            'issues': []
        }

        if len(found_tables) < min_tables:
            report['issues'].append(f"Only {len(found_tables)} tables found (min: {min_tables})")

        # Check for required breakdowns in table text
        content_lower = content.lower()
        found_breakdowns = set()
        for breakdown in required_breakdowns:
            breakdown_text = breakdown.replace('_', ' ').lower()
            if breakdown_text in content_lower:
                found_breakdowns.add(breakdown)

        if required_breakdowns:
            report['breakdown_coverage'] = len(found_breakdowns) / len(required_breakdowns)

        missing_breakdowns = required_breakdowns - found_breakdowns
        if missing_breakdowns:
            report['issues'].append(f"Missing breakdowns: {', '.join(missing_breakdowns)}")

        # Check range compliance (values should be ranges, not single points)
        range_pattern = r'\$?\d+(?:,\d{3})*(?:\.\d+)?\s*[-–]\s*\$?\d+(?:,\d{3})*(?:\.\d+)?'
        ranges_found = len(re.findall(range_pattern, content))
        single_values = len(re.findall(r'\$?\d+(?:,\d{3})*(?:\.\d+)?(?!\s*[-–])', content))

        if ranges_found + single_values > 0:
            report['range_compliance'] = ranges_found / (ranges_found + single_values)

        if report['range_compliance'] < 0.5:
            report['issues'].append(f"Low range usage: {int(report['range_compliance'] * 100)}% (target: 50%+)")

        # Overall quality score
        report['quality_score'] = int(
            (report['table_count_met'] * 40) +
            (report['breakdown_coverage'] * 30) +
            (report['range_compliance'] * 30)
        )

        logger.info(f"🔍 Table validation: {len(found_tables)} tables, {int(report['breakdown_coverage'] * 100)}% breakdown coverage, score: {report['quality_score']}/100")

        return report
