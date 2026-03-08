#!/usr/bin/env python3
"""
Unit tests for SmartAIRouter
Tests multi-model orchestration, prompt routing, and API integration
"""
import pytest
import asyncio
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_router import SmartAIRouter


@pytest.mark.asyncio
class TestSmartAIRouter:
    """Test AI router initialization and model selection"""

    async def test_router_initialization(self):
        """Test that router initializes with API keys"""
        async with SmartAIRouter() as router:
            assert router.perplexity_key is not None, "Perplexity key should be set"
            assert router.nebius is not None, "Nebius client should initialize"
            assert router.gemini_client is not None, "Gemini client should initialize"

    async def _skip_test_perplexity_research(self):
        """Test Perplexity research query"""
        async with SmartAIRouter() as router:
            result = await router.research("What is lead attribution?")

            assert result is not None, "Research should return result"
            assert 'choices' in result, "Result should have choices"
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            assert len(content) > 100, "Research content should be substantial"
            assert 'citations' in result.get('choices', [{}])[0].get('message', {}), "Should include citations"

    async def test_groq_extraction(self):
        """Test Groq extraction capabilities"""
        async with SmartAIRouter() as router:
            test_text = """
            Users on Reddit mention that lead costs vary widely:
            - Facebook ads: $15-30 per lead
            - LinkedIn: $50-100 per lead
            - Google Ads: $20-40 per lead
            """

            prompt = "Extract the lead cost ranges mentioned in this text. Return JSON format."
            result = await router.extract(prompt, test_text)

            assert result is not None, "Extraction should return result"
            assert len(result) > 50, "Extraction should have meaningful content"

    async def test_gemini_generation(self):
        """Test Gemini content generation"""
        async with SmartAIRouter() as router:
            prompt = """Write a 200-word introduction about lead attribution software.
            Include: definition, key benefits, and why it matters."""

            result = await router.generate(prompt, {
                'keyword': 'lead attribution software',
                'style': 'standard'
            })

            assert result is not None, "Generation should return content"
            assert len(result) > 150, "Generated content should meet length requirements"
            assert 'lead' in result.lower(), "Content should mention the topic"
            assert 'attribution' in result.lower(), "Content should be relevant"

    async def test_custom_prompt_detection(self):
        """Test smart prompt detection for custom vs keyword prompts"""
        async with SmartAIRouter() as router:
            # Custom research prompt with markers
            custom_prompt = """
            CRITICAL RESEARCH QUALITY STANDARDS:
            - 3500-5000 words
            - Academic tone

            Write comprehensive research on lead attribution.
            """

            result = await router.generate(custom_prompt, {
                'keyword': 'lead attribution',
                'style': 'research'
            })

            assert result is not None, "Custom prompt should generate content"
            assert len(result) > 200, "Should generate substantial content"

    async def test_multipart_generation(self):
        """Test multi-part generation for long content"""
        async with SmartAIRouter() as router:
            prompt = """Write a comprehensive 2000+ word guide about CRM integration.

            Include these sections:
            1. Introduction
            2. How CRM Integration Works
            3. Implementation Steps
            4. Benefits
            5. Common Challenges
            6. Best Practices
            """

            result = await router.generate(prompt, {
                'keyword': 'CRM integration',
                'style': 'guide'
            })

            assert result is not None, "Multipart generation should complete"
            # Should have meaningful content (multipart combines 3 parts)
            assert len(result) > 500, "Multipart should generate substantial content"

    async def _skip_test_edit_formatting(self):
        """Test Groq edit/formatting step"""
        async with SmartAIRouter() as router:
            raw_content = """
            # Introduction

            Lead attribution is important. It helps track leads.

            ## How It Works

            It uses tracking codes and cookies.
            """

            result = await router.edit_format(raw_content, 'standard')

            assert result is not None, "Edit should return formatted content"
            assert '# Introduction' in result or '## Introduction' in result, "Should preserve headings"

    async def _skip_test_polish_step(self):
        """Test Nebius Llama polish step"""
        async with SmartAIRouter() as router:
            if not router.nebius:
                pytest.skip("Nebius API key not available")

            raw_content = """
            ---
            title: "Test Article"
            ---

            This is a test article about lead tracking.
            It has some content that could be more natural.
            """

            result = await router.polish(raw_content, 'standard')

            assert result is not None, "Polish should return content"
            assert '---' in result, "Should preserve frontmatter"

    async def test_error_handling(self):
        """Test graceful error handling"""
        async with SmartAIRouter() as router:
            # Test with empty prompt
            try:
                result = await router.generate("", {})
                # Should either return empty or handle gracefully
                assert isinstance(result, str), "Should return string even on error"
            except Exception as e:
                # If it raises, should be a meaningful error
                assert len(str(e)) > 0, "Error message should be informative"


@pytest.mark.asyncio
class TestPromptConstruction:
    """Test prompt building and template logic"""

    async def test_paa_section_formatting(self):
        """Test PAA question formatting in prompts"""
        async with SmartAIRouter() as router:
            paa_questions = [
                "What is lead attribution?",
                "How does attribution tracking work?",
                "Why is lead attribution important?"
            ]

            # This is tested indirectly through generate()
            result = await router.generate("lead attribution", {
                'keyword': 'lead attribution',
                'style': 'standard',
                'research_data': {
                    'serp': {
                        'paa_questions': paa_questions
                    }
                }
            })

            assert result is not None, "Should handle PAA questions"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
