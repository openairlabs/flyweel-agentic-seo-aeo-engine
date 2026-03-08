"""
Intelligent Benchmark Extraction - NO HARDCODED DATA
Dynamically extracts industry benchmarks from research context for ANY topic.

This module discovers:
- What metrics are relevant (from keyword + research)
- Which industries apply (from ICP config + keyword)
- What data exists (from SERP/Reddit/Quora)
- How to structure tables (based on research intent)

NO HARDCODED BENCHMARK VALUES - everything is extracted from research.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IntelligentBenchmarkExtractor:
    """
    Extract industry benchmarks intelligently from research data.

    NO HARDCODED METRICS - discovers what to measure from research context.
    DOMAIN-CONSTRAINED: Focused on Brand's macro topics defined in the configuration.
    Intelligent within domain, not generic across all business topics.
    """

    def __init__(self, patterns_config_path: Optional[Path] = None):
        """Initialize with flexible extraction patterns (not hardcoded data)."""
        if patterns_config_path is None:
            patterns_config_path = Path(__file__).parent.parent / 'config' / 'benchmark_extraction_patterns.json'

        self.patterns = self._load_patterns(patterns_config_path)
        logger.info(f"🧠 Initialized IntelligentBenchmarkExtractor with patterns from {patterns_config_path}")

    def detect_relevant_metrics(self, keyword: str, serp_context: Dict, reddit_context: Dict) -> List[str]:
        """
        Detect which metrics are relevant for THIS specific research topic.

        Prioritizes metrics mentioned in keyword, then expands from research.
        Smart, focused, accurate.

        Args:
            keyword: The research keyword
            serp_context: SERP results with titles, snippets
            reddit_context: Reddit insights

        Returns:
            List of detected metric names (keyword metrics prioritized)
        """
        keyword_lower = keyword.lower()

        # Extract metrics explicitly mentioned in keyword
        keyword_metrics = self._extract_metric_names(keyword_lower)

        # If keyword specifies metrics, use ONLY those (focused)
        # If keyword has no metrics, extract from research (exploratory)
        if keyword_metrics:
            logger.info(f"🎯 Using {len(keyword_metrics)} metrics FROM KEYWORD: {keyword_metrics}")
            return keyword_metrics

        # No metrics in keyword - extract from research
        serp_text = ''
        if serp_context:
            if 'serp_analysis' in serp_context and serp_context['serp_analysis']:
                analysis = serp_context['serp_analysis'].get('analysis', '')
                serp_text += str(analysis) + ' '
            if 'paa_questions' in serp_context:
                paa_text = ' '.join(serp_context.get('paa_questions', []))
                serp_text += paa_text + ' '
            if 'search_results' in serp_context:
                results_text = ' '.join([
                    str(item.get('title', '')) + ' ' + str(item.get('snippet', ''))
                    for item in serp_context.get('search_results', [])[:10]
                ])
                serp_text += results_text

        reddit_text = str(reddit_context).lower() if reddit_context else ''
        combined_text = serp_text.lower() + ' ' + reddit_text
        research_metrics = self._extract_metric_names(combined_text)

        # Limit to top 8 metrics for exploratory research
        final_metrics = research_metrics[:8]

        logger.info(f"🔍 No metrics in keyword - extracted {len(final_metrics)} from research: {final_metrics}")
        return final_metrics

    def _extract_metric_names(self, text: str) -> List[str]:
        """
        Extract actual metric names from research using config patterns ONLY.

        Uses predefined metric patterns from config to avoid extracting garbage phrases.
        Simple, accurate, AI-friendly.
        """
        metrics = set()

        # Use ONLY config patterns - they're accurate and domain-specific
        for metric_category, config in self.patterns.get('metric_detection_patterns', {}).items():
            # Skip documentation/metadata fields
            if metric_category.startswith('_'):
                continue

            if not isinstance(config, dict):
                continue

            patterns_list = config.get('patterns', [])
            if not isinstance(patterns_list, list):
                continue

            # Check each pattern against text
            for pattern in patterns_list:
                if isinstance(pattern, str) and pattern.lower() in text.lower():
                    metrics.add(pattern.lower())

        # Return clean, verified metrics (no garbage phrases)
        return list(metrics)[:20]

    def discover_industry_segments(
        self,
        keyword: str,
        icp_config: Dict,
        research_context: Dict
    ) -> Dict[str, List[str]]:
        """
        Discover which industry segments are relevant for THIS research.

        Instead of forcing all ICP industries, intelligently detect:
        - If keyword is "solar lead generation" → focus on home_services/solar
        - If keyword is "SaaS pricing benchmarks" → focus on b2b_tech/SaaS
        - If keyword is generic → use all ICP industries

        Args:
            keyword: The research keyword
            icp_config: Loaded ICP configuration
            research_context: Dict with 'serp', 'reddit', 'quora' keys

        Returns:
            Dict like {"industry": ["Home Services/solar", ...], "company_size": ["SMB", ...]}
        """
        keyword_lower = keyword.lower()
        keyword_words = set(keyword_lower.split())
        segments = {}

        # Dimension 1: Industry Vertical (from ICP config)
        icp_industries = icp_config.get('primary_icps', {}).get('sales_led_services', {}).get('industries', {})

        relevant_industries = []
        for category, sub_industries in icp_industries.items():
            sub_ind_list = sub_industries if isinstance(sub_industries, list) else []
            for sub_ind in sub_ind_list:
                sub_lower = sub_ind.lower()

                # Exact substring match
                if sub_lower in keyword_lower:
                    relevant_industries.append(f"{category}/{sub_ind}")
                    continue

                # Word-level match (e.g., "solar" from "solar installers" matches "solar lead generation")
                sub_words = set(sub_lower.split())
                sub_significant_words = {w for w in sub_words if w not in ['installers', 'brokers', 'clinics', 'practices', 'firms', 'agencies', 'companies', 'services', 'providers']}

                if sub_significant_words & keyword_words:
                    relevant_industries.append(f"{category}/{sub_ind}")
                    continue

                # Check in SERP analysis and PAA questions
                serp_data = research_context.get('serp', {})
                serp_text = ''

                # Extract text from serp_analysis
                if 'serp_analysis' in serp_data and serp_data['serp_analysis']:
                    analysis = serp_data['serp_analysis'].get('analysis', '')
                    serp_text += str(analysis) + ' '

                # Extract text from PAA questions
                if 'paa_questions' in serp_data:
                    paa_text = ' '.join(serp_data.get('paa_questions', []))
                    serp_text += paa_text + ' '

                # Extract text from search_results if available (legacy)
                if 'search_results' in serp_data:
                    for item in serp_data.get('search_results', [])[:5]:
                        item_text = str(item.get('title', '')) + ' ' + str(item.get('snippet', ''))
                        serp_text += item_text + ' '

                serp_text_lower = serp_text.lower()
                serp_words = set(serp_text_lower.split())

                # Check both exact match and word match in SERP
                if sub_lower in serp_text_lower or (sub_significant_words & serp_words):
                    relevant_industries.append(f"{category}/{sub_ind}")
                    continue

        # If no specific match, use category-level (not all 45 sub-industries)
        if not relevant_industries:
            relevant_industries = [
                cat.replace('_', ' ').title()
                for cat in icp_industries.keys()
            ][:8]  # Limit to top 8 categories for manageability

        segments['industry'] = relevant_industries

        # Dimension 2: Company Size (detect from research)
        size_segments = self._extract_size_segments(research_context)
        if size_segments:
            segments['company_size'] = size_segments

        # Dimension 3: Geography (detect from research)
        geo_segments = self._extract_geo_segments(research_context)
        if geo_segments:
            segments['geography'] = geo_segments

        logger.info(f"🎯 Discovered {sum(len(v) for v in segments.values())} segments across {len(segments)} dimensions")
        return segments

    def _extract_size_segments(self, research_context: Dict) -> List[str]:
        """Extract company size segments mentioned in research."""
        size_keywords = {
            'SMB': ['smb', 'small business', 'small-medium', '1-50', '< 50 employees'],
            'Mid-Market': ['mid-market', 'middle market', '50-500', '100-1000 employees'],
            'Enterprise': ['enterprise', 'large enterprise', '500+', '1000+', 'fortune']
        }

        found_segments = []
        research_text = str(research_context).lower()

        for segment_name, keywords in size_keywords.items():
            if any(kw in research_text for kw in keywords):
                found_segments.append(segment_name)

        return found_segments or ['SMB', 'Mid-Market', 'Enterprise']  # Default if none detected

    def _extract_geo_segments(self, research_context: Dict) -> List[str]:
        """Extract geography segments mentioned in research."""
        geo_keywords = {
            'North America': ['north america', 'us', 'usa', 'canada', 'united states'],
            'Europe': ['europe', 'eu', 'emea', 'uk', 'germany', 'france'],
            'APAC': ['apac', 'asia pacific', 'australia', 'singapore', 'japan']
        }

        found_geos = []
        research_text = str(research_context).lower()

        for geo_name, keywords in geo_keywords.items():
            if any(kw in research_text for kw in keywords):
                found_geos.append(geo_name)

        return found_geos  # May be empty if not geography-specific research

    def build_intelligent_table_requirements(
        self,
        keyword: str,
        metrics: List[str],
        segments: Dict[str, List[str]],
        research_intent: str
    ) -> str:
        """
        Generate comprehensive multi-table requirements based on research intent.

        NO HARDCODED TABLE STRUCTURES - dynamically generates 3-5 table types
        based on detected metrics, segments, and research intent.

        Args:
            keyword: The research keyword
            metrics: List of detected metric names
            segments: Dict of segment dimensions and their values
            research_intent: Detected research intent (benchmarking, roi_analysis, etc.)

        Returns:
            Formatted prompt string with multi-table requirements
        """
        # Determine which table types to generate
        table_types = self._generate_table_type_requirements(research_intent, metrics, segments)

        # Choose primary segmentation dimension for main table
        primary_dimension = self._choose_primary_dimension(segments, research_intent)
        primary_segments = segments.get(primary_dimension, ['Category'])
        segment_count = len(primary_segments)

        # Build comprehensive multi-table prompt
        table_prompt = f"""
## Comprehensive Benchmark Tables (3-5 tables based on research data)

**Research Intent:** {research_intent}
**Detected Metrics:** {', '.join(metrics[:10]) if metrics else 'Use metrics found in research'}
**Primary Segmentation:** {primary_dimension}
**Segment Count:** {segment_count}

**CRITICAL: Generate {len(table_types)} different table types using REAL data from research. Each table must:**
- Use ONLY data found in research sources (NO fabrication)
- Cite source for EVERY data point: [Source, Year]
- Show ranges not single values: "$50-$150" not "$100"
- Use "Data unavailable" when research lacks specific data
- Skip optional tables if no relevant data exists in research

---

"""

        # Generate PRIMARY_BENCHMARK table (always required)
        table_prompt += f"""
### Table 1: Primary Industry Benchmarks (REQUIRED)

| {primary_dimension.replace('_', ' ').title()} | {' | '.join([m.title() for m in metrics[:4]]) if metrics else '[Metric 1] | [Metric 2] | [Metric 3]'} |
|{'-' * 20}|{'|'.join(['-' * 15 for _ in range(len(metrics[:4]) if metrics else 3)])}|

**Segment Rows (EXHAUSTIVE - include ALL {segment_count} segments found):**
{chr(10).join(f"- {seg}" for seg in primary_segments)}

**Metric Columns (use ONLY metrics from research):**
{chr(10).join(f"- {metric.title()}" for metric in metrics[:6]) if metrics else "- Use metrics found in SERP/Reddit/Quora"}

**Data Requirements:**
- Include ALL {segment_count} segment rows (do not limit to 3 findings)
- Use ranges: "$50-$150", "3.2%-4.8%", not single values
- Cite source for each data point: [Source, Year]
- If data unavailable for a segment, use "Data unavailable"
- Include sample size or N if mentioned in research

---

"""

        # Add additional table types based on research intent
        for table_type in table_types[1:]:  # Skip PRIMARY_BENCHMARK (already added)
            if table_type == "PERFORMANCE_TIERS":
                table_prompt += self._get_performance_tier_table_template(metrics)
            elif table_type == "TIME_BASED_TRENDS":
                table_prompt += self._get_time_based_trends_table_template(metrics)
            elif table_type == "STATISTICAL_DISTRIBUTION":
                table_prompt += self._get_statistical_distribution_table_template(metrics)
            elif table_type == "SEGMENT_COMPARISON" or table_type == "CROSS_SEGMENT_MATRIX":
                table_prompt += self._get_segment_comparison_table_template(segments, metrics)
            elif table_type == "GEOGRAPHIC_VARIATION":
                table_prompt += self._get_geographic_variation_table_template(metrics)
            elif table_type == "CHANNEL_COMPARISON":
                # Use segment comparison template with channel focus
                table_prompt += self._get_segment_comparison_table_template(segments, metrics)

            table_prompt += "\n---\n\n"

        # Add universal guidelines
        table_prompt += """
**Universal Table Guidelines (ALL TABLES):**

1. **NO Meta-Commentary:** Do NOT include explanatory text like "These tables show the median ranges from our 2026 research." Tables should stand alone without instructional commentary.

2. **Source Attribution:** Every numeric value must cite source: [Source, Year]

3. **Data Integrity:**
   - Use ONLY data found in research context
   - Show ranges not point estimates: "$45-$72" not "$58.50"
   - Use "Data unavailable" when research lacks specific data
   - Include confidence levels or sample sizes when mentioned

4. **Formatting:**
   - Use standard markdown table syntax
   - Align columns properly
   - Keep metric names concise but descriptive

5. **Completeness:**
   - Include ALL segments discovered (not just top 3)
   - Generate ALL applicable table types based on available research data
   - Skip optional tables ONLY if no relevant data exists

**DO NOT:**
- Add explanatory paragraphs above/below tables
- Include meta-commentary about data sources
- Fabricate data when research doesn't provide it
- Limit findings to 3 when many industries exist
- Use instructional language like "This table demonstrates..."
"""

        return table_prompt

    def _generate_table_type_requirements(
        self,
        research_intent: str,
        metrics: List[str],
        segments: Dict[str, List[str]]
    ) -> List[str]:
        """
        Determine which table types to require based on research intent.

        Returns list of table type identifiers to generate requirements for.
        Max 4 table types to avoid overwhelming content.
        """
        table_types = ["PRIMARY_BENCHMARK"]  # Always include

        if research_intent == "benchmarking":
            table_types.extend(["PERFORMANCE_TIERS", "STATISTICAL_DISTRIBUTION"])
        elif research_intent == "roi_analysis":
            table_types.extend(["PERFORMANCE_TIERS", "SEGMENT_COMPARISON"])
        elif research_intent == "market_research":
            table_types.extend(["TIME_BASED_TRENDS", "GEOGRAPHIC_VARIATION"])
        elif research_intent == "comparison":
            table_types.append("CROSS_SEGMENT_MATRIX")
        elif research_intent == "performance_analysis":
            table_types.extend(["PERFORMANCE_TIERS", "CHANNEL_COMPARISON"])

        return table_types[:4]  # Max 4 table types

    def _get_performance_tier_table_template(self, metrics: List[str]) -> str:
        """Generate performance tier table requirements (top 10%, median, bottom 25%)."""
        metric_cols = ' | '.join([f'[{m.title()}]' for m in metrics[:3]]) if metrics else '[Metric 1] | [Metric 2] | [Metric 3]'

        return f"""
### Performance Tier Breakdown (REQUIRED)
**Show quartile/decile performance distribution**

| Performance Tier | {metric_cols} | Sample Size |
|------------------|{'|'.join(['-' * 15 for _ in range(len(metrics[:3]) if metrics else 3)])}|-------------|
| Top 10% | [Range] | [Range] | [Range] | [N companies] |
| Top 25% | [Range] | [Range] | [Range] | [N companies] |
| Median (50th percentile) | [Range] | [Range] | [Range] | [N companies] |
| Bottom 25% | [Range] | [Range] | [Range] | [N companies] |
| Bottom 10% | [Range] | [Range] | [Range] | [N companies] |

**Requirements:**
- Use REAL quartile/decile data from research sources
- Include sample sizes for statistical credibility
- Show ranges (e.g., "$45-$72") not single values
- Cite source for each tier: [Source, Year]
- If tier data unavailable, use "Data unavailable" - DO NOT fabricate
"""

    def _get_time_based_trends_table_template(self, metrics: List[str]) -> str:
        """Generate time-based trends table requirements (YoY, QoQ)."""
        metric_cols = ' | '.join([f'[{m.title()}]' for m in metrics[:3]]) if metrics else '[Metric 1] | [Metric 2] | [Metric 3]'

        return f"""
### Time-Based Trends (if trend data available in research)
**Show year-over-year or quarter-over-quarter changes**

| Year/Period | {metric_cols} | % Change YoY |
|-------------|{'|'.join(['-' * 15 for _ in range(len(metrics[:3]) if metrics else 3)])}|--------------|
| 2024 | [Value/Range] | [Value/Range] | [Value/Range] | Baseline |
| 2025 | [Value/Range] | [Value/Range] | [Value/Range] | [+/-X%] |
| 2026 (Projected) | [Value/Range] | [Value/Range] | [Value/Range] | [+/-X%] |

**Requirements:**
- Use ONLY if research sources provide historical/trend data
- Include projected data ONLY if cited from credible industry reports
- Show % change calculations with direction (+/-)
- Cite source for each year's data: [Source, Year]
- If no trend data available, SKIP this table entirely
"""

    def _get_statistical_distribution_table_template(self, metrics: List[str]) -> str:
        """Generate statistical distribution table requirements (min, Q1, median, Q3, max)."""
        return f"""
### Statistical Distribution (for data-rich topics)
**Show full statistical breakdown of key metrics**

| Metric | Min | Q1 (25th) | Median | Q3 (75th) | Max | Std Dev |
|--------|-----|-----------|--------|-----------|-----|---------|
{chr(10).join(f"| {m.title()} | [Value] | [Value] | [Value] | [Value] | [Value] | [±Value] |" for m in metrics[:5]) if metrics else "| [Metric] | [Value] | [Value] | [Value] | [Value] | [Value] | [±Value] |"}

**Requirements:**
- Use ONLY if research provides statistical distribution data
- Include standard deviation or variance if mentioned
- Show confidence intervals if available
- Cite source for statistical data: [Source, Year]
- If no statistical data available, SKIP this table
"""

    def _get_segment_comparison_table_template(
        self,
        segments: Dict[str, List[str]],
        metrics: List[str]
    ) -> str:
        """Generate cross-segment comparison table requirements."""
        # Get two primary dimensions for comparison
        dimensions = list(segments.keys())[:2]
        dim1 = dimensions[0] if len(dimensions) > 0 else 'company_size'
        dim2 = dimensions[1] if len(dimensions) > 1 else 'industry'

        metric_cols = ' | '.join([f'[{m.title()}]' for m in metrics[:3]]) if metrics else '[Metric 1] | [Metric 2]'

        return f"""
### Cross-Segment Comparison
**Compare performance across multiple dimensions**

| {dim1.replace('_', ' ').title()} | {dim2.replace('_', ' ').title()} | {metric_cols} |
|{'|'.join(['-' * 15 for _ in range(2 + (len(metrics[:3]) if metrics else 2))])}|

**Requirements:**
- Create multi-dimensional comparison (e.g., B2B vs B2C across industries)
- Use REAL data from research showing segment differences
- Highlight notable performance gaps between segments
- Cite source for each data point: [Source, Year]
- If no cross-segment data available, SKIP this table
"""

    def _get_geographic_variation_table_template(self, metrics: List[str]) -> str:
        """Generate geographic variation table requirements."""
        metric_cols = ' | '.join([f'[{m.title()}]' for m in metrics[:3]]) if metrics else '[Metric 1] | [Metric 2] | [Metric 3]'

        return f"""
### Geographic Variation (if regional data available)
**Show regional performance differences**

| Region | {metric_cols} | Market Maturity |
|--------|{'|'.join(['-' * 15 for _ in range(len(metrics[:3]) if metrics else 3)])}|-----------------|
| North America | [Range] | [Range] | [Range] | [Mature/Growing/Emerging] |
| Europe | [Range] | [Range] | [Range] | [Mature/Growing/Emerging] |
| APAC | [Range] | [Range] | [Range] | [Mature/Growing/Emerging] |

**Requirements:**
- Use ONLY if research provides geographic breakdown
- Include regional context (market maturity, adoption rates)
- Cite source for each region: [Source, Year]
- If no geographic data available, SKIP this table
"""

    def _choose_primary_dimension(self, segments: Dict[str, List[str]], research_intent: str) -> str:
        """
        Choose which dimension to use as primary table breakdown.

        Priority logic:
        1. If industry is detected and research is about benchmarking → use industry
        2. If company_size is detected and many segments → use company_size
        3. If geography is research focus → use geography

        Args:
            segments: Dict of detected segments
            research_intent: Research intent type

        Returns:
            Name of primary dimension to use
        """
        if 'industry' in segments and len(segments['industry']) >= 3:
            return 'industry'

        if 'company_size' in segments and research_intent in ['benchmarking', 'roi_analysis']:
            return 'company_size'

        if 'geography' in segments and research_intent == 'market_research':
            return 'geography'

        # Default to first available dimension
        return list(segments.keys())[0] if segments else 'category'

    def _load_patterns(self, path: Path) -> Dict[str, Any]:
        """Load extraction patterns config."""
        try:
            with open(path, 'r') as f:
                patterns = json.load(f)
                logger.debug(f"✅ Loaded benchmark extraction patterns from {path}")
                return patterns
        except FileNotFoundError:
            logger.warning(f"⚠️  Benchmark extraction patterns not found at {path}, using defaults")
            return self._get_default_patterns()
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing patterns JSON: {e}, using defaults")
            return self._get_default_patterns()

    def _get_default_patterns(self) -> Dict[str, Any]:
        """Minimal fallback patterns if config file not found."""
        return {
            "metric_detection_patterns": {
                "financial_metrics": {
                    "patterns": ["cost", "price", "roi", "margin"],
                    "extract_types": ["dollar_amount", "percentage"]
                }
            },
            "industry_segmentation_patterns": {
                "primary_dimensions": ["industry", "company_size"],
                "dimension_detection": {
                    "industry": {
                        "extract_segments_from": "icp_config + research_context"
                    },
                    "company_size": {
                        "extract_segments_from": "research_context",
                        "default_segments": ["SMB", "Mid-Market", "Enterprise"]
                    }
                }
            }
        }
