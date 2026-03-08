# A/B Testing Guide for SEO Optimization

This guide outlines the manual A/B testing process for titles and meta descriptions to improve CTR from search results.

## Overview

A/B testing titles and meta descriptions is a proven method to improve Click-Through Rate (CTR) from search results. While we can't programmatically split test SERP appearances, we can systematically test variations over time and measure impact via Google Search Console.

## Process

### 1. Baseline Measurement (Week 1-2)

Before making changes, establish baseline metrics in GSC:

```bash
# Use content_monitor.py to get baseline
python -c "
import asyncio
from core.content_monitor import ContentMonitor

async def check():
    async with ContentMonitor() as monitor:
        needs_refresh, triggers = await monitor.check_refresh_needed('/blog/your-article')
        print(f'Triggers: {triggers}')

asyncio.run(check())
"
```

Record these baseline metrics:
- **Position**: Average ranking position
- **Impressions**: Total impressions over 14 days
- **CTR**: Click-through rate
- **Clicks**: Total clicks

### 2. Create Test Variants

For each element being tested, create 2-3 variants:

#### Title Variants
Follow SEO optimization rules from `config/seo_optimization.json`:

| Variant | Example | Strategy |
|---------|---------|----------|
| Control | "CRM Integration Guide 2026" | Current title |
| A | "15 Best CRM Integrations in 2026 (Reviewed)" | Numbers + year + value indicator |
| B | "How to Set Up CRM Integration in 2026" | Question format |

**Title Best Practices:**
- 50-60 characters ideal (max 70)
- Include year for freshness
- Use numbers for list content
- Include value indicators (Reviewed, Free, Tested)
- Avoid banned words (comprehensive, ultimate, leverage, utilize)

#### Meta Description Variants

| Variant | Example | Strategy |
|---------|---------|----------|
| Control | "Learn about CRM integration..." | Current description |
| A | "Compare 15 top CRM integrations. See pricing, features, and reviews. Get started free." | Comparison hook + CTA |
| B | "Stop wasting hours on manual data entry. CRM integration automates your workflow. See how." | Pain point + benefit + CTA |

**Meta Description Best Practices:**
- 150-160 characters ideal (max 160)
- Primary keyword in first 50 characters
- End with CTA (Get started free, See how, Compare now)
- Address user pain points

### 3. Implementation Schedule

Run each variant for 14-28 days to gather statistically significant data:

| Period | Action | Variant |
|--------|--------|---------|
| Days 1-14 | Baseline measurement | Control |
| Days 15-28 | Test Variant A | A |
| Days 29-42 | Test Variant B | B |
| Days 43-56 | Implement winner | Winner |

### 4. Measuring Results

Use GSC to track key metrics:

```
Position-specific CTR expectations:
- Position 1: 32%
- Position 2: 17%
- Position 3: 11%
- Position 4: 8%
- Position 5: 7%
- Position 6-10: 3-5%
```

**Success Criteria:**
- CTR improvement > 15% relative to control
- No position drop > 1 position
- Consistent improvement across 2+ weeks

### 5. Documentation Template

For each test, document:

```markdown
## A/B Test: [Article Name]

**URL:** /blog/article-slug
**Test Period:** YYYY-MM-DD to YYYY-MM-DD
**Element Tested:** Title / Meta Description

### Variants
| Variant | Text | Period |
|---------|------|--------|
| Control | [original] | Days 1-14 |
| A | [variant A] | Days 15-28 |
| B | [variant B] | Days 29-42 |

### Results
| Variant | Impressions | Clicks | CTR | Avg Position |
|---------|-------------|--------|-----|--------------|
| Control | X | X | X% | X |
| A | X | X | X% | X |
| B | X | X | X% | X |

### Winner: [Variant X]
**Improvement:** +X% CTR
**Notes:** [Any observations about the test]
```

## Quick Reference

### High-Impact Title Patterns
1. **Numbers First:** "15 Best...", "Top 10...", "5 Ways..."
2. **Year Tags:** "... in 2026", "2026 Guide"
3. **Value Indicators:** "(Reviewed)", "(Free)", "(Step-by-Step)"
4. **Question Format:** "How to...", "What is..."

### High-Converting Meta Patterns
1. **Hook → Benefit → CTA:** "Stop X. Do Y instead. See how."
2. **Comparison Hook:** "Compare the best X. See pricing and features. Get started free."
3. **Question + Answer:** "Looking for X? Here's everything you need to know. Learn more."

### Testing Priority

Prioritize testing for:
1. Pages with high impressions but low CTR (< 50% of expected for position)
2. Pages in positions 4-10 (high potential for improvement)
3. Newly published content (after 30 days of baseline)

## Integration with Content Engine

The content engine validates titles and meta descriptions automatically using:
- `validate_title()` - Checks character limits, banned words
- `validate_meta_description()` - Checks length, keyword placement
- `validate_frontmatter_seo()` - Combined validation

When creating A/B test variants, run them through validation:

```python
from core.formatter import validate_title, validate_meta_description

# Test title variant
is_valid, clean_title, issues = validate_title(
    "15 Best CRM Integrations in 2026 (Reviewed)",
    keyword="crm integration"
)
print(f"Valid: {is_valid}, Issues: {issues}")

# Test meta variant
is_valid, clean_meta, issues = validate_meta_description(
    "Compare the best CRM integrations. See pricing, features, and reviews. Get started free.",
    keyword="crm integration"
)
print(f"Valid: {is_valid}, Issues: {issues}")
```

## Resources

- **SEO Config:** `config/seo_optimization.json`
- **Content Monitor:** `core/content_monitor.py`
- **Validation Functions:** `core/formatter.py`
- **GSC Analyzer:** `core/gsc_analyzer.py`
