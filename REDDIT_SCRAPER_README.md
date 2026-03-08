# Reddit Scraper - Sentiment Analysis Tool

Standalone tool for scraping Reddit for hyper-similar sentiments on a given topic, scoring similarity with AI, filtering by platforms/tools, and outputting structured results with clickable links.

## Features

✅ **AI-Powered Similarity Scoring**: Uses Qwen 235B to score each Reddit post 0-100 for relevance
✅ **Platform Filtering**: Filter posts that discuss specific platforms/tools (e.g., HubSpot, Salesforce)
✅ **Time Filtering**: Search posts from all time, last month, or last week
✅ **Minimum Guarantee**: Ensures at least N outputs by relaxing threshold if needed
✅ **Rich Console Output**: Colored formatting with clickable Reddit links
✅ **File Exports**: Markdown document + JSON data export

## Installation

Requires existing V2 Brand Content Engine environment:

```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Verify API keys are configured in .env
PERPLEXITY_API_KEY=pplx-...
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=...
NEBIUS_API_KEY=...  # Optional but recommended for Qwen 235B scoring
```

## Quick Start

### Basic Usage

```bash
# Analyze Reddit sentiment on a topic
python reddit_scraper.py --t "CRM integration challenges"
```

This will:
1. Mine Reddit for 30 posts about "CRM integration challenges"
2. Score each post 0-100 for similarity using Qwen 235B
3. Filter to posts scoring ≥60 (threshold)
4. Display results in console with clickable links
5. Save markdown + JSON files to `output/reddit_analysis/`

### With Platform Filtering

```bash
# Find posts discussing specific platforms
python reddit_scraper.py --t "marketing automation" --pl "HubSpot,Salesforce,Marketo"
```

Only shows posts that mention HubSpot, Salesforce, or Marketo.

### With Time Filtering

```bash
# Posts from last week only
python reddit_scraper.py --t "lead attribution" -1w

# Posts from last month
python reddit_scraper.py --t "CRM migration" -1mo

# All time (default)
python reddit_scraper.py --t "sales enablement" -alltime
```

### Advanced Usage

```bash
# High threshold + more results
python reddit_scraper.py --t "B2B SaaS pricing" --threshold 80 --limit 50 --min 10

# Multiple filters combined
python reddit_scraper.py --t "marketing attribution" --pl "Google Analytics,Segment" -1mo --threshold 70

# Custom output directory
python reddit_scraper.py --t "lead scoring" --output my_research/reddit/
```

## Command-Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--topic` | `-t` | **REQUIRED**. Topic to analyze | - |
| `--platforms` | `--pl` | Comma-separated platforms/tools to filter by | None |
| `--limit` | | Max insights to retrieve | 30 |
| `--min` | | Minimum outputs to guarantee | 5 |
| `--threshold` | | Similarity threshold (0-100) | 60 |
| `--output` | | Output directory | `output/reddit_analysis/` |
| `-alltime` | | Search all time | ✓ (default) |
| `-1mo` | | Search last 30 days | |
| `-1w` | | Search last 7 days | |

## How It Works

### Phase 1: Reddit Mining (30-45s)
1. Generates 100 natural language questions from your topic using Groq
2. Uses Groq Compound (Llama 3.3 70B + web search) to search Reddit
3. Extracts 30+ Reddit posts with content, URLs, metadata

### Phase 2: Similarity Scoring (10-15s)
1. Sends all posts to Qwen 235B for batch scoring
2. Each post receives:
   - **Score** (0-100): How similar to topic
   - **Reasoning**: Why it received that score
   - **Platform mentions**: Detected platforms/tools
3. Scores based on:
   - Semantic similarity to topic (40 points)
   - Specificity of insights (30 points)
   - Actionability of content (30 points)
   - Platform bonus (+10 if mentions filtered platforms)

### Phase 3: Platform Filtering (if --pl specified)
1. Filters to posts mentioning specified platforms
2. Uses AI-detected platform mentions (from Phase 2)
3. Fallback to keyword search if AI detection missed

### Phase 4: Threshold Application + Minimum Guarantee
1. Filters to posts scoring ≥ threshold
2. If fewer than `--min` posts:
   - Relaxes threshold by 10 points and retries
   - Continues until minimum is reached
   - If threshold reaches 0, takes top N by score

### Phase 5: Output Generation
1. **Console**: Colored output with clickable links, scores, reasoning
2. **Markdown**: Full document with all post details
3. **JSON**: Structured data export for further analysis

## Output Examples

### Console Output

```
═══════════════════════════════════════════════════════════════
🎯 Reddit Sentiment Analysis: "CRM integration challenges"
📊 Found 30 posts | Filtered to 12 high-relevance insights | Min threshold: 60
🔍 Platform filter: HubSpot, Salesforce
═══════════════════════════════════════════════════════════════

[Score: 94] 🔗 https://reddit.com/r/SaaS/comments/xyz123
Title: CRM Integration Nightmare - 3 Months Wasted
Author: u/frustrated_ops | Subreddit: r/SaaS | within 1 week
🔼 247 votes

Excerpt:
We spent 3 months trying to integrate HubSpot with our custom CRM.
The main issue was data mapping conflicts between custom fields...

Platform mentions: HubSpot, Salesforce
Similarity reasoning: Directly discusses CRM integration challenges with specific pain points

─────────────────────────────────────────────────────────────

[Score: 89] 🔗 https://reddit.com/r/marketing/comments/abc456
...
```

### File Outputs

**Markdown** (`output/reddit_analysis/crm-integration-challenges-YYYYMMDD-HHMMSS.md`):
- Full document with all post details
- Structured sections for each post
- Complete content, metadata, scores, reasoning

**JSON** (`output/reddit_analysis/crm-integration-challenges-YYYYMMDD-HHMMSS.json`):
- Machine-readable structured data
- All posts, scores, metadata
- Useful for further programmatic analysis

## Use Cases

### 1. Customer Research
```bash
# Find what customers say about a topic
python reddit_scraper.py --t "lead generation challenges for B2B SaaS" --threshold 70
```

### 2. Competitive Intelligence
```bash
# See what people say about competitors
python reddit_scraper.py --t "Salesforce alternatives" --pl "HubSpot,Pipedrive,Zoho" -1mo
```

### 3. Product Feedback
```bash
# Find recent product feedback
python reddit_scraper.py --t "HubSpot CRM problems" -1w --min 10
```

### 4. Market Research
```bash
# Broad market sentiment
python reddit_scraper.py --t "marketing automation trends 2025" --limit 50
```

### 5. Pain Point Discovery
```bash
# Find specific pain points
python reddit_scraper.py --t "manual data reconciliation" --threshold 80
```

## Performance & Costs

- **Speed**: 60-90 seconds total (depends on limit and API response times)
- **API Costs**: ~$0.10-0.15 per run
  - Groq Compound: ~$0.05 (10 searches)
  - Qwen 235B scoring: ~$0.05 (batch of 30 posts)
  - Question generation: ~$0.02

## Troubleshooting

### "No Reddit posts found"
- Topic might be too specific/niche
- Try broader keywords
- Try `-alltime` instead of time-restricted search

### Low similarity scores
- Topic mismatch - Reddit discussions use different terminology
- Try rewording topic to match natural language
- Lower `--threshold` to see more results

### Platform filter returns no results
- Check platform name spelling
- Platform may not be discussed in context of your topic
- Remove `--pl` to see all results first

### "Qwen 235B unavailable"
- Check NEBIUS_API_KEY in `.env`
- Tool will fallback to Llama 3.3 70B (slightly lower quality)
- Or use basic keyword scoring (lowest quality)

## Advanced Tips

### Finding Niche Insights
```bash
# High threshold + relaxed minimum
python reddit_scraper.py --t "niche topic" --threshold 90 --min 3
```

### Bulk Research
```bash
# Create a script to run multiple topics
for topic in "topic1" "topic2" "topic3"; do
    python reddit_scraper.py --t "$topic" --output "research/$topic/"
done
```

### Custom Analysis
```bash
# Export JSON and analyze programmatically
python reddit_scraper.py --t "your topic" --output data/
# Then: process data/your-topic-*.json with custom scripts
```

## Integration with Main Pipeline

The Reddit Scraper uses the same infrastructure as the main content generator:

- **`SmartAIRouter`**: Multi-model orchestration
- **`CommunityResearcher`**: Reddit mining logic
- **Groq Compound**: Web search for Reddit posts
- **Qwen 235B**: Quality filtering and scoring

This ensures consistency and leverages battle-tested infrastructure.

## Comparison with Main Generator

| Feature | Reddit Scraper | Main Generator (`generate.py`) |
|---------|---------------|-------------------------------|
| **Purpose** | Reddit sentiment analysis | Full blog post generation |
| **Output** | Console + MD + JSON | MDX blog post |
| **AI Scoring** | Qwen 235B similarity scoring | Content quality filtering |
| **Time Filter** | ✅ Yes (alltime/1mo/1w) | ❌ No |
| **Platform Filter** | ✅ Yes (--pl flag) | ❌ No |
| **Min Guarantee** | ✅ Yes (--min flag) | ❌ No |
| **Clickable Links** | ✅ Yes (console output) | ❌ No |
| **Use Case** | Research & discovery | Content creation |

## Future Enhancements

Potential future features:
- [ ] Subreddit filtering (e.g., only r/SaaS, r/marketing)
- [ ] Vote threshold filtering (e.g., only posts with >100 votes)
- [ ] Sentiment analysis (positive/negative/neutral)
- [ ] Topic clustering (group similar insights)
- [ ] Export to CSV/Excel
- [ ] Integration with main generator (auto-research phase)

## Support

For issues, questions, or feature requests, see main project documentation:
- `README.md`: Main project overview
- `CLAUDE.md`: Development guidelines
- `QUICK_START.md`: Setup instructions

---

**Happy Reddit scraping! 🚀**
