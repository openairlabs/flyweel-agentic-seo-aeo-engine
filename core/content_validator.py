"""
Content Validator - Post-Generation Quality Assurance

Validates research content against quality standards from research_config.json:
- Structure validation (heading hierarchy, section word counts, tables)
- FAQ optimization (12-15 questions, 40-60 word answers, direct format)
- AEO readiness scoring (0-100 based on AI visibility factors)
- Table quality (context-aware breakdowns, numerical ranges)
- Data density and citation coverage

Integrates with:
- research_config.json (quality thresholds)
- fact_checker.py (citation analysis)
- context_intelligence.py (table validation)
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationReport:
    """Structured validation report with scores and recommendations."""

    def __init__(self, content_type: str = "research"):
        self.content_type = content_type
        self.checks = []
        self.warnings = []
        self.errors = []
        self.scores = {}
        self.overall_score = 0
        self.passed = False

    def add_check(self, name: str, passed: bool, message: str, score: int = 0):
        """Add validation check result."""
        self.checks.append({
            'name': name,
            'passed': passed,
            'message': message,
            'score': score
        })

        if not passed:
            if score > 0:
                self.warnings.append(f"{name}: {message}")
            else:
                self.errors.append(f"{name}: {message}")

    def add_score(self, category: str, score: int, max_score: int):
        """Add category score."""
        self.scores[category] = {
            'score': score,
            'max': max_score,
            'percentage': (score / max_score * 100) if max_score > 0 else 0
        }

    def calculate_overall_score(self):
        """Calculate overall validation score (0-100)."""
        if not self.scores:
            self.overall_score = 0
            return

        total_score = sum(s['score'] for s in self.scores.values())
        total_max = sum(s['max'] for s in self.scores.values())

        self.overall_score = int((total_score / total_max * 100) if total_max > 0 else 0)
        self.passed = self.overall_score >= 70  # Min threshold

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging/output."""
        return {
            'content_type': self.content_type,
            'overall_score': self.overall_score,
            'passed': self.passed,
            'scores': self.scores,
            'checks_passed': len([c for c in self.checks if c['passed']]),
            'checks_total': len(self.checks),
            'warnings': self.warnings,
            'errors': self.errors
        }

    def __str__(self) -> str:
        """Human-readable summary."""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        return f"{status} | Score: {self.overall_score}/100 | Errors: {len(self.errors)} | Warnings: {len(self.warnings)}"


class ContentValidator:
    """Validate research content against quality standards."""

    def __init__(self, research_config_path: Optional[Path] = None, icp_config_path: Optional[Path] = None):
        """
        Initialize validator with research quality config.

        Args:
            research_config_path: Path to research_config.json (optional)
            icp_config_path: Path to icp_config.json (optional)
        """
        if research_config_path is None:
            research_config_path = Path(__file__).parent.parent / 'config' / 'research_config.json'

        if icp_config_path is None:
            icp_config_path = Path(__file__).parent.parent / 'config' / 'icp_config.json'

        self.config = self._load_config(research_config_path)
        self.icp_config = self._load_icp_config(icp_config_path)

    def _load_config(self, path: Path) -> Dict[str, Any]:
        """Load research quality configuration."""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                logger.debug(f"✅ Loaded research quality config")
                return config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"⚠️  Could not load research_config.json: {e}, using defaults")
            return self._get_default_config()

    def _load_icp_config(self, path: Path) -> Dict[str, Any]:
        """Load ICP configuration for industry validation."""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                logger.debug(f"✅ Loaded ICP config for industry validation")
                return config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"⚠️  Could not load icp_config.json: {e}, industry validation disabled")
            return {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Fallback default configuration."""
        return {
            'word_count_requirements': {
                'min_total_words': 3500,
                'methodology': {'min': 300, 'max': 400, 'required': True},
                'faq_section': {'min': 300, 'max': 500, 'min_questions': 12}
            },
            'faq_optimization': {
                'min_questions': 12,
                'answer_word_count': {'min': 40, 'max': 60}
            },
            'aeo_readiness': {
                'target_score': 85,
                'scoring_factors': {
                    'faq_count': 25,
                    'direct_answers': 20,
                    'data_density': 15,
                    'citation_coverage': 20,
                    'schema_markup': 20
                }
            }
        }

    def validate_structure(
        self,
        content: str,
        frontmatter: Dict[str, Any]
    ) -> ValidationReport:
        """
        Validate content structure (headings, sections, tables).

        Args:
            content: Full MDX content
            frontmatter: Frontmatter dict

        Returns:
            ValidationReport with structure checks

        Validates:
        - Heading hierarchy (H1 → H2 → H3, no skips)
        - Mandatory sections present
        - Section word counts meet minimums
        - Table presence and formatting
        """
        report = ValidationReport("structure")

        # Extract headings
        headings = self._extract_headings(content)

        # 1. Heading hierarchy validation
        hierarchy_valid, hierarchy_issues = self._validate_heading_hierarchy(headings)
        report.add_check(
            "Heading Hierarchy",
            hierarchy_valid,
            f"Found {len(hierarchy_issues)} hierarchy issues" if hierarchy_issues else "Valid H1→H2→H3 hierarchy",
            score=10 if hierarchy_valid else 0
        )

        # 2. Mandatory sections validation
        mandatory = self.config.get('structure_requirements', {}).get('mandatory_sections', [])
        missing_sections = self._check_mandatory_sections(headings, mandatory)
        report.add_check(
            "Mandatory Sections",
            len(missing_sections) == 0,
            f"Missing: {', '.join(missing_sections)}" if missing_sections else f"All {len(mandatory)} required sections present",
            score=20 if len(missing_sections) == 0 else max(0, 20 - len(missing_sections) * 4)
        )

        # 3. Section word counts
        section_counts = self._count_section_words(content, headings)
        word_count_issues = self._validate_section_word_counts(section_counts)
        report.add_check(
            "Section Word Counts",
            len(word_count_issues) == 0,
            f"{len(word_count_issues)} sections below minimum" if word_count_issues else "All sections meet minimum word counts",
            score=15 if len(word_count_issues) == 0 else max(0, 15 - len(word_count_issues) * 3)
        )

        # 4. Table validation
        tables = self._extract_tables(content)
        min_tables = self.config.get('structure_requirements', {}).get('min_tables', 2)
        report.add_check(
            "Table Presence",
            len(tables) >= min_tables,
            f"Found {len(tables)} tables (min: {min_tables})",
            score=10 if len(tables) >= min_tables else max(0, int(len(tables) / min_tables * 10))
        )

        table_quality_score, table_issues = self._validate_table_quality(tables)
        report.add_check(
            "Table Quality",
            len(table_issues) == 0,
            f"{len(table_issues)} table quality issues" if table_issues else f"{len(tables)} tables formatted correctly",
            score=table_quality_score
        )

        # Calculate score
        report.add_score("structure", sum(c['score'] for c in report.checks), 65)
        report.calculate_overall_score()

        logger.info(f"📐 Structure validation: {report}")
        return report

    def _extract_headings(self, content: str) -> List[Dict[str, Any]]:
        """Extract all headings with levels and text."""
        headings = []
        pattern = r'^(#{1,6})\s+(.+)$'

        for match in re.finditer(pattern, content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({
                'level': level,
                'text': text,
                'position': match.start()
            })

        return headings

    def _validate_heading_hierarchy(
        self,
        headings: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """Check for heading hierarchy violations (skipped levels)."""
        issues = []
        prev_level = 0

        for i, heading in enumerate(headings):
            level = heading['level']

            # Check for skipped levels (e.g., H1 → H3)
            if level > prev_level + 1 and prev_level > 0:
                issues.append(f"Skipped level at '{heading['text'][:50]}' (H{prev_level} → H{level})")

            prev_level = level

        return len(issues) == 0, issues

    def _check_mandatory_sections(
        self,
        headings: List[Dict[str, Any]],
        mandatory: List[str]
    ) -> List[str]:
        """Check if mandatory sections are present."""
        heading_texts = [h['text'].lower() for h in headings]
        missing = []

        for section in mandatory:
            section_lower = section.lower()
            # Fuzzy match (section name anywhere in heading)
            if not any(section_lower in text for text in heading_texts):
                missing.append(section)

        return missing

    def _count_section_words(
        self,
        content: str,
        headings: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Count words in each H2 section."""
        counts = {}

        h2_headings = [h for h in headings if h['level'] == 2]

        for i, heading in enumerate(h2_headings):
            # Extract text between this H2 and next H2 (or end)
            start = heading['position']
            end = h2_headings[i + 1]['position'] if i + 1 < len(h2_headings) else len(content)

            section_text = content[start:end]
            word_count = len(section_text.split())

            counts[heading['text']] = word_count

        return counts

    def _validate_section_word_counts(
        self,
        section_counts: Dict[str, int]
    ) -> List[str]:
        """Validate section word counts against config minimums."""
        issues = []
        word_reqs = self.config.get('word_count_requirements', {})

        # Check specific sections
        for section_name, count in section_counts.items():
            section_lower = section_name.lower()

            # Match to config requirements
            if 'methodology' in section_lower:
                min_words = word_reqs.get('methodology', {}).get('min', 300)
                if count < min_words:
                    issues.append(f"'{section_name}': {count} words (min: {min_words})")

            elif 'case' in section_lower and 'stud' in section_lower:
                min_words = word_reqs.get('case_studies_section', {}).get('min', 750)
                if count < min_words:
                    issues.append(f"'{section_name}': {count} words (min: {min_words})")

            elif 'benchmark' in section_lower or 'comparative' in section_lower:
                min_words = word_reqs.get('comparative_benchmarking', {}).get('min', 400)
                if count < min_words:
                    issues.append(f"'{section_name}': {count} words (min: {min_words})")

        return issues

    def _extract_tables(self, content: str) -> List[str]:
        """Extract markdown tables from content."""
        # Match markdown table pattern
        table_pattern = r'(\|.+\|\n\|[-:\s|]+\|\n(?:\|.+\|\n)+)'
        tables = re.findall(table_pattern, content)
        return tables

    def _validate_table_quality(
        self,
        tables: List[str]
    ) -> Tuple[int, List[str]]:
        """
        Validate table quality (rows, columns, formatting).

        Returns:
            Tuple of (score out of 10, list of issues)
        """
        if not tables:
            return 0, ["No tables found"]

        issues = []
        quality_reqs = self.config.get('table_quality_requirements', {})
        min_rows = quality_reqs.get('min_rows', 4)
        min_cols = quality_reqs.get('min_columns', 3)

        for i, table in enumerate(tables, 1):
            rows = table.strip().split('\n')

            # Check row count (excluding header and separator)
            data_rows = [r for r in rows if not re.match(r'\|[-:\s|]+\|', r)]
            if len(data_rows) < min_rows + 1:  # +1 for header
                issues.append(f"Table {i}: Only {len(data_rows) - 1} data rows (min: {min_rows})")

            # Check column count
            if rows:
                col_count = rows[0].count('|') - 1  # -1 for empty edges
                if col_count < min_cols:
                    issues.append(f"Table {i}: Only {col_count} columns (min: {min_cols})")

            # Check for consistent column counts
            col_counts = [row.count('|') for row in rows]
            if len(set(col_counts)) > 1:
                issues.append(f"Table {i}: Inconsistent column counts")

        # Score: 10 points minus 2 per issue (min 0)
        score = max(0, 10 - len(issues) * 2)
        return score, issues

    def validate_faq_answers(
        self,
        faq_list: List[Dict[str, str]]
    ) -> ValidationReport:
        """
        Validate FAQ answers for AEO optimization.

        Args:
            faq_list: List of {question, answer} dicts from frontmatter

        Returns:
            ValidationReport with FAQ checks

        Validates:
        - FAQ count (12-15 for 90% AI visibility)
        - Answer length (40-60 words optimal for AI extraction)
        - Direct answer format (answer in first sentence)
        """
        report = ValidationReport("faq")
        faq_config = self.config.get('faq_optimization', {})

        min_questions = faq_config.get('min_questions', 12)
        max_questions = faq_config.get('max_questions', 15)
        word_config = faq_config.get('answer_word_count', {})
        min_words = word_config.get('min', 40)
        max_words = word_config.get('max', 60)

        # 1. FAQ count validation
        faq_count = len(faq_list)
        optimal_count = min_questions <= faq_count <= max_questions

        report.add_check(
            "FAQ Count",
            optimal_count,
            f"{faq_count} FAQs (optimal: {min_questions}-{max_questions})",
            score=25 if optimal_count else max(0, int(faq_count / min_questions * 25))
        )

        # 2. Answer length validation
        length_issues = []
        for i, faq in enumerate(faq_list, 1):
            answer = faq.get('answer', '')
            word_count = len(answer.split())

            if word_count < min_words:
                length_issues.append(f"FAQ {i}: {word_count} words (min: {min_words})")
            elif word_count > max_words:
                length_issues.append(f"FAQ {i}: {word_count} words (max: {max_words})")

        optimal_length_ratio = 1 - (len(length_issues) / max(faq_count, 1))
        report.add_check(
            "Answer Length (40-60 words)",
            len(length_issues) == 0,
            f"{len(length_issues)} answers outside optimal range" if length_issues else f"All {faq_count} answers optimized for AI extraction",
            score=int(optimal_length_ratio * 30)
        )

        # 3. Direct answer format validation
        direct_answer_count = 0
        for faq in faq_list:
            answer = faq.get('answer', '')
            # Check if first sentence is direct (contains key question words)
            first_sentence = answer.split('.')[0] if '.' in answer else answer
            if len(first_sentence.split()) >= 10:  # Substantial first sentence
                direct_answer_count += 1

        direct_answer_ratio = direct_answer_count / max(faq_count, 1)
        report.add_check(
            "Direct Answer Format",
            direct_answer_ratio >= 0.8,
            f"{direct_answer_count}/{faq_count} FAQs have direct first-sentence answers",
            score=int(direct_answer_ratio * 20)
        )

        # Calculate score
        report.add_score("faq", sum(c['score'] for c in report.checks), 75)
        report.calculate_overall_score()

        logger.info(f"❓ FAQ validation: {report}")
        return report

    def score_aeo_readiness(
        self,
        content: str,
        frontmatter: Dict[str, Any],
        has_schema: bool = False,
        citation_coverage: float = 0.0
    ) -> ValidationReport:
        """
        Score content for Answer Engine Optimization (AEO) readiness (0-100).

        Args:
            content: Full MDX content
            frontmatter: Frontmatter dict
            has_schema: Whether JSON-LD schema is present
            citation_coverage: Ratio of claims with citations (0.0-1.0)

        Returns:
            ValidationReport with AEO score

        Scoring factors (from research_config.json):
        - FAQ count (25 pts): 12-15 FAQs for 90% AI visibility
        - Direct answers (20 pts): First sentence answers questions
        - Data density (15 pts): Statistics and metrics present
        - Citation coverage (20 pts): Claims are sourced
        - Schema markup (20 pts): JSON-LD present
        """
        report = ValidationReport("aeo")
        scoring = self.config.get('aeo_readiness', {}).get('scoring_factors', {})

        # 1. FAQ Count Score (25 pts)
        faq_list = frontmatter.get('faq', [])
        faq_count = len(faq_list)
        faq_score = min(25, int(faq_count / 12 * 25)) if faq_count <= 15 else 25

        report.add_check(
            "FAQ Count (AI Visibility)",
            faq_count >= 12,
            f"{faq_count} FAQs (90% AI visibility at 12-15)",
            score=faq_score
        )

        # 2. Direct Answers Score (20 pts)
        # Count sections with direct first-sentence answers
        direct_answer_sections = self._count_direct_answer_sections(content)
        direct_answer_score = min(20, direct_answer_sections * 2)  # 2 pts per direct answer section

        report.add_check(
            "Direct Answer Sections",
            direct_answer_sections >= 8,
            f"{direct_answer_sections} sections lead with direct answers (target: 8+)",
            score=direct_answer_score
        )

        # 3. Data Density Score (15 pts)
        data_points = self._count_data_points(content)
        data_density_score = min(15, int(data_points / 15 * 15))

        report.add_check(
            "Data Density",
            data_points >= 15,
            f"{data_points} statistics/metrics (min: 15)",
            score=data_density_score
        )

        # 4. Citation Coverage Score (20 pts)
        citation_score = int(citation_coverage * 20)

        report.add_check(
            "Citation Coverage",
            citation_coverage >= 0.8,
            f"{int(citation_coverage * 100)}% of claims cited (target: 80%+)",
            score=citation_score
        )

        # 5. Schema Markup Score (20 pts)
        schema_score = 20 if has_schema else 0

        report.add_check(
            "Schema Markup (JSON-LD)",
            has_schema,
            "BlogPosting + FAQPage schema present" if has_schema else "No schema markup found",
            score=schema_score
        )

        # Calculate overall AEO score
        report.add_score("aeo_readiness", sum(c['score'] for c in report.checks), 100)
        report.calculate_overall_score()

        logger.info(f"🎯 AEO readiness: {report}")
        return report

    def _count_direct_answer_sections(self, content: str) -> int:
        """Count H2 sections that start with direct answer sentences."""
        headings = self._extract_headings(content)
        h2_headings = [h for h in headings if h['level'] == 2]

        direct_count = 0
        for i, heading in enumerate(h2_headings):
            # Extract first paragraph after heading
            start = heading['position'] + len(heading['text']) + 10
            end = h2_headings[i + 1]['position'] if i + 1 < len(h2_headings) else len(content)

            section_text = content[start:end]
            first_para = section_text.split('\n\n')[0] if '\n\n' in section_text else section_text

            # Check if first sentence is substantial (15+ words)
            first_sentence = first_para.split('.')[0] if '.' in first_para else first_para
            if len(first_sentence.split()) >= 15:
                direct_count += 1

        return direct_count

    def _count_data_points(self, content: str) -> int:
        """Count statistical data points (percentages, metrics, dollar amounts)."""
        patterns = [
            r'\d+(?:\.\d+)?%',  # Percentages
            r'\$\d+(?:,\d{3})*(?:\.\d+)?[KMB]?',  # Dollar amounts
            r'\d+x',  # Multipliers
            r'\d+\s*(?:hours?|days?|weeks?|months?)',  # Time periods
        ]

        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, content)
            count += len(matches)

        return count

    def validate_industry_table_coverage(
        self,
        content: str,
        keyword: str
    ) -> ValidationReport:
        """
        Validate that tables use real ICP industries from config, not hardcoded values.

        Args:
            content: Full MDX content
            keyword: Research keyword (used to detect expected industry)

        Returns:
            ValidationReport with industry coverage checks

        Validates:
        - Tables contain industry breakdowns (not generic data)
        - Industries used match icp_config.json (not hardcoded)
        - Detected industry from keyword appears in tables
        - No generic placeholder industries (e.g., "Industry A", "Various")
        """
        report = ValidationReport("industry_coverage")

        if not self.icp_config:
            logger.warning("⚠️  ICP config not loaded, skipping industry validation")
            report.add_check(
                "ICP Config Available",
                False,
                "ICP config not loaded - industry validation skipped",
                score=0
            )
            report.calculate_overall_score()
            return report

        # Extract valid industries from ICP config
        valid_industries = self._extract_valid_industries()
        logger.debug(f"📋 Valid ICP industries: {list(valid_industries.keys())}")

        # Detect expected industry from keyword
        detected_industry = self._detect_keyword_industry(keyword, valid_industries)

        # Extract tables from content
        tables = self._extract_tables(content)

        if not tables:
            report.add_check(
                "Tables Present",
                False,
                "No tables found in content - cannot validate industry coverage",
                score=0
            )
            report.calculate_overall_score()
            return report

        # Check if tables contain industry-specific data
        tables_with_industries = 0
        hardcoded_industry_issues = []
        detected_industry_present = False

        for i, table in enumerate(tables, 1):
            table_lower = table.lower()

            # Check for industry mentions
            industries_in_table = []
            for industry_key, industry_subs in valid_industries.items():
                # Check for industry category name
                industry_display = industry_key.replace('_', ' ').title()
                if industry_display.lower() in table_lower:
                    industries_in_table.append(industry_display)
                    tables_with_industries += 1
                    if industry_key == detected_industry:
                        detected_industry_present = True

                # Check for sub-industries
                for sub in industry_subs:
                    if sub.lower() in table_lower:
                        industries_in_table.append(sub)
                        tables_with_industries += 1
                        if industry_key == detected_industry:
                            detected_industry_present = True

            # Check for hardcoded/generic industry names
            generic_patterns = [
                r'industry\s+[a-d]',  # "Industry A", "Industry B"
                r'generic\s+industry',
                r'example\s+industry',
                r'various\s+industri',
                r'sample\s+data',
                r'\[industry\s+name\]'
            ]

            for pattern in generic_patterns:
                if re.search(pattern, table_lower):
                    hardcoded_industry_issues.append(f"Table {i}: Contains generic placeholder '{pattern}'")

        # 1. Industry presence validation (30 pts)
        industry_coverage_ratio = tables_with_industries / max(len(tables), 1)
        industry_score = int(industry_coverage_ratio * 30)

        report.add_check(
            "Industry-Specific Tables",
            tables_with_industries > 0,
            f"{tables_with_industries}/{len(tables)} tables contain ICP industry data",
            score=industry_score
        )

        # 2. No hardcoded/generic industries (30 pts)
        no_hardcoded = len(hardcoded_industry_issues) == 0
        hardcoded_score = 30 if no_hardcoded else max(0, 30 - len(hardcoded_industry_issues) * 10)

        report.add_check(
            "No Generic Placeholders",
            no_hardcoded,
            f"{len(hardcoded_industry_issues)} generic/hardcoded industry issues" if hardcoded_industry_issues else "All industries from ICP config",
            score=hardcoded_score
        )

        # 3. Detected industry coverage (40 pts)
        if detected_industry:
            detected_industry_display = detected_industry.replace('_', ' ').title()
            report.add_check(
                f"Keyword Industry Coverage ({detected_industry_display})",
                detected_industry_present,
                f"Tables cover detected industry '{detected_industry_display}' for keyword '{keyword}'" if detected_industry_present else f"Missing expected industry '{detected_industry_display}' for '{keyword}'",
                score=40 if detected_industry_present else 0
            )
        else:
            report.add_check(
                "Keyword Industry Detection",
                False,
                f"Could not detect specific industry from keyword '{keyword}' - validation limited",
                score=20  # Partial credit if we can't detect industry
            )

        # Calculate score
        report.add_score("industry_coverage", sum(c['score'] for c in report.checks), 100)
        report.calculate_overall_score()

        logger.info(f"🏭 Industry coverage validation: {report}")
        return report

    def _extract_valid_industries(self) -> Dict[str, List[str]]:
        """
        Extract valid industry categories and sub-industries from ICP config.

        Returns:
            Dict mapping industry category (e.g., 'home_services') to list of sub-industries
        """
        industries = {}

        # Navigate ICP config structure
        sales_led = self.icp_config.get('primary_icps', {}).get('sales_led_services', {})
        industry_dict = sales_led.get('industries', {})

        for category, subs in industry_dict.items():
            if isinstance(subs, list):
                industries[category] = subs

        return industries

    def _detect_keyword_industry(self, keyword: str, valid_industries: Dict[str, List[str]]) -> Optional[str]:
        """
        Detect which ICP industry category the keyword relates to.

        Args:
            keyword: Research keyword
            valid_industries: Dict of industry categories and sub-industries

        Returns:
            Industry category key (e.g., 'home_services') or None
        """
        keyword_lower = keyword.lower()
        keyword_words = set(keyword_lower.split())

        # Check each industry category and sub-industries
        for category, subs in valid_industries.items():
            # Check category name
            category_display = category.replace('_', ' ')
            if category_display in keyword_lower:
                logger.info(f"🎯 Detected industry '{category}' from keyword '{keyword}' (category match)")
                return category

            # Check sub-industries with flexible word matching
            for sub in subs:
                sub_lower = sub.lower()

                # Exact substring match (e.g., "HVAC" in "HVAC lead costs")
                if sub_lower in keyword_lower:
                    logger.info(f"🎯 Detected industry '{category}' from keyword '{keyword}' (sub-industry: {sub})")
                    return category

                # Word-level match (e.g., "solar" from "solar installers" matches "solar lead generation")
                sub_words = set(sub_lower.split())
                # Filter out common words (installers, brokers, clinics, etc.)
                sub_significant_words = {w for w in sub_words if w not in ['installers', 'brokers', 'clinics', 'practices', 'firms', 'agencies', 'companies', 'services', 'providers']}

                # If any significant word from sub-industry appears in keyword, it's a match
                if sub_significant_words & keyword_words:
                    logger.info(f"🎯 Detected industry '{category}' from keyword '{keyword}' (word match: {sub})")
                    return category

        logger.debug(f"❓ Could not detect specific industry from keyword '{keyword}'")
        return None

    def validate_complete_research_content(
        self,
        content: str,
        frontmatter: Dict[str, Any],
        has_schema: bool = False,
        verified_claims: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Run complete validation suite for research content.

        Args:
            content: Full MDX content
            frontmatter: Frontmatter dict
            has_schema: Whether JSON-LD schema is present
            verified_claims: List of verified claims from FactChecker

        Returns:
            Complete validation report dict with all scores

        This is the main entry point for end-to-end validation.
        """
        logger.info("🔍 Running complete research content validation...")

        # Calculate citation coverage
        citation_coverage = 0.0
        if verified_claims:
            verified_count = sum(1 for c in verified_claims if c.get('verified', False))
            citation_coverage = verified_count / max(len(verified_claims), 1)

        # Run all validations
        structure_report = self.validate_structure(content, frontmatter)
        faq_report = self.validate_faq_answers(frontmatter.get('faq', []))
        aeo_report = self.score_aeo_readiness(content, frontmatter, has_schema, citation_coverage)

        # Compile complete report
        complete_report = {
            'overall_score': int((structure_report.overall_score + faq_report.overall_score + aeo_report.overall_score) / 3),
            'passed': all([structure_report.passed, faq_report.passed, aeo_report.passed]),
            'structure': structure_report.to_dict(),
            'faq': faq_report.to_dict(),
            'aeo_readiness': aeo_report.to_dict(),
            'summary': {
                'total_checks': sum([len(r.checks) for r in [structure_report, faq_report, aeo_report]]),
                'passed_checks': sum([len([c for c in r.checks if c['passed']]) for r in [structure_report, faq_report, aeo_report]]),
                'total_errors': len(structure_report.errors) + len(faq_report.errors) + len(aeo_report.errors),
                'total_warnings': len(structure_report.warnings) + len(faq_report.warnings) + len(aeo_report.warnings)
            }
        }

        # Log summary
        status = "✅ VALIDATION PASSED" if complete_report['passed'] else "⚠️  VALIDATION ISSUES FOUND"
        logger.info(f"{status} | Overall Score: {complete_report['overall_score']}/100")
        logger.info(f"  Structure: {structure_report.overall_score}/100 | FAQ: {faq_report.overall_score}/100 | AEO: {aeo_report.overall_score}/100")

        if complete_report['summary']['total_errors'] > 0:
            logger.warning(f"  {complete_report['summary']['total_errors']} errors, {complete_report['summary']['total_warnings']} warnings")

        return complete_report
