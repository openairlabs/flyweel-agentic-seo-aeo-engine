"""Lean Research Module - Just what we need for quality content"""
import asyncio
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from .ai_router import SmartAIRouter
from .gsc_analyzer import calculate_traffic_potential, CTR_BY_POSITION, GSCAnalyzer

# Load environment variables from project root with override to ensure fresh values
load_dotenv(Path(__file__).parent.parent / '.env', override=True)

# Setup logging
logger = logging.getLogger(__name__)


def load_icp_context_for_research() -> str:
    """Load ICP context optimized for research prompts - business model buckets only"""
    return """
RELEVANCE FILTER - Prioritize insights from these BUSINESS MODELS:
- Sales-led businesses (ad spend → lead capture → sales team → close)
- Pipeline-led businesses (marketing → nurture → convert over time)
- Service businesses (enquiry → quote → job → invoice, 60-90 day cycles)

Key roles: Business owners, marketers, and media buyers dealing with operational challenges.

"""


# Cache ICP context at module level for efficiency
_ICP_RESEARCH_CONTEXT = load_icp_context_for_research()


# Intent classification patterns (from SEO best practices)
INTENT_PATTERNS = {
    'informational': {
        'patterns': ['what is', 'how to', 'how do', 'why', 'guide', 'tutorial', 'learn', 'explain', 'understand', 'definition'],
        'recommended_style': 'guide',
        'structure_priority': 'what_is_section_first',
        'content_focus': 'educational_depth'
    },
    'commercial': {
        'patterns': ['best', 'top', 'vs', 'versus', 'comparison', 'compare', 'review', 'alternative', 'alternatives to', 'like'],
        'recommended_style': 'comparison',
        'structure_priority': 'comparison_table_first',
        'content_focus': 'feature_comparison'
    },
    'transactional': {
        'patterns': ['buy', 'price', 'pricing', 'discount', 'free trial', 'sign up', 'get started', 'download', 'deal'],
        'recommended_style': 'feature',
        'structure_priority': 'cta_heavy',
        'content_focus': 'conversion_focused'
    },
    'navigational': {
        'patterns': ['login', 'official', 'site', 'website', 'app', 'dashboard'],
        'recommended_style': 'standard',
        'structure_priority': 'direct_answer',
        'content_focus': 'quick_navigation'
    }
}


def classify_keyword_intent(keyword: str) -> Dict[str, Any]:
    """
    Classify keyword search intent and recommend content structure.

    Based on SEO best practices:
    - Informational: "what is X", "how to Y" → guide style, educational depth
    - Commercial: "best X", "X vs Y" → comparison style, feature tables first
    - Transactional: "buy X", "X pricing" → feature style, CTA-heavy
    - Navigational: "X login", "X app" → standard style, direct answer

    Args:
        keyword: The target keyword to classify

    Returns:
        Dict with intent type, recommended style, and structure guidance
    """
    keyword_lower = keyword.lower()

    # Score each intent type based on pattern matches
    intent_scores = {}
    for intent_type, config in INTENT_PATTERNS.items():
        score = 0
        matched_patterns = []
        for pattern in config['patterns']:
            if pattern in keyword_lower:
                # Weight longer patterns more heavily
                weight = len(pattern.split())
                score += weight
                matched_patterns.append(pattern)
        intent_scores[intent_type] = {
            'score': score,
            'matched_patterns': matched_patterns
        }

    # Find highest scoring intent
    best_intent = max(intent_scores.items(), key=lambda x: x[1]['score'])
    intent_type = best_intent[0]
    intent_data = best_intent[1]

    # Default to informational if no patterns matched
    if intent_data['score'] == 0:
        intent_type = 'informational'

    config = INTENT_PATTERNS[intent_type]

    result = {
        'intent_type': intent_type,
        'confidence': min(intent_data['score'] / 3.0, 1.0),  # Normalize to 0-1
        'matched_patterns': intent_data.get('matched_patterns', []),
        'recommended_style': config['recommended_style'],
        'structure_priority': config['structure_priority'],
        'content_focus': config['content_focus'],
        'guidance': _get_structure_guidance(intent_type, config)
    }

    logger.info(f"🎯 Intent Classification: {intent_type} (confidence: {result['confidence']:.0%})")
    logger.info(f"   SEO-suggested style: {config['recommended_style']} (informational only, does not override user selection)")
    logger.info(f"   Structure priority: {config['structure_priority']}")

    return result


def _get_structure_guidance(intent_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Get specific content structure guidance based on intent."""
    guidance = {
        'informational': {
            'opening': 'Start with "What is [topic]?" definition section',
            'h2_priority': ['Definition', 'How It Works', 'Benefits', 'Implementation', 'Best Practices', 'FAQ'],
            'cta_placement': 'end_of_sections',
            'comparison_table': False,
            'faq_required': True,
            'min_word_count': 2000
        },
        'commercial': {
            'opening': 'Lead with quick comparison table showing top options',
            'h2_priority': ['Quick Comparison', 'Top Solutions', 'Feature Comparison', 'Pricing', 'Best For', 'FAQ'],
            'cta_placement': 'after_comparison_table',
            'comparison_table': True,
            'faq_required': True,
            'min_word_count': 2500
        },
        'transactional': {
            'opening': 'Hook → Solution → Benefits → CTA in first 200 words',
            'h2_priority': ['Key Features', 'Pricing', 'How to Get Started', 'Benefits', 'FAQ'],
            'cta_placement': 'prominent_throughout',
            'comparison_table': False,
            'faq_required': True,
            'min_word_count': 1500
        },
        'navigational': {
            'opening': 'Direct answer in first paragraph',
            'h2_priority': ['Overview', 'Key Features', 'Getting Started', 'FAQ'],
            'cta_placement': 'single_prominent',
            'comparison_table': False,
            'faq_required': False,
            'min_word_count': 1000
        }
    }
    return guidance.get(intent_type, guidance['informational'])

class WebResearcher:
    """Handles SERP analysis and GSC data"""
    
    def __init__(self):
        self.perplexity_key = os.getenv('PERPLEXITY_API_KEY')
        # Removed Google Custom Search dependencies
        self.session = None
        self._gsc_service = None
        self._init_gsc()
        self.ai = SmartAIRouter()
    
    def _init_gsc(self):
        """Initialize Google Search Console"""
        creds_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
        if creds_path and os.path.exists(creds_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
                self._gsc_service = build('searchconsole', 'v1', credentials=credentials)
                self.site_url = os.getenv('GSC_PROPERTY_URL', os.getenv('GSC_SITE_URL', 'https://acme.com'))
            except Exception as e:
                print(f"GSC init failed: {e}")
                self._gsc_service = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def analyze_serp(self, keyword: str, augment_serp: bool = False, style: str = "standard") -> Dict[str, Any]:
        """Get comprehensive SERP data using Perplexity and GSC (no Google Custom Search dependency)"""
        # First, generate a shorter, broader keyword for SERP analysis
        serp_keyword = await self._generate_serp_keyword(keyword)
        print(f"Using SERP keyword: '{serp_keyword}' (from original: '{keyword}')")

        # Create ordered tasks with fixed indices
        task_map = {
            'paa': None,
            'gsc': None,
            'serp_analysis': None
        }
        tasks = []

        # Get People Also Ask (index 0) - use the broader SERP keyword
        task_map['paa'] = len(tasks)
        tasks.append(self._extract_paa(serp_keyword))

        # Get GSC data for existing keywords (index 1) - use the broader SERP keyword
        if self._gsc_service and augment_serp:
            task_map['gsc'] = len(tasks)
            tasks.append(self._get_gsc_data(serp_keyword))
        else:
            task_map['gsc'] = len(tasks)
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))  # Empty placeholder

        # Add comprehensive SERP analysis using Perplexity (index 2) - use the broader SERP keyword
        if self.perplexity_key and augment_serp:
            task_map['serp_analysis'] = len(tasks)
            tasks.append(self._analyze_serp_landscape(serp_keyword, style=style))
        else:
            task_map['serp_analysis'] = len(tasks)
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))  # Empty placeholder

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract results by their known indices
        paa_result = results[task_map['paa']]
        gsc_result = results[task_map['gsc']]
        serp_analysis_result = results[task_map['serp_analysis']]

        # Process PAA results
        if isinstance(paa_result, Exception):
            print(f"Warning: PAA extraction failed: {paa_result}")
            paa_questions = []
        else:
            paa_questions = paa_result if paa_result else []

        # Classify keyword intent for content structure guidance
        intent_classification = classify_keyword_intent(keyword)

        # Build SERP data from available sources
        serp_data = {
            "keyword": keyword,  # Keep original keyword in results
            "serp_keyword": serp_keyword,  # Include the SERP keyword used
            "timestamp": datetime.now().isoformat(),
            "search_results": [],  # No longer using Google Custom Search
            "paa_questions": paa_questions,
            "gsc_data": gsc_result if not isinstance(gsc_result, Exception) else None,
            "serp_analysis": serp_analysis_result if not isinstance(serp_analysis_result, Exception) else None,
            "intent_classification": intent_classification,  # SEO intent mapping
            "content_gaps": [],
            "recommended_length": intent_classification['guidance'].get('min_word_count', 2500)
        }

        # Use SERP analysis for content insights if available
        if serp_data["serp_analysis"]:
            try:
                serp_data["content_gaps"] = self._extract_content_gaps_from_analysis(serp_data["serp_analysis"])
                serp_data["recommended_length"] = self._calculate_length_from_analysis(serp_data["serp_analysis"])
            except Exception as e:
                print(f"Warning: Content analysis failed: {e}")
                serp_data["content_gaps"] = []

        return serp_data

    async def _generate_serp_keyword(self, original_keyword: str) -> str:
        """Generate a shorter, broader keyword optimized for SERP analysis using AI"""
        try:
            # Use Perplexity to generate a good SERP keyword
            prompt = f"""Given this keyword: "{original_keyword}"

Create a shorter, optimized version (4-6 words) that would be effective for SERP analysis and People Also Ask questions.

Requirements:
- Analyze semantically to identify core concepts and distinguishing qualifiers
- Preserve terms that differentiate this topic from related but different topics
- Keep domain-specific qualifiers that add critical semantic meaning
- Remove question words and generic fluff ("state of", "guide to", "best", year numbers)
- Make it broad enough to capture related searches but specific enough to maintain unique context
- Focus on what users actually search for in this domain
- Target 4-6 words for natural, contextually rich queries

Return only the optimized keyword, no explanation.
"""
            # Use Perplexity AI to generate optimized SERP keyword
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.perplexity_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "sonar",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 30
                }

                async with session.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        serp_keyword = data["choices"][0]["message"]["content"].strip()

                        # Clean up formatting
                        serp_keyword = serp_keyword.strip('"').strip("'").strip('*').strip()

                        # Validate the result
                        if (len(serp_keyword) > 5 and len(serp_keyword) < len(original_keyword)
                            and ' ' in serp_keyword and len(serp_keyword.split()) <= 6):
                            return serp_keyword

        except Exception as e:
            print(f"AI keyword generation failed: {e}")

        # Fallback to simple extraction
        words = original_keyword.split()
        # Skip question words and take content words, preserving all important terms
        content_words = [w for w in words if w.lower() not in {'which', 'what', 'how', 'why', 'when', 'where', 'who', 'are', 'the', 'best', 'top'}]
        # Take up to 6 words for better context preservation
        result = ' '.join(content_words[:6]) if content_words else ' '.join(words[:6])
        print(f"Fallback SERP keyword: '{result}' from '{original_keyword}'")
        return result


    async def _extract_paa(self, keyword: str) -> List[str]:
        """Extract People Also Ask questions using Perplexity with robust fallback strategy"""
        if not self.perplexity_key:
            print("Warning: PERPLEXITY_API_KEY not found, using AI-generated fallback questions")
            return await self._generate_fallback_questions(keyword)

        # Multi-model fallback strategy with retry - use reasoning model first for better quality
        models = ["sonar-reasoning-pro", "sonar-pro"]
        max_retries = 3

        for attempt in range(max_retries):
            for model in models:
                try:
                    questions = await self._try_extract_with_model(keyword, model)
                    if questions and len(questions) >= 8:
                        print(f"Successfully extracted {len(questions)} PAA questions for '{keyword}' using {model}")
                        return questions
                except Exception as e:
                    print(f"Warning: {model} failed on attempt {attempt + 1}: {e}")
                    continue

            # Exponential backoff between attempts
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        # All models failed, use AI-generated fallbacks
        print(f"Warning: All PAA extraction methods failed for '{keyword}', using AI-generated fallback questions")
        return await self._generate_fallback_questions(keyword)

    async def _try_extract_with_model(self, keyword: str, model: str) -> List[str]:
        """Try extracting PAA with a specific model"""
        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json"
        }

        # Get ICP context for targeted research
        icp_context = _ICP_RESEARCH_CONTEXT
        logger.info(f"🎯 PAA extraction: ICP context injected ({len(icp_context)} chars)")

        prompt = f"""You are analyzing search intent and related questions for the keyword: "{keyword}"

Task: Extract and generate the most relevant "People Also Ask" (PAA) style questions that searchers would ask related to this keyword.
{icp_context}
Context Guidelines:
- Consider the search intent behind "{keyword}" (informational, commercial, navigational, transactional)
- Focus on questions that address different aspects: what, how, why, when, where, which, who
- Include questions about implementation, benefits, challenges, comparisons, costs, best practices
- Prioritize questions that reflect real user pain points and information needs
- Consider both beginner and advanced user perspectives

Quality Guidelines:
- Prioritize questions from credible, recent sources (2024-2025)
- Focus on specific, actionable questions over generic ones
- Prefer questions with data-driven or expert backing

Return ONLY a valid JSON object with this exact structure:
{{
  "questions": ["Question 1?", "Question 2?", "Question 3?"]
}}

Requirements:
- Array must contain 8-12 high-quality, relevant questions
- Each question must be a complete sentence ending with ?
- Questions should naturally follow from search intent for "{keyword}"
- Vary question types (what, how, why, best, compare, etc.)
- No explanations or additional text outside the JSON structure"""

        payload = {
            "model": model,
            "messages": [{
                "role": "system",
                "content": "You are an expert SEO analyst specializing in understanding search intent and related questions. You analyze keywords and extract the most relevant questions that users would ask."
            }, {
                "role": "user",
                "content": prompt
            }],
            "temperature": 0.2,
            "max_tokens": 1500,
            "search_recency_filter": "month",
            "return_citations": True
        }

        async with self.session.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            if response.status != 200:
                raise Exception(f"API returned status {response.status}")

            data = await response.json()
            content = data["choices"][0]["message"]["content"]

            # Parse and validate the response
            return self._parse_and_validate_paa_response(content, keyword)

    def _parse_and_validate_paa_response(self, content: str, keyword: str) -> List[str]:
        """Parse JSON response and validate questions"""
        # Clean content first
        content = self._clean_json_content(content)

        try:
            # Try to parse as JSON object with questions key
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "questions" in parsed:
                questions = parsed["questions"]
                if isinstance(questions, list):
                    return self._validate_and_filter_questions(questions, keyword)

            # Fallback: try to parse as direct array
            if content.strip().startswith('['):
                questions = json.loads(content)
                if isinstance(questions, list):
                    return self._validate_and_filter_questions(questions, keyword)

        except json.JSONDecodeError:
            # Try to repair common JSON issues
            repaired_content = self._repair_json_content(content)
            if repaired_content:
                try:
                    parsed = json.loads(repaired_content)
                    if isinstance(parsed, dict) and "questions" in parsed:
                        questions = parsed["questions"]
                        if isinstance(questions, list):
                            return self._validate_and_filter_questions(questions, keyword)
                    elif isinstance(parsed, list):
                        return self._validate_and_filter_questions(parsed, keyword)
                except json.JSONDecodeError:
                    pass

        # Last resort: extract questions with regex
        questions = re.findall(r'"([^"]+\?)"', content)
        if questions:
            return self._validate_and_filter_questions(questions, keyword)

        return []

    def _clean_json_content(self, content: str) -> str:
        """Clean JSON content by removing thinking tags and extra text"""
        # Remove thinking tags
        content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)

        # Remove markdown code blocks
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)

        # Extract JSON object or array
        content = content.strip()

        # Find JSON boundaries
        start_brace = content.find('{')
        start_bracket = content.find('[')

        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            # JSON object
            end_brace = content.rfind('}')
            if end_brace > start_brace:
                return content[start_brace:end_brace + 1]
        elif start_bracket != -1:
            # JSON array
            end_bracket = content.rfind(']')
            if end_bracket > start_bracket:
                return content[start_bracket:end_bracket + 1]

        return content

    def _repair_json_content(self, content: str) -> str:
        """Repair common JSON formatting issues"""
        try:
            # Remove trailing commas
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            # Fix unquoted keys
            content = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', content)
            # Fix single quotes
            content = re.sub(r"'([^']*)'", r'"\1"', content)
            # Fix missing quotes around string values
            content = re.sub(r':\s*([a-zA-Z][^,}\]]*)\s*([,}\]])', r': "\1"\2', content)
            return content
        except:
            return None

    def _validate_and_filter_questions(self, questions: list, keyword: str) -> List[str]:
        """Validate and filter extracted questions"""
        if not isinstance(questions, list):
            return []

        validated = []
        seen = set()

        for q in questions:
            if not isinstance(q, str):
                continue

            q = q.strip()
            # Relaxed length check - allow shorter questions and longer ones
            if len(q) < 8 or len(q) > 300:
                continue

            if not q.endswith('?'):
                continue

            # Check for duplicates
            q_lower = q.lower()
            if q_lower in seen:
                continue
            seen.add(q_lower)

            # Relaxed quality check - PAA questions are related to search intent
            # but don't always contain the exact keyword parts
            keyword_lower = keyword.lower()
            # Allow questions that contain at least one significant word from keyword
            # or are clearly related to the topic
            significant_words = [w for w in keyword_lower.split() if len(w) > 2]
            has_relevance = any(word in q_lower for word in significant_words)

            # If no direct keyword match, check if it's a general question about the domain
            if not has_relevance:
                domain_indicators = ['crm', 'budget', 'ad', 'tool', 'integration', 'management', 'marketing']
                has_relevance = any(indicator in q_lower for indicator in domain_indicators)

            if not has_relevance:
                continue

            validated.append(q)

        # Ensure we have at least 8 questions, pad with basic ones if needed
        if len(validated) < 8:
            basic_questions = [
                f"What is {keyword}?",
                f"How does {keyword} work?",
                f"What are the benefits of {keyword}?",
                f"How much does {keyword} cost?",
                f"What are the best {keyword} tools?",
                f"How to implement {keyword}?",
                f"What are {keyword} features?",
                f"Why use {keyword}?"
            ]
            for q in basic_questions:
                if q not in validated and len(validated) < 12:
                    validated.append(q)

        return validated[:12]

    async def _generate_fallback_questions(self, keyword: str) -> List[str]:
        """Generate fallback questions using SmartAIRouter"""
        try:
            async with SmartAIRouter() as ai:
                questions = await ai.generate_questions(keyword, count=10)
                # Filter to questions only
                return [q for q in questions if '?' in q][:10]
        except Exception as e:
            print(f"Warning: AI fallback failed: {e}")
            # Ultimate fallback
            return [
                f"What is {keyword}?",
                f"How does {keyword} work?",
                f"What are the benefits of {keyword}?",
                f"How much does {keyword} cost?",
                f"What are the best {keyword} tools?",
                f"How to implement {keyword}?",
                f"What are {keyword} features?",
                f"Why use {keyword}?",
                f"How to choose {keyword}?",
                f"What problems does {keyword} solve?"
            ]
    
    async def _get_gsc_data(self, keyword: str) -> Dict[str, Any]:
        """Get Google Search Console data for the keyword with traffic potential scoring.

        Implements Traffic Maximization Formula:
        Traffic Potential = Impressions × Expected CTR at Target Position

        This quantifies keyword value beyond raw impressions - a keyword at
        position 5 with 1000 impressions has more potential than one at
        position 20 with 2000 impressions.
        """
        if not self._gsc_service:
            return {}

        try:
            end_date = datetime.now() - timedelta(days=3)
            start_date = end_date - timedelta(days=90)  # Extended to 90 days for better data

            # Use the core keyword only - keep it simple
            request_body = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'dimensionFilterGroups': [{
                    'filters': [{
                        'dimension': 'query',
                        'expression': keyword,
                        'operator': 'contains'
                    }]
                }],
                'rowLimit': 50  # Get more keywords for comprehensive analysis
            }

            response = self._gsc_service.searchanalytics().query(
                siteUrl=self.site_url,
                body=request_body
            ).execute()

            if 'rows' in response and response['rows']:
                # Process all keywords with traffic potential
                keyword_data = []
                for row in response['rows']:
                    impressions = row.get('impressions', 0)
                    position = row.get('position', 100)
                    traffic_potential = calculate_traffic_potential(impressions, position)

                    keyword_data.append({
                        'query': row.get('keys', [keyword])[0],
                        'impressions': impressions,
                        'clicks': row.get('clicks', 0),
                        'ctr': row.get('ctr', 0),
                        'position': position,
                        'traffic_potential': traffic_potential
                    })

                # Sort by traffic potential (not just clicks) for prioritization
                keyword_data.sort(key=lambda x: x['traffic_potential'], reverse=True)

                # Find primary keyword (highest traffic potential with 4+ words preferred)
                high_intent = [k for k in keyword_data if len(k['query'].split()) >= 4]
                primary = high_intent[0] if high_intent else keyword_data[0]

                # Get secondary keywords for H2 distribution (top 4-10 by position)
                secondaries = sorted(
                    [k for k in keyword_data if k != primary and k['impressions'] > 10],
                    key=lambda x: x['position']
                )[:10]

                # Extract question keywords for FAQ
                questions = [
                    k for k in keyword_data
                    if any(k['query'].lower().startswith(q) for q in
                           ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'can', 'does', 'is'])
                ]

                return {
                    'primary_keyword': primary,
                    'secondary_keywords': secondaries[:5],  # Top 5 for H2s
                    'questions': questions[:10],  # For FAQ section
                    'all_keywords': keyword_data,
                    'total_traffic_potential': sum(k['traffic_potential'] for k in keyword_data),
                    # Legacy fields for backwards compatibility
                    'impressions': primary.get('impressions', 0),
                    'clicks': primary.get('clicks', 0),
                    'ctr': primary.get('ctr', 0),
                    'position': primary.get('position', 0),
                    'query': primary.get('query', keyword)
                }

        except Exception as e:
            print(f"GSC query failed for '{keyword}': {e}")

        return {}

    async def get_gsc_content_recommendations(self, keyword: str) -> Dict[str, Any]:
        """
        Get comprehensive GSC-driven recommendations for content creation.

        Uses Traffic Maximization Formula for keyword prioritization and
        provides actionable insights:
        - Primary keyword (use EXACT in title)
        - Secondary keywords (distribute across H2s)
        - Question keywords (use for FAQ section)
        - Traffic potential estimate

        Args:
            keyword: Target keyword for content

        Returns:
            Dict with structured recommendations for content generation
        """
        try:
            async with GSCAnalyzer() as gsc:
                if not gsc.is_available:
                    logger.warning("GSC not available for content recommendations")
                    return {'available': False}

                # Get comprehensive recommendations
                recommendations = await gsc.get_content_recommendations(keyword)

                # Log key insights
                primary = recommendations.get('primary_keyword', {})
                if primary.get('query'):
                    traffic_potential = primary.get('traffic_potential', 0)
                    logger.info(f"🎯 GSC Primary Keyword: '{primary['query']}' (Traffic Potential: {traffic_potential:.0f})")

                    if primary.get('position'):
                        logger.info(f"   Current Position: {primary['position']:.1f}")

                secondaries = recommendations.get('secondary_keywords', [])
                if secondaries:
                    logger.info(f"📊 Secondary Keywords for H2s: {len(secondaries)}")
                    for i, kw in enumerate(secondaries[:4], 1):
                        logger.info(f"   H2 {i}: '{kw['query']}' (pos: {kw['position']:.1f})")

                faq_questions = recommendations.get('faq_questions', [])
                if faq_questions:
                    logger.info(f"❓ GSC-derived FAQ questions: {len(faq_questions)}")

                return {
                    'available': True,
                    **recommendations
                }

        except Exception as e:
            logger.error(f"Failed to get GSC recommendations: {e}")
            return {'available': False, 'error': str(e)}

    def _analyze_content_gaps(self, serp_data: Dict[str, Any]) -> List[str]:
        """Identify content gaps from SERP analysis"""
        gaps = []
        
        # Common topics in top results
        search_results = serp_data.get("search_results", [])
        snippets = []
        
        # Handle different data structures safely
        for r in search_results:
            if isinstance(r, dict):
                snippets.append(r.get("snippet", ""))
            elif isinstance(r, str):
                snippets.append(r)
        
        all_snippets = " ".join(snippets)
        
        # Simple gap detection based on common patterns
        patterns = {
            "how to": r"how to \w+",
            "benefits": r"benefits of|advantages",
            "vs/comparison": r"vs\.|versus|compared to",
            "best practices": r"best practices|tips",
            "tools": r"tools?|software|platforms?",
            "guide": r"guide|tutorial|step.by.step",
            "cost/pricing": r"cost|pricing|price|how much",
            "examples": r"examples?|case studies"
        }
        
        for gap_type, pattern in patterns.items():
            if re.search(pattern, all_snippets, re.IGNORECASE):
                gaps.append(gap_type)
        
        return gaps
    
    def _calculate_optimal_length(self, serp_data: Dict[str, Any]) -> int:
        """Calculate recommended content length based on SERP competition"""
        # Simple heuristic based on competition
        num_results = len(serp_data.get("search_results", []))
        base_length = 2000

        # Add length for competitive keywords
        if num_results >= 8:
            base_length += 500

        # Add length for content gaps
        gaps = serp_data.get("content_gaps", [])
        base_length += len(gaps) * 200

        # Cap at reasonable maximum
        return min(base_length, 3500)

    def _extract_content_gaps_from_analysis(self, serp_analysis: Dict[str, Any]) -> List[str]:
        """Extract content gaps from Perplexity SERP analysis"""
        if not serp_analysis or not isinstance(serp_analysis, dict):
            return []

        analysis_text = serp_analysis.get("analysis", "").lower()
        gaps = []

        # Look for common gap indicators in the analysis
        gap_indicators = [
            "missing", "lacking", "no content", "gap", "opportunity",
            "not covered", "overlooked", "missing information", "needs more",
            "lacks", "doesn't include", "missing from"
        ]

        # Extract potential gaps from analysis text
        for indicator in gap_indicators:
            if indicator in analysis_text:
                # Try to extract the topic after the indicator
                start_idx = analysis_text.find(indicator)
                if start_idx != -1:
                    # Get context around the indicator
                    context_start = max(0, start_idx - 50)
                    context_end = min(len(analysis_text), start_idx + 100)
                    context = analysis_text[context_start:context_end]

                    # Extract meaningful phrases
                    sentences = context.split('.')
                    for sentence in sentences:
                        if indicator in sentence:
                            # Clean up the sentence
                            clean_sentence = sentence.strip()
                            if len(clean_sentence) > 20 and len(clean_sentence) < 100:
                                gaps.append(clean_sentence)

        # Deduplicate and limit
        unique_gaps = list(set(gaps))[:5]  # Limit to 5 gaps
        return unique_gaps

    def _calculate_length_from_analysis(self, serp_analysis: Dict[str, Any]) -> int:
        """Calculate recommended content length from SERP analysis"""
        if not serp_analysis or not isinstance(serp_analysis, dict):
            return 2500

        analysis_text = serp_analysis.get("analysis", "").lower()
        base_length = 2000

        # Increase length for competitive signals
        competitive_signals = [
            "highly competitive", "competitive market", "many competitors",
            "top results", "featured snippets", "comprehensive guides",
            "in-depth analysis", "detailed reviews"
        ]

        for signal in competitive_signals:
            if signal in analysis_text:
                base_length += 300

        # Increase for content gaps
        if "gap" in analysis_text or "missing" in analysis_text:
            base_length += 400

        # Cap at reasonable maximum
        return min(base_length, 3500)
    
    async def _analyze_serp_landscape(self, keyword: str, style: str = "standard") -> Dict[str, Any]:
        """Deep SERP analysis using Perplexity sonar-reasoning-pro with style-aware quality filtering"""
        if not self.perplexity_key:
            logger.warning("⚠️  Perplexity API key not found - skipping SERP analysis")
            return {}

        # Dynamic date context for freshness (SEO best practice)
        current_date = datetime.now().strftime("%B %Y")  # e.g., "January 2026"
        current_year = datetime.now().strftime("%Y")     # e.g., "2026"
        previous_year = str(int(current_year) - 1)       # e.g., "2025"

        # Determine model before logging
        if style == "research":
            model = "sonar-deep-research"
            timeout = 1200  # 20 minutes
        else:
            model = "sonar-reasoning-pro"
            timeout = 300  # 5 minutes

        logger.info(f"🔍 Starting SERP analysis using {model} (timeout: {timeout}s)...")

        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json"
        }

        # Tiered quality instructions based on content style (with dynamic dates)
        if style == "research":
            quality_filter = f"""
RESEARCH-GRADE SOURCES REQUIRED - Must meet these quality standards:
CURRENT DATE CONTEXT: {current_date}

SOURCE CATEGORIES (of equivalent reputation/quality/trust):
* Market research firms with published methodologies
* Survey platforms with disclosed sample sizes and methods
* Think tanks & consulting firms with peer-reviewed analysis
* Academic journals and university research publications
* Government data sources and official statistics
* Industry research organizations with transparent data collection

QUALITY REQUIREMENTS:
* Cited data with sources and methodology disclosed
* Recent publication ({previous_year}-{current_year} strongly preferred)
* Author credentials and expertise verified
* Peer-reviewed or editorially vetted content
* Transparent data collection and analysis methods

- REJECT: opinion blogs, promotional content, uncited claims, aggregator sites without original research
"""
        else:
            quality_filter = f"""
PREFER credible sources:
CURRENT DATE CONTEXT: {current_date}
* Established publications with specific data and examples
* Recent content ({previous_year}-{current_year} preferred)
* Expert authors with credentials
* Sources that cite data or provide evidence

- AVOID: pure opinion, outdated (pre-{int(current_year)-2}), overly promotional
"""

        prompt = f"""Analyze the SERP landscape for "{keyword}":
{quality_filter}

1. Top ranking domains and their content approach
2. Common content formats (guides, tools, comparisons)
3. Average content depth and comprehensiveness
4. Unique angles competitors are taking
5. Missing topics that users are searching for
6. Featured snippets and their content structure

Provide actionable insights for creating content that will outrank competitors."""

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "search_recency_filter": "month",
            "return_citations": True
        }

        try:
            logger.info(f"   ⏳ Calling Perplexity API...")
            async with self.session.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    analysis = data["choices"][0]["message"]["content"]
                    citations = data.get("citations", [])

                    analysis_len = len(analysis)
                    citation_count = len(citations)

                    logger.info(f"   ✅ Sonar analysis complete: {analysis_len} chars, {citation_count} citations")

                    return {
                        "analysis": analysis,
                        "citations": citations
                    }
                else:
                    logger.warning(f"   ⚠️  Perplexity API failed: HTTP {response.status}")
                    return {}

        except asyncio.TimeoutError:
            logger.error(f"   ❌ Perplexity API timeout after {timeout}s")
            return {}
        except Exception as e:
            logger.error(f"   ❌ SERP analysis error: {e}")
            return {}

    async def _discover_topical_insights(
        self,
        keyword: str,
        topic_scope: str = "broad",
        max_insights: int = 10
    ) -> Dict[str, Any]:
        """
        Discover topical authority insights using Perplexity sonar-reasoning-pro.

        This is SEPARATE from PAA extraction - focuses on:
        - Industry insights & recent developments
        - Expert opinions & thought leadership
        - Data points & statistics from authoritative sources
        - Case studies & real-world examples

        Args:
            keyword: Target keyword to research
            topic_scope: Search breadth - "narrow" (specific solutions),
                        "broad" (industry trends), "industry" (market analysis)
            max_insights: Maximum insights to return after filtering

        Returns:
            Dict with insights, sources, and confidence levels
        """
        if not self.perplexity_key:
            logger.warning("⚠️  Perplexity API key not found - skipping topical insights")
            return {'insights': [], 'sources': [], 'enabled': False}

        logger.info(f"🔍 Discovering topical insights for '{keyword}' (scope: {topic_scope})...")

        # Dynamic date context
        current_date = datetime.now().strftime("%B %Y")
        current_year = datetime.now().strftime("%Y")
        previous_year = str(int(current_year) - 1)

        # Scope-based search configuration
        scope_prompts = {
            "narrow": f"""Focus on SPECIFIC SOLUTIONS and tools related to "{keyword}":
- Feature comparisons between leading solutions
- Implementation case studies with quantified outcomes
- Pricing and ROI data from real deployments
- Expert reviews and evaluations""",
            "broad": f"""Explore INDUSTRY TRENDS and best practices for "{keyword}":
- Emerging trends and innovations in this space
- Best practices from industry leaders
- Common challenges and proven solutions
- Expert perspectives and thought leadership""",
            "industry": f"""Analyze MARKET DYNAMICS for "{keyword}":
- Market size, growth rates, and projections
- Competitive landscape and key players
- Investment and funding trends
- Regulatory and compliance considerations"""
        }

        scope_prompt = scope_prompts.get(topic_scope, scope_prompts["broad"])

        # ICP-aware research prompt
        prompt = f"""Research authoritative insights about "{keyword}" for content creation.

{scope_prompt}

CURRENT DATE: {current_date}
RELEVANCE FILTER - Prioritize insights for these BUSINESS MODELS:
- Sales-led businesses (ad spend → lead capture → sales team → close)
- Pipeline-led businesses (marketing → nurture → convert over time)
- Service businesses (enquiry → quote → job → invoice, 60-90 day cycles)


QUALITY REQUIREMENTS:
- Recent sources ({previous_year}-{current_year} strongly preferred)
- Specific data points with percentages, dollar amounts, timeframes
- Named sources (companies, research firms, publications)
- Actionable insights that can inform content creation

Return 8-12 distinct insights, each with:
1. The specific insight or data point
2. Source attribution (company/publication name)
3. Why this matters for the target audience
4. Confidence level: RESEARCH (peer-reviewed/major research firms), INDUSTRY (established publications/vendors), or OBSERVATIONAL (community/practitioner sources)

Format each insight as:
INSIGHT: [Specific data point or finding]
SOURCE: [Named source]
RELEVANCE: [Why this matters]
CONFIDENCE: [RESEARCH/INDUSTRY/OBSERVATIONAL]
---"""

        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "sonar-reasoning-pro",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "search_recency_filter": "month",
            "return_citations": True
        }

        try:
            async with self.session.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    citations = data.get("citations", [])

                    # Parse insights from response
                    parsed_insights = self._parse_topical_insights(content, keyword)

                    # Filter for relevance
                    filtered_insights = await self._filter_topical_insights(parsed_insights, keyword)

                    # Classify source confidence
                    classified_insights = self._classify_source_confidence(filtered_insights)

                    # Limit to max_insights
                    final_insights = classified_insights[:max_insights]

                    logger.info(f"   ✅ Topical insights: {len(final_insights)}/{len(parsed_insights)} passed filter")

                    return {
                        'insights': final_insights,
                        'sources': citations,
                        'scope': topic_scope,
                        'enabled': True,
                        'raw_count': len(parsed_insights),
                        'filtered_count': len(final_insights)
                    }
                else:
                    logger.warning(f"   ⚠️  Topical insights API failed: HTTP {response.status}")
                    return {'insights': [], 'sources': [], 'enabled': False}

        except asyncio.TimeoutError:
            logger.error(f"   ❌ Topical insights timeout after 120s")
            return {'insights': [], 'sources': [], 'enabled': False}
        except Exception as e:
            logger.error(f"   ❌ Topical insights error: {e}")
            return {'insights': [], 'sources': [], 'enabled': False}

    def _parse_topical_insights(self, content: str, keyword: str) -> List[Dict[str, Any]]:
        """Parse structured insights from Perplexity response."""
        insights = []

        # Split by separator
        blocks = content.split('---')

        for block in blocks:
            if not block.strip():
                continue

            insight = {
                'text': '',
                'source': '',
                'relevance': '',
                'confidence': 'OBSERVATIONAL'  # Default
            }

            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('INSIGHT:'):
                    insight['text'] = line.replace('INSIGHT:', '').strip()
                elif line.startswith('SOURCE:'):
                    insight['source'] = line.replace('SOURCE:', '').strip()
                elif line.startswith('RELEVANCE:'):
                    insight['relevance'] = line.replace('RELEVANCE:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    conf = line.replace('CONFIDENCE:', '').strip().upper()
                    if conf in ['RESEARCH', 'INDUSTRY', 'OBSERVATIONAL']:
                        insight['confidence'] = conf

            # Only add if we have meaningful content
            if insight['text'] and len(insight['text']) > 20:
                insights.append(insight)

        # Fallback: if structured parsing fails, extract paragraphs
        if not insights:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and len(p.strip()) > 50]
            for para in paragraphs[:10]:
                insights.append({
                    'text': para,
                    'source': 'Perplexity Research',
                    'relevance': f'Related to {keyword}',
                    'confidence': 'INDUSTRY'
                })

        return insights

    async def _filter_topical_insights(self, insights: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
        """
        Filter insights for strict relevance to keyword and ICP.

        Stringent filtering criteria:
        1. Must be directly relevant to keyword topic
        2. Must match ICP business models (sales-led, pipeline-led, service)
        3. Must have actionable/informative value
        4. Must not be generic/obvious statements
        """
        if not insights:
            return []

        filtered = []
        keyword_lower = keyword.lower()

        # ICP-relevant terms
        icp_positive = [
            'lead', 'pipeline', 'sales', 'marketing', 'conversion', 'crm',
            'campaign', 'attribution', 'roi', 'ad spend', 'funnel',
            'b2b', 'service', 'agency', 'consultant', 'smb', 'small business',
            'media buyer', 'advertiser', 'ppc', 'paid media', 'demand gen'
        ]

        # Reject terms
        reject_terms = [
            'ecommerce', 'e-commerce', 'shopify', 'retail', 'store',
            'inventory', 'shopping cart', 'checkout', 'product catalog',
            'merchandise', 'warehouse', 'fulfillment', 'dropshipping'
        ]

        for insight in insights:
            text_lower = insight.get('text', '').lower()

            # Skip if contains reject terms
            if any(term in text_lower for term in reject_terms):
                continue

            # Score relevance
            relevance_score = 0

            # Keyword presence
            keyword_parts = keyword_lower.split()
            for part in keyword_parts:
                if len(part) > 3 and part in text_lower:
                    relevance_score += 2

            # ICP alignment
            for term in icp_positive:
                if term in text_lower:
                    relevance_score += 1

            # Has specific data (numbers, percentages)
            if any(char.isdigit() for char in insight.get('text', '')):
                relevance_score += 2
            if '%' in insight.get('text', ''):
                relevance_score += 1
            if '$' in insight.get('text', ''):
                relevance_score += 1

            # Named source bonus
            if insight.get('source') and insight['source'] != 'Perplexity Research':
                relevance_score += 1

            # Include if score meets threshold
            if relevance_score >= 3:
                insight['relevance_score'] = relevance_score
                filtered.append(insight)

        # Sort by relevance score descending
        filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        return filtered

    def _classify_source_confidence(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify and validate source confidence levels.

        RESEARCH-GRADE: Peer-reviewed, .edu/.gov, Gartner/Forrester/McKinsey
        INDUSTRY: Established publications, vendor reports
        OBSERVATIONAL: Community insights, practitioner sources
        """
        research_indicators = [
            'gartner', 'forrester', 'mckinsey', 'harvard', 'mit', 'stanford',
            '.edu', '.gov', 'research', 'study', 'survey', 'pew', 'nielsen',
            'deloitte', 'accenture', 'bcg', 'bain', 'idc', 'statista'
        ]

        industry_indicators = [
            'hubspot', 'salesforce', 'marketo', 'linkedin', 'google',
            'meta', 'facebook', 'microsoft', 'adobe', 'oracle',
            'martech', 'adweek', 'marketing week', 'techcrunch', 'forbes',
            'harvard business review', 'hbr', 'entrepreneur'
        ]

        for insight in insights:
            source_lower = insight.get('source', '').lower()
            text_lower = insight.get('text', '').lower()

            # Check for research-grade indicators
            if any(ind in source_lower or ind in text_lower for ind in research_indicators):
                insight['confidence'] = 'RESEARCH'
            # Check for industry indicators
            elif any(ind in source_lower or ind in text_lower for ind in industry_indicators):
                insight['confidence'] = 'INDUSTRY'
            # Default to observational if not already set higher
            elif insight.get('confidence') not in ['RESEARCH', 'INDUSTRY']:
                insight['confidence'] = 'OBSERVATIONAL'

        return insights


class CommunityResearcher:
    """Handles Reddit, Quora, and community insights"""

    def __init__(self):
        self.ai = None
        self.session = None

    async def _extract_question_topic(self, keyword: str) -> str:
        """Extract core topic from a long keyword using AI for summarization."""
        try:
            prompt = f"""
            Extract the core topic from the following keyword. The topic should be a concise phrase of 5-8 words that captures the main subject and the user's intent.
            It should be suitable for generating search queries for community research on platforms like Reddit and Quora.

            - Preserve key concepts, entities, and relationships.
            - Remove generic filler words but keep important context.
            - The output should be a phrase of 5-8 words, not a full sentence.

            Keyword: "{keyword}"

            Core Topic (5-8 words):
            """
            
            if self.ai.nebius:
                response = await self.ai.nebius.chat.completions.create(
                    model="Qwen/Qwen3-235B-A22B-Instruct-2507",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=50
                )
                topic = response.choices[0].message.content.strip().strip('"')

                if topic:
                    print(f"Extracted question topic: '{topic}' from '{keyword}'")
                    return topic

        except Exception as e:
            print(f"AI topic extraction failed: {e}. Falling back to rule-based method.")

        # Fallback to a simpler, improved rule-based method
        # Clean the string
        cleaned_keyword = re.sub(r'[()]', '', keyword)
        words = cleaned_keyword.split()

        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'in', 'on', 'at', 'by', 'from', 'to', 'vs',
            'how', 'to', 'it', 'for', 'as', 'with'
        }
        
        # A simple noun phrase extractor (very basic)
        content_words = [w for w in words if w.lower() not in stop_words and len(w) > 2]
        
        # Join and limit length
        result = ' '.join(content_words)
        if len(result) > 100: # Limit to a reasonable length
            result = result[:100]

        print(f"Extracted question topic (fallback): '{result}' from '{keyword}'")
        return result

    async def __aenter__(self):
        self.ai = SmartAIRouter()
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def mine_reddit(self, keyword: str, serp_context: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, style: Optional[str] = None) -> Dict[str, Any]:
        """Extract Reddit discussions using Groq Compound - finds highly relevant insights, stops after 2 consecutive failures or max 10

        Args:
            keyword: Target keyword
            serp_context: Optional SERP context for better targeting
            limit: Optional limit on number of insights (for --nrl flag)
            style: Optional content style for question type optimization (e.g., 'research' for data-driven questions)
        """
        try:
            # Initialize AI router for question generation and Compound research
            async with self.ai as ai:
                # Extract core topic for question generation
                question_topic = await self._extract_question_topic(keyword)

                # Enhance topic with SERP context if available
                if serp_context and 'paa_questions' in serp_context:
                    paa_questions = serp_context['paa_questions'][:5]  # Use top 5 PAA questions
                    if paa_questions:
                        # Use AI to blend topic with PAA insights
                        enhanced_topic = await self._enhance_topic_with_serp(question_topic, paa_questions, ai)
                        question_topic = enhanced_topic or question_topic
                        print(f"Enhanced topic with SERP context: '{question_topic}'")

                # Generate 100 natural language questions optimized for Reddit search
                print(f"🎯 Generating 100 Reddit-optimized queries for '{keyword}'...")
                context_questions = serp_context.get('paa_questions', [])[:3] if serp_context else []
                all_questions = await ai.generate_questions(question_topic, count=100, context_questions=context_questions, platform="reddit", style=style)
                print(f"✅ Generated {len(all_questions)} questions")

                # Find highly relevant insights - configurable max queries with minimum enforcement
                all_insights = []
                all_citations = []
                used_questions = []
                successful_queries = 0
                consecutive_failures = 0

                # Determine max queries and minimum based on limit parameter
                # Research mode (limit >= 25): minimum 25 queries, then 1 failure allowed to stop
                # Limited mode (limit = 3): max 3 queries
                # Unlimited mode: max 10 queries
                if limit is not None:
                    max_successful_queries = limit
                    # For research mode, enforce 25 query minimum
                    min_successful_queries = 25 if limit >= 25 else 0

                    if limit >= 25:
                        print(f"📊 Mining Reddit (RESEARCH MODE): target {limit} queries, minimum {min_successful_queries}")
                        print(f"   Strategy: 5 retries before {min_successful_queries} queries, then 1 failure stops mining")
                    else:
                        print(f"📊 Mining Reddit (LIMITED MODE): target {limit} queries, allows 5 consecutive failures")
                else:
                    max_successful_queries = 10  # Default cap for unlimited mode
                    min_successful_queries = 0
                    print(f"📊 Mining Reddit for highly relevant insights (max {max_successful_queries} queries, allows 5 consecutive failures)...")

                question_index = 0

                while successful_queries < max_successful_queries and question_index < len(all_questions):
                    # Get next question
                    current_question = [all_questions[question_index]]

                    print(f"🔍 Reddit Query (attempt {question_index + 1}): '{current_question[0][:50]}...'")

                    # Search Reddit with current question
                    reddit_results = await ai.research_with_compound(current_question, platform="reddit")

                    # Check for insights
                    batch_insights = reddit_results.get('insights', [])
                    batch_citations = reddit_results.get('citations', [])

                    if batch_insights:
                        all_insights.extend(batch_insights)
                        all_citations.extend(batch_citations)
                        used_questions.append(current_question[0])
                        successful_queries += 1
                        consecutive_failures = 0  # Reset failure counter on success

                        # Show progress toward target with visual progress bar
                        queries_remaining = max_successful_queries - successful_queries
                        progress_pct = int((successful_queries / max_successful_queries) * 100)
                        bar_length = 20
                        filled_length = int(bar_length * successful_queries / max_successful_queries)
                        progress_bar = '█' * filled_length + '░' * (bar_length - filled_length)
                        print(f"✅ Found {len(batch_insights)} insights! [{progress_bar}] {progress_pct}% ({successful_queries}/{max_successful_queries} queries, {len(all_insights)} total)")
                    else:
                        consecutive_failures += 1

                        # Dynamic failure tolerance based on progress
                        # Before minimum: tolerate 5 consecutive failures (resilient)
                        # After minimum: tolerate only 1 failure (easy exit)
                        if successful_queries >= min_successful_queries:
                            # After minimum threshold - strict mode (1 failure stops)
                            failure_tolerance = 1
                        else:
                            # Before minimum - resilient mode (5 failures allowed)
                            failure_tolerance = 5

                        print(f"❌ No insights found (consecutive failures: {consecutive_failures}/{failure_tolerance})")

                        # Check if we should stop
                        if consecutive_failures >= failure_tolerance:
                            if successful_queries >= min_successful_queries:
                                print(f"⚠️  Stopping Reddit mining after {consecutive_failures} failure(s) - minimum {min_successful_queries} queries met ({successful_queries} total)")
                                break
                            else:
                                print(f"🔄 {consecutive_failures} consecutive failures, but minimum {min_successful_queries} not met ({successful_queries}/{min_successful_queries}), continuing...")
                                consecutive_failures = 0  # Reset to keep trying until minimum is met

                    question_index += 1

                    # Safety limit - don't exhaust all questions
                    if question_index >= len(all_questions):
                        print(f"⚠️  Exhausted all questions after {successful_queries} successful queries")
                        break

                print(f"📊 Reddit mining complete: {successful_queries} successful queries, {len(all_insights)} total insights")

                # NOTE: Do NOT truncate insights here - send ALL to AI filter for intelligent selection
                # The 'limit' parameter controls QUERIES, not insight count
                # AI filter will intelligently select the most relevant insights from the full set

                return {
                    "insights": all_insights,
                    "questions": used_questions,
                    "citations": all_citations,
                    "successful_queries": successful_queries,
                    "success": successful_queries > 0  # Success if we found any relevant insights
                }
                
        except Exception as e:
            print(f"ERROR in mine_reddit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"insights": [], "questions": [], "citations": [], "success": False}
    
    async def mine_quora(self, keyword: str, serp_context: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, style: Optional[str] = None) -> Dict[str, Any]:
        """Extract Quora questions using Groq Compound - finds highly relevant insights, stops after 2 consecutive failures

        Args:
            keyword: Target keyword
            serp_context: Optional SERP context for better targeting
            limit: Optional limit on number of insights (for --nrl flag)
            style: Optional content style for question type optimization (e.g., 'research' for data-driven questions)
        """
        try:
            # Initialize AI router for question generation and Compound research
            async with SmartAIRouter() as ai:
                # Extract core topic for question generation
                question_topic = await self._extract_question_topic(keyword)

                # Enhance topic with SERP context if available
                if serp_context and 'paa_questions' in serp_context:
                    paa_questions = serp_context['paa_questions'][:5]  # Use top 5 PAA questions
                    if paa_questions:
                        # Use AI to blend topic with PAA insights
                        enhanced_topic = await self._enhance_topic_with_serp(question_topic, paa_questions, ai)
                        question_topic = enhanced_topic or question_topic
                        print(f"Enhanced topic with SERP context: '{question_topic}'")

                # Generate 100 natural language questions optimized for Quora search
                print(f"🎯 Generating 100 Quora-optimized questions for '{keyword}'...")
                context_questions = serp_context.get('paa_questions', [])[:3] if serp_context else []
                all_questions = await ai.generate_questions(question_topic, count=100, context_questions=context_questions, platform="quora", style=style)
                print(f"✅ Generated {len(all_questions)} questions")

                # Find highly relevant insights - stop after 2 consecutive failures or max 5 questions
                all_insights = []
                all_citations = []
                used_questions = []
                successful_queries = 0
                consecutive_failures = 0
                max_consecutive_failures = 2
                max_successful_queries = 5  # Cap at 5 questions
                question_index = 50  # Start from middle of list (different from Reddit)

                # If limit mode is active, reduce query attempts to match target
                if limit is not None:
                    max_successful_queries = min(limit, max_successful_queries)
                    print(f"📊 Mining Quora in LIMITED mode (target: {limit} insights, max {max_successful_queries} queries)")
                else:
                    print(f"📊 Mining Quora for highly relevant insights (max {max_successful_queries} questions, stops after {max_consecutive_failures} consecutive failures)...")

                while consecutive_failures < max_consecutive_failures and successful_queries < max_successful_queries and question_index < len(all_questions):
                    # Get next question
                    current_question = [all_questions[question_index]]

                    print(f"🔍 Quora Query (attempt {question_index - 49}): '{current_question[0][:50]}...'")

                    # Search Quora with current question
                    quora_results = await ai.research_with_compound(current_question, platform="quora")

                    # Check for insights
                    batch_insights = quora_results.get('insights', [])
                    batch_citations = quora_results.get('citations', [])

                    if batch_insights:
                        all_insights.extend(batch_insights)
                        all_citations.extend(batch_citations)
                        used_questions.append(current_question[0])
                        successful_queries += 1
                        consecutive_failures = 0  # Reset failure counter on success

                        # Show progress toward target with visual progress bar
                        progress_pct = int((successful_queries / max_successful_queries) * 100)
                        bar_length = 20
                        filled_length = int(bar_length * successful_queries / max_successful_queries)
                        progress_bar = '█' * filled_length + '░' * (bar_length - filled_length)
                        print(f"✅ Found {len(batch_insights)} insights! [{progress_bar}] {progress_pct}% ({successful_queries}/{max_successful_queries} queries, {len(all_insights)} total)")
                    else:
                        consecutive_failures += 1
                        print(f"❌ No insights found (consecutive failures: {consecutive_failures}/{max_consecutive_failures})")

                        if consecutive_failures >= max_consecutive_failures:
                            print(f"⚠️  Stopping Quora mining after {max_consecutive_failures} consecutive failures")
                            break

                    question_index += 1

                    # Safety limit - don't exhaust all questions
                    if question_index >= len(all_questions):
                        print(f"⚠️  Exhausted all questions after {successful_queries} successful queries")
                        break

                print(f"📊 Quora mining complete: {successful_queries} successful queries, {len(all_insights)} total insights")

                # If still over limit, truncate (shouldn't happen with query limiting, but safety check)
                if limit is not None and len(all_insights) > limit:
                    print(f"🔍 Truncating Quora insights from {len(all_insights)} to {limit}")
                    all_insights = all_insights[:limit]

                # Format results to match expected structure
                return {
                    "questions": used_questions,
                    "expert_insights": all_insights,
                    "citations": all_citations,
                    "raw_content": f"Collected {len(all_insights)} insights from {successful_queries} successful queries",
                    "successful_queries": successful_queries,
                    "success": successful_queries > 0  # Success if we found any relevant insights
                }
                
        except Exception as e:
            print(f"ERROR in mine_quora: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"questions": [], "expert_insights": [], "citations": [], "success": False}
    
    async def analyze_citations(self, content: str) -> Dict[str, Any]:
        """Verify and analyze citations in content"""
        # Extract all claims that might need citations
        claims_pattern = r'(?:According to|Studies show|Research indicates|Data shows|Reports suggest)[^.]+\.'
        claims = re.findall(claims_pattern, content, re.IGNORECASE)
        
        # Extract existing citations
        citation_pattern = r'\[(\d+)\]|\(([^)]+, \d{4})\)'
        citations = re.findall(citation_pattern, content)
        
        return {
            "claims_needing_citation": claims[:10],
            "existing_citations": len(citations),
            "citation_ratio": len(citations) / max(len(claims), 1)
        }
    
    def _extract_insights(self, text: str) -> List[str]:
        """Extract key insights from text"""
        insights = []
        
        # Look for insight patterns
        patterns = [
            r'(?:pain point|frustration|problem|issue|challenge)[:\s]+([^.]+)',
            r'(?:users? (?:report|mention|say|complain))[:\s]+([^.]+)',
            r'(?:common (?:mistake|misconception|problem))[:\s]+([^.]+)',
            r'(?:the (?:biggest|main|primary) (?:issue|problem|challenge))[:\s]+([^.]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            insights.extend([m.strip() for m in matches if len(m.strip()) > 20])
        
        # Deduplicate
        seen = set()
        unique_insights = []
        for insight in insights:
            insight_lower = insight.lower()
            if insight_lower not in seen:
                seen.add(insight_lower)
                unique_insights.append(insight)
        
        return unique_insights
    
    async def _enhance_topic_with_serp(self, base_topic: str, paa_questions: List[str], ai) -> Optional[str]:
        """Use AI to enhance topic with SERP context for better question generation"""
        try:
            if not ai.nebius:
                return None

            prompt = f"""Given the base topic: "{base_topic}"

And these People Also Ask questions from search results:
{chr(10).join(f'- {q}' for q in paa_questions)}

Create an enhanced topic (2-5 words) that captures the core intent and includes key concepts from both the base topic and the PAA questions. Focus on what users are actually searching for.

Enhanced topic should be:
"""

            response = await ai.nebius.chat.completions.create(
                model="Qwen/Qwen3-235B-A22B-Instruct-2507",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )
            enhanced = response.choices[0].message.content.strip().strip('"').strip("'")
            if enhanced and len(enhanced.split()) >= 2 and len(enhanced) < len(base_topic) + 20:
                return enhanced
        except Exception as e:
            print(f"Warning: Failed to enhance topic with SERP: {e}")

        return None

    def _extract_questions(self, text: str) -> List[str]:
        """Extract questions from text"""
        # Simple question extraction
        questions = re.findall(r'[^.!]+\?', text)

        # Clean and filter
        cleaned = []
        for q in questions:
            q = q.strip()
            if len(q) > 15 and len(q) < 200:
                # Remove quotes if present
                q = re.sub(r'^["\']+|["\']+$', '', q)
                cleaned.append(q)

        return cleaned