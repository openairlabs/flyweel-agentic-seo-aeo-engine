# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

V2 Brand Content Engine - A lean AI content generator producing SEO-optimized blog posts via multi-model orchestration. Interactive CLI tool with Rich prompts, GSC-driven SEO optimization, and direct publishing to astro-site.

## Development Commands

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Required `.env` keys:**
```
PERPLEXITY_API_KEY=pplx-...   # SERP analysis + Reddit/Quora community mining (primary)
GOOGLE_API_KEY=...            # Gemini content generation + grounded search (fallback community mining)
NEBIUS_API_KEY=...            # Extraction, editing, filtering, polish (most pipeline steps)
```

### Running the Generator

```bash
# Interactive mode (default)
python generate.py

# Interactive with keyword preset
python generate.py -k "your keyword"

# Classic CLI mode (non-interactive)
python generate.py --no-int -k "your keyword"

# Common flags
--style [standard|guide|comparison|research|news|category|top-compare|feature]
--nr              # Skip Reddit/Quora (faster, cheaper)
--nrl             # Limited: 3 Reddit + 1 Quora
--nb             # No Brand mentions (educational mode)
--publish         # Auto-publish to astro-site
--local           # Save locally only
--depth [quick|standard|comprehensive]
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_formatter.py -v

# Run only unit tests (fast, no API needed)
pytest tests/ -m unit -v

# Run integration tests (requires API keys)
pytest tests/ -m integration -v

# With coverage
pytest tests/ --cov=core --cov-report=html
```

Test markers: `unit`, `integration`, `slow`, `research`, `generation`

### Quick Validation

```bash
# Verify imports
python -c "from core.generator import ContentGenerator; print('OK')"

# Test intent classification
python -c "from core.research import classify_keyword_intent; print(classify_keyword_intent('best crm tools'))"

# Check model initialization
python -c "from core.ai_router import SmartAIRouter; r = SmartAIRouter(); print('Gemini:', '✓' if r.gemini else '✗')"
```

### Code Quality

```bash
flake8 core/ --max-line-length=127
black core/ generate.py
isort core/ generate.py
```

## Core Architecture

### Multi-Model Pipeline (executed in parallel where possible)

| Phase | Model | Provider | Purpose | Temp |
|-------|-------|----------|---------|------|
| SERP Analysis | `sonar-reasoning-pro` | Perplexity | PAA extraction, search landscape | 0.2 |
| Reddit/Quora Mining | `sonar-reasoning-pro` | Perplexity | Community insight extraction (domain-filtered) | 0.2 |
| Reddit/Quora Fallback | `gemini-3-flash-preview` | Google | Grounded search fallback for community mining | 0.2 |
| Content Generation | `gemini-3-flash-preview` | Google | Long-form content (3-part to avoid truncation) | 0.3 |
| Extraction | `moonshotai/Kimi-K2.5` | Nebius | Insight/question/citation extraction | 0.1 |
| Title Optimization | `moonshotai/Kimi-K2.5` | Nebius | SEO title rewrite (creative) | 0.7 |
| Heading Optimization | `moonshotai/Kimi-K2.5` | Nebius | SEO/AEO heading rewrite (creative) | 0.4 |
| Section Editing | `zai-org/GLM-4.7-FP8` | Nebius | Precision section editing (word-count preserving) | 0.15 |
| Segmented Editing | `zai-org/GLM-4.7-FP8` | Nebius | Full content edit pass (MDX/schema-aware) | 0.2 |
| Insight Filtering | `Qwen3-235B-A22B-Instruct-2507` | Nebius | Research quality filtering | 0.1 |
| Content Polish | `Kimi-K2-Instruct` + `Qwen3-235B` | Nebius | A/B test humanization, brand links | 0.35 |
| Question Generation (fallback) | `moonshotai/Kimi-K2.5` | Nebius | Community research questions (if no Gemini) | 0.6 |
| Site Analysis | `zai-org/GLM-4.7-FP8` | Nebius | Live site content extraction | 0.1 |

**Nebius fallback chain**: Kimi-K2.5 → GLM-4.7-FP8 → Qwen3-235B → DeepSeek-V3.2

### Key Files

```
core/
├── ai_router.py      # SmartAIRouter - multi-model orchestration
├── generator.py      # ContentGenerator - main generation logic, 8 content styles
├── research.py       # Web research + classify_keyword_intent()
├── formatter.py      # AstroFormatter + SEO validation gates
├── gsc_analyzer.py   # GSC API, traffic potential formula, cannibalization check
├── content_monitor.py # Refresh triggers (position drops, CTR, staleness)
├── publisher.py      # Direct publish to astro-site/content/blog/
├── repo_extractor.py # Astro-brand repo context extraction
└── cli/              # Interactive CLI (Click + Rich + Questionary)
    ├── app.py        # Main Click commands
    ├── prompts.py    # Interactive prompts
    ├── output.py     # Rich panels and tables
    └── progress.py   # Progress tracking

config/
├── brand_voice_config.json    # Tone, banned words, style rules
├── icp_config.json            # Ideal Customer Profile
├── seo_optimization.json      # Title/meta limits, banned words, CTR targets
├── products.json              # Brand product registry
└── content-templates.json     # Style templates

generate.py                    # CLI entry point
```

### Content Styles

1. **standard** - Comprehensive overview (2000-2500 words)
2. **guide** - Step-by-step tutorial with "Manual Way vs Brand way"
3. **comparison** - Product comparison with H4 review framework
4. **top-compare** - "Top X Best" ranked listicle (Omnius-style)
5. **research** - Data-driven analysis with executive summary
6. **news** - Trending topic coverage
7. **category** - Category overview/listicle
8. **feature** - Conversion-focused product page

### Key Patterns

**3-Part Content Generation**: Gemini output split into 3 sequential parts to avoid truncation:
- Part 1: Frontmatter + intro + first 2 sections
- Part 2: Middle sections (with Part 1 context)
- Part 3: Final sections + FAQ (with Parts 1+2 context)

**Segmented Edit/Polish**: Content split by H2 headings, processed in batches of 2 with ±8% word count tolerance.

**Intent-Based Structure**: `classify_keyword_intent()` returns recommended style:
- Informational (how to, what is) → guide
- Commercial (best, top, vs) → comparison
- Transactional (pricing, buy) → feature
- Navigational → standard

**GSC Traffic Formula** (`core/gsc_analyzer.py`):
```
Traffic Potential = Impressions × Expected CTR at Target Position
Position 1: 32%, Position 5: 7%, Position 10: 2.5%
```

### SEO Validation Gates

`core/formatter.py` enforces rules from `config/seo_optimization.json`:

```python
from core.formatter import validate_title, validate_meta_description

# Title: 30-70 chars, keyword required, banned words filtered
is_valid, clean_title, issues = validate_title("My Title", "keyword")

# Meta: 120-160 chars, keyword in first 50 chars, CTA required
is_valid, clean_meta, issues = validate_meta_description("Description...", "keyword")
```

## Adding a New Content Style

1. Add prompt builder in `core/generator.py`:
   ```python
   def _get_my_style_prompt(self, keyword: str, context: Dict, no_brand: bool = False) -> str:
       pass
   ```

2. Register in `self.style_prompts` dict in `ContentGenerator.__init__`

3. Add to CLI choices in `generate.py` and `core/cli/app.py`

4. Add to `core/cli/prompts.py` style selection

## Modifying SEO Rules

Edit `config/seo_optimization.json` - changes apply immediately (no restart needed):
```json
{
  "title_rules": {
    "min_length": 30,
    "max_length": 70,
    "banned_words": ["comprehensive", "ultimate", "leverage"]
  }
}
```

## Error Handling

- Missing Nebius key: Extraction, editing, filtering, polish all skipped (graceful degradation)
- Missing Perplexity key: SERP analysis fails, community mining falls back to Gemini grounded search
- Missing Gemini key: Content generation fails, community mining falls back to nothing if Perplexity also missing
- GSC unavailable: Continues without GSC features
- Cannibalization detected: Aborts with recommendation to optimize existing content
- Research failures: Return empty structures, generation continues

## Output Structure

```
output/generations/YYYY-MM-DD_keyword-slug/
├── final.mdx      # Polished, ready-to-publish
├── raw.mdx        # Pre-polish draft
└── metadata.json  # Research data (with --save-research)
```

## Performance

- **Generation time**: 15-25 seconds (full pipeline)
- **Cost per article**: ~$0.11 (with community research), ~$0.08 (with `--nr`)
