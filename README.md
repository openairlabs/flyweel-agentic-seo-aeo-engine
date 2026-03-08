
![AEO Engine Architecture Overview](assets/readme-hero.png)

*Originally built by [Flyweel](https://flyweel.co)*

**We're building the layer connecting spend, revenue, and capital with agentic finance.**

An open-source, lean AI content generator producing SEO-optimized blog posts via multi-model orchestration. 
Interactive CLI tool with Rich prompts, GSC-driven SEO optimization, and direct publishing capabilities.

## 🛠 Getting Started for Your Brand

To use this engine for your own company, follow these steps to customize the brand identity:

1. **Environment Setup**: 
   Copy `.env.example` to `.env` and fill in your API keys and `GSC_SITE_URL`.
2. **Brand Configuration**: 
   Update the files in the `config/` directory with your own brand details:
   - `author_profiles.json` (Your team and schema markup details)
   - `products.json` (Your products to be contextually injected)
   - `keywords.json` (Your targeted SEO clusters)
   - `seo_optimization.json` (Your specific CTR targets)
   - `brand_voice_config.json` (Your tone of voice instructions)
3. **Global Replace**:
   Search the codebase for `acme.com` and `Acme` and replace them with your actual domain and brand name.
   

**Complete Guide for All Skill Levels**

[![Tests](https://github.com/yourusername/FLYWEEL-AGENTIC-CONTENT-ENGINE/workflows/V2%20Content%20Engine%20Tests/badge.svg)](https://github.com/yourusername/FLYWEEL-AGENTIC-CONTENT-ENGINE/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> A lean, blazing-fast AI content generator that produces SEO-optimized blog posts using multi-model AI orchestration. Refactored for lower complexity and clearer modules while maintaining all quality features.

---

## 📋 Table of Contents

- [Overview](#overview)
- [For Beginners](#for-beginners-start-here)
- [For Developers](#for-developers)
- [For Advanced Users](#for-advanced-users)
- [Architecture Deep Dive](#architecture-deep-dive)
- [API Reference](#api-reference)
- [Performance & Optimization](#performance--optimization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

### What is V2 Content Engine?

V2 is an automated content generation system that creates **high-quality, SEO-optimized blog posts** in **fast, multi-model runs** (speed varies by depth, APIs, and network). It uses multiple specialized AI models working in parallel to:

1. **Research** your topic across the web and community platforms
2. **Generate** comprehensive, well-structured content (about 1500-4500 words, based on depth)
3. **Format** it as production-ready Astro MDX with schema-ready frontmatter and JSON-LD
4. **Optimize** for SEO/AEO with citations, internal links, and FAQs

### Key Features

✅ **Multi-Model AI Orchestration** - Uses the best model for each task
✅ **8 Content Styles** - Standard, Guide, Comparison, Top-Compare, Research, News, Category, Feature
✅ **Parallel Research** - SERP + Reddit + Quora mining (simultaneous)
✅ **Comprehensive Citations** - 20+ citation patterns for research credibility
✅ **SEO + AEO Output** - Schema-ready frontmatter, JSON-LD, PAA/FAQ coverage, internal linking
✅ **Cost-Efficient** - Costs vary by provider, depth, and community limits
✅ **Lightning Fast** - Fast runs; actual time varies by depth and APIs
✅ **Production-Ready** - Valid Astro MDX with frontmatter, JSON-LD, and metadata
✅ **GSC-Aware Strategy** - Optional cannibalization checks and refresh triggers via GSC

### Who Should Use This?

- **Content Marketers** - Generate SEO blog posts at scale
- **Developers** - Integrate AI content generation into applications
- **SEO Specialists** - Create optimized content with schema-ready frontmatter and JSON-LD
- **Researchers** - Produce data-driven research articles with citations
- **Agencies** - Streamline content production workflows

---

## For Beginners (Start Here)

### Step 1: What You'll Need

Before starting, gather these items:

1. **A computer** with Python 3.9 or newer installed (3.12 tested)
2. **API keys** from these services (all have free tiers):
   - [Perplexity AI](https://www.perplexity.ai/api) - For web research
   - [Groq](https://console.groq.com) - For fast extraction and editing
   - [Google AI Studio](https://makersuite.google.com/app/apikey) - For content generation
   - [Nebius](https://studio.nebius.com) (optional) - For content polish

3. **A text editor** (VS Code, Sublime Text, or even Notepad)

### Step 2: Installation

#### On Windows

1. Open Command Prompt (search for "cmd" in Start menu)
2. Navigate to where you want the project:
   ```cmd
   cd C:\Users\YourName\Documents
   ```
3. Clone the repository:
   ```cmd
   git clone https://github.com/yourusername/FLYWEEL-AGENTIC-CONTENT-ENGINE.git
   cd FLYWEEL-AGENTIC-CONTENT-ENGINE
   ```
4. Install Python dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

#### On Mac/Linux

1. Open Terminal
2. Navigate to your preferred directory:
   ```bash
   cd ~/Documents
   ```
3. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/FLYWEEL-AGENTIC-CONTENT-ENGINE.git
   cd FLYWEEL-AGENTIC-CONTENT-ENGINE
   ```
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Step 3: Configure API Keys

1. In the project folder, create a file named `.env` (note the dot at the beginning)
2. Open it in your text editor
3. Add your API keys like this:

```env
PERPLEXITY_API_KEY=pplx-your-key-here
GROQ_API_KEY=gsk_your-key-here
GOOGLE_API_KEY=your-google-key-here
NEBIUS_API_KEY=your-nebius-key-here
```

**Important**: Replace `your-key-here` with your actual API keys!
**Optional**: Add `GOOGLE_SERVICE_ACCOUNT_PATH` and `GSC_SITE_URL` if you want GSC checks, and `AUTHOR_EMAIL` for frontmatter.

### Step 4: Generate Your First Article

Run this command:

```bash
python generate.py -k "lead generation strategies"
```

Wait a bit (time varies by depth and APIs), and you'll see:

```
✅ GENERATION COMPLETE
━━━━━━━━━━━━━━━━━━━━
📝 Title: Complete Guide to Lead Generation Strategies in 2025
📁 Output Folder: output/generations/2025-01-19_lead-generation-strategies
📄 Final: output/generations/2025-01-19_lead-generation-strategies/final.mdx
📄 Raw: output/generations/2025-01-19_lead-generation-strategies/raw.mdx
✨ Polish Model: Qwen3 235B
🎭 Mode: Standard Mode (Brand Integrated)
📏 Words: 2,347
⏱️  Time: 92.4s
```

**That's it!** You've created your first AI-generated blog post!

### Step 5: Find Your Generated Content

Your article is saved in:
```
output/generations/YYYY-MM-DD_your-keyword-slug/final.mdx
```

Open it in any text editor to see the complete article with:
- SEO-optimized frontmatter
- Well-structured sections
- Internal links and citations
- FAQ section
- Schema-ready frontmatter with JSON-LD and FAQ data
- Optional research metadata if you used `--save-research`

---

## For Developers

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Generate content
python generate.py -k "your keyword" --style standard

# Run tests
pytest tests/ -v
```

### Command-Line Interface

#### Basic Usage

```bash
python generate.py -k "KEYWORD" [OPTIONS]
```

**Note**: Interactive mode is the default. Use `--no-int` for classic CLI.

#### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--keyword` | `-k` | **Required**. Keyword/topic to generate content for | None |
| `--style` | | Content style (see below) | `standard` |
| `--no-int` | | Disable interactive mode (classic CLI) | False |
| `--output` | | Output directory | `output` |
| `--save-research` | | Save research data as JSON | False |
| `--augment-serp` | | Use SERP and GSC data | True |
| `--nr` / `--no-reddit` | | Skip Reddit and Quora entirely | False |
| `--nrl` / `--no-reddit-limited` | | Limited: 3 Reddit + 1 Quora | False |
| `--use-llama-polish` | | Use Kimi K2 (Nebius) for polish instead of Qwen3 235B | False |
| `--nb` / `--no-brand` | | Remove brand mentions (keep only final CTA) | False |
| `--lb` / `--limited-brand` | | Limit brand mentions (2-3 total) | False |
| `--no-icp` / `--skip-icp` | | Skip ICP context injection | False |
| `--no-gsc-check` | | Disable GSC cannibalization check | False |
| `--no-gsc-keywords` | | Disable GSC keyword logging | False |
| `--solutions` | | Number of solutions for top-compare | 8 |
| `--min-tools` | | Minimum tools for comparison content | 12 |
| `--depth` | | quick / standard / comprehensive | `standard` |
| `--publish` | | Auto-publish in interactive mode | False |
| `--local` | | Save locally only in interactive mode | False |
| `--no-draft` | | Publish without draft status (interactive) | False |
| `--json` | | Output JSON for automation | False |
| `--comp` / `--competitors` | | Comma-separated competitor list | None |
| `--verbose` | `-v` | Show detailed debug logs | False |

#### Content Styles

1. **`standard`** - Comprehensive overview (2000-2500 words)
   ```bash
   python generate.py -k "CRM integration" --style standard
   ```

2. **`guide`** - Step-by-step tutorial (2000-3000 words)
   ```bash
   python generate.py -k "how to set up Facebook lead ads" --style guide
   ```

3. **`comparison`** - Product/solution comparison (2000-3000 words)
   ```bash
   python generate.py -k "HubSpot vs Salesforce" --style comparison
   ```

4. **`research`** - Data-driven analysis (3000-4000 words, deep citations)
   ```bash
   python generate.py -k "marketing attribution models 2025" --style research
   ```

5. **`news`** - Trending topics (2000-3000 words)
   ```bash
   python generate.py -k "Google Ads API changes 2025" --style news
   ```

6. **`category`** - Category overview/listicle (2000-3000 words)
   ```bash
   python generate.py -k "best CRM software" --style category
   ```

7. **`top-compare`** - Top tools with strict compare blocks (2000-3500 words)
   ```bash
   python generate.py -k "best attribution tools" --style top-compare --solutions 10
   ```

8. **`feature`** - Feature or use-case focused content (2000-3000 words)
   ```bash
   python generate.py -k "multi-touch attribution feature" --style feature
   ```

**Note**: Use `--depth quick|standard|comprehensive` to shift the final length.

### Performance Optimization Flags

#### Skip Community Research (Fastest)
```bash
python generate.py -k "keyword" --nr
```
- **Time saved**: Varies by APIs and depth
- **Cost saved**: Varies by provider and depth
- **Use when**: Speed > community insights

#### Limited Community Research (Balanced)
```bash
python generate.py -k "keyword" --nrl
```
- **Time saved**: Varies by APIs and depth
- **Cost saved**: Varies by provider and depth
- **Use when**: Need some community insights but faster

#### Custom Output Directory
```bash
python generate.py -k "keyword" --output my_content/
```
Articles saved to `my_content/` instead of default `output/`

### Programmatic Usage

```python
import asyncio
from core.generator import ContentGenerator

async def main():
    generator = ContentGenerator()

    result = await generator.generate(
        keyword="lead attribution software",
        style="standard",
        skip_community=False,
        limit_community=False,
        brand_mode="full"
    )

    if result['success']:
        print(f"Generated: {result['title']}")
        print(f"Words: {result['metrics']['word_count']}")
        print(f"Content: {result['content'][:200]}...")
    else:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests (fast)
pytest tests/test_formatter.py tests/test_ai_router.py -v

# Run integration tests (requires API keys)
pytest tests/test_integration.py -v -m integration

# Run with coverage
pytest tests/ --cov=core --cov-report=html

# Run specific test
pytest tests/test_formatter.py::TestAstroFormatter::test_citation_injection -v
```

### Project Structure

```
FLYWEEL-AGENTIC-CONTENT-ENGINE/
├── core/                      # Core modules
│   ├── ai_router.py          # Multi-model AI orchestration
│   ├── research.py           # Web & community research
│   ├── generator.py          # Main generation logic
│   ├── formatter.py          # Astro MDX formatting
│   ├── site_extractor.py     # Live site context extraction
│   ├── repo_extractor.py     # Local repo context extraction
│   ├── context_builder.py    # Pain points + data point extraction
│   ├── cli/                  # Interactive CLI + prompts
│   ├── publisher.py          # Publish to Astro repo
│   ├── gsc_analyzer.py       # GSC analysis + recommendations
│   └── content_monitor.py    # Refresh triggers
├── config/                    # JSON configuration files
│   ├── brand_voice_config.json
│   ├── icp_config.json
│   ├── customer-language.json
│   ├── products.json
│   ├── competitors.json
│   ├── content-templates.json
│   ├── seo_optimization.json
│   └── blog-content-schema.json
├── tests/                     # Test suite
│   ├── test_ai_router.py
│   ├── test_research.py
│   ├── test_formatter.py
│   └── test_integration.py
├── .github/workflows/         # CI/CD
│   └── tests.yml
├── generate.py                # CLI entry point
├── reddit_scraper.py          # Standalone community mining tool
├── requirements.txt           # Dependencies
├── pytest.ini                 # Test configuration
└── README.md                  # This file
```

---

## For Advanced Users

### Multi-Model AI Architecture

V2 uses **specialized models** for each task in the pipeline:

#### 1. Research Phase (Parallel Execution)

**Perplexity Sonar Models**
- **All non-research styles**: `sonar-reasoning-pro` (timeout varies by provider)
- **Research**: `sonar-deep-research` (timeout varies by provider)
- Purpose: Real-time SERP analysis with intent and PAA context
- Output: SERP landscape, PAA questions, authoritative citations

**Groq Compound (web search for community data)**
- Reddit mining: up to 10 question runs, stops after 2 consecutive failures
- Quora extraction: up to 5 question runs, same stop rule
- Purpose: Community intelligence and real-world pain points
- Output: Insights + citations, filtered via Qwen3 235B (fallback to Llama 3.3 if Nebius missing)

**Topical Insights (Perplexity sonar-reasoning-pro)**
- Enabled for non-research styles to add industry signals
- Purpose: Fill topical gaps and add real-world context
- Output: Filtered insights + sources for prompt injection

**Gemini Grounded Search (compare styles)**
- Competitor discovery for comparison and top-compare
- Purpose: Expand and validate competitor lists
- Output: Candidate solutions for user approval

#### 2. Generation Phase

**Gemini 3 Flash**
- Multi-part generation (3 parts) to avoid truncation
- Fast inference with strong reasoning
- Purpose: Long-form content generation with complete structure
- Output: ~1500-4500 words depending on style and depth

#### 3. Refinement Phase

**Groq OSS 120B (edit and extraction)**
- Segmented editing by H2 sections (batches of 2)
- Targeted fixes (grammar, remove AI phrases, stronger first sentence, bold key concepts)
- Word count preservation (±25% tolerance, retries up to 3x)
- Purpose: Clean up sections while preserving markdown structure
- Output: Edited sections, no code fences, structure preserved

**Nebius Qwen3 235B or Kimi K2 (optional polish)**
- Frontmatter humanization
- Content polish for natural flow
- Brand link injection (unless `--nb` flag)
- Purpose: Final quality enhancement
- Output: Human-like, engaging content

#### 4. Formatting Phase

**Python AstroFormatter**
- Frontmatter generation
- Schema-ready frontmatter, JSON-LD, and FAQ schema data
- Citation injection (20+ patterns)
- Internal linking
- CTA placement
- Purpose: Production-ready MDX
- Output: Complete Astro-compatible file

### Advanced Configuration

#### Environment Variables

```env
# Required
PERPLEXITY_API_KEY=pplx-xxx
GROQ_API_KEY=gsk_xxx
GOOGLE_API_KEY=xxx

# Optional
NEBIUS_API_KEY=xxx          # Skip polish if missing (graceful degradation)
GOOGLE_SERVICE_ACCOUNT_PATH=xxx  # Enable GSC features
GSC_SITE_URL=https://your-site.com  # Or GSC_PROPERTY_URL for exact property match
GROQ_BASE_URL=xxx           # Optional: add support in ai_router.py if you need a custom endpoint
NEBIUS_BASE_URL=xxx         # Optional: add support in ai_router.py if you need a custom endpoint
```

#### Config Files Deep Dive

**`config/content-templates.json`**
```json
{
  "standard": {
    "structure": [
      "Introduction",
      "Core Definition",
      "How It Works",
      "Implementation",
      "Benefits",
      "Common Challenges"
    ],
    "word_count_target": 2000,
    "brand_mentions": 15
  }
}
```

**`config/brand_voice_config.json`**
- Tone, banned words, and readability rules
- Brand mention modes (full/limited/none)
- Sentence length and style constraints

**`config/icp_config.json`**
- Ideal customer profile traits
- Pain points and target segments
- Used to guide research and phrasing

**`config/seo_optimization.json`**
- Title and meta rules
- H2/H3 structure rules
- FAQ count and answer limits
- Content refresh triggers

**`config/products.json`**
- Product names and aliases
- Disambiguation rules
- Used to prevent wrong context

**`config/competitors.json`**
- Seed competitor list
- Used for compare and category styles

**`config/blog-content-schema.json`** (optional)
- Defines schema-ready frontmatter structure
- Used with SchemaGenerator to emit JSON-LD (BlogPosting, FAQPage, ClaimReview, HowTo)
- Customizable per content type

**`config/customer-language.json`**
- Customer phrases and terms
- Preferred wording patterns
- Used to mirror how buyers speak

### Custom Style Creation

Create your own content style:

```python
# In core/generator.py

async def generate(self, keyword: str, style: str = "standard", ...):
    # Add your custom style
    if style == "my_custom_style":
        prompt = self._get_custom_style_prompt(keyword, research_data)
        # ... generation logic

def _get_custom_style_prompt(self, keyword: str, research_data: Dict) -> str:
    """Custom style prompt builder"""
    return f"""
    Write a {keyword} article with:
    - Custom structure here
    - Word count: 2500
    - Tone: Technical but accessible

    {self._format_paa_section(research_data)}
    """
```

### Performance Benchmarks

| Mode | Time | Cost | Quality |
|------|------|------|---------|
| Full (Reddit + Quora) | Varies (depth + APIs) | Varies by provider | ⭐⭐⭐⭐⭐ |
| Limited (--nrl) | Varies (depth + APIs) | Varies by provider | ⭐⭐⭐⭐ |
| Skip (--nr) | Varies (depth + APIs) | Varies by provider | ⭐⭐⭐ |

### Parallel Execution Deep Dive

Research phase uses `asyncio.gather()` for simultaneous execution:

```python
# In core/generator.py
research_tasks = [
    web_researcher.analyze_serp(keyword, style=style),
    community_researcher.mine_reddit(keyword, limit=None),
    community_researcher.mine_quora(keyword, limit=None)
]

serp_result, reddit_result, quora_result = await asyncio.gather(*research_tasks)
```

**Speedup**: Parallel research reduces wall time; exact savings vary by APIs and depth.

### Citation System Architecture

**Pattern Categories** (22 total patterns across 6 groups):

1. **Research Terminology** (6 patterns)
   - "Our analysis reveals..."
   - "Data demonstrates..."
   - "Industry data shows..."

2. **Statistical Claims** (5 patterns)
   - "$70.11 per lead"
   - "20–40% reduction"
   - Dollar ranges, percentages

3. **Expert Attribution** (3 patterns)
   - "According to..."
   - "Industry experts argue..."

4. **Study References** (3 patterns)
   - "Studies show..."
   - "Research indicates..."

5. **Claim Validation** (3 patterns)
   - "This demonstrates..."
   - "Evidence confirms..."

6. **Legacy Patterns** (2 patterns)
   - "Users report..."
   - "Many companies..."

**Style-Aware Filtering**:
- **Research style**: All 22 patterns (max citations)
- **Other styles**: Skips two academic-style patterns (keeps 20)

**Citation Sources Used**:
- **Research style**: SERP/Perplexity citations only
- **Other styles**: Reddit + Quora + SERP (citation pool order is Reddit → Quora → SERP)

---

## Architecture Deep Dive

### System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│                  python generate.py -k "keyword"                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESEARCH PHASE (Parallel)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Perplexity   │  │   Reddit     │  │    Quora     │          │
│  │ Sonar API    │  │   Mining     │  │  Extraction  │          │
│  │ (SERP)       │  │  (Groq)      │  │   (Groq)     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └─────────────────┴──────────────────┘                   │
│                           │                                       │
│                   asyncio.gather()                               │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GENERATION PHASE                               │
│                  (Gemini 3 Flash)                                │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Multi-Part Generation (3 parts):                  │         │
│  │  Part 1: Frontmatter + Intro + Sections 1-2        │         │
│  │  Part 2: Sections 3-5 (with Part 1 context)        │         │
│  │  Part 3: Sections 6+ + FAQ (with Parts 1-2)        │         │
│  └─────────────────────────┬──────────────────────────┘         │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FORMAT PHASE                                   │
│                 (Python AstroFormatter)                          │
│  ┌────────────────────────────────────────────────────┐         │
│  │  1. Frontmatter validation                          │         │
│  │  2. Schema-ready frontmatter + JSON-LD + FAQ data   │         │
│  │  3. Citation injection (22 patterns)                │         │
│  │  4. Internal linking                                │         │
│  │  5. CTA placement                                   │         │
│  │  6. MDX structure validation                        │         │
│  └─────────────────────────┬──────────────────────────┘         │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EDIT PHASE                                    │
│                 (Groq OSS 120B)                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Segmented by H2 headings (batches of 2):           │         │
│  │  1. Targeted fixes only (no full rewrites)          │         │
│  │  2. Preserve markdown + word count (±25%)           │         │
│  │  3. Retry up to 3x if drift                         │         │
│  └─────────────────────────┬──────────────────────────┘         │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   POLISH PHASE (Optional)                        │
│                 (Nebius Qwen3 235B or Kimi K2)                    │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Batch processing:                                  │         │
│  │  1. Frontmatter polish                              │         │
│  │  2. Content sections (2 per batch)                  │         │
│  │  3. Natural flow enhancement                        │         │
│  │  4. Brand link injection (unless --nb)             │         │
│  └─────────────────────────┬──────────────────────────┘         │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SEO/AEO OPTIMIZATION                              │
│           (Groq OSS 120B + Gemini 3 Pro)                          │
│  ┌────────────────────────────────────────────────────┐         │
│  │  1. Heading SEO/AEO rewrite (Groq)                  │         │
│  │  2. Title SEO/AEO rewrite (Gemini 3 Pro)            │         │
│  └─────────────────────────┬──────────────────────────┘         │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OUTPUT FILES                                 │
│  output/generations/YYYY-MM-DD_slug/raw.mdx      (raw Gemini)    │
│  output/generations/YYYY-MM-DD_slug/final.mdx    (production-ready) │
│  output/generations/YYYY-MM-DD_slug/metadata.json (optional)    │
│  astro-site/content/blog/slug.mdx                (published)     │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**Research Data Structure**:
```python
{
    'serp': {
        'keyword': str,
        'serp_keyword': str,
        'timestamp': str,
        'paa_questions': List[str],
        'gsc_data': Dict | None,
        'serp_analysis': {
            'analysis': str,
            'citations': List[str]
        } | None,
        'intent_classification': Dict,
        'content_gaps': List[str],
        'recommended_length': int,
        'search_results': List[Dict]  # Placeholder (currently empty)
    },
    'community': {
        'reddit': {
            'insights': List[str],
            'questions': List[str],
            'citations': List[Dict],
            'successful_queries': int,  # If available
            'success': bool             # If available
        },
        'quora': {
            'expert_insights': List[str],
            'questions': List[str],
            'citations': List[Dict],
            'successful_queries': int,  # If available
            'success': bool             # If available
        }
    }
}
```

**Generation Result Structure**:
```python
{
    'success': bool,
    'keyword': str,
    'style': str,
    'title': str,
    'meta_description': str,
    'slug': str,
    'content': str,          # Final polished content
    'raw_content': str,      # Pre-polish draft
    'edited_content': str,   # Post-edit, pre-polish
    'research_data': Dict,   # Full research results
    'metrics': {
        'word_count': int,
        'generation_time': float,
        'paa_questions_answered': int,
        'reddit_insights_used': int,
        'citation_ratio': float,
        'content_gaps_addressed': int,
        'h2_sections': int
    },
    'generated_at': str,
    'error': str  # Only if success=False
}
```

### Error Handling Strategy

1. **Research Failures**: Return empty structures, continue generation
2. **API Timeouts**: Caught with appropriate timeout values per model
3. **Generation Failures**: Fail fast with clear errors (validation + repair first)
4. **Polish Failures**: Skip polish, use raw content (graceful degradation)
5. **Format Failures**: Auto-repair MDX structure, inject minimal frontmatter

### Caching Strategy

- **Site context**: Cached after first load (avoid redundant scraping)
- **Research results**: Can be saved with `--save-research` flag
- **API responses**: No caching (always fresh data)

---

## API Reference

### ContentGenerator

**Main generation interface**

```python
from core.generator import ContentGenerator

generator = ContentGenerator()
```

#### Methods

##### `generate()`

Generate complete blog post content.

```python
async def generate(
    keyword: str,
    style: str = "standard",
    augment_serp: bool = False,
    skip_community: bool = False,
    limit_community: bool = False,
    use_llama_polish: bool = False,
    brand_mode: str = "full",
    skip_icp: bool = False,
    solution_count: int = 8,
    gsc_check: bool = False,
    gsc_keywords: bool = False,
    approved_solutions: Optional[List[str]] = None
) -> Dict[str, Any]
```

**Parameters**:
- `keyword` (str): Topic/keyword to generate content for
- `style` (str): Content style (standard/guide/comparison/top-compare/research/news/category/feature)
- `augment_serp` (bool): Use SERP + GSC analysis (default: False in API; CLI defaults to True)
- `skip_community` (bool): Skip Reddit/Quora entirely (default: False)
- `limit_community` (bool): Limited insights (3 Reddit + 1 Quora) (default: False)
- `use_llama_polish` (bool): Use Kimi K2 instead of Qwen3 235B (default: False)
- `brand_mode` (str): Brand mention mode (full/limited/none)
- `skip_icp` (bool): Skip ICP context injection (default: False)
- `solution_count` (int): Number of solutions for compare styles (default: 8)
- `gsc_check` (bool): Run GSC cannibalization checks (default: False in API; CLI defaults to True)
- `gsc_keywords` (bool): Log GSC keywords (default: False in API; CLI defaults to True)
- `approved_solutions` (list): User-approved competitor list (optional)

**Returns**: Dict with structure shown in [Data Flow](#data-flow)

**Example**:
```python
result = await generator.generate(
    keyword="lead attribution models",
    style="research",
    skip_community=True
)

print(result['title'])
print(result['metrics']['word_count'])
```

---

### SmartAIRouter

**Multi-model AI orchestration**

```python
from core.ai_router import SmartAIRouter

async with SmartAIRouter() as router:
    # Use router methods
```

#### Methods

##### `research()`

Query Perplexity Sonar for web research.

```python
async def research(query: str, model: str = "sonar-reasoning-pro") -> Dict
```

##### `extract()`

Extract structured data using Groq.

```python
async def extract(prompt: str, text: str) -> str
```

##### `generate()`

Generate content using Gemini 3 Flash.

```python
async def generate(prompt: str, context: Dict) -> str
```

##### `edit()`

Edit full content by H2 batches using Groq OSS 120B.

```python
async def edit(
    content: str,
    style_guide: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> str
```

##### `polish_content()`

Polish content using Qwen3 235B or Kimi K2.

```python
async def polish_content(content: str, use_llama: bool = False) -> Dict[str, str]
```

##### `polish_frontmatter()`

Polish frontmatter without breaking the YAML block.

```python
async def polish_frontmatter(content: str, use_llama: bool = False) -> Dict[str, str]
```

##### `_optimize_headings_seo()` and `optimize_title_seo()`

Rewrite headings and title to match SEO rules.

```python
async def _optimize_headings_seo(content: str, keyword: str) -> str
async def optimize_title_seo(content: str, keyword: str, style: str) -> str
```

##### `filter_research_insights()`

Rank and trim insights by relevance.

```python
async def filter_research_insights(insights: List[str], keyword: str, context: str) -> List[str]
```

##### `discover_competitors_intelligent()`

Find competitors with Perplexity + Gemini grounded search.

```python
async def discover_competitors_intelligent(keyword: str, existing: List[str]) -> List[str]
```

##### `research_with_compound()` and `generate_questions()`

Community search and query generation.

```python
async def research_with_compound(questions: List[str], platform: str) -> Dict[str, Any]
async def generate_questions(keyword: str, count: int = 100) -> List[str]
```

---

### WebResearcher

**SERP analysis and web research**

```python
from core.research import WebResearcher

async with WebResearcher() as researcher:
    result = await researcher.analyze_serp("keyword", style="standard")
```

#### Methods

##### `analyze_serp()`

Analyze search engine results.

```python
async def analyze_serp(keyword: str, style: str = "standard") -> Dict
```

**Returns**:
```python
{
    'serp_analysis': Dict,
    'paa_questions': List[str],
    'search_results': List[Dict],
    'gsc_data': Dict
}
```

---

### CommunityResearcher

**Reddit and Quora mining**

```python
from core.research import CommunityResearcher

async with CommunityResearcher() as researcher:
    reddit = await researcher.mine_reddit("keyword")
    quora = await researcher.mine_quora("keyword")
```

#### Methods

##### `mine_reddit()`

Mine Reddit for community insights.

```python
async def mine_reddit(
    keyword: str,
    serp_context: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None
) -> Dict
```

##### `mine_quora()`

Extract Quora expert insights.

```python
async def mine_quora(
    keyword: str,
    serp_context: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None
) -> Dict
```

---

### AstroFormatter

**MDX formatting and citation injection**

```python
from core.formatter import AstroFormatter

formatter = AstroFormatter()
result = formatter.format(
    content=raw_content,
    keyword="keyword",
    style="research",
    research_data=research_data
)
```

#### Methods

##### `format()`

Format content as Astro MDX with citations.

```python
def format(
    content: str,
    keyword: str,
    style: str,
    research_data: Dict
) -> str
```

**Returns**: Complete Astro MDX with frontmatter, citations, and JSON-LD schema data

---

## Performance & Optimization

### Cost Analysis

**Per Article Cost Breakdown**:
*Costs vary by provider, depth, and community limits. Use this as a planning template.*

| Component | Model | Cost |
|-----------|-------|------|
| SERP Analysis (Standard) | Sonar Reasoning Pro | Varies by provider |
| SERP Analysis (Research) | Sonar Deep Research | Varies by provider |
| Reddit Mining (10 queries) | Groq Compound | Varies by provider |
| Quora Extraction (5 queries) | Groq Compound | Varies by provider |
| Content Generation | Gemini 3 Flash | Varies by provider |
| Edit/Format | Groq OSS 120B | Varies by provider |
| Polish | Qwen3 235B or Kimi K2 | Varies by provider |
| **Total (Full)** | | **Varies by provider** |
| **Total (--nr)** | | **Varies by provider** |
| **Total (--nrl)** | | **Varies by provider** |

### Speed Optimization

**Fastest Generation** (time varies by APIs and depth):
```bash
python generate.py -k "keyword" --nr --style standard
```

**Balanced** (time varies by APIs and depth):
```bash
python generate.py -k "keyword" --nrl --style standard
```

**Highest Quality** (time varies by APIs and depth):
```bash
python generate.py -k "keyword" --style research
```

### Batch Processing

Generate multiple articles efficiently:

```python
import asyncio
from core.generator import ContentGenerator

async def batch_generate(keywords: list):
    generator = ContentGenerator()

    # Generate in parallel (be mindful of rate limits)
    tasks = [
        generator.generate(keyword, style="standard", skip_community=True)
        for keyword in keywords
    ]

    results = await asyncio.gather(*tasks)

    for keyword, result in zip(keywords, results):
        if result['success']:
            print(f"✅ {keyword}: {result['metrics']['word_count']} words")
        else:
            print(f"❌ {keyword}: {result['error']}")

keywords = [
    "lead attribution software",
    "CRM integration tools",
    "marketing automation platforms"
]

asyncio.run(batch_generate(keywords))
```

**Warning**: Parallel generation increases API costs. Consider rate limits.

### Memory Optimization

V2 uses async context managers to clean up resources:

```python
# Automatic cleanup
async with SmartAIRouter() as router:
    result = await router.generate(prompt, context)
# Router closed automatically

# Manual cleanup (if needed)
router = SmartAIRouter()
try:
    result = await router.generate(prompt, context)
finally:
    await router.__aexit__(None, None, None)
```

---

## Troubleshooting

### Common Issues

#### 1. "Missing API key" Error

**Problem**:
```
⚠️  Warning: Missing API keys: PERPLEXITY_API_KEY
```

**Solution**:
- Verify `.env` file exists in project root
- Check key names match exactly (case-sensitive)
- Ensure no extra spaces around `=`
- Reload environment: `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('PERPLEXITY_API_KEY'))"`

#### 2. Generation Timeout

**Problem**: Generation takes several minutes or times out

**Solution**:
- Check internet connection
- Use `--nr` flag to skip community research
- Verify API keys are valid and have credits
- For research style, allow a few minutes depending on depth and APIs

#### 3. Import Errors

**Problem**:
```
ModuleNotFoundError: No module named 'google.generativeai'
```

**Solution**:
```bash
pip install -r requirements.txt --upgrade
```

#### 4. Only 1-3 Citations in Research Articles

**Problem**: Research articles have minimal citations despite many sources

**Solution**: This was fixed in recent version (20+ citation patterns added). Update to latest:
```bash
git pull origin main
```

#### 5. Content Too Short

**Problem**: Generated content < 1000 words (or much shorter than expected)

**Causes & Solutions**:
- **Research mode not detected**: Verify style is exactly `research`
- **Custom prompt ignored**: Ensure prompt has detection markers
- **Polish step truncated**: Check Nebius API key and logs

**Debug**:
```bash
python generate.py -k "keyword" --style research --save-research
# Check research JSON for comprehensive data
```

#### 6. Invalid MDX Output

**Problem**: Generated MDX fails to compile in Astro

**Solution**:
- Check for unescaped braces `{` outside code blocks
- Verify frontmatter is valid YAML (check indentation)
- Run validation:
```bash
python -c "from core.formatter import AstroFormatter; f = AstroFormatter(); print('Valid')"
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Then run generation
python generate.py -k "keyword"
```

### API Rate Limits

| Provider | Limit | Solution |
|----------|-------|----------|
| Perplexity | 50 req/min | Add delays: `await asyncio.sleep(1.2)` |
| Groq | 30 req/min | Use `--nr` flag or add delays |
| Gemini | 60 req/min | Unlikely to hit (1 req per generation) |

### Getting Help

1. **Check logs**: Generation shows detailed progress
2. **Run tests**: `pytest tests/ -v` to verify setup
3. **Validate installation**: `python -c "from core.generator import ContentGenerator; print('✓ OK')"`
4. **Create issue**: [GitHub Issues](https://github.com/yourusername/FLYWEEL-AGENTIC-CONTENT-ENGINE/issues)

---

## Contributing

### Development Setup

```bash
# Clone repo
git clone https://github.com/yourusername/FLYWEEL-AGENTIC-CONTENT-ENGINE.git
cd FLYWEEL-AGENTIC-CONTENT-ENGINE

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov black flake8 mypy

# Run tests
pytest tests/ -v
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_formatter.py -v

# With coverage
pytest tests/ --cov=core --cov-report=html

# Integration tests only
pytest tests/ -m integration
```

### Code Quality

```bash
# Format code
black core/ generate.py

# Lint
flake8 core/ --max-line-length=127

# Type check
mypy core/ --ignore-missing-imports
```

### Pull Request Guidelines

1. **Fork** the repository
2. **Create branch**: `git checkout -b feature/your-feature-name`
3. **Write tests** for new features
4. **Run tests**: Ensure all tests pass
5. **Format code**: Run `black` and `flake8`
6. **Commit**: Use clear, descriptive messages
7. **Push**: `git push origin feature/your-feature-name`
8. **Create PR**: Describe changes and link related issues

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Perplexity AI** - Real-time SERP intelligence
- **Groq** - Lightning-fast inference
- **Google AI** - Comprehensive generation with Gemini
- **Nebius** - Natural language polish

---

## Changelog

### Version 2.1.0 (2025-10-02)

**Features**:
- ✨ Expanded citation patterns from 7 to 22 (~3x coverage improvement)
- ✨ Style-aware citation filtering
- ✨ Research-optimized terminology matching

**Fixes**:
- 🐛 Fixed research prompt detection and passthrough
- 🐛 Fixed SERP citation extraction
- 🐛 Fixed community citation filtering for research style

**Performance**:
- ⚡ Reduced generation time by 15% with parallel research

### Version 2.0.0 (2025-09-28)

**Initial Release**:
- 🎉 Complete rewrite from V1 (85% code reduction)
- 🎉 Multi-model AI orchestration
- 🎉 6 content styles
- 🎉 Parallel research execution
- 🎉 Production-ready Astro MDX output

---

**Questions?** Open an [issue](https://github.com/yourusername/FLYWEEL-AGENTIC-CONTENT-ENGINE/issues) or check existing [discussions](https://github.com/yourusername/FLYWEEL-AGENTIC-CONTENT-ENGINE/discussions).

**Happy Content Generating! 🚀**
