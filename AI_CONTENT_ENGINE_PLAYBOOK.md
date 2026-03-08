# The Complete Guide to Building Your AI Content Engine
## A Non-Technical Playbook for AEO/SEO Content Automation

**Who This Is For**: Marketing executives, content directors, operations managers, and developers who want to understand how to build AI-powered content systems that actually work.

**What You'll Learn**: How to automate 90% of SEO content production while maintaining quality, authenticity, and brand voice—without needing to be a programmer.

**Reading Time**: 45 minutes for full guide | 15 minutes for executive summary

---

## Table of Contents

### Part 1: Understanding the Opportunity
1. [Executive Summary](#executive-summary)
2. [The Business Case for Content Automation](#the-business-case)
3. [What Makes This Different from "Just Using ChatGPT"](#what-makes-this-different)
4. [Real-World Results You Can Expect](#real-world-results)

### Part 2: How It Works (Non-Technical)
5. [The Four-Phase Content Factory](#the-four-phase-content-factory)
6. [Why Multiple AI Models Beat One](#why-multiple-ai-models)
7. [The Human-in-the-Loop Safety Net](#human-in-the-loop)
8. [Quality Control That Actually Works](#quality-control)

### Part 3: Building Your System
9. [The 8-Week Implementation Plan](#8-week-implementation-plan)
10. [Choosing Your AI Models](#choosing-ai-models)
11. [Cost Structure and Optimization](#cost-structure)
12. [Team Structure and Roles](#team-structure)

### Part 4: Making It Work Long-Term
13. [Deployment Options for Different Team Sizes](#deployment-options)
14. [Common Mistakes and How to Avoid Them](#common-mistakes)
15. [Scaling from 10 to 1000 Articles/Month](#scaling)
16. [Developer's Implementation Guide](#developers-guide) *(Technical Section)*

---

## Executive Summary

**The Problem**: Your content team needs to produce 50-100 SEO-optimized blog posts per month, but:
- Writers cost $150-500 per article
- Freelancers deliver inconsistent quality
- ChatGPT alone produces generic, obviously AI-written content
- SEO tools like Clearscope don't actually write content

**The Solution**: A specialized AI pipeline that:
- Researches topics like a human strategist (15 seconds)
- Writes like your best writer (10 seconds)
- Formats for your CMS automatically (5 seconds)
- Sounds authentic, not robotic (5 seconds)
- Costs $0.05-$0.25 per 2500-word article

**The Catch**: This isn't plug-and-play. You'll need 4-8 weeks to build it, but once running, it:
- Reduces content production costs by 85-95%
- Increases output capacity by 10-20x
- Maintains (or improves) quality vs. human writers
- Frees your team for strategy, not execution

**Who's Doing This**: Tech companies, marketing agencies, publishers, and enterprise content operations teams are building these systems internally rather than relying on generic AI writing tools.

---

## The Business Case

### Why Content Automation Matters Now

**The Search Landscape Has Changed**

In 2024-2025, two major shifts happened:
1. **60% of searches now happen through AI interfaces** (ChatGPT, Perplexity, Google AI Overview)
2. **Traditional SEO still drives 40%** of organic traffic through Google's blue links

This means you need content optimized for **both** traditional search engines (SEO) and AI answer engines (AEO). That's double the content requirements with the same budget.

**The Math That Matters**

Traditional approach:
- 50 articles/month × $250/article = **$12,500/month**
- Plus: editor time, SEO optimization, CMS formatting
- Total: **$15,000-20,000/month**

Automated approach:
- 50 articles/month × $0.10/article = **$5/month** (AI costs)
- Plus: 1 content strategist reviewing/approving = **$8,000/month**
- Total: **$8,000/month** (47% cost reduction)

But more importantly: **Same team can now produce 200-500 articles/month** instead of 50.

### ROI Timeline

**Month 1-2**: Building the system (-$15K in dev time)
**Month 3-4**: Testing and refinement (-$5K)
**Month 5**: Break even
**Month 6+**: 10-20x productivity increase with same team size

**Year 1 Savings**: $80,000-150,000 for a 50-person marketing team

### Why This Beats Generic AI Writing Tools

**Generic AI Tools** (Jasper, Copy.ai, Writer):
- ❌ Generic templates that everyone uses
- ❌ No real research, just reformatting prompts
- ❌ Can't integrate your specific brand context
- ❌ Expensive ($500-2000/month for team plans)
- ❌ Still requires 30-60 minutes of editing per piece

**Custom AI Pipeline**:
- ✅ Researches like your strategist would
- ✅ Integrates your actual brand voice and product knowledge
- ✅ Costs pennies per article (API fees only)
- ✅ Requires 5-10 minutes of review, not rewriting
- ✅ You own and control the system

---

## What Makes This Different

### The Core Insight: Specialization

Think of your current approach like hiring one person to:
1. Research a topic on Google
2. Write a comprehensive article
3. Format it for your blog
4. Proofread and polish it

**That person would be exhausted and the quality would suffer.**

Instead, you'd hire:
- A researcher (fast, web-savvy)
- A writer (creative, comprehensive)
- An editor (detail-oriented, follows style guides)
- A proofreader (makes it sound natural)

**The same applies to AI models.** Different models excel at different tasks:

| Task | Best AI Model Type | Why |
|------|-------------------|-----|
| **Research** | Models with real-time web access | Need current SERP data, Reddit discussions, trending topics |
| **Writing** | Large creative models | Need long-form coherence, natural flow, reasoning |
| **Formatting** | Structured output models | Need precise markdown, schema.org, no hallucinations |
| **Polish** | Natural language specialists | Need to sound human, match brand voice |

**Using GPT-4 for everything is like hiring a CEO to also answer phones and clean the office.** It works, but it's expensive and inefficient.

---

## Architecture Overview

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
│  Keyword + Style + Brand Context + Custom Instructions           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: RESEARCH                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SERP Analysis│  │ Community    │  │ Competitor   │          │
│  │              │  │ Mining       │  │ Analysis     │          │
│  │ Perplexity   │  │ Groq/Llama   │  │ Web Scraper  │          │
│  │ or Exa       │  │ or Exa       │  │ + GPT-4o     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                  │
│                        │                                          │
│                        ▼                                          │
│               Research Context (JSON)                             │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                    [GATE 1: Human approves research]
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 2: GENERATION                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Long-Context Model                                      │   │
│  │  Options: Claude 4.5 Sonnet, GPT-5, Gemini 2.5 Pro      │   │
│  │           or Llama 3.3 70B/Qwen 2.5 72B (open-source)   │   │
│  │                                                          │   │
│  │  - Processes full research context (200K+ tokens)       │   │
│  │  - Generates 2000-4000 word draft                       │   │
│  │  - Multi-part generation to avoid truncation            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                        │                                          │
│                        ▼                                          │
│                  Raw Draft Content                                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                    [GATE 2: Human reviews draft]
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 3: EDITING                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Structured Output Model                                 │   │
│  │  Options: GPT-5, Gemini 2.5 Flash, Claude 4.5 Haiku    │   │
│  │           or Qwen 2.5 72B (open-source)                 │   │
│  │                                                          │   │
│  │  - Formats to publishing platform (MDX/HTML/WordPress)  │   │
│  │  - Adds schema.org markup                               │   │
│  │  - Injects brand links and CTAs                         │   │
│  │  - Validates SEO requirements                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                        │                                          │
│                        ▼                                          │
│              Formatted Draft (Platform-Ready)                     │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                    [GATE 3: Human reviews formatting]
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 4: POLISH                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Natural Language Model                                  │   │
│  │  Options: Claude 4.5 Haiku, GPT-5-mini                  │   │
│  │           or Llama 3.3 70B (open-source)                │   │
│  │                                                          │   │
│  │  - Humanizes AI-generated text                          │   │
│  │  - Applies brand voice guidelines                       │   │
│  │  - Final readability pass                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Python Formatter (Non-AI)                              │   │
│  │  - Validates all structured data                        │   │
│  │  - Auto-repairs common issues                           │   │
│  │  - Generates final file                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                        │                                          │
│                        ▼                                          │
│            Publication-Ready Content File                         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                    [GATE 4: Final approval]
                        │
                        ▼
                ┌───────────────┐
                │   PUBLISH     │
                └───────────────┘
```

### Key Architectural Principles

1. **Parallel Execution**: Research tasks run simultaneously to reduce latency (45s → 15s)
2. **Graceful Degradation**: System works even if optional components fail (e.g., community mining)
3. **Validation at Every Step**: Automatic quality checks prevent cascading errors
4. **Model Agnosticism**: Easy to swap AI providers without rewriting logic
5. **Cost Optimization**: Cheaper models for simple tasks, premium models only when needed

### Model Options by Deployment Strategy (October 2025)

**Cloud API Strategy** (Easiest setup, pay-per-use):
- Research: Perplexity Sonar Pro or Exa Search
- Generation: Claude 4.5 Sonnet or GPT-5
- Editing: GPT-5 or Gemini 2.5 Flash
- Polish: Claude 4.5 Haiku or GPT-5-mini

**Hybrid Strategy** (Best cost/quality balance) - **Recommended for most companies**:
- Research: Groq (Llama 3.3 70B with web search) - $0.59/1M tokens, <500ms latency
- Generation: Claude 4.5 Sonnet or Gemini 2.5 Pro - premium quality, reasonable cost
- Editing: Groq (Qwen 2.5 72B) - $0.20/1M tokens, excellent structured output
- Polish: Groq (Llama 3.3 70B) or Claude 4.5 Haiku - natural language polish

**Self-Hosted Strategy** (Maximum control, upfront GPU costs):
- Research: Exa API (web search) + self-hosted Llama 3.3 70B for analysis
- Generation: Self-hosted Llama 3.1 405B, Qwen 2.5 72B, or upcoming Llama 4 70B
- Editing: Self-hosted Qwen 2.5 72B (excellent structured output, quantized to 4-bit)
- Polish: Self-hosted Llama 3.3 70B (optimized for speed)

**Cost Comparison** (per 1000 articles):
- Cloud API (Premium): $80-250 (using GPT-5/Claude 4.5 for all phases)
- Hybrid (Recommended): $30-80 (Groq for speed, Claude/GPT-5 for quality phases)
- Self-Hosted: $0 API costs, $2000-5000 GPU upfront (ROI after 20-60K articles)

**Note**: Groq's inference platform offers open-source models (Llama, Qwen) at API-level convenience with 200-500ms latency, making it ideal for research/editing phases where speed matters more than absolute quality.

---

## The Four-Phase Content Factory

Think of this like an assembly line, with each station doing one thing extremely well:

### Phase 1: Research Station (10-15 seconds)

**What It Does** (in plain English):
Your system simultaneously:
1. Searches Google for your target keyword
2. Extracts the "People Also Ask" questions
3. Analyzes what the top 10 results are covering
4. Searches Reddit for real user pain points and questions
5. Searches Quora for expert answers and discussions
6. Identifies what competitors are missing (content gaps)

All of this happens **in parallel** (at the same time), so it takes 10-15 seconds instead of 2-3 hours a human researcher would need.

**Why This Matters**:
- AI doesn't make up statistics when it has real data to work from
- You're covering topics your audience actually cares about (based on PAA questions)
- You're including authentic user voices (Reddit/Quora), not just corporate marketing speak
- You find unique angles competitors haven't covered

**Example Output**:
For the keyword "CRM integration best practices":
- Found 23 "People Also Ask" questions
- Discovered users on Reddit complaining about "duplicate contact syncing between Salesforce and Gmail"
- Identified gap: no one covers small business implementation under $1000/month
- Extracted 47 upvoted user insights about common failures

**Cost**: $0.02-$0.04 per keyword

<details>
<summary><strong>🔧 For Developers: Technical Implementation</strong></summary>

Use parallel execution with `asyncio.gather()`:
- **SERP Analysis**: Perplexity API (`sonar-pro` or `sonar-deep-research`) or Exa API for semantic search
- **Community Mining**:
  - **Paid**: Groq Compound (Llama 3.3 70B with web search) for 10 Reddit + 5 Quora queries
  - **Open-source**: Self-hosted Llama 3.3 70B + Exa API for search
- **Competitor Analysis**: Web scraper + GPT-4o-mini or Llama 3.3 70B for semantic analysis

All tasks run simultaneously and combine results into structured JSON for next phase. Use Groq for sub-second latency (200-500ms per query).
</details>

---

### Phase 2: Writing Station (8-12 seconds)

**What It Does**:
Your system takes all that research and generates a complete 2000-4000 word article that:
- Answers the most important questions from research
- Uses real data points and statistics (not made up)
- Follows a logical structure (intro → body sections → FAQ → conclusion)
- Mentions your product/brand naturally (3-5 times, not salesy)
- Includes practical examples and actionable advice

**The Multi-Part Trick**:
Here's the secret: **AI models get lazy after 1000-1500 words.** They start to trail off or just stop.

The solution is like writing a book chapter-by-chapter:
1. **Part 1**: Introduction + first 2 sections (500-600 words)
2. **Part 2**: Middle 3 sections, carrying context from Part 1 (600-700 words)
3. **Part 3**: Final sections + FAQ, with Parts 1+2 as context (500-600 words)

This ensures you get comprehensive 2000+ word articles without the AI giving up halfway through.

**Why This Matters**:
- Longer content (2000+ words) ranks better for competitive keywords
- Multi-part generation prevents the "unfinished article" problem
- AI can maintain consistent tone and flow across all sections
- You're not getting generic filler to hit word count

**Content Style Templates**:

You can configure different templates for different content types:

| Style | Word Count | Use Case | Structure |
|-------|-----------|----------|-----------|
| **Guide** | 2500-3000 | How-to tutorials | Step-by-step instructions with examples |
| **Comparison** | 2000-2500 | Product comparisons | Feature tables, pricing, use cases |
| **Research** | 3500-5000 | Industry reports | Data-heavy, academic tone, trend analysis |
| **News** | 2000-3000 | Trending topics | Timeline, expert quotes, impact analysis |

**Cost**: $0.01-$0.15 per article (depending on model choice)

<details>
<summary><strong>🔧 For Developers: Model Selection (Oct 2025)</strong></summary>

**Paid Models** (October 2025):
- **Quality-first**: Claude 4.5 Sonnet ($0.08/article) - best natural writing, 200K context
- **Balanced**: GPT-5 ($0.10/article) - multimodal, excellent reasoning, 1M context
- **Cost-optimized**: Gemini 2.5 Pro ($0.04/article) - 2M context window, strong performance
- **Speed-optimized**: Groq Llama 3.3 70B ($0.01/article, <2s latency)

**Open-Source Models** (self-hosted or via Groq/Together/Nebius):
- **Flagship**: Llama 3.1 405B - GPT-4-class quality, self-host on 8×H100s or via Nebius API
- **Best cost/quality**: Qwen 2.5 72B - excellent reasoning, often beats GPT-4
- **Fast inference**: Llama 3.3 70B - optimized for speed via Groq (<500ms)
- **Budget**: DeepSeek V3 - $0.01 via API or self-host on 4×A100s (quantized to 4-bit)
- **Upcoming**: Llama 4 70B (Q1 2026) - expected to match Claude 4.5 quality

**Implementation**: Use 3-part generation with context carryover. Each part includes previous content to maintain continuity. For self-hosted models, use vLLM or TGI for 2-5x throughput improvement. Consider Groq's inference platform for API-level ease with open-source economics.
</details>

---

### Phase 3: Formatting Station (3-5 seconds)

**What It Does**:
Your system takes the raw draft and:
- Converts to your publishing format (Markdown, WordPress, Webflow, etc.)
- Adds frontmatter (title, meta description, publish date, author, tags)
- Inserts schema.org markup (helps Google show rich snippets)
- Adds internal links to your existing content
- Inserts image placeholders with SEO-optimized alt text
- Creates a table of contents
- Injects your brand CTAs at strategic points

**The Segmented Approach**:

**The Problem**: When you ask AI to "format this 3000-word article," it often:
- Drops 30-40% of the content (loses entire paragraphs)
- Changes the meaning while fixing grammar
- Gets creative when you just want formatting

**The Solution**: Edit **2 sections at a time** instead of the whole article.

Think of it like painting a house one room at a time instead of trying to paint the entire house in one day. You maintain quality and nothing gets missed.

**Why This Matters**:
- Your content team doesn't waste time manually formatting
- Schema.org markup improves your search appearance (star ratings, FAQs in results)
- Internal linking happens automatically (boosts SEO, keeps visitors on site)
- Content is already in your brand's style guide format

**What Gets Automated**:
- Title optimization (under 60 characters for SEO)
- Meta description (150-155 characters, includes keyword)
- Heading hierarchy (proper H1 > H2 > H3 structure)
- FAQ schema (makes your content appear in Google's "People Also Ask")
- Image alt text (accessibility + SEO)
- Citation formatting

**Cost**: $0.005-$0.03 per article

<details>
<summary><strong>🔧 For Developers: Implementation Pattern (Oct 2025)</strong></summary>

Split content by H2 headings, process in batches of 2 sections. Use models with strong structured output:

**Paid Models** (October 2025):
- **Best precision**: GPT-5 (structured outputs API) - $0.04/article, perfect JSON/schema adherence
- **Fast**: Gemini 2.5 Flash - $0.01/article, excellent structured output
- **Balanced**: GPT-5-mini - $0.008/article, 92% of GPT-5 quality

**Open-Source Models**:
- **Best**: Qwen 2.5 72B via Groq - $0.005/article, excellent at following formatting rules
- **Self-hosted**: Qwen 2.5 72B or Llama 3.3 70B with guided generation (JSON schema enforcement via vLLM/TGI)

**Implementation**: Validate word count after each batch. If drift >8%, retry with stronger preservation prompt. Auto-repair common issues (missing frontmatter, broken links) with Python validators. Use Pydantic models for structured output validation.
</details>

---

### Phase 4: Polish Station (3-5 seconds)

**What It Does**:
This is where you remove the "AI smell" from content. Your system:
- Removes robotic phrases like "In today's digital landscape..."
- Varies sentence length (AI loves 20-25 word sentences, humans use 10-30)
- Adds conversational elements (contractions: "you're" not "you are")
- Replaces jargon with plain language ("use" not "leverage")
- Adds rhetorical questions to engage readers
- Applies your specific brand voice rules

**The De-AI-ification Process**:

Before Polish:
> "In today's fast-paced digital landscape, CRM integration has become increasingly important for organizations seeking to leverage their customer data effectively."

After Polish:
> "Your customer data lives everywhere—email, sales tools, support tickets. CRM integration brings it all together so you're not switching between five tabs to help one customer."

**Why This Matters**:
- Google (and readers) are getting better at detecting AI-written content
- Generic AI writing uses the same phrases everyone else uses
- Your brand voice is what differentiates you from competitors
- Humanized content performs better in engagement metrics (time on page, shares)

**Brand Voice Configuration**:

You define your voice rules once, and the system applies them forever:

**Example Brand Voice Rules**:
- **Tone**: Conversational, helpful, not salesy
- **Banned Words**: "leverage," "synergy," "paradigm shift," "game changer"
- **Good Words**: "simple," "quick," "practical," "real-world"
- **Style Rules**:
  - Use "you" and "your" (second person)
  - Active voice 85% of the time
  - One idea per sentence
  - 2-3 questions per article to engage readers
- **Sentence Length**: Average 18 words (range 8-28)
- **Paragraph Length**: 4-6 sentences max

**Quality Checks**:
- Readability score (Flesch-Kincaid 50-70 = "plain English")
- Sentence variety (not all the same length)
- Transition words between sections
- No banned corporate jargon

**Cost**: $0.005-$0.02 per article

<details>
<summary><strong>🔧 For Developers: Model Selection (Oct 2025)</strong></summary>

**Paid Models** (October 2025):
- **Best humanization**: Claude 4.5 Sonnet ($0.03) - most natural-sounding output, industry-leading
- **Balanced**: GPT-5 ($0.04) - precise brand voice matching, multimodal capabilities
- **Cost-effective**: Claude 4.5 Haiku ($0.006) - 92% of Sonnet quality, 5x cheaper
- **Budget**: GPT-5-mini ($0.004) - excellent for high-volume polish

**Open-Source Models**:
- **Best quality**: Llama 3.3 70B via Groq ($0.005) or Nebius ($0.007) - very natural polish
- **Self-hosted**: Llama 3.3 70B or Qwen 2.5 72B - both excellent at natural language
- **Budget self-hosted**: Llama 3.1 8B (runs on consumer GPUs, surprisingly good for basic polish)
- **Upcoming**: Llama 4 70B (Q1 2026) - expected to rival Claude 4.5 for humanization

**Implementation**: Pass brand voice config as JSON in system prompt. Use temperature=0.7-0.8 for natural variation. Follow with Python validation for:
- Readability scores (textstat library: Flesch-Kincaid 50-70)
- Banned word detection (simple string matching)
- Sentence length distribution (avoid all 20-word sentences)
- Contraction usage (should be 10-20% of personal pronouns)
</details>

---

## Why Multiple AI Models

### The Restaurant Analogy

Imagine you're running a restaurant. You could hire one person who:
- Shops for ingredients
- Cooks all the dishes
- Plates them beautifully
- Serves customers
- Cleans up

**That person would be overwhelmed and nothing would be excellent.**

Instead, you hire:
- A procurement specialist (finds best ingredients at best prices)
- A chef (creative, skilled at cooking)
- A plating expert (makes it look beautiful)
- Servers (friendly, efficient)
- Dishwashers (fast, thorough)

**Your AI pipeline works the same way.** Each model is the "best in class" for its specific task:

### Model Comparison: What You're Actually Choosing

| What You Need | Model Type | Real-World Example | Cost | Why It's Best |
|---------------|------------|-------------------|------|---------------|
| **Fast web research** | Search-enabled AI | Perplexity, Groq Compound | $0.01-0.03 | Has real-time internet access, returns current data |
| **Creative long-form writing** | Large language model | Claude 3.5, GPT-4 | $0.06-0.15 | Best at maintaining coherent narrative across 3000+ words |
| **Structured formatting** | Precision model | GPT-4 Turbo, Gemini Pro | $0.01-0.03 | Follows formatting rules exactly, doesn't hallucinate structure |
| **Natural polish** | Conversation model | Claude Haiku, GPT-3.5 | $0.005-0.02 | Makes text sound human, good at brand voice matching |

### The Cost vs. Quality Tradeoff

You can tune your system based on priorities:

**Premium Quality Mode** ($0.25/article):
- Best research: Perplexity deep search
- Best writing: Claude 3.5 Sonnet
- Best formatting: GPT-4 Turbo
- Best polish: Claude 3.5 Sonnet
- **Use for**: Pillar content, thought leadership, high-traffic pages

**Standard Quality Mode** ($0.08/article):
- Good research: Groq Compound
- Good writing: Gemini 2.0 Pro
- Good formatting: Qwen 2.5 72B
- Good polish: Claude Haiku
- **Use for**: Most blog content, educational articles

**Budget Mode** ($0.03/article):
- Fast research: Groq Compound
- Fast writing: DeepSeek V3
- Fast formatting: Qwen 2.5 72B
- Fast polish: Llama 3.1 70B
- **Use for**: High-volume content, less competitive keywords

**Why This Matters**:
- You're not overpaying for simple tasks
- You can scale to 100+ articles/month for under $10 in AI costs
- Quality is consistent (same models, same results)
- Easy to upgrade specific phases later (swap one model without rebuilding)

---

## Human-in-the-Loop

### Why Automated ≠ Autonomous

**The Wrong Approach**: "Set it and forget it"
- AI generates 100 articles
- Published automatically
- No human review
- **Result**: Generic content, factual errors, off-brand messaging

**The Right Approach**: "Human-in-the-Loop" (HITL)
- AI generates content
- Human approves at 4 key checkpoints
- AI continues only after approval
- **Result**: AI speed + human judgment

### The 4 Approval Gates

Think of these like security checkpoints where a human gives a thumbs up or thumbs down:

**Gate 1: Research Approval** (after Phase 1)
- **What you review**: List of questions, topics, data sources, user insights
- **What you're checking**: "Are these the right questions?" "Do we have unique angles?"
- **Time required**: 2-3 minutes
- **Why it matters**: Everything downstream depends on good research

**Gate 2: Draft Approval** (after Phase 2)
- **What you review**: Full 2500-word draft
- **What you're checking**: "Is this accurate?" "Does it sound like us?" "Any major gaps?"
- **Time required**: 5-7 minutes (skim reading, not deep editing)
- **Why it matters**: Easier to fix issues now than after formatting

**Gate 3: Formatting Approval** (after Phase 3)
- **What you review**: Formatted article with headings, links, CTAs
- **What you're checking**: "Are links correct?" "Is schema.org working?" "Any broken formatting?"
- **Time required**: 3-4 minutes
- **Why it matters**: Technical issues break user experience and SEO

**Gate 4: Final Approval** (after Phase 4)
- **What you review**: Polished, publication-ready article
- **What you're checking**: "Ready to publish?" "Brand voice correct?" "Final quality check"
- **Time required**: 2-3 minutes
- **Why it matters**: Last chance to catch anything before it's live

**Total Time Per Article**: 12-17 minutes (vs. 4-6 hours to write from scratch)

### The Approval Interface

You need a simple web interface where:
- Content appears at each gate
- Big "Approve" and "Reject" buttons
- Reject sends it back with your feedback
- Progress bar shows which phase you're in
- Multiple team members can review simultaneously

**Example Workflow**:
1. Content strategist enters keyword: "best CRM for small business"
2. Clicks "Generate"
3. 15 seconds later: Research gate opens
4. Strategist reviews questions, clicks "Approve"
5. 12 seconds later: Draft gate opens
6. Editor reviews content, requests one change, clicks "Approve with edits"
7. 8 seconds later: Formatting gate opens
8. Editor checks links, clicks "Approve"
9. 5 seconds later: Final polish gate opens
10. Editor does final check, clicks "Publish"

**Total time: Under 20 minutes for a 3000-word, publication-ready article.**

---

## Quality Control That Actually Works

### The Problem with AI Content

**Common AI Failures**:
1. **Hallucinated Facts**: "Studies show 87% of users..." (no study exists)
2. **Generic Writing**: "In today's digital world..." (everyone uses this)
3. **Word Count Loss**: Starts with 3000 words, editing drops it to 1800
4. **Formatting Breaks**: Links broken, headings wrong, schema invalid
5. **Too Salesy**: Mentions your product 47 times inappropriately

### The 5-Layer Quality System

**Layer 1: Automated Validation** (happens automatically, no human needed)

After each phase, Python scripts check:
- **Word count**: Must be 1500+ words minimum
- **Heading structure**: Exactly 1 H1, 5-10 H2s, proper hierarchy
- **Keyword placement**: Keyword appears in first 100 words
- **Readability score**: Flesch-Kincaid between 50-70 (plain English)
- **Brand voice**: No banned words detected
- **Link validity**: All internal links exist, no broken URLs
- **Schema.org**: Valid JSON-LD markup

**If any check fails**: Article sent back automatically for fixing (no human time wasted)

**Layer 2: Research Grounding** (prevents hallucinations)

The generation prompt explicitly says:
- "Only use facts from this research data"
- "Cite sources inline as [Source: URL]"
- "If a statistic isn't in research, don't include it"

This grounds the AI in real data instead of letting it make things up.

**Layer 3: Multi-Part Generation** (prevents word count loss)

By generating in 3 parts:
- Each part has a specific word count target
- AI can't get lazy and trail off
- Final article consistently hits 2000-3000 words

**Layer 4: Segmented Editing** (prevents content shrinkage during formatting)

By editing 2 sections at a time:
- Word count validated after each batch
- If sections shrink >8%, system retries automatically
- No more "where did 1200 words go?"

**Layer 5: Brand Voice Rules** (prevents generic AI writing)

Your configuration file lists:
- 25+ banned phrases ("game changer," "paradigm shift," etc.)
- Sentence length targets (variety, not all 22 words)
- Required elements (2-3 questions per article, contractions, active voice)

AI polish step specifically removes AI-isms and applies your voice.

### The Quality Score

Each article gets a 0-100 score based on:
- **Word count**: -20 points if under 1500 words
- **SEO structure**: -10 points per heading issue
- **Readability**: -15 points if too complex or too simple
- **Brand voice**: -5 points per banned word found
- **Research integration**: +10 points if answers 5+ PAA questions

**Publishing Rules**:
- Score 85-100: Auto-publish (after final human approval)
- Score 70-84: Needs minor edits before publish
- Score below 70: Regenerate or heavy editing required

This prevents low-quality content from reaching your audience.

---

## 8-Week Implementation Plan

### Week 1-2: MVP with Single Model

**Goal**: Get something working end-to-end

**What you're building**:
- Simple command-line tool
- Enter a keyword, get an article
- Uses GPT-4 for all tasks (research, write, format, polish)
- Saves article as markdown file

**Who's involved**:
- 1 developer (or technical contractor)
- 1 content strategist (defines what "good" looks like)

**Deliverable**:
You can type:
```
generate-article "CRM integration best practices"
```

And 30 seconds later, you have a 1500+ word draft in a file.

**Success metric**: 1 readable article that's 80% as good as a human writer

**Cost**: $2,000-5,000 in developer time + $50 in API costs for testing

---

### Week 3-4: Multi-Model Optimization

**Goal**: Improve quality and reduce cost

**What you're adding**:
- AI Router that picks the best model for each task
- Perplexity for research (cheaper, better at web search)
- Claude or Gemini for writing (better quality)
- Groq for editing (faster, cheaper)
- Cost tracking (see exactly what each article costs)

**Who's involved**:
- Same developer
- Content strategist testing quality improvements

**Deliverable**:
Same command, but now:
- Quality is better (more natural writing, better research)
- Cost is lower ($0.25 → $0.08 per article)
- Speed is faster (30s → 20s)

**Success metric**: Same or better quality for <$0.10 per article

**Cost**: $3,000-6,000 in developer time

---

### Week 5-6: Human-in-the-Loop Web Interface

**Goal**: Make it usable by non-technical team members

**What you're building**:
- Web interface (like a mini-app you open in a browser)
- Enter keyword, select content style, add custom instructions
- See progress in real-time
- Approval gates at each phase (Approve/Reject buttons)
- Preview content before publishing
- Download final article

**Who's involved**:
- Developer
- UI/UX designer (optional, makes it prettier)
- 2-3 content team members for beta testing

**Deliverable**:
Your content team can:
1. Open the web app
2. Enter a keyword
3. Click through 4 approval gates (15 minutes total)
4. Download publication-ready content

**Success metric**: A non-technical team member can generate an article without developer help

**Cost**: $5,000-10,000 in developer time

---

### Week 7-8: Production Hardening

**Goal**: Make it reliable for daily use

**What you're adding**:
- Error handling (what happens if OpenAI is down?)
- Automatic retries (try 3 times before failing)
- Rate limiting (don't hit API limits)
- Usage dashboard (how many articles this month? what did they cost?)
- Database (store all articles, track versions)
- Quality scoring (automatic 0-100 score per article)
- Email notifications (when articles are ready for review)

**Who's involved**:
- Developer
- Content operations manager (defines processes)

**Deliverable**:
A system that:
- Works 95%+ of the time
- Handles errors gracefully
- Tracks usage and costs
- Can be used by 5-10 team members simultaneously

**Success metric**: 95% success rate over 100 articles, <5 minutes downtime/month

**Cost**: $4,000-8,000 in developer time

---

### Total Investment: Weeks 1-8

**Developer time**: $14,000-29,000 (depends on rates, in-house vs. contractor)
**API costs**: $100-300 (for testing)
**Design** (optional): $2,000-5,000

**Total**: $16,000-34,000

**Payback period**: 1-3 months if replacing $15K/month in content costs

---

## Choosing AI Models

### The Decision Framework for Non-Technical Leaders

You don't need to understand how GPT-4 works. You need to understand **what you're paying for**.

### Research Phase Models

**What you're choosing**: How your system gathers information before writing

| Model/Service | Speed | Data Recency | Cost per Keyword | Best For |
|---------------|-------|--------------|------------------|----------|
| **Perplexity API** | ⚡⚡ Fast | Real-time | $0.03 | Current events, trending topics, SERP analysis |
| **Groq Compound** | ⚡⚡⚡ Very Fast | Real-time | $0.01 | Reddit/Quora mining, bulk research |
| **Exa Search** | ⚡⚡⚡ Very Fast | Real-time | $0.05 | Finding specific discussions, semantic search |
| **Brave Search + GPT-4** | ⚡⚡ Fast | Real-time | $0.02 | Budget alternative to Perplexity |

**Recommendation**:
- **Best quality**: Perplexity ($0.03/keyword)
- **Best value**: Groq Compound ($0.01/keyword)
- **Best for community insights**: Exa + Groq ($0.02/keyword)

**Why it matters**:
Research determines quality. Saving $0.02 here but getting worse research is a false economy.

---

### Writing Phase Models

**What you're choosing**: The "brain" that actually writes your article

| Model | Quality | Speed | Cost/Article | Best For |
|-------|---------|-------|--------------|----------|
| **GPT-4 Turbo** (OpenAI) | ⭐⭐⭐⭐⭐ Excellent | ⚡⚡ Good | $0.15 | Technical accuracy, complex topics, following rules |
| **Claude 3.5 Sonnet** (Anthropic) | ⭐⭐⭐⭐⭐ Excellent | ⚡⚡ Good | $0.06 | Creative writing, natural tone, storytelling |
| **Gemini 2.0 Pro** (Google) | ⭐⭐⭐⭐ Great | ⚡ OK | $0.03 | Research-heavy content, data analysis |
| **Llama 3.3 70B** (Groq) | ⭐⭐⭐ Good | ⚡⚡⚡ Fast | $0.01 | High-volume content, speed critical |
| **DeepSeek V3** | ⭐⭐⭐⭐ Great | ⚡⚡ Good | $0.01 | Best cost/quality ratio, technical content |

**Recommendation**:
- **Best quality**: Claude 3.5 Sonnet ($0.06) — Writes most naturally
- **Best value**: DeepSeek V3 ($0.01) — 80% of Claude's quality at 1/6 the price
- **Best speed**: Llama 3.3 70B ($0.01) — Sub-2-second generation

**Why it matters**:
This is your biggest cost driver. Claude vs. DeepSeek is the difference between $60 and $10 for 1000 articles.

---

### Editing Phase Models

**What you're choosing**: How your raw draft gets formatted for publishing

| Model | Structured Output | Speed | Cost/Article | Best For |
|-------|------------------|-------|--------------|----------|
| **GPT-4 Turbo** | ✅ Excellent | ⚡⚡ Good | $0.03 | Complex formatting, schema.org, JSON output |
| **Qwen 2.5 72B** (Groq) | ⚠️ Good | ⚡⚡⚡ Very Fast | $0.005 | MDX/Markdown, fast iterations |
| **Gemini 1.5 Pro** | ✅ Good | ⚡⚡ Good | $0.01 | Schema.org generation, structured data |

**Recommendation**:
- **Best precision**: GPT-4 Turbo ($0.03)
- **Best value**: Qwen 2.5 72B ($0.005) — 6x cheaper, 90% as good

**Why it matters**:
Formatting is high-volume (every article needs it), so cost adds up. Qwen saves you $250/month on 1000 articles.

---

### Polish Phase Models

**What you're choosing**: How your content sounds human vs. robotic

| Model | Humanization Quality | Cost/Article | Best For |
|-------|---------------------|--------------|----------|
| **Claude 3.5 Sonnet** | ⭐⭐⭐⭐⭐ Best | $0.02 | Premium content, thought leadership |
| **GPT-4 Turbo** | ⭐⭐⭐⭐ Great | $0.03 | Precise brand voice matching |
| **Claude 3 Haiku** | ⭐⭐⭐⭐ Great | $0.005 | High-volume polish, good enough quality |
| **Llama 3.1 70B** | ⭐⭐⭐ Good | $0.005 | Budget option, self-hosted |

**Recommendation**:
- **Best quality**: Claude 3.5 Sonnet ($0.02)
- **Best value**: Claude 3 Haiku ($0.005) — Same quality 80% of the time

**Why it matters**:
Polish is the difference between "obviously AI" and "sounds human." Don't cheap out here unless you're doing high volume.

---

### Recommended Configurations

**For Most Companies** (Standard Quality, $0.08/article):
- Research: Groq Compound ($0.01)
- Writing: Gemini 2.0 Pro or DeepSeek V3 ($0.03)
- Editing: Qwen 2.5 72B ($0.005)
- Polish: Claude 3 Haiku ($0.005)
- **Total**: $0.05-0.08 per 2500-word article

**For Premium Content** ($0.25/article):
- Research: Perplexity deep search ($0.03)
- Writing: Claude 3.5 Sonnet ($0.06)
- Editing: GPT-4 Turbo ($0.03)
- Polish: Claude 3.5 Sonnet ($0.02)
- **Total**: $0.14-0.25 per article

**For High-Volume** ($0.03/article):
- Research: Groq Compound ($0.01)
- Writing: DeepSeek V3 or Llama 3.3 70B ($0.01)
- Editing: Qwen 2.5 72B ($0.005)
- Polish: Llama 3.1 70B ($0.005)
- **Total**: $0.03 per article

---

## Cost Structure

### Understanding the Real Costs

**AI API Costs** (what you pay AI providers):
- $0.03-0.25 per article depending on model choices
- $3-25 per 100 articles
- $30-250 per 1000 articles

**Human Review Time** (what you pay your team):
- 15 minutes per article × $60/hour = $15 per article
- 25 hours per 100 articles
- 250 hours per 1000 articles

**Infrastructure** (what you pay for hosting, if applicable):
- Local/CLI: $0 (runs on your laptop)
- Self-hosted: $60/month (covers unlimited articles)
- Cloud-hosted: $20-300/month depending on scale

### Total Cost Comparison: 100 Articles/Month

**Traditional Approach**:
- Writers: 100 × $250 = $25,000
- Editing: 100 × $50 = $5,000
- **Total**: $30,000/month

**AI-Assisted Approach (using your system)**:
- AI costs: 100 × $0.08 = $8
- Human review: 100 × 15 min × $60/hr = $1,500
- Infrastructure: $60
- **Total**: $1,568/month

**Savings**: $28,432/month (95% reduction)

---

### ROI Calculator

Fill in your numbers:

**Current Monthly Content Costs**:
- Articles per month: _______
- Cost per article (writer + editor): $_______
- Total monthly spend: $_______

**Projected AI System Costs**:
- AI cost per article: $0.08 (standard) or $0.25 (premium)
- Review time: 15 min × your team's hourly rate
- Infrastructure: $60/month
- **Total new monthly spend**: $_______

**Monthly Savings**: $_______
**Annual Savings**: $_______ × 12 = $_______

**System Build Cost**: $20,000-35,000
**Payback Period**: Build cost ÷ Monthly savings = _______ months

**Example**:
- Current: $30,000/month
- New system: $1,600/month
- Savings: $28,400/month
- Build cost: $25,000
- Payback: **0.88 months** (less than 1 month!)

---

## Team Structure

### Who You Need

**During Build Phase** (Weeks 1-8):
- **1 Developer**: Builds the pipeline, integrates APIs, creates web interface
  - In-house: 50% time allocation for 8 weeks
  - Contractor: $100-200/hour, ~100-150 hours total
- **1 Content Strategist**: Defines quality standards, tests output, creates brand voice config
  - In-house: 25% time allocation for 8 weeks
- **1 Operations Manager** (optional): Project management, stakeholder communication
  - In-house: 10% time allocation

**During Operations Phase** (Month 3+):
- **1-2 Content Strategists**: Review and approve articles at gates
  - Can handle 200-400 articles/month per person
- **0.5 Developer**: Maintenance, updates, bug fixes
  - 4-8 hours/month
- **Quality Analyst** (optional): Spot-checks published articles, tracks metrics
  - Part-time or shared role

### Scaling Team for Volume

| Articles/Month | Human Reviewers Needed | Developer Time |
|----------------|------------------------|----------------|
| 50 | 1 part-time (20 hrs) | 4 hrs/month |
| 100 | 1 full-time (40 hrs) | 4 hrs/month |
| 250 | 2 full-time | 8 hrs/month |
| 500 | 3-4 full-time | 12 hrs/month |
| 1000 | 6-8 full-time | 20 hrs/month |

**Key insight**: You can 10x your output with only 2-3x the team size.

---

## Deployment Options

### Option 1: Local CLI (Command-Line Interface)

**What it is**: Program runs on your laptop, type commands to generate articles

**Best for**:
- Individual content creators
- Testing and development
- Small teams (1-3 people)
- When you don't need collaboration

**How it works**:
1. Open terminal
2. Type: `generate-article "your keyword"`
3. Wait 20-30 seconds
4. Article saved to your computer

**Pros**:
- ✅ Zero hosting costs
- ✅ Complete control
- ✅ Fast setup (1-2 weeks)
- ✅ Easy to modify and test

**Cons**:
- ❌ No team collaboration
- ❌ Manual execution
- ❌ Requires basic terminal knowledge

**Cost**: $0/month (just API costs)

---

### Option 2: Self-Hosted Web App

**What it is**: Internal website your team accesses to generate content

**Best for**:
- Small to medium teams (5-20 people)
- When you want full control
- Companies with existing servers
- Security-conscious organizations

**How it works**:
1. Your IT team sets up a server
2. Team members go to internal URL (like `content-generator.yourcompany.com`)
3. Use web interface to generate and review articles
4. All data stays on your servers

**Pros**:
- ✅ Full data ownership
- ✅ Customizable to your needs
- ✅ No usage limits
- ✅ Works with your SSO/authentication

**Cons**:
- ❌ Requires IT/DevOps expertise
- ❌ You handle backups, updates, security
- ❌ Scaling complexity

**Cost**: $60-200/month (server + database)

---

### Option 3: Cloud-Hosted (Managed Service)

**What it is**: Hosted on platforms like AWS, Railway, Render — they handle infrastructure

**Best for**:
- Growing teams (20+ people)
- When you don't have DevOps resources
- Need automatic scaling
- Want minimal maintenance

**How it works**:
1. Deploy to cloud platform (Render, Railway, Vercel)
2. Platform handles servers, backups, scaling
3. You just use the web interface
4. Pay based on usage

**Platform Recommendations**:

| Platform | Setup Difficulty | Cost/Month | Auto-Scaling | Best For |
|----------|-----------------|------------|--------------|----------|
| **Railway** | ⭐ Easy | $20-50 | ✅ Yes | Quick start, small teams |
| **Render** | ⭐⭐ Medium | $25-75 | ✅ Yes | Mid-size teams, good support |
| **Vercel + Supabase** | ⭐⭐ Medium | $0-50 | ✅ Yes | Serverless, generous free tier |
| **AWS (ECS/Fargate)** | ⭐⭐⭐⭐ Complex | $100-300 | ✅ Yes | Enterprise, maximum control |

**Pros**:
- ✅ No DevOps headaches
- ✅ Automatic backups and updates
- ✅ Scales automatically
- ✅ Professional uptime (99.9%+)

**Cons**:
- ❌ Monthly recurring costs
- ❌ Less customization
- ❌ Vendor lock-in

**Cost**: $20-300/month depending on team size

---

## Common Mistakes

### Mistake 1: Using One Model for Everything

**What people do**: "GPT-4 is the best, so I'll use it for all 4 phases"

**Why it fails**:
- GPT-4 costs 10-50x more than specialized models for simple tasks
- Research needs web access (GPT-4 doesn't have real-time search)
- $0.15/article × 1000 articles = $150/month vs. $30 with multi-model

**Fix**: Use the AI Router pattern — right model for right task

**Real example**:
Company started with GPT-4 for everything. Switched to:
- Groq for research and editing: $0.015
- Gemini for writing: $0.03
- Claude Haiku for polish: $0.005
- **Result**: $0.15 → $0.05 per article (70% cost reduction, same quality)

---

### Mistake 2: No Human Review

**What people do**: "AI generates 100 articles overnight, auto-publish them all"

**Why it fails**:
- Hallucinated statistics get published (credibility damage)
- Off-brand content goes live (brand reputation hit)
- Factual errors rank in Google (SEO damage)
- Readers notice AI patterns (engagement drops)

**Fix**: 4 approval gates, 15 minutes of human review per article

**Real example**:
E-commerce company auto-published 200 AI articles. Problems found:
- 23 articles cited studies that don't exist
- 47 articles recommended competitor products
- 12 articles had broken internal links
- **Result**: Pulled all articles, 3 weeks of cleanup work, Google penalty

---

### Mistake 3: Generic Prompts

**What people do**: "Write a blog post about [keyword]" — that's the whole prompt

**Why it fails**:
- AI has no context about your brand, product, audience
- Every output sounds generic
- Mentions competitors randomly
- Ignores your research data

**Fix**: Comprehensive prompts with:
- All research data
- Brand voice guidelines
- Product context
- Specific structure requirements
- Word count targets

**Real example**:
Tech company went from:
- Generic prompt: "Write about CRM integration"
- **Result**: Generic 1200-word article mentioning Salesforce 8 times, their product 0 times

To:
- Detailed prompt with research data, brand voice, product info
- **Result**: 2500-word article answering real user questions, natural product mentions (3x), unique angle

---

### Mistake 4: Ignoring Word Count Loss

**What people do**: Generate 3000-word draft, send whole thing to "edit" prompt

**Why it fails**:
- AI editing often shortens content by 30-40%
- 3000 words → 1800 words after formatting
- SEO suffers (shorter = lower rankings for competitive terms)

**Fix**: Segmented editing (2 sections at a time) with word count validation

**Real example**:
Marketing agency noticed articles kept coming out short:
- Generated: 2800 words
- After editing: 1650 words
- **Problem**: Editing in one pass lost 41% of content

Switched to:
- Edit 2 sections at a time
- Validate word count after each batch
- Retry if shrinkage >8%
- **Result**: 2800 → 2650 words (5% loss, acceptable)

---

### Mistake 5: Skipping Polish Phase

**What people do**: "Formatting looks good, let's publish" — no humanization step

**Why it fails**:
- Content sounds robotic ("In today's digital landscape...")
- All sentences same length (AI loves 22-word sentences)
- No contractions ("you are" instead of "you're")
- Readers immediately recognize AI writing

**Fix**: Dedicated polish phase with de-AI-ification prompts

**Real example**:
Blog post before polish:
> "In the current digital landscape, organizations are increasingly recognizing the importance of customer relationship management integration. It is essential to understand that CRM integration facilitates..."

After polish:
> "Your sales team lives in Salesforce. Your support team lives in Zendesk. Your marketing team lives in HubSpot. CRM integration brings them all together so everyone sees the same customer data."

**Engagement metrics improved 40%** (time on page, scroll depth)

---

### Mistake 6: No Brand Voice Configuration

**What people do**: Trust AI to "sound like us" without specific guidance

**Why it fails**:
- AI defaults to corporate jargon
- Uses phrases from training data (everyone else's content)
- No consistency across articles
- Doesn't match your actual brand

**Fix**: Create brand voice config file with:
- Banned words list (25+ corporate buzzwords)
- Good words (your preferred terminology)
- Tone description
- Sentence structure rules
- Example transformations

**Real example**:
Business's AI kept writing:
- "Leverage our solution to optimize synergies..."
- "Best-in-class platform for enterprise-grade..."

After brand voice config:
- "Use [Product] to connect your tools..."
- "Built for teams who need reliable..."

**Customer feedback**: "Finally sounds like you, not a press release"

---

### Mistake 7: Caching Nothing

**What people do**: Fetch brand context and competitor data fresh for every article

**Why it fails**:
- Scraping your website 100 times/month wastes time and API calls
- Competitor analysis doesn't change daily
- Adds 5-10 seconds to every generation
- Increases costs

**Fix**: Cache expensive operations:
- Brand context: 7 days
- Competitor analysis: 14 days
- SERP data for evergreen topics: 3 days

**Real example**:
Content team generating 200 articles/month:
- Before caching: 200 × $0.03 brand scraping = $6
- After caching: 4 × $0.03 = $0.12 (scrape once/week)
- **Saved**: 50x reduction in scraping costs

---

### Mistake 8: Deploying Too Early

**What people do**: Build MVP in week 2, make it company-wide tool by week 3

**Why it fails**:
- Bugs hit 20 people instead of 2
- No error handling for edge cases
- System goes down, blocks entire content team
- Reputation damage ("the AI tool doesn't work")

**Fix**: Proper rollout:
- Week 1-2: Developer only
- Week 3-4: Developer + 1 content tester
- Week 5-6: Pilot with 3-5 users
- Week 7-8: Hardening based on feedback
- Week 9: Company-wide rollout

**Real example**:
Marketing team rushed rollout:
- Made tool available to 15 people in week 3
- 8 simultaneous users hit API rate limit
- System crashed
- Team lost confidence, stopped using it

Proper rollout:
- Week 3-4: 2 beta testers, found 14 bugs
- Week 5-6: Fixed bugs, added error handling
- Week 7-8: 5 pilot users, smooth experience
- Week 9: Full team rollout, 95% adoption

---

### Mistake 9: No Analytics

**What people do**: Generate articles but never track costs, success rate, or quality scores

**Why it fails**:
- Don't know which models work best
- Can't prove ROI to leadership
- Don't catch quality degradation
- Can't optimize costs

**Fix**: Build dashboard tracking:
- Articles generated this month
- Total API costs
- Cost per article (by model choice)
- Success rate (% that pass all gates)
- Average quality score (0-100)
- Time saved vs. manual writing

**Real example**:
Agency couldn't justify system to CFO:
- "We spent $25K building this, but I can't show the savings"

After adding analytics:
- Dashboard showed: 342 articles, $28 in API costs, $5,130 in review time
- vs. Traditional: 342 × $250 = $85,500
- **Proved ROI**: $80,342 saved in first quarter

---

### Mistake 10: Giving Up After First Failures

**What people do**: First 10 articles are mediocre, conclude "AI can't write good content"

**Why it fails**:
- AI is a tool, not magic
- Quality comes from prompt engineering, not just using GPT-4
- Takes iteration to dial in brand voice
- Need to tune research → generation → editing pipeline

**Fix**: Expect 2-4 weeks of iteration:
- Week 1: 40% quality (first attempts)
- Week 2: 60% quality (better prompts)
- Week 3: 75% quality (brand voice tuning)
- Week 4: 85% quality (ready for production)

**Real example**:
Publisher almost abandoned project after week 1:
- 10 articles generated
- 2 were publishable (20% success rate)
- "This doesn't work"

Stuck with it:
- Analyzed what was wrong (no research grounding, generic prompts)
- Improved prompts with specific research data
- Added brand voice config
- Implemented segmented editing
- Week 4: 80% publishable (8/10 articles)
- Month 2: 90% publishable

---

## Scaling from 10 to 1000 Articles/Month

### The Scaling Challenges

**10 articles/month**: Easy
- 1 person part-time
- Local CLI works fine
- Manual tracking in spreadsheet

**100 articles/month**: Medium complexity
- 1-2 people full-time
- Need web interface
- Basic analytics

**500 articles/month**: High complexity
- 3-4 reviewers full-time
- Queue management
- Load balancing across AI providers

**1000+ articles/month**: Enterprise scale
- 6-8 reviewers
- Multiple approval workflows
- API rate limit management
- Cost optimization critical

### Scaling Infrastructure

**Phase 1: 0-50 articles/month**
- Local CLI or simple web app
- Single AI provider (OpenAI or Anthropic)
- No database needed (save to files)
- Cost: ~$4-5/month AI + $0 infrastructure

**Phase 2: 50-200 articles/month**
- Web interface required
- Multiple AI providers (avoid rate limits)
- Database (track articles, versions, approvals)
- Queue system (process articles in order)
- Cost: ~$16-20/month AI + $60/month infrastructure

**Phase 3: 200-500 articles/month**
- Background job processing
- Concurrent generation (5-10 at once)
- Load balancing across providers
- Caching layer (reduce API calls)
- Cost: ~$40-50/month AI + $100-200/month infrastructure

**Phase 4: 500-1000 articles/month**
- Distributed workers
- Redis queue
- Auto-scaling
- Monitoring and alerting
- Cost: ~$80-100/month AI + $200-400/month infrastructure

### Scaling Team

**The 1:200 Ratio**

One full-time reviewer can handle ~200 articles/month (15 min each × 200 = 50 hours)

| Target Volume | Reviewers Needed | Developer Support |
|---------------|-----------------|-------------------|
| 50/month | 1 part-time (20 hrs) | 4 hrs/month maintenance |
| 200/month | 1 full-time | 8 hrs/month |
| 500/month | 3 full-time | 12 hrs/month + 1 week/quarter for features |
| 1000/month | 6 full-time | 20 hrs/month + ongoing optimization |

### Scaling Costs

**The S-Curve**: Costs grow slowly, then spike, then flatten

| Volume | AI Costs | Infrastructure | Human Review | Total Monthly |
|--------|----------|----------------|--------------|---------------|
| 50 | $4 | $0 | $750 | $754 |
| 100 | $8 | $60 | $1,500 | $1,568 |
| 200 | $16 | $60 | $3,000 | $3,076 |
| 500 | $40 | $150 | $7,500 | $7,690 |
| 1000 | $80 | $300 | $15,000 | $15,380 |

**Key insight**: Human review is 95%+ of your cost. Infrastructure and AI costs are minimal.

### Optimization Strategies at Scale

**At 100+ articles/month**:
- Implement caching (brand context, competitor data)
- Switch to cheaper models for non-critical phases
- Batch process during off-peak hours (lower API costs)

**At 500+ articles/month**:
- Negotiate volume discounts with AI providers
- Self-host open-source models for editing/polish (Llama 3.1 70B)
- Implement smart routing (if OpenAI is slow, use Anthropic)

**At 1000+ articles/month**:
- Fine-tune your own models on approved content (reduce per-article cost to <$0.01)
- Run multiple approval workflows (junior reviewers for simple content, senior for complex)
- A/B test model combinations to find optimal quality/cost ratio

---

## Developers' Implementation Guide

*This section is technical. If you're non-technical, you can skip this and share with your development team.*

### Technical Architecture

**Core Components**:

1. **Research Engine** (`core/research.py`)
   - Parallel execution with `asyncio.gather()`
   - SERP analysis: Perplexity API or Brave Search + summarization
   - Community mining: Groq Compound (Llama 3.3 70B + web search)
   - Output: Structured JSON with PAA questions, entities, insights

2. **AI Router** (`core/ai_router.py`)
   - Model selection based on task type + priority
   - Usage tracking (tokens, cost, latency)
   - Automatic fallbacks if primary model fails
   - Rate limit handling with exponential backoff

3. **Content Generator** (`core/generator.py`)
   - Multi-part generation (3 parts with context carryover)
   - Style-based prompt templates (guide, comparison, research, etc.)
   - Brand context injection
   - Word count validation after each phase

4. **Formatter** (`core/formatter.py`)
   - Segmented editing (2 sections at a time)
   - Frontmatter generation (title, meta, tags)
   - Schema.org JSON-LD injection
   - Internal link insertion
   - Python validators (not AI) for final quality checks

5. **Polish Engine** (`core/polish.py`)
   - Brand voice application
   - De-AI-ification prompts
   - Readability scoring (Flesch-Kincaid)
   - Banned word detection

### Key Implementation Patterns

**Pattern 1: Multi-Part Generation**

Problem: AI models truncate long-form output
Solution: Generate in sequential parts with context

```
Part 1: Intro + Sections 1-2 (500-600 words)
Part 2: Sections 3-5 + Part 1 as context (600-700 words)
Part 3: Sections 6-7 + FAQ + Parts 1-2 as context (500-600 words)

Final output: 1600-1900 words (consistently hits 2000+ after polish)
```

**Pattern 2: Segmented Editing**

Problem: Editing 3000-word articles loses 30-40% of content
Solution: Edit 2 sections at a time, validate word count

```
Split by H2 headings → Batch in groups of 2 → Edit each batch → Validate ±8% word count → Retry if fails
```

**Pattern 3: Parallel Research**

Problem: Sequential research takes 45+ seconds
Solution: Run all research tasks simultaneously

```
asyncio.gather(
    analyze_serp(keyword),
    mine_reddit(keyword),
    mine_quora(keyword),
    analyze_competitors(keyword)
)
Total time: 12-15 seconds (vs. 45s sequential)
```

### Model Selection Logic

**AI Router Example**:

```
task_map = {
    ('research', 'quality'): Perplexity Sonar Pro,
    ('research', 'cost'): Groq Llama 3.3 70B Compound,
    ('generate', 'quality'): Claude 3.5 Sonnet,
    ('generate', 'cost'): Gemini 2.0 Flash or DeepSeek V3,
    ('edit', 'quality'): GPT-4 Turbo,
    ('edit', 'cost'): Groq Qwen 2.5 72B,
    ('polish', 'quality'): Claude 3.5 Sonnet,
    ('polish', 'cost'): Claude 3 Haiku
}

model = router.select(task='generate', priority='cost')
# Returns: Gemini 2.0 Flash
```

### API Integration Examples

**Perplexity (Research)**:
- Endpoint: `https://api.perplexity.ai/chat/completions`
- Model: `sonar-reasoning-pro`
- Parameters: `search_recency_filter="month"`, `return_citations=true`
- Cost: ~$3/1M tokens

**Groq (Fast Inference)**:
- Endpoint: `https://api.groq.com/openai/v1/chat/completions`
- Models: `llama-3.3-70b-versatile` (general), `llama-3.3-70b-specdec` (web search)
- Latency: <2 seconds for 2000 tokens
- Cost: ~$0.59/1M input tokens

**Anthropic (Writing + Polish)**:
- Endpoint: `https://api.anthropic.com/v1/messages`
- Model: `claude-3-5-sonnet-20241022` (latest)
- Context window: 200K tokens
- Cost: $3/1M input, $15/1M output

**Google (Generation)**:
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-pro:generateContent`
- Context window: 2M tokens (experimental)
- Cost: $1.25/1M input

### Database Schema

**Minimal schema for tracking**:

```
articles:
  - id (uuid)
  - keyword (text)
  - style (enum: guide, comparison, research)
  - status (enum: queued, research, draft, editing, polishing, review, published)
  - research_data (json)
  - draft_content (text)
  - formatted_content (text)
  - final_content (text)
  - quality_score (int 0-100)
  - word_count (int)
  - cost_breakdown (json: {research: 0.01, generate: 0.06, edit: 0.005, polish: 0.005})
  - created_at (timestamp)
  - published_at (timestamp)

approvals:
  - id (uuid)
  - article_id (foreign key)
  - phase (enum: research, draft, editing, final)
  - reviewer_id (foreign key to users)
  - approved (boolean)
  - feedback (text)
  - timestamp (timestamp)
```

### Error Handling

**Critical patterns**:

1. **Retry with Exponential Backoff**
```
max_retries = 3
for attempt in range(max_retries):
    try:
        result = await api_call()
        break
    except RateLimitError:
        wait_time = 2 ** attempt  # 1s, 2s, 4s
        await asyncio.sleep(wait_time)
    except Exception as e:
        log_error(e)
        if attempt == max_retries - 1:
            raise
```

2. **Graceful Degradation**
```
try:
    community_insights = await mine_reddit(keyword)
except:
    community_insights = []  # Continue without community data
    log_warning("Community mining failed, proceeding without")
```

3. **Model Fallbacks**
```
try:
    result = await claude_generate(prompt)
except:
    log_warning("Claude failed, falling back to GPT-4")
    result = await gpt4_generate(prompt)
```

### Deployment Recommendations

**For MVP (Weeks 1-4)**:
- Local Python script + OpenAI SDK
- Save to files, no database
- Manual testing

**For Beta (Weeks 5-6)**:
- FastAPI backend + simple React frontend (or Reflex for Python-only)
- SQLite database
- Deploy to Railway or Render

**For Production (Weeks 7-8)**:
- FastAPI + React (or Reflex)
- PostgreSQL database
- Redis for caching and queue
- Deploy to Railway (easiest) or AWS ECS (most control)

### Monitoring and Observability

**Essential metrics**:
- Success rate by phase
- Average generation time
- Cost per article (tracked by model)
- Quality score distribution
- API latency by provider
- Error rate by error type

**Tools**:
- Logging: Python `logging` + file rotation
- Metrics: Prometheus + Grafana (if self-hosted)
- Alerts: Email/Slack when error rate >5%

### Testing Strategy

**Unit tests**:
- Research data extraction
- Prompt building
- Word count validation
- Brand voice compliance

**Integration tests**:
- Full pipeline (keyword → published article)
- Model fallbacks
- Error recovery

**Quality tests**:
- Generate 10 test articles
- Human evaluation (0-100 score)
- Automated validators (SEO structure, readability, brand voice)

---

## Conclusion

### What You've Learned

**The Business Case**:
- 85-95% cost reduction for content production
- 10-20x increase in output capacity
- ROI payback in 1-3 months

**The System**:
- 4-phase pipeline: Research → Generate → Edit → Polish
- Multi-model approach beats single-model by 40-60%
- Human-in-the-loop prevents AI failures
- Quality control at every step

**The Implementation**:
- 8-week build timeline
- $16K-34K total investment
- Works for 10-1000+ articles/month
- Scales linearly with team size

### What to Do Next

**Week 1**: Get buy-in
- Share this playbook with stakeholders
- Calculate your specific ROI
- Identify 1 developer + 1 content strategist

**Week 2-3**: MVP
- Build command-line tool
- Test with 10 articles
- Prove the concept

**Week 4-8**: Production system
- Add web interface
- Implement approval gates
- Harden for daily use

**Month 3+**: Scale
- Ramp from 10 to 100 articles/month
- Optimize costs and quality
- Measure and prove ROI

### Resources

**AI Provider APIs**:
- OpenAI: platform.openai.com
- Anthropic: console.anthropic.com
- Google AI: ai.google.dev
- Groq: console.groq.com
- Perplexity: docs.perplexity.ai

**Web Frameworks**:
- FastAPI: fastapi.tiangolo.com (Python backend)
- Reflex: reflex.dev (Python full-stack)
- React: react.dev (JavaScript frontend)

**Deployment Platforms**:
- Railway: railway.app (easiest)
- Render: render.com (good balance)
- Vercel: vercel.com (serverless)
- AWS: aws.amazon.com (enterprise)

**Community**:
- Discord servers for AI builders
- GitHub repos with open-source examples
- Industry Slack channels

---

## Final Thoughts

**This isn't about replacing writers.** It's about freeing your content team from repetitive execution so they can focus on:
- Strategy and planning
- High-value pillar content
- Creative campaigns
- Thought leadership

**The AI handles**:
- Research and data gathering
- First drafts of standard content
- Formatting and technical SEO
- Scaling to 10x your current output

**Your team handles**:
- Quality approval
- Brand voice stewardship
- Strategic direction
- Final editorial polish

The companies winning with AI content aren't using it to cut headcount. They're using it to 10x output with the same team, capturing market share through sheer content volume while maintaining quality.

**Your competitors are building this right now.** The question isn't whether to automate content, but whether you'll build a custom system that fits your brand or settle for generic tools everyone else uses.

**Start small. Prove the ROI. Scale from there.**

---

*This playbook is a living document. As you build your system, you'll discover optimizations and pitfalls not covered here. Please contribute your learnings back to the community.*

**Questions? Found this helpful?** Share your experience and help others learn from your journey.


---

# Part 5: Technical Implementation Map & Architecture

# Guide: Rebuild the Full AGENTIC CONTENT ENGINE

## Agents at a glance (purpose, outcome, tips)
These agents work as one system. The goal is simple: ship on brand, SEO ready, publishable content with proof and links. The outcome is a draft you can trust and refresh. They aim to cut risk, reduce guesswork, and save time. Tips are short and direct so you can act fast.

- Input agent: Sets the keyword, style, and limits. Aim: clear goals. Outcome: a clean run config. Tip: use one main intent and one audience.
- Brand voice agent: Loads voice and ICP rules. Aim: fit and tone. Outcome: on brand copy. Tip: keep banned words short and visible.
- Context agent: Reads your site repo or sitemap. Aim: true facts. Outcome: accurate links and claims. Tip: keep your content clean and updated.
- SERP agent: Pulls PAA and SERP data. Aim: real demand. Outcome: a search led angle. Tip: keep the core keyword short and stable.
- Community agent: Mines Reddit and Quora. Aim: raw pain. Outcome: real phrasing. Tip: use limited mode to cut cost and noise.
- Insight filter agent: Ranks insights by fit. Aim: cut noise. Outcome: tight proof. Tip: use embeddings when you can.
- Competitor agent: Builds a rival list. Aim: fair compare. Outcome: trusted tables. Tip: allow a manual override and clear exclusions.
- Draft agent: Writes in 3 parts. Aim: full coverage. Outcome: a complete draft. Tip: keep prompts lean and data rich.
- Formatter agent: Builds MDX and frontmatter. Aim: schema ready. Outcome: publishable files. Tip: check title length and slug length.
- Editor agent: Rewrites each H2 section. Aim: fix flow. Outcome: clean sections. Tip: keep H2 count in range.
- Polish agent: Smooths tone and links. Aim: human feel. Outcome: a ready draft. Tip: recheck frontmatter after polish.
- SEO agent: Tunes headings and title. Aim: higher CTR. Outcome: better snippets. Tip: add year and numbers for lists.
- Publish agent: Writes to your repo. Aim: ship fast. Outcome: a file in your blog path. Tip: keep draft true by default.
- Monitor agent: Watches GSC. Aim: refresh timing. Outcome: a queue of updates. Tip: set a clear drop threshold.

## Simple map of the agent and why each step exists
- Input: You give a keyword, style, and limits. This sets the goal.
- Brand guardrails: Load brand voice, ICP, and customer language. This keeps tone and fit.
- Context scan: Read your site or repo. This keeps facts and links true.
- SERP scan: Pull PAA and SERP data. This finds real search demand.
- Community scan: Mine Reddit and Quora. This finds raw pain and phrasing.
- Filter: Rank insights by relevance. This keeps only strong proof.
- GSC check: Flag cannibalization. This avoids self harm.
- Plan: Choose an angle and outline. This keeps the draft focused.
- Draft: Write in 3 parts. This avoids long prompt failures.
- Format: Build MDX with frontmatter and FAQ. This fits the blog schema.
- Edit: Rewrite each H2 section. This fixes flow and gaps.
- Polish: Improve clarity and voice. This makes it read human.
- SEO pass: Tune titles and headings. This lifts rank and CTR.
- Save and publish: Save to output, then push to the site. This ships.

## AEO and output choices (why we do each piece)
Answer engines need short, clear, and structured answers. This guide builds that in on purpose.

- FAQ block: Gives direct Q and A pairs. This feeds answer engines and voice answers.
- Short answers: Each FAQ answer is under 50 words. This fits snippets and chat cards.
- Schema fields: Frontmatter sets `schemaType: Article`. This helps indexing.
- PAA questions: PAA is real search intent. It makes answers match queries.
- H2 rules: 5 to 7 H2s keep the page scannable. This helps answer extraction.
- Comparison tables: Tables are easy to parse. This boosts quick decisions.
- ROI blocks: They show value fast. This helps conversion intent.
- Citations: Sources build trust. This helps EEAT and answer ranking.
- Internal links: They map authority. This helps site level ranking.
- Canonical and slug rules: They stop dupes. This protects AEO signals.
- Nofollow on most external links: This limits link risk while still citing.
- MDX output: It supports components and schema in one file. This makes publish safe.

## Output artifacts and why (everything the repo emits)
- Frontmatter `title`: Clear topic label for search and share.
- Frontmatter `description`: Short summary for snippets and previews.
- `publishDate`: Shows freshness and helps sort.
- `author`: Adds ownership and trust.
- `image`: Tells the site which hero to render.
- `tags` and `category`: Power site filters and related content.
- `categories`: Mirrors category for schema and site rules.
- `featured: false`: Safe default to avoid auto spotlight.
- `draft: true`: Prevents accidental publish before review.
- `canonical`: Stops duplicate URL conflicts.
- `readingTime`: Sets reader expectations and UX.
- `seo.title`: Keeps title limits and SEO rules intact.
- `seo.description`: Keeps meta length and CTA rules intact.
- `seo.focusKeyword`: Pins the main keyword for audits.
- FAQ frontmatter list: Enables FAQ schema and AEO answers.
- MDX imports: Loads the components your MDX uses.
- Compare imports: Enable compare cards and summary blocks.
- FAQ heading format: Sets a clear Q and A section label.
- Comparison table block: Quick scan for buyers and engines.
- H4 review blocks: Force a consistent review format per tool.
- ROI calculator block: Converts vague value into numbers.
- Citations list: Gives proof and reduces claim risk.
- Confidence labels: Mark research vs industry vs community claims.
- Nofollow links: Cite without leaking authority.
- Internal links: Build topic hubs and reduce bounce.
- `raw.mdx`: Keeps the pre edit draft for diff and QA.
- `final.mdx`: The polished publishable output.
- `metadata.json`: Stores research data for audits and reuse.
- Slug rules: Keep URLs short, stable, and clean.
- Hero image path update: Keeps the asset pipeline happy.
- Dated output folder: Makes runs easy to track.

## Why specific outputs beat simpler options
- ROI calculator vs bullets: A calculator gives numbers users can trust and compare. Bullets are fast but less persuasive.
- Comparison table vs prose: Tables help users and engines scan faster. Prose hides key trade offs.
- Citations with confidence labels: Labels show risk level. This keeps claims honest and safe.
- FAQ in frontmatter vs body only: Frontmatter supports schema. Body only does not.
- Canonical per post vs none: Canonical stops split ranking. None can split signals.
- Internal links vs no links: Links grow topical authority and help crawlers.

## Requirements to start
- Python with async support (repo ships a Python 3.12 venv).
- API keys for full flow:
  - `GOOGLE_API_KEY` (Gemini draft and question generation).
  - `GROQ_API_KEY` (section edits, extraction, Groq Compound research).
  - `PERPLEXITY_API_KEY` (SERP, PAA, topical insights).
- Optional keys:
  - `NEBIUS_API_KEY` (Qwen/Kimi polish and embeddings).
  - `GOOGLE_SERVICE_ACCOUNT_PATH` plus `GSC_PROPERTY_URL` or `GSC_SITE_URL` (GSC).
  - `AUTHOR_EMAIL` (frontmatter contact).
- Config JSONs in `config/` (brand voice, ICP, customer language, templates, SEO rules, products, competitors).
- Access to your site content repo or sitemap for context.
- Output path for drafts (default `output/generations/`).
- A clear brand name, product list, and a home page URL for canonicals.
- A simple budget rule for research calls to control spend.

## Claude Skill to use with this guide
Save this as `agentic-content-rebuild/SKILL.md` in your skills folder.

```markdown
---
name: agentic-content-rebuild
description: Rebuild or adapt this repo's agentic content engine for a new company, including research, drafting, SEO formatting, publishing, and model routing. Use when you need a full end to end rebuild plan, model choices, or code scaffolding for the pipeline described in AI_CONTENT_ENGINE_PLAYBOOK.md.
---

# Agentic Content Rebuild

Follow AI_CONTENT_ENGINE_PLAYBOOK.md and mirror the repo pipeline.

## Workflow
1. Ask for the target company, products, ICP, and voice rules.
2. Ask for the site repo path or sitemap and the target MDX schema.
3. Ask for chosen model providers and API keys (names only).
4. Map the pipeline steps to code modules and configs.
5. Generate the rebuild plan, then create or edit files.
6. Verify with a dry run and list missing keys or files.

Keep responses short and use simple words.
```

## Full rebuild guide (plain words, full detail)

### Step 1: Copy the repo shape
- Create `core/` for the pipeline modules.
- Create `config/` for JSON inputs.
- Keep `generate.py` as the main entry point.
- Keep `reddit_scraper.py` as a standalone tool.
- Keep `_template.mdx` at repo root.
- Use `output/` for generated MDX.

### Step 2: Load config and data
- Build these JSON files in `config/`:
  - `brand_voice_config.json` for tone, banned words, and mention rules.
  - `icp_config.json` for audience fit and pain points.
  - `customer-language.json` for phrases to mirror.
  - `products.json` for product names and disambiguation.
  - `competitors.json` for known rivals and comparison rules.
  - `content-templates.json` for style prompts and section shapes.
  - `seo_optimization.json` for title rules, CTA rules, and refresh triggers.
- Keep all copy in plain English. Short lines help readability.

### Step 3: Build the AI router (core/ai_router.py)
- Create one router that owns all model clients and fallbacks.
- Wire clients from env vars: Perplexity, Groq, Gemini, Nebius.
- Current model map in this repo:
  - SERP and PAA: Perplexity `sonar`, `sonar-reasoning-pro`, `sonar-deep-research`.
  - Draft: Gemini `gemini-3-flash-preview` in 3 parts.
  - Grounded competitor search: Gemini `gemini-2.5-flash-preview-05-20`.
  - Edit and extract: Groq `openai/gpt-oss-120b`.
  - Community search: Groq `groq/compound`.
  - Insight filter fallback: Groq `llama-3.3-70b-versatile`.
  - Polish: Nebius `Qwen/Qwen3-235B-A22B-Instruct-2507` or `moonshotai/Kimi-K2-Instruct`.
  - Embeddings: Nebius OpenAI compatible embed endpoint.
- Keep a fallback path when a key is missing.
- Log model names so runs are easy to audit.

### Step 4: Build context extractors
- `core/repo_extractor.py` reads a local site repo for internal links and brand patterns.
  - Set your site repo path (example: `/path/to/your-site/apps/web/src`).
  - Set a cache file (example: `/tmp/your_company_repo_context_cache.json`).
- `core/site_extractor.py` crawls a live site by sitemap and caches to a local file (example: `/tmp/your_company_context_cache.json`).
- `core/context_builder.py` pulls pain phrases and data points into short lists.
- Use the repo extractor in CLI mode and the site extractor as fallback.

### Step 5: Build the research layer
- `core/research.py` does SERP and community research.
- SERP flow:
  - Shorten the keyword with Perplexity `sonar`.
  - Pull PAA with `sonar-reasoning-pro` and fall back if needed.
  - Add deep SERP analysis if `augment_serp` is true.
  - Add GSC data if service account is set.
- Community flow:
  - Extract a short topic with Qwen3.
  - Generate 100 questions with Gemini 3 Flash.
  - Run Groq Compound search for Reddit and Quora.
  - Stop after two failed queries or 10 wins.
  - Use `limit` mode when cost is a concern.

### Step 6: Filter and rank insights
- Use `SmartAIRouter.filter_research_insights` to rank insights by relevance.
- Prefer Nebius Qwen3 when available.
- Fall back to Groq Llama 3.3 if Nebius is missing.
- Use embeddings to drop low match quotes.

### Step 7: Handle competitors and solutions
- Only run this for compare styles.
- Seed from `config/competitors.json`.
- Use `SmartAIRouter.discover_competitors_intelligent`.
- Allow a manual list in CLI if AI discovery fails.
- Pass the approved list as `approved_solutions`.

### Step 8: Draft generation and style control
- `core/generator.py` runs the full flow.
- Styles used by the code:
  - `standard`, `guide`, `comparison`, `top-compare`, `research`, `news`, `category`, `feature`.
- Key flags to keep:
  - `skip_community` and `limit_community`.
  - `brand_mode` set to `full`, `limited`, or `none` (called `brand_mode` in code).
  - `skip_icp` to omit ICP copy.
  - `solution_count` for comparisons.
  - `gsc_check` and `gsc_keywords`.
- If `gsc_check` is on, stop on an abort recommendation.
- If `gsc_keywords` is on, keywords are logged but not yet wired into title.
- Draft is written in 3 parts by Gemini and stitched.
- Inputs to the prompt include config JSON, SERP data, community insights, and site context.

### Step 9: Format into MDX with SEO checks
- `core/formatter.py` builds frontmatter and MDX content.
- It adds:
  - Frontmatter fields (title, description, tags, category, canonical).
  - FAQ items from PAA.
  - Comparison tables and ROI blocks for compare styles.
  - Citations and nofollow on external links.
- Internal links are injected unless `brand_mode` is `none` (called `brand_mode` in code).
- `validate_frontmatter_seo` enforces limits from `config/seo_optimization.json`.

### Step 10: Edit, polish, and SEO
- Split the draft by H2 and edit in small batches.
- Use Groq `openai/gpt-oss-120b` for section edits and heading fixes.
- Use Nebius Qwen3 for final polish, or Kimi K2 if you toggle.
- Keep frontmatter intact during polish.
- Run `optimize_title_seo` after headings. Groq is primary, Gemini is fallback.

### Step 11: Save and publish
- Write outputs to `output/generations/<date>_<slug>/raw.mdx` and `final.mdx`.
- Write `metadata.json` for trace data.
- `core/publisher.py` writes to your site repo blog path.
- Slug is sanitized and image paths are fixed during publish.

### Step 12: Monitor and refresh
- `core/content_monitor.py` uses GSC data to flag drops in rank or CTR.
- Triggers live in `config/seo_optimization.json`.
- Use this to queue refresh runs.

## Hyper detailed rebuild guide (plain words, full detail)
This section is the full build plan. It keeps every detail from the code.

### A. Core folders and entry points
- `generate.py` is the main runner. It wires CLI flags to the pipeline.
- `core/cli/app.py` holds the Click CLI and interactive prompts.
- `core/ai_router.py` owns all model calls and fallbacks.
- `core/generator.py` runs research, draft, format, and polish.
- `core/research.py` handles SERP and community work.
- `core/formatter.py` turns text into valid MDX and frontmatter.
- `core/publisher.py` writes to your site repo.
- `core/content_monitor.py` uses GSC to trigger refresh jobs.
- `_template.mdx` gives the base MDX shape the model should follow.

### B. Brand and ICP rules in detail
- The voice rules live in `config/brand_voice_config.json`.
- The tone is conversational and jargon free.
- Banned words include terms like "leverage" and "optimize".
- Good words include "use", "make", and "simple".
- The target Flesch score is 90 to 95.
- The style rules push 12 to 15 words per line.
- The brand mention modes are `full`, `limited`, and `none`.
- `full` mode allows up to 10 mentions across the article.
- `limited` mode allows 2 to 3 mentions total.
- `none` mode allows zero mentions, with only a soft CTA if needed.
- Sentence rules ban long lines, em dashes, and semicolons.
- Keyword density is capped at 1 to 1.5 percent.
- FAQ heading style can be contextual or standard.

### C. SEO rules you must mirror
- Title length target is 50 to 60 chars.
- Title must include the year and a number for lists.
- Title must avoid banned phrases like "ultimate" or "comprehensive".
- Meta description must be 120 to 160 chars.
- Meta must include the primary keyword in the first 50 chars.
- Meta must include a short CTA like "Learn more".
- H2 count must be 5 to 7 and max 5 words each.
- H4 review blocks are required for comparisons.
- Review blocks must include Key Features, Pros, Cons, Best For, Pricing, Score.
- FAQ count must be 12 to 15 and each answer under 50 words.
- Comparison tables must have Tool, Best For, Price, Rating.
- External links default to `nofollow` except whitelisted domains.
- Content refresh triggers include rank drop below 5 and Jan or Jul checks.

### D. Site or repo context rules
- Repo context is faster and more exact than crawling.
- `RepoContextExtractor` reads MDX in your site repo.
- It skips drafts and files that start with `_`.
- It parses frontmatter to get tags, categories, and author.
- It builds a map of internal links from real content.
- It extracts features and integration lists for product context.
- It stores a cache in a local file (example: `/tmp/your_company_repo_context_cache.json`).
- Site context uses a sitemap crawl as a fallback.
- Site context cache is stored in a local file (example: `/tmp/your_company_context_cache.json`).
- Cache is valid for about 24 hours.
- Use your own repo path and base URL in your fork.

### E. SERP and PAA in depth
- `analyze_serp` runs PAA, GSC, and deep SERP in parallel.
- It first shortens the keyword with Perplexity `sonar`.
- PAA uses `sonar-reasoning-pro` first, then `sonar-pro`.
- PAA prompt injects ICP context for relevance.
- PAA returns a JSON list of 8 to 12 questions.
- Deep SERP is only used when `augment_serp` is true.
- GSC data only runs with a service account key.
- Intent classification guides style and structure.
- Recommended length is computed from SERP results.

### F. Topical insights and deep research
- Topical insights are used for all styles except `research`.
- Topic scope uses the mapping in `seo_optimization.json`.
- The model is `sonar-reasoning-pro`.
- Insight count is capped to keep prompts short.
- Research style uses `sonar-deep-research` for longer proof.
- Research style should be longer than standard blog posts.

### G. Community research in depth
- The community flow runs only if `skip_community` is false.
- A short topic is extracted first. Qwen3 is used when possible.
- Gemini 3 Flash generates 100 query ideas.
- The prompt enforces casual tone and short line length.
- It blocks competitor brand names and irrelevant industry terms.
- Reddit uses shorter keyword phrases for weak search.
- Quora uses longer full questions for better match.
- Each query hits Groq Compound for result clusters.
- The miner stops after 2 fails or 10 wins.
- `limit_community` keeps only a few insights for low cost.
- Insights are stored with citations for later use.

### H. Insight filtering and embeddings
- The filter step removes off topic or weak quotes.
- Nebius Qwen3 is the first choice for filtering.
- Groq Llama 3.3 is used when Nebius is missing.
- Embeddings are used to score relevance to the keyword.
- Low match quotes are dropped before prompt assembly.

### I. Competitor discovery and approval
- This only runs for compare styles.
- Competitor seeds come from `config/competitors.json`.
- Perplexity discovers more names by keyword context.
- Gemini grounded adds more names with proof.
- The list is deduped and cleaned.
- CLI can pass `--comp` with a manual list.
- Interactive mode lets the user approve the final list.
- Approved names are passed as `approved_solutions`.

### J. Draft assembly details
- The generator builds a context bundle for the prompt.
- It loads brand voice, ICP, and customer language.
- It injects product names and disambiguation rules.
- It injects SERP data, PAA, and topical insights.
- It injects community insights and citations.
- It injects the approved competitor list for compare styles.
- It injects internal links and site features.
- It injects `_template.mdx` to enforce structure.
- It sets `brand_mode` to control brand mentions (called `brand_mode` in code).
- It can skip ICP for generic content.

### K. Draft generation details
- The draft is written in 3 parts by Gemini.
- Each part is generated with the same base prompt.
- Parts are stitched in order into one MDX body.
- The draft is checked for frontmatter markers.
- If the draft lacks frontmatter, it is rejected.

### L. Formatter details that often get missed
- Slug is derived from title or keyword and trimmed to 40 chars.
- The slug strips trailing stop words like "the" and "and".
- Canonical is built from the slug and base URL.
- The default author is your team name string.
- `AUTHOR_EMAIL` is used when provided.
- `image` defaults to `/src/assets/blog/<slug>-hero.webp`.
- `readingTime` is computed from word count.
- `schemaType` is set to `Article`.
- FAQ data is placed in frontmatter for schema use.
- Base MDX imports are always added to the top.
- Compare styles add extra MDX imports.
- Internal link injection is skipped when `brand_mode` is `none` (called `brand_mode` in code).

### M. Edit and polish edge cases
- The editor splits on H2 for safe edits.
- Each section is edited with Groq `openai/gpt-oss-120b`.
- Polish first touches frontmatter, then body.
- If the polish output is too short, keep the original.
- If polish breaks the frontmatter, keep the original.
- `use_llama_polish` selects Kimi K2 via Nebius.
- The log may say Llama, but the model is Kimi K2.

### N. Title and heading optimization
- Headings are rewritten after polish for SEO fit.
- Title is the very last step in the pipeline.
- Groq `openai/gpt-oss-120b` is the primary title model.
- Gemini is used if Groq is not available.
- Title rules come from `seo_optimization.json`.

### O. Output and publish details
- `_save_local` creates a dated output folder.
- It writes `final.mdx` and `raw.mdx` when available.
- `--save-research` writes `metadata.json` with research data.
- Publisher writes to your site repo blog folder.
- Set the blog path to your site repo blog folder (example: `/path/to/your-site/apps/web/src/content/blog`).
- Publisher sanitizes slugs and sets `draft` as needed.
- It updates image paths for the static site asset pipeline.
- It does not run git commands. You commit manually.

### P. GSC analyzer details
- GSC needs a service account JSON file path.
- Set the site URL to your base domain (example: `https://www.yourcompany.com`).
- It computes CTR expectations by rank.
- It estimates traffic potential per keyword.
- It can suggest cannibalization or consolidation actions.

### Q. Monitoring and refresh triggers
- Refresh triggers use position drop and CTR underperformance.
- It also flags impression spikes as opportunities.
- It supports annual refresh months in Jan and Jul.
- The default max stale age is 180 days.

### R. CLI flags you should keep
- `--style` sets the content style.
- `--no-int` runs non interactive mode.
- `--nrl` limits community research.
- `--skip-community` skips Reddit and Quora.
- `--nb` sets brand_mode to none.
- `--lb` sets brand_mode to limited.
- `--comp` passes a manual rival list for compare styles.
- `--gsc-check` runs cannibalization checks.
- `--gsc-keywords` logs GSC keyword data.
- `--save-research` writes `metadata.json`.

### S. Example run flows you can copy
- Basic run: `python generate.py -k "your keyword"`.
- Non interactive: `python generate.py --no-int -k "your keyword"`.
- Comparison run: `python generate.py -k "best X" --style comparison --comp "A,B,C"`.
- Low cost run: `python generate.py -k "X" --nrl --lb`.
- Full research run: `python generate.py -k "X" --gsc-check --gsc-keywords --save-research`.

### T. Hand off checklist for a rebuild
- Provide your base domain and canonical rules.
- Provide your brand voice file and banned words.
- Provide your ICP file and top pain points.
- Provide your product list and alias list.
- Provide your competitor list and compare rules.
- Provide your SEO rules file and H2 and FAQ rules.
- Provide your site repo path or sitemap URL.
- Provide your model choices and env var names.
- Provide your publish path and asset path.
- Provide your desired output MDX schema.

## Model options if you swap providers
- Search with citations: Perplexity Sonar models. Swap with any search API that returns cited sources (SerpAPI plus your LLM, or another search LLM).
- Draft writing: Gemini 3 Flash. Swap with Claude 3.5 Sonnet or GPT-4.1 if you adjust prompts and limits.
- Editing and extraction: Groq gpt-oss-120b. Swap with Llama 3.1 70B or Mixtral class models.
- Polish: Qwen3 235B or Kimi K2. Swap with a strong long context model that keeps tone.
- Embeddings: Nebius embed endpoint. Swap with OpenAI text-embedding-3-large or Cohere embed models.
- Provider set ideas: Perplexity, Groq, Google, Nebius, OpenAI, Anthropic, Mistral, Cohere.
- Start with one provider per stage, then swap once quality is stable.

## What to give Claude or Codex for a rebuild
- Your product list and product naming rules.
- Your ICP, brand voice, and banned words list.
- Your sitemap or site repo path and internal link rules.
- Your SEO limits (title, description, and tag rules).
- Your desired output schema and MDX components.
- Your model provider choices and env var names.
- Your content styles and length targets.
- Your publish path and slug rules.
- Your preferred tone examples and two sample posts you like.
- Your legal or compliance rules for claims and citations.
- Your budget cap per run and your target word counts.
