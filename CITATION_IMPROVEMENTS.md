# Citation Format Improvements

**Implemented:** October 2, 2025
**Impact:** E-E-A-T signals, SEO, UX, readability

---

## Problem Statement

### Before: Anonymous `[[source](URL)]` Format

```markdown
According to industry data, 60% of marketers struggle with attribution [[source](https://example.com/long-url)].
```

**Issues:**
1. ❌ No descriptive anchor text (just generic "source")
2. ❌ Poor E-E-A-T signals (can't assess authority without clicking)
3. ❌ Bad UX - readers don't know what they're clicking
4. ❌ Weak SEO - no keyword-rich anchor text
5. ❌ Low credibility - looks unprofessional

---

## Solution: Numbered References with Descriptive Titles

### New Format

**Inline Citation** (in text):
```markdown
According to industry data, 60% of marketers struggle with attribution [1].
```

**Reference Section** (at bottom):
```markdown
## Sources and References

> This article cites the following authoritative sources:

[1] [2024 Marketing Attribution Benchmark Report](https://example.com/long-url) - Industry Report
[2] [Amazon PPC Tips For Beginners - r/PPC](https://reddit.com/r/PPC/comments/abc/amazon-ppc-tips/) - Community Discussion
[3] [HubSpot Marketing Resources](https://hubspot.com/guide) - Expert Guide
```

---

## Implementation Details

### 1. New Method: `_extract_source_title()`

**Purpose**: Extract meaningful, descriptive titles from citations

**Priority Order:**
1. Use existing title from research data (Perplexity/SERP)
2. Extract from URL patterns (Reddit, Quora, known domains)
3. Fallback to platform/domain name

**Examples:**

```python
# Reddit URL
Input:  'https://www.reddit.com/r/PPC/comments/abc/amazon_ppc_tips/'
Output: 'Amazon Ppc Tips - r/PPC'

# Research with existing title
Input:  {'title': '2024 Marketing Report', 'url': 'https://hubspot.com/...'}
Output: '2024 Marketing Report'

# Known authority domain
Input:  'https://www.hubspot.com/resources/guide'
Output: 'HubSpot Marketing Resources'

# Unknown domain
Input:  'https://www.example-marketing.com/guide'
Output: 'Example-Marketing Industry Resource'
```

### 2. New Method: `_get_source_type()`

**Purpose**: Categorize sources for E-E-A-T credibility signals

**Source Type Hierarchy:**

#### SERP/Research Sources (Highest Authority)
- `.edu`, `.gov`, `.org` → "Educational/Government Resource"
- URLs with "research", "study", "whitepaper" → "Research Study"
- URLs with "report", "benchmark", "survey" → "Industry Report"
- URLs with "guide", "best-practices" → "Expert Guide"
- Default → "Industry Analysis"

#### Community Sources
- Reddit → "Community Discussion"
- Quora → "Expert Q&A"

#### Fallback
- Unknown → "Industry Resource"

### 3. Updated Citation Injection

**Old Code** (line 1013):
```python
replacement = match.group(1).rstrip('.') + f" [[source]({citation['url']})]."
```

**New Code** (line 1120):
```python
citation_number = citation_index + 1
replacement = match.group(1).rstrip('.') + f" [{citation_number}]."
used_citations.append(citation)  # Track for references section
```

### 4. Rebuilt References Section

**Old Format**:
```markdown
> This article incorporates research from authoritative industry sources:
>
> [Research Source](https://example.com) - Industry research and analysis
> [r/PPC: Topic](https://reddit.com/...) - Reddit discussion
```

**New Format**:
```markdown
> This article cites the following authoritative sources:

[1] [Descriptive Title](https://example.com) - Source Type
[2] [Another Descriptive Title](https://reddit.com/...) - Community Discussion
```

---

## Benefits

### 1. E-E-A-T Signals
✅ **Expertise**: Source types show which are expert vs community
✅ **Authoritativeness**: Descriptive titles reveal authority domains
✅ **Trustworthiness**: Professional formatting builds credibility

### 2. SEO Improvements
✅ Keyword-rich anchor text in references
✅ Semantic HTML with proper link context
✅ Better crawlability - search engines understand source quality

### 3. User Experience
✅ Scan references to assess credibility before reading
✅ Numbers don't break reading flow
✅ Click-worthy titles increase engagement

### 4. Readability
✅ Clean inline citations: `data shows X [1].` vs `data shows X [[source](URL)].`
✅ Organized reference list vs scattered blockquotes
✅ Professional academic-style formatting

---

## Examples

### Research Article (Before & After)

#### Before:
```markdown
Our analysis reveals that 60% of marketers struggle with multi-touch attribution [[source](https://www.gartner.com/report-2024)].

Studies show that proper UTM conventions improve tracking accuracy by 40% [[source](https://www.reddit.com/r/PPC/comments/abc/utm-naming-best-practices/)].

## Sources and Further Reading

> This article incorporates research from authoritative industry sources:
>
> [Research Source](https://www.gartner.com/report-2024) - Industry research
> [r/PPC: Utm Naming Best Practices](https://www.reddit.com/r/PPC/...) - Reddit discussion
```

#### After:
```markdown
Our analysis reveals that 60% of marketers struggle with multi-touch attribution [1].

Studies show that proper UTM conventions improve tracking accuracy by 40% [2].

## Sources and References

> This article cites the following authoritative sources:

[1] [Gartner Research Report](https://www.gartner.com/report-2024) - Industry Report
[2] [UTM Naming Best Practices - r/PPC](https://www.reddit.com/r/PPC/comments/abc/utm-naming-best-practices/) - Community Discussion
```

---

## Code Changes Summary

### Files Modified
- **`core/formatter.py`**:
  - Added: `_extract_source_title()` method (lines 900-971)
  - Added: `_get_source_type()` method (lines 973-1001)
  - Updated: Inline citation format (line 1120)
  - Rebuilt: References section (lines 1126-1144)

### Testing
```bash
# Verify methods load
python3 -c "from core.formatter import AstroFormatter; f = AstroFormatter(); print('✓ Methods loaded')"

# Test citation extraction
python3 -c "
from core.formatter import AstroFormatter
f = AstroFormatter()
citation = {'url': 'https://www.reddit.com/r/PPC/comments/abc/test/', 'type': 'community'}
print(f._extract_source_title(citation))
print(f._get_source_type(citation))
"
```

---

## Migration

### Existing Content
- ✅ Preserved - no changes to existing MDX files
- Old format remains in `output/generations/` folders

### New Content
- ✅ Uses improved format automatically
- Next `python generate.py -k "keyword"` will use new citations

---

## Authority Domain Recognition

The formatter recognizes these authority domains automatically:

| Domain | Label |
|--------|-------|
| hubspot.com | HubSpot Marketing Resources |
| searchengineland.com | Search Engine Land Industry Report |
| moz.com | Moz SEO Best Practices |
| marketingland.com | Marketing Land Industry Analysis |
| adweek.com | Adweek Marketing Insights |
| forbes.com | Forbes Business Analysis |
| entrepreneur.com | Entrepreneur Industry Report |
| inc.com | Inc. Business Insights |
| gartner.com | Gartner Research Report |
| forrester.com | Forrester Industry Study |

*More domains can be added in `_extract_source_title()` method*

---

## Future Enhancements

### Potential Improvements:
1. **Schema Markup**: Add `citation` schema.org markup
2. **Link Preview**: Fetch Open Graph data for richer previews
3. **Authority Scoring**: Weight citations by domain authority
4. **Custom Templates**: Per-style citation formats
5. **Citation Clustering**: Group by topic/theme

---

**Last Updated**: 2025-10-02
**Version**: 1.0
**Status**: ✅ Production Ready
