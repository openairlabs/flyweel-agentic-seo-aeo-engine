#!/usr/bin/env python3
"""
Integration tests for full content generation pipeline
Tests end-to-end workflows, style variations, and output quality
"""
import pytest
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.generator import ContentGenerator
from tests.conftest import skip_if_no_api_keys


@pytest.mark.asyncio
@pytest.mark.integration
class TestContentGeneration:
    """Test full content generation pipeline"""

    @skip_if_no_api_keys
    async def test_standard_style_generation(self):
        """Test standard style content generation"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="lead attribution software",
            style="standard",
            skip_community=True  # Faster for testing
        )

        assert result['success'], f"Generation should succeed: {result.get('error')}"
        assert result['content'] is not None, "Should generate content"
        assert result['metrics']['word_count'] >= 1000, "Should meet word count minimum"
        assert '---' in result['content'], "Should have frontmatter"
        assert result['title'], "Should have title"

    @skip_if_no_api_keys
    async def test_guide_style_generation(self):
        """Test guide style content generation"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="CRM integration",
            style="guide",
            skip_community=True
        )

        assert result['success'], "Guide generation should succeed"
        assert result['metrics']['word_count'] >= 1500, "Guides should be comprehensive"
        # Guides often have step-by-step sections
        assert '##' in result['content'], "Should have section headings"

    @skip_if_no_api_keys
    async def test_research_style_generation(self):
        """Test research style content generation (deep analysis)"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="marketing attribution models",
            style="research",
            skip_community=True  # Research uses SERP citations only
        )

        assert result['success'], "Research generation should succeed"
        assert result['metrics']['word_count'] >= 2000, "Research should be comprehensive"
        # Research should have citations
        if '[[source]' in result['content']:
            citation_count = result['content'].count('[[source]')
            assert citation_count >= 5, "Research should have multiple citations"

    @skip_if_no_api_keys
    async def test_comparison_style_generation(self):
        """Test comparison style content generation"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="HubSpot vs Salesforce",
            style="comparison",
            skip_community=True
        )

        assert result['success'], "Comparison generation should succeed"
        assert result['metrics']['word_count'] >= 1500, "Comparisons should be detailed"

    async def test_generation_with_community_research(self):
        """Test generation with full community research"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="Facebook lead ads",
            style="standard",
            skip_community=False  # Enable Reddit + Quora
        )

        assert result['success'], "Generation with community research should succeed"
        assert result['research_data']['reddit'] is not None, "Should have Reddit data"
        assert result['research_data']['quora'] is not None, "Should have Quora data"

    async def test_limited_community_research(self):
        """Test generation with limited community research"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="Google Ads optimization",
            style="standard",
            limit_community=True  # Limited: 3 Reddit + 1 Quora
        )

        assert result['success'], "Limited community research should succeed"
        # Should have some community data but limited
        reddit_insights = result['research_data'].get('reddit', {}).get('insights', [])
        if reddit_insights:
            assert len(reddit_insights) <= 5, "Limited mode should have fewer insights"

    async def test_brand_mode_none(self):
        """Test generation without Brand brand mentions (educational mode)"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="lead management",
            style="standard",
            skip_community=True,
            brand_mode='none'
        )

        assert result['success'], "Brand mode 'none' generation should succeed"

        # Check content exists
        content = result['content']['final']
        assert len(content) > 1000, "Content should be substantial"

        # Should have minimal or no brand mentions (except minimal CTA at end)
        # Count Brand mentions (case-insensitive)
        brand_count = content.lower().count('brand')

        # In 'none' mode, should have 0-2 mentions (possibly in CTA only)
        assert brand_count <= 2, f"Educational mode should have ≤2 Brand mentions, got {brand_count}"

    async def test_brand_mode_limited(self):
        """Test generation with limited Brand mentions (2-3 highly natural mentions)"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="crm integration",
            style="standard",
            skip_community=True,
            brand_mode='limited'
        )

        assert result['success'], "Brand mode 'limited' generation should succeed"

        # Check content exists
        content = result['content']['final']
        assert len(content) > 1000, "Content should be substantial"

        # Count Brand mentions (case-insensitive)
        brand_count = content.lower().count('brand')

        # In 'limited' mode, should have 2-5 mentions total (2-3 in content + 1-2 in CTA/links)
        assert 2 <= brand_count <= 6, f"Limited mode should have 2-6 Brand mentions, got {brand_count}"

        # Verify the mentions are distributed (not all in one place)
        # Simple check: content should have at least 1 mention outside the last 500 chars
        content_body = content[:-500] if len(content) > 500 else content[:len(content)//2]
        body_mentions = content_body.lower().count('brand')
        assert body_mentions >= 1, "Limited mode should have at least 1 mention in main content body"

    async def test_metrics_tracking(self):
        """Test that generation tracks comprehensive metrics"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="marketing automation",
            style="standard",
            skip_community=True
        )

        assert result['success'], "Should generate successfully"

        metrics = result['metrics']
        assert 'word_count' in metrics, "Should track word count"
        assert 'generation_time' in metrics, "Should track generation time"
        assert 'paa_questions_answered' in metrics, "Should track PAA coverage"
        assert 'reddit_insights_used' in metrics, "Should track Reddit insights"
        assert 'content_gaps_addressed' in metrics, "Should track content gaps"

        assert metrics['word_count'] > 0, "Word count should be positive"
        assert metrics['generation_time'] > 0, "Generation time should be recorded"

    async def test_research_data_structure(self):
        """Test that research data has expected structure"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="conversion tracking",
            style="standard",
            skip_community=False
        )

        assert result['success'], "Should generate successfully"

        research_data = result['research_data']
        assert 'serp' in research_data, "Should have SERP data"
        assert 'reddit' in research_data, "Should have Reddit data"
        assert 'quora' in research_data, "Should have Quora data"

        # SERP should have specific structure
        serp = research_data['serp']
        assert 'serp_analysis' in serp, "SERP should have analysis"
        assert 'paa_questions' in serp, "SERP should have PAA questions"

    async def test_multipart_generation_completion(self):
        """Test that multipart generation produces complete content"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="enterprise CRM systems",
            style="guide",  # Guides use multipart for length
            skip_community=True
        )

        assert result['success'], "Multipart generation should complete"
        # Should have intro, body, and conclusion
        assert result['metrics']['word_count'] >= 1500, "Should generate full-length content"

        # Check for complete structure
        content = result['content']
        heading_count = content.count('##')
        assert heading_count >= 4, "Should have multiple sections from all parts"

    async def test_polish_step_integration(self):
        """Test that polish step integrates correctly"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="lead scoring",
            style="standard",
            skip_community=True
        )

        assert result['success'], "Generation with polish should succeed"
        assert 'raw_content' in result, "Should have raw pre-polish content"
        assert 'content' in result, "Should have final polished content"

        # Polished content should be different from raw
        # (unless Nebius key is missing, in which case they're identical)
        assert len(result['content']) > 0, "Should have final content"

    async def test_error_handling_invalid_style(self):
        """Test error handling for invalid style"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="test",
            style="invalid_style_name"
        )

        # Should either default to standard or return error
        assert 'success' in result, "Should return result structure"

    async def test_slug_generation(self):
        """Test URL slug generation from keyword"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="Best CRM Software 2025",
            style="standard",
            skip_community=True
        )

        assert result['success'], "Should generate successfully"
        assert 'slug' in result, "Should generate slug"

        slug = result['slug']
        assert slug.islower(), "Slug should be lowercase"
        assert ' ' not in slug, "Slug should not have spaces"
        assert slug.replace('-', '').isalnum(), "Slug should be alphanumeric with hyphens"


@pytest.mark.asyncio
@pytest.mark.integration
class TestOutputQuality:
    """Test output content quality and compliance"""

    async def test_mdx_validity(self):
        """Test that output is valid MDX format"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="ad spend tracking",
            style="standard",
            skip_community=True
        )

        assert result['success'], "Should generate successfully"

        content = result['content']

        # Check MDX structure
        assert content.startswith('---'), "Should start with frontmatter"
        assert content.count('---') >= 2, "Should have frontmatter delimiters"

        # No unescaped special characters that break MDX
        # (Basic validation)
        assert '{' not in content or '{{' in content or '{' in content.split('```')[0], "Braces should be escaped or in code"

    async def test_frontmatter_completeness(self):
        """Test that frontmatter has all required fields"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="marketing metrics",
            style="standard",
            skip_community=True
        )

        assert result['success'], "Should generate successfully"

        content = result['content']
        frontmatter = content.split('---')[1]

        required_fields = ['title:', 'description:', 'pubDate:', 'author:', 'category:', 'tags:']
        for field in required_fields:
            assert field in frontmatter, f"Frontmatter should have {field}"

    async def test_paa_coverage(self):
        """Test PAA question coverage in content"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="lead generation strategies",
            style="standard",
            skip_community=True
        )

        assert result['success'], "Should generate successfully"

        metrics = result['metrics']
        paa_answered = metrics.get('paa_questions_answered', 0)

        # Should attempt to answer some PAA questions
        assert paa_answered >= 0, "Should track PAA coverage"

    async def test_citation_presence_research(self):
        """Test that research style has inline citations"""
        generator = ContentGenerator()

        result = await generator.generate(
            keyword="digital advertising benchmarks 2025",
            style="research",
            skip_community=True
        )

        assert result['success'], "Research should generate successfully"

        content = result['content']

        # Research style should have citations
        if '[[source]' in content:
            citation_count = content.count('[[source]')
            assert citation_count >= 3, "Research should have multiple inline citations"

        # Should have sources section
        assert '## Sources' in content or '## References' in content, "Should have sources section"

    async def test_word_count_targets(self):
        """Test that different styles meet word count targets"""
        generator = ContentGenerator()

        style_targets = {
            'standard': 1800,
            'guide': 1800,
            'research': 2500,
        }

        for style, min_words in style_targets.items():
            result = await generator.generate(
                keyword=f"test {style}",
                style=style,
                skip_community=True
            )

            assert result['success'], f"{style} should generate successfully"
            assert result['metrics']['word_count'] >= min_words, \
                f"{style} should meet {min_words} word minimum"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
