#!/usr/bin/env python3
"""
Test citation pattern matching against research-style content
"""
import re

# Sample research content with various citation-worthy statements
sample_research_content = """
Our analysis reveals that businesses using automated lead enrichment see significant improvements in conversion rates. Data demonstrates an average cost per lead of $70.11 across advertising platforms in 2025.

Industry data shows that companies integrating CRM automation achieve 20–40% reduction in manual processing time. Research shows that lead management efficiency correlates directly with revenue growth.

According to industry experts, the average Facebook lead costs $18.68, while LinkedIn leads average $75.51 per acquisition. Studies show that multi-touch attribution reduces wasted ad spend by 15–25%.

Quantitative assessment indicates that automated workflows improve lead response time from 24 hours to under 5 minutes. Market analysis suggests that integration platforms reduce technical overhead by 30–50%.

The data confirms that businesses report averaging $50–$200 per qualified lead depending on industry. This demonstrates the critical importance of proper lead valuation and tracking.
"""

# All citation patterns from formatter.py
all_citation_patterns = [
    # === RESEARCH TERMINOLOGY ===
    r'((?:our|the) analysis (?:reveals|shows|demonstrates|indicates)[^.]+\.)',
    r'(data (?:demonstrates|shows|reveals|indicates|suggests)[^.]+\.)',
    r'((?:research|industry) (?:data|findings|analysis) (?:shows|indicates|reveals|confirms)[^.]+\.)',
    r'(market analysis (?:suggests|shows|reveals|indicates)[^.]+\.)',
    r'((?:quantitative|empirical) (?:assessment|evidence|analysis) (?:indicates|supports|shows)[^.]+\.)',
    r'(comparative evaluation (?:shows|reveals|indicates)[^.]+\.)',

    # === STATISTICAL CLAIMS ===
    r'((?:averaging|average|median) \$?\d+(?:[.,]\d+)?(?:%| (?:per|each|in))?[^.]+\.)',
    r'(\d+(?:[.,]\d+)?% (?:increase|decrease|reduction|improvement|growth|of|higher|lower)[^.]+\.)',
    r'((?:from |range of )?\$\d+(?:[.,]\d+)? (?:to|-)?\s?\$?\d+(?:[.,]\d+)?[^.]+\.)',
    r'(\d+–\d+% [^.]+\.)',

    # === INDUSTRY/EXPERT ATTRIBUTION ===
    r'(according to [^.]+\.)',
    r'((?:industry|leading|performance) (?:experts|marketers|analysts|professionals) (?:argue|suggest|recommend|agree)[^.]+\.)',
    r'(experts (?:recommend|suggest|agree|argue)[^.]+\.)',

    # === STUDY/RESEARCH REFERENCES ===
    r'(studies (?:show|indicate|reveal|suggest|demonstrate)[^.]+\.)',
    r'(research (?:shows|indicates|reveals|suggests|demonstrates)[^.]+\.)',
    r'((?:a|the) (?:study|survey|report|analysis) (?:found|showed|revealed|indicated)[^.]+\.)',

    # === CLAIM LANGUAGE ===
    r'((?:businesses|companies|advertisers|organizations) (?:report|experience|achieve|see)[^.]+\d+[^.]*\.)',
    r'(this (?:shows|demonstrates|reveals|indicates)[^.]+\.)',
    r'((?:data|evidence|analysis) (?:confirms|validates|supports)[^.]+\.)',

    # === LEGACY PATTERNS ===
    r'(users report[^.]+\.)',
    r'(many (?:users|businesses|companies)[^.]+\.)',
]

print("🔍 Testing Citation Pattern Matching")
print("=" * 60)
print("\nSample Content:")
print("-" * 60)
print(sample_research_content)
print("\n" + "=" * 60)
print("\nPattern Matches Found:")
print("-" * 60)

total_matches = 0
for i, pattern in enumerate(all_citation_patterns, 1):
    matches = list(re.finditer(pattern, sample_research_content, re.IGNORECASE))
    if matches:
        print(f"\n✓ Pattern {i}: {len(matches)} matches")
        for match in matches:
            matched_text = match.group(1)
            # Truncate if too long
            if len(matched_text) > 80:
                matched_text = matched_text[:77] + "..."
            print(f"  - {matched_text}")
            total_matches += 1

print("\n" + "=" * 60)
print(f"\n📊 RESULTS:")
print(f"   Total patterns: {len(all_citation_patterns)}")
print(f"   Total matches: {total_matches}")
print(f"   Expected inline citations: {total_matches}")
print("\n✅ Pattern expansion successful!" if total_matches >= 10 else "⚠️  Pattern coverage may be insufficient")
