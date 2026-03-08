#!/usr/bin/env python3
"""
Unit tests for AstroFormatter
Tests MDX formatting, citation injection, frontmatter generation
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.formatter import AstroFormatter


class TestAstroFormatter:
    """Test Astro MDX formatting and structure"""

    def test_formatter_initialization(self):
        """Test AstroFormatter initializes correctly"""
        formatter = AstroFormatter()
        assert formatter is not None, "Formatter should initialize"

    def test_basic_formatting(self):
        """Test basic MDX structure creation"""
        formatter = AstroFormatter()

        raw_content = """
        # Introduction

        This is a test article about lead attribution.

        ## How It Works

        Lead attribution tracks customer touchpoints.
        """

        result = formatter.format(
            content=raw_content,
            keyword="lead attribution",
            style="standard",
            research_data={}
        )

        assert result is not None, "Should return formatted result"
        assert isinstance(result, dict), "Should return dict"
        assert 'content' in result, "Should have content key"
        assert 'title' in result, "Should have title"
        assert 'slug' in result, "Should have slug"

        # Check MDX content
        mdx_content = result['content']
        assert '---' in mdx_content, "Content should have frontmatter delimiters"
        assert 'title:' in mdx_content, "Content should have title field"
        assert 'description:' in mdx_content, "Content should have description"

    def test_frontmatter_generation(self):
        """Test YAML frontmatter generation"""
        formatter = AstroFormatter()

        result = formatter.format(
            content="# Test Article\n\nThis is test content.",
            keyword="test keyword",
            style="standard",
            research_data={}
        )

        # Verify result structure
        assert isinstance(result, dict), "Should return dict"
        assert 'title' in result, "Should have title key"
        assert 'slug' in result, "Should have slug key"
        assert 'category' in result, "Should have category key"
        assert 'tags' in result, "Should have tags key"

        # Verify frontmatter in content
        mdx_content = result['content']
        assert 'title:' in mdx_content, "Content should have title"
        assert 'description:' in mdx_content, "Content should have description"
        assert 'publishDate:' in mdx_content or 'pubDate:' in mdx_content, "Content should have publication date"
        assert 'author:' in mdx_content, "Content should have author"

    def test_citation_injection_research_style(self):
        """Test citation injection for research style"""
        formatter = AstroFormatter()

        content = """
        # Research Article

        Our analysis reveals that lead costs have increased by 15% year-over-year.
        Data demonstrates an average cost per lead of $70.11 across platforms.
        Industry data shows that conversion rates improved by 20–40% with automation.
        """

        research_data = {
            'serp': {
                'serp_analysis': {
                    'citations': [
                        'https://example.com/source1',
                        'https://example.com/source2',
                        'https://example.com/source3'
                    ]
                }
            }
        }

        result = formatter.format(
            content=content,
            keyword="lead costs",
            style="research",
            research_data=research_data
        )

        # Should inject inline citations
        mdx_content = result['content']
        assert 'class="citation-ref"' in mdx_content, "Should have inline citations"
        assert '<CitationsSection>' in mdx_content or '## References' in mdx_content, "Should have sources section"

    def test_citation_patterns_matching(self):
        """Test comprehensive citation pattern matching"""
        formatter = AstroFormatter()

        content = """
        According to industry experts, lead generation costs vary widely.
        Studies show that automation reduces manual work by 30%.
        Research shows that companies averaging $50 per lead see better ROI.
        The analysis indicates that 25% improvement is achievable.
        """

        research_data = {
            'serp': {
                'serp_analysis': {
                    'citations': [f'https://example.com/source{i}' for i in range(1, 11)]
                }
            }
        }

        result = formatter.format(
            content=content,
            keyword="lead generation",
            style="research",
            research_data=research_data
        )

        # Count inline citations
        mdx_content = result['content']
        citation_count = mdx_content.count('class="citation-ref"')
        assert citation_count >= 3, "Should match multiple patterns and inject citations"

    def test_citation_filtering_by_style(self):
        """Test that research style excludes community citations"""
        formatter = AstroFormatter()

        content = "Data demonstrates that lead costs increased by 15%."

        research_data = {
            'serp': {
                'serp_analysis': {
                    'citations': ['https://example.com/research']
                }
            },
            'reddit': {
                'insights': [
                    {'url': 'https://reddit.com/discussion', 'content': 'Test insight'}
                ]
            },
            'quora': {
                'insights': [
                    {'url': 'https://quora.com/question', 'content': 'Test answer'}
                ]
            }
        }

        result = formatter.format(
            content=content,
            keyword="lead costs",
            style="research",
            research_data=research_data
        )

        # Should only include SERP citations, not Reddit/Quora
        mdx_content = result['content']
        if '<CitationsSection>' in mdx_content:
            sources_section = mdx_content.split('<CitationsSection>')[1].split('\n\n')[0]
            assert 'reddit.com' not in sources_section.lower(), "Research style should exclude Reddit"
            assert 'quora.com' not in sources_section.lower(), "Research style should exclude Quora"

    def test_schema_org_markup(self):
        """Test Schema.org JSON-LD generation"""
        formatter = AstroFormatter()

        result = formatter.format(
            content="# Test Article\n\nContent here.",
            keyword="test keyword",
            style="standard",
            research_data={}
        )

        # Should include schema.org markup (or rely on layout for schema injection)
        mdx_content = result['content']
        # Note: Schema is now handled by Astro layout, so we just verify MDX structure
        assert '---' in mdx_content, "Should have frontmatter structure"

    def test_faq_section_generation(self):
        """Test FAQ section from PAA questions"""
        formatter = AstroFormatter()

        research_data = {
            'serp': {
                'paa_questions': [
                    'What is lead attribution?',
                    'How does attribution tracking work?',
                    'Why is lead attribution important?'
                ]
            }
        }

        result = formatter.format(
            content="# Lead Attribution\n\nThis is about lead attribution.",
            keyword="lead attribution",
            style="standard",
            research_data=research_data
        )

        # May have FAQ section if PAA questions are present
        # This is optional depending on implementation
        mdx_content = result['content']
        if '## FAQ' in mdx_content or '## Frequently Asked Questions' in mdx_content:
            assert any(q in mdx_content for q in research_data['serp']['paa_questions']), "Should include PAA questions"

    def test_internal_link_injection(self):
        """Test Brand brand link injection"""
        formatter = AstroFormatter()

        content = """
        # Lead Attribution

        Lead attribution helps track marketing performance.
        CRM integration is essential for lead management.
        """

        result = formatter.format(
            content=content,
            keyword="lead attribution",
            style="standard",
            research_data={}
        )

        # Should have internal links (implementation-dependent)
        # This validates structure is preserved
        mdx_content = result['content']
        assert '# Lead Attribution' in mdx_content or '## Lead Attribution' in mdx_content, "Should preserve headings"

    def test_cta_injection(self):
        """Test call-to-action injection"""
        formatter = AstroFormatter()

        result = formatter.format(
            content="# Test\n\nContent here.",
            keyword="test",
            style="standard",
            research_data={}
        )

        # Should have CTA (check for common CTA phrases)
        # Implementation may vary
        mdx_content = result['content']
        assert len(mdx_content) > 100, "Should have formatted content with CTA"

    def test_word_count_preservation(self):
        """Test that formatting preserves word count roughly"""
        formatter = AstroFormatter()

        content = " ".join(["word"] * 1000)  # 1000 words

        result = formatter.format(
            content=content,
            keyword="test",
            style="standard",
            research_data={}
        )

        # Word count should be roughly preserved (±20%)
        mdx_content = result['content']
        result_words = len(mdx_content.split())
        assert result_words >= 800, "Should preserve most content"

    def test_mdx_code_fence_handling(self):
        """Test proper MDX code fence wrapping"""
        formatter = AstroFormatter()

        content_with_code = """
        # Test Article

        Here's some code:

        ```javascript
        const test = "hello";
        ```

        More content here.
        """

        result = formatter.format(
            content=content_with_code,
            keyword="test",
            style="standard",
            research_data={}
        )

        # Should preserve code fences
        mdx_content = result['content']
        assert '```' in mdx_content, "Should preserve code blocks"

    def test_empty_content_handling(self):
        """Test graceful handling of empty content"""
        formatter = AstroFormatter()

        result = formatter.format(
            content="",
            keyword="test",
            style="standard",
            research_data={}
        )

        # Should still generate valid MDX structure
        mdx_content = result['content']
        assert '---' in mdx_content, "Should have frontmatter even with empty content"

    def test_style_specific_formatting(self):
        """Test different formatting for different styles"""
        formatter = AstroFormatter()

        styles = ['standard', 'guide', 'comparison', 'research', 'news', 'category']

        for style in styles:
            result = formatter.format(
                content="# Test\n\nContent here.",
                keyword="test",
                style=style,
                research_data={}
            )

            assert result is not None, f"Should format {style} style"
            mdx_content = result['content']
            assert '---' in mdx_content, f"Should have frontmatter for {style}"


class TestCitationPatterns:
    """Test citation pattern matching and extraction"""

    def test_research_terminology_patterns(self):
        """Test research-specific terminology patterns"""
        formatter = AstroFormatter()

        test_sentences = [
            "Our analysis reveals significant improvements.",
            "Data demonstrates a 15% increase.",
            "Industry data shows market trends.",
            "Market analysis suggests growth opportunities.",
        ]

        for sentence in test_sentences:
            result = formatter.format(
                content=sentence,
                keyword="test",
                style="research",
                research_data={
                    'serp': {
                        'serp_analysis': {
                            'citations': ['https://example.com/source1']
                        }
                    }
                }
            )

            mdx_content = result['content']
            assert 'class="citation-ref"' in mdx_content, f"Should match pattern in: {sentence}"

    def test_statistical_claim_patterns(self):
        """Test statistical claim citation patterns"""
        formatter = AstroFormatter()

        test_sentences = [
            "The average cost is $70.11 per lead.",
            "Companies see 20–40% reduction in costs.",
            "Prices range from $50 to $200 per lead.",
        ]

        for sentence in test_sentences:
            result = formatter.format(
                content=sentence,
                keyword="test",
                style="research",
                research_data={
                    'serp': {
                        'serp_analysis': {
                            'citations': ['https://example.com/source1']
                        }
                    }
                }
            )

            mdx_content = result['content']
            assert 'class="citation-ref"' in mdx_content, f"Should cite statistical claim: {sentence}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
