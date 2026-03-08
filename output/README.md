# Output Directory Structure

This directory contains all content generations organized chronologically in date-stamped folders.

## Directory Structure

```
output/
├── generations/
│   ├── 2025-10-02_the-cost-of-leads-report-2025-by-ad/
│   │   ├── final.mdx           # Published-ready polished content
│   │   ├── raw.mdx             # Pre-polish draft
│   │   └── metadata.json       # (optional) Generation params & research data
│   ├── 2025-10-02_buying-leads-from-a-lead-gen-agency-ppl/
│   │   ├── final.mdx
│   │   ├── raw.mdx
│   │   └── metadata.json
│   └── ...
├── archive/
│   ├── pre_reorganization/     # Backup of all files before migration
│   ├── test_files/             # Archived test outputs
│   └── elon_mode/              # Archived experimental outputs
└── README.md                   # This file
```

## Folder Naming Convention

**Format**: `YYYY-MM-DD_slug-from-title/`

**Examples**:
- `2025-10-02_the-cost-of-leads-report-2025-by-ad/`
- `2025-09-21_crm-integration-best-practices/`
- `2025-09-30_how-to-why-naming-conventions-on-ads/`

The date corresponds to when the content was generated (file modification timestamp).

## File Descriptions

### Inside each generation folder:

1. **`final.mdx`** (required)
   - The published-ready, polished content
   - Includes all formatting, frontmatter, citations, CTAs
   - This is the version you publish to your blog

2. **`raw.mdx`** (required for new generations)
   - Pre-polish draft version
   - Generated content before humanization pass
   - Useful for debugging or comparing versions

3. **`metadata.json`** (optional)
   - Generated when using `--save-research` flag
   - Contains:
     - Generation parameters (keyword, style, timestamp)
     - Research data (SERP, Reddit, Quora insights)
     - Title and slug information

## Usage Examples

### Generate new content
```bash
python generate.py -k "your keyword" --style standard
```

Output will be saved to:
```
output/generations/2025-10-02_your-keyword/
├── final.mdx
└── raw.mdx
```

### Generate with research metadata
```bash
python generate.py -k "your keyword" --save-research
```

Output includes metadata:
```
output/generations/2025-10-02_your-keyword/
├── final.mdx
├── raw.mdx
└── metadata.json
```

### Find specific content
```bash
# List all generations chronologically
ls -lt output/generations/

# Find content by keyword
find output/generations -name "*lead-attribution*"

# View latest generation
ls -t output/generations | head -1
```

## Archive Directory

The `archive/` directory contains backups of all previous output structures:

- **`pre_reorganization/`**: All MDX files from before the new folder structure was implemented (Oct 2, 2025)
- **`test_files/`**: Archived test outputs from `test_output/` directory
- **`elon_mode/`**: Experimental outputs from previous version iterations

These are preserved for reference and rollback purposes. They are **not** used in the current workflow.

## Benefits of This Structure

✅ **Chronological Organization**: Easy to see when content was created
✅ **Isolated Generations**: Each piece of content has its own folder with all related files
✅ **Version Comparison**: Compare raw vs final to understand polish improvements
✅ **Scalable**: Handles hundreds of generations without clutter
✅ **Metadata Preservation**: Optional research data for auditing and improvement
✅ **Clean Root**: No sprawling files in output/ root directory

## Migration Notes

This structure was implemented on **October 2, 2025** to replace the previous flat file structure.

All existing content was migrated automatically while preserving:
- Original file modification timestamps
- File content and metadata
- Chronological ordering

Original files are backed up in `archive/pre_reorganization/`.

---

**Last Updated**: 2025-10-02
**Structure Version**: 1.0
