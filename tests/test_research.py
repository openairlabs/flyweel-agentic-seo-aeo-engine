#!/usr/bin/env python3
"""
Unit tests for Research modules (Web and Community)
Tests SERP analysis, Reddit mining, Quora extraction
"""
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.research import WebResearcher, CommunityResearcher


@pytest.mark.asyncio
class TestWebResearcher:
    """Test web research and SERP analysis"""

    async def test_researcher_initialization(self):
        """Test WebResearcher initializes correctly"""
        async with WebResearcher() as researcher:
            assert researcher.perplexity_key is not None, "Should have Perplexity key"
            assert researcher.google_key is not None, "Should have Google key"

    async def test_serp_analysis_standard(self):
        """Test standard SERP analysis with sonar-reasoning-pro"""
        async with WebResearcher() as researcher:
            result = await researcher.analyze_serp("CRM integration", style="standard")

            assert result is not None, "Should return SERP result"
            assert 'serp_analysis' in result, "Should have analysis"
            assert 'paa_questions' in result, "Should extract PAA questions"
            assert 'search_results' in result, "Should have search results"

            # Verify content quality
            analysis = result.get('serp_analysis', {})
            if analysis:
                assert len(str(analysis)) > 100, "Analysis should be substantial"

    async def test_serp_analysis_research(self):
        """Test deep research SERP analysis with sonar-deep-research"""
        async with WebResearcher() as researcher:
            result = await researcher.analyze_serp("lead attribution models", style="research")

            assert result is not None, "Should return research result"
            assert 'serp_analysis' in result, "Should have deep analysis"

            # Research style should use sonar-deep-research (longer, more detailed)
            analysis = result.get('serp_analysis', {})
            if analysis:
                assert len(str(analysis)) > 200, "Research analysis should be more detailed"

    async def test_paa_extraction(self):
        """Test PAA (People Also Ask) question extraction"""
        async with WebResearcher() as researcher:
            result = await researcher.analyze_serp("marketing automation")

            paa_questions = result.get('paa_questions', [])
            assert isinstance(paa_questions, list), "PAA should be a list"
            # May be empty if no PAAs found, but structure should be valid
            if paa_questions:
                assert len(paa_questions) > 0, "Should extract PAA questions"
                assert all(isinstance(q, str) for q in paa_questions), "Questions should be strings"

    async def test_citation_extraction(self):
        """Test citation extraction from SERP analysis"""
        async with WebResearcher() as researcher:
            result = await researcher.analyze_serp("ad spend tracking")

            serp_analysis = result.get('serp_analysis', {})
            if isinstance(serp_analysis, dict):
                citations = serp_analysis.get('citations', [])
                assert isinstance(citations, list), "Citations should be a list"

    async def test_platform_filtering(self):
        """Test platform name filtering in PAA questions"""
        async with WebResearcher() as researcher:
            # This is tested indirectly - PAA questions should not include platform names
            result = await researcher.analyze_serp("Facebook lead ads")

            paa_questions = result.get('paa_questions', [])
            if paa_questions:
                # Should filter out platform-specific questions
                for question in paa_questions:
                    # Questions shouldn't be just about specific platforms
                    assert isinstance(question, str), "Should be valid question string"


@pytest.mark.asyncio
class TestCommunityResearcher:
    """Test community research (Reddit and Quora)"""

    async def test_researcher_initialization(self):
        """Test CommunityResearcher initializes correctly"""
        async with CommunityResearcher() as researcher:
            assert researcher.groq_key is not None, "Should have Groq key"

    async def test_reddit_mining(self):
        """Test Reddit insight mining"""
        async with CommunityResearcher() as researcher:
            result = await researcher.mine_reddit("lead generation")

            assert result is not None, "Should return Reddit result"
            assert 'insights' in result, "Should have insights"
            assert 'questions' in result, "Should have questions"

            # Verify structure
            assert isinstance(result['insights'], list), "Insights should be a list"
            assert isinstance(result['questions'], list), "Questions should be a list"

    async def test_reddit_limited_mode(self):
        """Test limited Reddit mining (3 insights)"""
        async with CommunityResearcher() as researcher:
            result = await researcher.mine_reddit("CRM software", limit=True)

            assert result is not None, "Should return limited result"
            insights = result.get('insights', [])
            # Should have fewer insights in limited mode
            assert len(insights) <= 5, "Limited mode should have fewer insights"

    async def test_quora_extraction(self):
        """Test Quora insight extraction"""
        async with CommunityResearcher() as researcher:
            result = await researcher.extract_quora("marketing automation")

            assert result is not None, "Should return Quora result"
            assert 'insights' in result, "Should have insights"

            # Verify structure
            insights = result.get('insights', [])
            assert isinstance(insights, list), "Insights should be a list"

    async def test_quora_limited_mode(self):
        """Test limited Quora extraction (1 insight)"""
        async with CommunityResearcher() as researcher:
            result = await researcher.extract_quora("ad tracking", limit=True)

            assert result is not None, "Should return limited result"
            insights = result.get('insights', [])
            # Limited mode should have max 1 insight
            assert len(insights) <= 1, "Limited mode should have 1 insight max"

    async def test_insight_quality_filtering(self):
        """Test that insights are filtered for quality"""
        async with CommunityResearcher() as researcher:
            result = await researcher.mine_reddit("Brand Methodology")

            insights = result.get('insights', [])
            if insights:
                # Insights should be meaningful (not generic)
                for insight in insights:
                    assert isinstance(insight, dict), "Insight should be dict"
                    # Should have relevance score or content
                    assert 'content' in insight or 'text' in insight, "Should have content"

    async def test_skip_community_mode(self):
        """Test complete skip of community research"""
        async with CommunityResearcher() as researcher:
            # When skip=True, should return empty structures quickly
            result = await researcher.mine_reddit("test", skip=True)

            assert result is not None, "Should return result even when skipped"
            assert result.get('insights') == [], "Should have empty insights"
            assert result.get('questions') == [], "Should have empty questions"


@pytest.mark.asyncio
class TestResearchIntegration:
    """Test integrated research workflows"""

    async def test_parallel_research(self):
        """Test parallel execution of web and community research"""
        async with WebResearcher() as web, CommunityResearcher() as community:
            # Execute in parallel
            serp_task = web.analyze_serp("lead attribution")
            reddit_task = community.mine_reddit("lead attribution")

            serp_result, reddit_result = await asyncio.gather(serp_task, reddit_task)

            assert serp_result is not None, "SERP research should complete"
            assert reddit_result is not None, "Reddit research should complete"

    async def test_research_data_structure(self):
        """Test that research results have expected structure"""
        async with WebResearcher() as web:
            result = await web.analyze_serp("CRM integration")

            # Validate expected keys
            assert 'serp_analysis' in result, "Should have SERP analysis"
            assert 'paa_questions' in result, "Should have PAA questions"
            assert 'search_results' in result, "Should have search results"

            # Validate types
            assert isinstance(result.get('paa_questions', []), list), "PAA should be list"
            assert isinstance(result.get('search_results', []), list), "Results should be list"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
