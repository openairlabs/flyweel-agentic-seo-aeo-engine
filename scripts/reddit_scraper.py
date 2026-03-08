#!/usr/bin/env python3
"""
Reddit Sentiment Analyzer - Standalone Tool

Scrapes Reddit for hyper-similar sentiments on a given topic, scores similarity,
filters by platforms/tools, and outputs structured results with clickable links.

Usage:
    python3 reddit_scraper.py -t "CRM integration challenges"
    python3 reddit_scraper.py -t "marketing automation" --pl "HubSpot,Salesforce" --threshold 70
"""

import asyncio
import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Import existing infrastructure
from core.ai_router import SmartAIRouter
from core.research import CommunityResearcher


class SimilarityScorer:
    """Qwen 235B-powered similarity scoring for Reddit posts"""

    def __init__(self, ai_router: SmartAIRouter):
        self.ai = ai_router

    async def score_batch(self, posts: List[Dict[str, Any]], topic: str, platforms: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Score similarity of Reddit posts to topic using Qwen 235B

        Args:
            posts: List of post dicts with 'id', 'title', 'content', 'url'
            topic: Topic to score similarity against
            platforms: Optional list of platforms to consider in scoring

        Returns:
            Dict mapping post_id to {"score": 85, "reasoning": "...", "platform_mentions": [...]}
        """
        if not posts:
            return {}

        if not self.ai.nebius:
            print("⚠️  Qwen 235B unavailable, using Llama 3.3 70B fallback for scoring")
            return await self._score_with_llama(posts, topic, platforms)

        # Prepare posts for scoring (limit content length for token efficiency)
        posts_for_scoring = []
        for post in posts[:30]:  # Batch limit
            posts_for_scoring.append({
                "id": post.get('id', ''),
                "title": post.get('title', '')[:200],
                "content": post.get('content', '')[:500],  # First 500 chars
                "url": post.get('url', '')
            })

        platform_instruction = ""
        if platforms:
            platform_instruction = f"\n\n**Platform Bonus**: Add +10 points if post meaningfully discusses: {', '.join(platforms)}"

        prompt = f"""Score these Reddit posts for similarity to the topic: "{topic}"

Scoring criteria (0-100 scale):
1. **Semantic similarity** (0-40): How closely related is the post to "{topic}"?
2. **Specificity** (0-30): Does it provide specific insights, pain points, or experiences?
3. **Actionability** (0-30): Are there concrete examples, solutions, or lessons?
{platform_instruction}

Posts to score:
{json.dumps(posts_for_scoring, indent=2)}

**Return ONLY valid JSON** with this structure:
{{
  "post_id_1": {{
    "score": 85,
    "reasoning": "Directly discusses [topic aspect] with specific examples of X and Y",
    "platform_mentions": ["Platform1", "Platform2"]
  }},
  "post_id_2": {{
    "score": 72,
    "reasoning": "Related to topic but focuses on tangential issue Z",
    "platform_mentions": []
  }}
}}

Rules:
- Score objectively based on relevance and value
- Lower scores (0-40): Off-topic, generic, or unhelpful
- Medium scores (41-70): Related but not directly on-topic
- High scores (71-100): Highly relevant with specific, actionable insights
- Return ONLY the JSON object, no markdown, no explanations
"""

        try:
            response = await self.ai.nebius.chat.completions.create(
                model="Qwen/Qwen3-235B-A22B-Instruct-2507",
                messages=[
                    {"role": "system", "content": "You are an expert at evaluating content relevance and quality. You score Reddit posts objectively for similarity to a given topic. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )

            result = response.choices[0].message.content.strip()

            # Parse JSON with fallback strategies
            scores = self._parse_scores_json(result)

            if not scores:
                print("⚠️  Failed to parse Qwen scoring response, using fallback")
                return await self._score_with_llama(posts, topic, platforms)

            return scores

        except Exception as e:
            print(f"⚠️  Qwen scoring failed: {e}, using Kimi fallback")
            return await self._score_with_llama(posts, topic, platforms)

    async def _score_with_llama(self, posts: List[Dict[str, Any]], topic: str, platforms: Optional[List[str]]) -> Dict[str, Dict[str, Any]]:
        """Fallback scoring using Kimi-K2.5 on Nebius"""
        if not self.ai.nebius:
            # Ultimate fallback: basic keyword matching
            return self._keyword_score_fallback(posts, topic, platforms)

        # Simplified prompt for Llama
        posts_for_scoring = []
        for post in posts[:30]:
            posts_for_scoring.append({
                "id": post.get('id', ''),
                "title": post.get('title', '')[:150],
                "content": post.get('content', '')[:400]
            })

        prompt = f"""Score Reddit posts 0-100 for relevance to: "{topic}"

Posts: {json.dumps(posts_for_scoring, indent=2)}

Return JSON: {{"post_id": {{"score": 75, "reasoning": "..."}}, ...}}"""

        try:
            response = await self.ai.nebius.chat.completions.create(
                model=self.ai.model_creative,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=3000
            )

            result = response.choices[0].message.content.strip()
            scores = self._parse_scores_json(result)

            # Fill in missing platform_mentions if not returned
            for post_id, score_data in scores.items():
                if 'platform_mentions' not in score_data:
                    score_data['platform_mentions'] = []

            return scores if scores else self._keyword_score_fallback(posts, topic, platforms)

        except Exception as e:
            print(f"⚠️  Kimi scoring failed: {e}, using keyword fallback")
            return self._keyword_score_fallback(posts, topic, platforms)

    def _parse_scores_json(self, text: str) -> Dict[str, Dict[str, Any]]:
        """Parse JSON scores with repair strategies"""
        # Clean markdown code fences
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = text.strip()

        # Find JSON object
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]

        try:
            scores = json.loads(text)
            # Validate structure
            if isinstance(scores, dict):
                for post_id, data in scores.items():
                    if not isinstance(data, dict) or 'score' not in data:
                        return {}
                return scores
        except json.JSONDecodeError:
            # Try repair
            try:
                # Remove trailing commas
                repaired = re.sub(r',(\s*[}\]])', r'\1', text)
                scores = json.loads(repaired)
                if isinstance(scores, dict):
                    return scores
            except:
                pass

        return {}

    def _keyword_score_fallback(self, posts: List[Dict[str, Any]], topic: str, platforms: Optional[List[str]]) -> Dict[str, Dict[str, Any]]:
        """Basic keyword-based scoring as ultimate fallback"""
        topic_words = set(topic.lower().split())
        platform_words = set([p.lower() for p in platforms]) if platforms else set()

        scores = {}
        for post in posts:
            post_id = post.get('id', '')
            title = post.get('title', '').lower()
            content = post.get('content', '').lower()
            combined = f"{title} {content}"

            # Count topic word matches
            matches = sum(1 for word in topic_words if word in combined and len(word) > 3)
            score = min(100, matches * 15)  # 15 points per keyword match, max 100

            # Platform bonus
            platform_matches = [p for p in platforms if p.lower() in combined] if platforms else []
            if platform_matches:
                score = min(100, score + 10)

            scores[post_id] = {
                "score": score,
                "reasoning": f"Keyword matching: {matches} topic words found",
                "platform_mentions": platform_matches
            }

        return scores


class PlatformFilter:
    """Context-aware platform filtering using AI"""

    def __init__(self, ai_router: SmartAIRouter):
        self.ai = ai_router

    def filter_by_platforms(self, posts: List[Dict[str, Any]], platforms: List[str], scores: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter posts that meaningfully discuss specified platforms

        Args:
            posts: List of post dicts
            platforms: List of platform/tool names to filter by
            scores: Scoring results with platform_mentions

        Returns:
            Filtered list of posts that discuss the platforms
        """
        if not platforms:
            return posts

        filtered = []
        for post in posts:
            post_id = post.get('id', '')

            # Check if scoring detected platform mentions
            score_data = scores.get(post_id, {})
            detected_platforms = score_data.get('platform_mentions', [])

            # If scoring found platforms, use that
            if detected_platforms:
                # Check if any detected platform matches our filter
                if any(p.lower() in [dp.lower() for dp in detected_platforms] for p in platforms):
                    filtered.append(post)
                    continue

            # Fallback: simple keyword check in content
            content = f"{post.get('title', '')} {post.get('content', '')}".lower()
            if any(platform.lower() in content for platform in platforms):
                filtered.append(post)

        return filtered


class OutputFormatter:
    """Formats output for console and file"""

    # ANSI color codes
    COLORS = {
        'header': '\033[95m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'bold': '\033[1m',
        'underline': '\033[4m',
        'reset': '\033[0m'
    }

    def print_console_header(self, topic: str, total: int, filtered: int, threshold: int, platforms: Optional[List[str]] = None):
        """Print colored console header"""
        print(f"\n{self.COLORS['bold']}{self.COLORS['cyan']}{'═' * 70}{self.COLORS['reset']}")
        print(f"{self.COLORS['bold']}🎯 Reddit Sentiment Analysis: {self.COLORS['green']}\"{topic}\"{self.COLORS['reset']}")
        print(f"{self.COLORS['yellow']}📊 Found {total} posts | Filtered to {filtered} high-relevance insights | Min threshold: {threshold}{self.COLORS['reset']}")

        if platforms:
            print(f"{self.COLORS['cyan']}🔍 Platform filter: {', '.join(platforms)}{self.COLORS['reset']}")

        print(f"{self.COLORS['bold']}{self.COLORS['cyan']}{'═' * 70}{self.COLORS['reset']}\n")

    def print_console_post(self, post: Dict[str, Any], score_data: Dict[str, Any], index: int):
        """Print single post with formatting"""
        score = score_data.get('score', 0)
        reasoning = score_data.get('reasoning', 'No reasoning provided')
        platform_mentions = score_data.get('platform_mentions', [])

        # Score color based on value
        if score >= 80:
            score_color = self.COLORS['green']
        elif score >= 60:
            score_color = self.COLORS['yellow']
        else:
            score_color = self.COLORS['red']

        # Print post header
        print(f"{self.COLORS['bold']}[Score: {score_color}{score}{self.COLORS['reset']}{self.COLORS['bold']}] 🔗 {self.COLORS['blue']}{post.get('url', 'No URL')}{self.COLORS['reset']}")
        print(f"{self.COLORS['bold']}Title:{self.COLORS['reset']} {post.get('title', 'Untitled')}")

        # Metadata
        author = post.get('author', 'unknown')
        subreddit = post.get('subreddit', 'unknown')
        timestamp = post.get('timestamp', 'unknown')
        votes = post.get('votes', 0)

        print(f"{self.COLORS['cyan']}Author:{self.COLORS['reset']} u/{author} | {self.COLORS['cyan']}Subreddit:{self.COLORS['reset']} r/{subreddit} | {timestamp}")
        if votes:
            print(f"{self.COLORS['green']}🔼 {votes} votes{self.COLORS['reset']}")

        # Content excerpt
        content = post.get('content', '')
        if content:
            excerpt = content[:300] + "..." if len(content) > 300 else content
            print(f"\n{self.COLORS['bold']}Excerpt:{self.COLORS['reset']}\n{excerpt}\n")

        # Platform mentions
        if platform_mentions:
            print(f"{self.COLORS['cyan']}Platform mentions:{self.COLORS['reset']} {', '.join(platform_mentions)}")

        # Reasoning
        print(f"{self.COLORS['yellow']}Similarity reasoning:{self.COLORS['reset']} {reasoning}")

        print(f"\n{self.COLORS['cyan']}{'─' * 70}{self.COLORS['reset']}\n")

    def generate_markdown(self, topic: str, posts: List[Dict[str, Any]], scores: Dict[str, Dict[str, Any]],
                          metadata: Dict[str, Any]) -> str:
        """Generate markdown document"""
        md = f"""# Reddit Sentiment Analysis: {topic}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Posts Analyzed**: {metadata.get('total_analyzed', 0)}
**Filtered Results**: {metadata.get('filtered_count', 0)}
**Similarity Threshold**: {metadata.get('threshold', 0)}
**Time Filter**: {metadata.get('time_filter', 'alltime')}
"""

        if metadata.get('platforms'):
            md += f"**Platform Filter**: {', '.join(metadata['platforms'])}\n"

        md += "\n---\n\n## High-Relevance Insights\n\n"

        for i, post in enumerate(posts, 1):
            post_id = post.get('id', '')
            score_data = scores.get(post_id, {})
            score = score_data.get('score', 0)
            reasoning = score_data.get('reasoning', 'No reasoning provided')
            platform_mentions = score_data.get('platform_mentions', [])

            md += f"### {i}. [Score: {score}] {post.get('title', 'Untitled')}\n\n"
            md += f"**Link**: {post.get('url', 'No URL')}\n"
            md += f"**Author**: u/{post.get('author', 'unknown')}\n"
            md += f"**Subreddit**: r/{post.get('subreddit', 'unknown')}\n"
            md += f"**Posted**: {post.get('timestamp', 'unknown')}\n"

            if post.get('votes'):
                md += f"**Votes**: {post.get('votes')} ⬆\n"

            md += f"\n**Full Post Content**:\n```\n{post.get('content', 'No content')}\n```\n\n"

            if platform_mentions:
                md += f"**Platform Mentions**: {', '.join(platform_mentions)}\n"

            md += f"**Similarity Score**: {score}/100\n"
            md += f"**Reasoning**: {reasoning}\n\n"
            md += "---\n\n"

        return md

    def save_files(self, topic: str, posts: List[Dict[str, Any]], scores: Dict[str, Dict[str, Any]],
                   metadata: Dict[str, Any], output_dir: str):
        """Save markdown and JSON files"""
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate slug
        slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        base_name = f"{slug}-{timestamp}"

        # Save markdown
        md_content = self.generate_markdown(topic, posts, scores, metadata)
        md_file = output_path / f"{base_name}.md"
        md_file.write_text(md_content)
        print(f"{self.COLORS['green']}✅ Saved markdown: {md_file}{self.COLORS['reset']}")

        # Save JSON
        json_data = {
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
            "metadata": metadata,
            "posts": posts,
            "scores": scores
        }
        json_file = output_path / f"{base_name}.json"
        json_file.write_text(json.dumps(json_data, indent=2))
        print(f"{self.COLORS['green']}✅ Saved JSON: {json_file}{self.COLORS['reset']}")


class RedditSentimentAnalyzer:
    """Main orchestrator for Reddit sentiment analysis"""

    def __init__(self):
        self.ai = None
        self.community = None
        self.scorer = None
        self.platform_filter = None
        self.formatter = OutputFormatter()

    async def analyze(self, topic: str, platforms: Optional[List[str]] = None,
                     limit: int = 30, min_outputs: int = 5, threshold: int = 60,
                     output_dir: str = "output/reddit_analysis", time_filter: str = "alltime"):
        """Main analysis pipeline

        Args:
            topic: Topic to analyze
            platforms: Optional list of platforms to filter by
            limit: Max insights to retrieve
            min_outputs: Minimum outputs to guarantee
            threshold: Similarity threshold (0-100)
            output_dir: Output directory path
            time_filter: Time filter (alltime, 1mo, 1w)
        """
        print(f"\n{self.formatter.COLORS['bold']}🚀 Starting Reddit Sentiment Analysis{self.formatter.COLORS['reset']}")
        print(f"{self.formatter.COLORS['cyan']}Topic: {topic}{self.formatter.COLORS['reset']}")
        print(f"{self.formatter.COLORS['cyan']}Target: {limit} posts | Min outputs: {min_outputs} | Threshold: {threshold} | Time: {time_filter}{self.formatter.COLORS['reset']}\n")

        # Initialize
        async with SmartAIRouter() as ai, CommunityResearcher() as community:
            self.ai = ai
            self.community = community
            self.scorer = SimilarityScorer(ai)
            self.platform_filter = PlatformFilter(ai)

            # Phase 1: Mine Reddit
            print(f"{self.formatter.COLORS['yellow']}⏳ Phase 1: Mining Reddit (time filter: {time_filter})...{self.formatter.COLORS['reset']}")
            posts = await self._mine_reddit_with_time_filter(topic, limit, time_filter)

            if not posts:
                print(f"{self.formatter.COLORS['red']}❌ No Reddit posts found for topic: {topic}{self.formatter.COLORS['reset']}")
                return

            print(f"{self.formatter.COLORS['green']}✅ Found {len(posts)} Reddit posts{self.formatter.COLORS['reset']}\n")

            # Phase 2: Score similarity
            print(f"{self.formatter.COLORS['yellow']}⏳ Phase 2: Scoring similarity with Qwen 235B...{self.formatter.COLORS['reset']}")
            scores = await self.scorer.score_batch(posts, topic, platforms)
            print(f"{self.formatter.COLORS['green']}✅ Scored {len(scores)} posts{self.formatter.COLORS['reset']}\n")

            # Phase 3: Filter by platforms (if specified)
            if platforms:
                print(f"{self.formatter.COLORS['yellow']}⏳ Phase 3: Filtering by platforms: {', '.join(platforms)}...{self.formatter.COLORS['reset']}")
                posts = self.platform_filter.filter_by_platforms(posts, platforms, scores)
                print(f"{self.formatter.COLORS['green']}✅ Filtered to {len(posts)} posts mentioning platforms{self.formatter.COLORS['reset']}\n")

            # Phase 4: Apply threshold and guarantee minimum
            print(f"{self.formatter.COLORS['yellow']}⏳ Phase 4: Applying threshold and ensuring minimum outputs...{self.formatter.COLORS['reset']}")
            final_posts, final_threshold = self._apply_threshold_with_guarantee(posts, scores, threshold, min_outputs)
            print(f"{self.formatter.COLORS['green']}✅ Final result: {len(final_posts)} posts (threshold: {final_threshold}){self.formatter.COLORS['reset']}\n")

            # Phase 5: Output
            print(f"{self.formatter.COLORS['yellow']}⏳ Phase 5: Generating output...{self.formatter.COLORS['reset']}\n")

            # Console output
            self.formatter.print_console_header(topic, len(posts), len(final_posts), final_threshold, platforms)

            for i, post in enumerate(final_posts, 1):
                post_id = post.get('id', '')
                score_data = scores.get(post_id, {})
                self.formatter.print_console_post(post, score_data, i)

            # Save files
            metadata = {
                "total_analyzed": len(posts),
                "filtered_count": len(final_posts),
                "threshold": final_threshold,
                "platforms": platforms,
                "time_filter": time_filter
            }
            self.formatter.save_files(topic, final_posts, scores, metadata, output_dir)

            print(f"\n{self.formatter.COLORS['bold']}{self.formatter.COLORS['green']}🎉 Analysis complete!{self.formatter.COLORS['reset']}\n")

    async def _mine_reddit_with_time_filter(self, topic: str, limit: int, time_filter: str) -> List[Dict[str, Any]]:
        """Mine Reddit with time filtering

        Args:
            topic: Topic to mine
            limit: Max posts to retrieve
            time_filter: Time filter (alltime, 1mo, 1w)

        Returns:
            List of post dicts
        """
        try:
            # Generate simple template-based questions (fast, no AI needed)
            print(f"🎯 Generating search questions for '{topic}'...")
            max_queries = min(10, limit // 3)  # Calculate needed queries first
            questions = self._generate_simple_questions(topic, max_queries * 2)  # 2x buffer for quality

            # Build time-filtered search queries
            time_query_map = {
                "alltime": "",  # No time restriction
                "1mo": "after:30d",  # Posts from last 30 days
                "1w": "after:7d"  # Posts from last 7 days
            }

            time_query = time_query_map.get(time_filter, "")

            all_posts = []
            used_questions = []

            print(f"🔍 Mining Reddit with {max_queries} queries (time filter: {time_filter})...")

            for i, question in enumerate(questions[:max_queries]):
                # Build search query with time filter
                if time_query:
                    search_query = f"site:reddit.com {time_query} {question}"
                else:
                    search_query = f"site:reddit.com {question}"

                print(f"   Query {i+1}/{max_queries}: {question[:60]}...")

                # Use Perplexity + Gemini grounded search
                result = await self.ai.research_with_compound([question], platform="reddit")

                insights = result.get('insights', [])
                citations = result.get('citations', [])

                if insights:
                    print(f"   ✅ Found {len(insights)} insights")

                    # Convert to structured posts
                    for j, insight in enumerate(insights):
                        citation_url = citations[j] if j < len(citations) else ''
                        author, subreddit, post_id = self._parse_reddit_url(citation_url)

                        all_posts.append({
                            "id": post_id or f"post_{len(all_posts)}",
                            "title": insight[:100] if len(insight) > 100 else insight,
                            "content": insight,
                            "url": citation_url if citation_url else f"https://reddit.com/unknown_{len(all_posts)}",
                            "author": author or "unknown",
                            "subreddit": subreddit or "unknown",
                            "timestamp": self._format_time_filter(time_filter),
                            "votes": 0
                        })

                        used_questions.append(question)

                        if len(all_posts) >= limit:
                            print(f"✅ Reached limit of {limit} posts")
                            return all_posts[:limit]
                else:
                    print(f"   ⚠️  No insights found")

                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)

            print(f"✅ Collected {len(all_posts)} total posts")
            return all_posts[:limit]

        except Exception as e:
            print(f"{self.formatter.COLORS['red']}❌ Reddit mining failed: {e}{self.formatter.COLORS['reset']}")
            import traceback
            traceback.print_exc()
            return []

    def _format_time_filter(self, time_filter: str) -> str:
        """Format time filter for display"""
        time_map = {
            "alltime": "any time",
            "1mo": "within 1 month",
            "1w": "within 1 week"
        }
        return time_map.get(time_filter, "recent")

    def _generate_simple_questions(self, topic: str, count: int) -> List[str]:
        """Generate template-based questions instantly (no AI needed)"""
        templates = [
            f"How do I {topic}?",
            f"What's the best way to {topic}?",
            f"Help with {topic}",
            f"Problems with {topic}",
            f"Anyone else struggling with {topic}?",
            f"{topic} tips and tricks",
            f"Best practices for {topic}",
            f"Common mistakes when {topic}",
            f"Why is {topic} so difficult?",
            f"{topic} workflow",
            f"Automating {topic}",
            f"{topic} solutions",
            f"{topic} tools and software",
            f"Manual {topic} vs automated",
            f"{topic} errors and fixes",
            f"Simplify {topic}",
            f"{topic} step by step",
            f"Quick way to {topic}",
            f"{topic} headaches",
            f"Frustrated with {topic}"
        ]
        return templates[:count]

    async def _mine_reddit(self, topic: str, limit: int) -> List[Dict[str, Any]]:
        """Mine Reddit for posts about topic"""
        try:
            # Use existing CommunityResearcher infrastructure
            result = await self.community.mine_reddit(topic, serp_context=None, limit=limit)

            insights = result.get('insights', [])
            citations = result.get('citations', [])

            # Convert insights to structured posts
            posts = []
            for i, insight in enumerate(insights):
                # Try to extract metadata from citation if available
                citation_url = citations[i] if i < len(citations) else ''

                # Parse Reddit URL for metadata
                author, subreddit, post_id = self._parse_reddit_url(citation_url)

                posts.append({
                    "id": post_id or f"post_{i}",
                    "title": insight[:100] if len(insight) > 100 else insight,  # First 100 chars as title
                    "content": insight,
                    "url": citation_url if citation_url else f"https://reddit.com/unknown_{i}",
                    "author": author or "unknown",
                    "subreddit": subreddit or "unknown",
                    "timestamp": "recent",
                    "votes": 0  # Not extracted by current system
                })

            return posts

        except Exception as e:
            print(f"{self.formatter.COLORS['red']}❌ Reddit mining failed: {e}{self.formatter.COLORS['reset']}")
            return []

    def _parse_reddit_url(self, url: str) -> tuple:
        """Extract author, subreddit, post_id from Reddit URL"""
        if not url or 'reddit.com' not in url:
            return None, None, None

        # Pattern: reddit.com/r/subreddit/comments/post_id/title/
        match = re.search(r'reddit\.com/r/([^/]+)/comments/([^/]+)', url)
        if match:
            subreddit = match.group(1)
            post_id = match.group(2)
            return None, subreddit, post_id

        return None, None, None

    def _apply_threshold_with_guarantee(self, posts: List[Dict[str, Any]],
                                       scores: Dict[str, Dict[str, Any]],
                                       threshold: int, min_outputs: int) -> tuple:
        """Apply threshold with minimum output guarantee

        Returns:
            (filtered_posts, final_threshold)
        """
        # Attach scores to posts and sort
        scored_posts = []
        for post in posts:
            post_id = post.get('id', '')
            score_data = scores.get(post_id, {})
            score = score_data.get('score', 0)
            scored_posts.append((post, score))

        # Sort by score descending
        scored_posts.sort(key=lambda x: x[1], reverse=True)

        # Try original threshold
        filtered = [(p, s) for p, s in scored_posts if s >= threshold]

        if len(filtered) >= min_outputs:
            return [p for p, s in filtered], threshold

        # Relax threshold if needed
        current_threshold = threshold
        while len(filtered) < min_outputs and current_threshold > 0:
            current_threshold -= 10
            filtered = [(p, s) for p, s in scored_posts if s >= current_threshold]

        if len(filtered) >= min_outputs:
            return [p for p, s in filtered], current_threshold

        # If still not enough, take top N by score
        print(f"{self.formatter.COLORS['yellow']}⚠️  Insufficient high-scoring posts, taking top {min_outputs} by score{self.formatter.COLORS['reset']}")
        return [p for p, s in scored_posts[:min_outputs]], 0


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Reddit Sentiment Analyzer - Scrape and analyze Reddit for hyper-similar sentiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 reddit_scraper.py -t "CRM integration challenges"
  python3 reddit_scraper.py -t "marketing automation" --pl "HubSpot,Salesforce"
  python3 reddit_scraper.py -t "lead attribution" --threshold 70 --min 10 -1w
  python3 reddit_scraper.py -t "CRM migration" -1mo --pl "Salesforce"
        """
    )

    parser.add_argument('-t', '--topic', required=True, help='Topic to analyze (REQUIRED)')
    parser.add_argument('--pl', '--platforms', dest='platforms', help='Comma-separated platforms/tools to filter by')
    parser.add_argument('--limit', type=int, default=30, help='Max insights to retrieve (default: 30)')
    parser.add_argument('--min', type=int, default=5, help='Minimum outputs to guarantee (default: 5)')
    parser.add_argument('--threshold', type=int, default=60, help='Similarity threshold 0-100 (default: 60)')
    parser.add_argument('--output', default='output/reddit_analysis', help='Output directory (default: output/reddit_analysis/)')

    # Time filter options (mutually exclusive)
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('-alltime', action='store_const', const='alltime', dest='time_filter', default='alltime', help='Search all time (default)')
    time_group.add_argument('-1mo', action='store_const', const='1mo', dest='time_filter', help='Search posts from last 30 days')
    time_group.add_argument('-1w', action='store_const', const='1w', dest='time_filter', help='Search posts from last 7 days')

    args = parser.parse_args()

    # Parse platforms
    platforms = None
    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(',')]

    # Validate inputs
    if args.threshold < 0 or args.threshold > 100:
        print("❌ Error: Threshold must be between 0 and 100")
        sys.exit(1)

    if args.min < 1:
        print("❌ Error: Minimum outputs must be at least 1")
        sys.exit(1)

    if args.limit < args.min:
        print(f"⚠️  Warning: Limit ({args.limit}) is less than min ({args.min}), setting limit to {args.min}")
        args.limit = args.min

    # Run analysis
    analyzer = RedditSentimentAnalyzer()
    await analyzer.analyze(
        topic=args.topic,
        platforms=platforms,
        limit=args.limit,
        min_outputs=args.min,
        threshold=args.threshold,
        output_dir=args.output,
        time_filter=args.time_filter
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
