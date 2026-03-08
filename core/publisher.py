"""Astro Publisher - Publish MDX directly to astro-site repo

Writes generated content to the local astro-site repository's
blog content directory for manual git commit by the user.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AstroPublisher:
    """Publish generated MDX content to astro-site repository

    Features:
    - Validates frontmatter against content.config.ts schema
    - Sanitizes slugs for URL/filesystem compatibility
    - Ensures draft status is set correctly
    - Updates image paths for Astro asset pipeline
    - No git operations (user handles manually)
    """

    # Default paths (configurable via environment variables)
    ASTRO_BLOG_PATH = Path(os.getenv("ASTRO_SITE_PATH", "../my-astro-site")) / "src" / "content" / "blog"
    ASTRO_ASSETS_PATH = Path(os.getenv("ASTRO_SITE_PATH", "../my-astro-site")) / "src" / "assets" / "blog"

    # Required frontmatter fields
    REQUIRED_FIELDS = ['title', 'description']

    # Recommended frontmatter fields
    RECOMMENDED_FIELDS = ['publishDate', 'author', 'tags', 'category']

    def __init__(
        self,
        blog_path: Optional[Path] = None,
        assets_path: Optional[Path] = None
    ):
        """Initialize publisher with optional custom paths

        Args:
            blog_path: Path to blog content directory
            assets_path: Path to blog assets directory
        """
        self.blog_path = blog_path or self.ASTRO_BLOG_PATH
        self.assets_path = assets_path or self.ASTRO_ASSETS_PATH

        logger.info(f"📤 AstroPublisher initialized for {self.blog_path}")

    def publish(
        self,
        content: str,
        slug: str,
        draft: bool = False,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """Publish MDX content to astro-site blog directory

        Args:
            content: Complete MDX content with frontmatter
            slug: URL slug for the post (will be sanitized)
            draft: Whether to set draft: true (default: False for production)
            overwrite: Whether to overwrite existing files (default: False)

        Returns:
            Dict with success status, path, validation warnings, etc.
        """
        try:
            # Validate blog path exists
            if not self.blog_path.exists():
                return {
                    'success': False,
                    'error': f"Blog path not found: {self.blog_path}",
                    'hint': "Is the astro-site repo cloned at the expected location?",
                }

            # Sanitize slug
            clean_slug = self._sanitize_slug(slug)
            if clean_slug != slug:
                logger.info(f"📝 Sanitized slug: '{slug}' → '{clean_slug}'")

            # Check for existing file
            target_path = self.blog_path / f"{clean_slug}.mdx"
            if target_path.exists() and not overwrite:
                return {
                    'success': False,
                    'error': f"File already exists: {target_path}",
                    'existing_slug': clean_slug,
                    'hint': "Use overwrite=True to replace, or choose a different slug",
                }

            # Ensure draft status is set correctly
            content = self._ensure_draft_status(content, draft)

            # Validate frontmatter
            validation = self._validate_frontmatter(content)
            if not validation['valid']:
                logger.warning(f"⚠️  Validation issues: {validation['errors']}")

            # Update image paths for Astro asset pipeline
            content = self._update_image_paths(content, clean_slug)

            # Validate and repair import syntax before publishing (final safety check)
            import_section = content.split('---')[2] if content.count('---') >= 2 else ''
            first_100_lines = '\n'.join(import_section.split('\n')[:100])

            # Check for malformed imports (periods instead of semicolons)
            if '. import ' in first_100_lines:
                logger.warning("⚠️  Detected malformed imports, attempting repair...")
                # Split concatenated imports
                content = content.replace('. import ', ';\nimport ')

            # Check for imports without semicolons
            import_lines = [line for line in first_100_lines.split('\n') if line.strip().startswith('import ')]
            for line in import_lines:
                if line.strip() and not line.strip().endswith(';'):
                    logger.warning(f"⚠️  Import missing semicolon: {line[:50]}")
                    content = content.replace(line, line.rstrip() + ';')

            # Write MDX file
            target_path.write_text(content, encoding='utf-8')

            logger.info(f"✅ Published to: {target_path}")

            return {
                'success': True,
                'path': str(target_path),
                'slug': clean_slug,
                'draft': draft,
                'validation': validation,
                'hero_image_path': str(self.assets_path / f"{clean_slug}-hero.webp"),
                'hero_image_needed': not self._check_hero_image_exists(clean_slug),
            }

        except PermissionError as e:
            logger.error(f"❌ Permission denied: {e}")
            return {
                'success': False,
                'error': f"Permission denied writing to {self.blog_path}",
            }
        except Exception as e:
            logger.error(f"❌ Publish failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }

    def preview(self, content: str, slug: str) -> Dict[str, Any]:
        """Preview what would be published without writing

        Args:
            content: MDX content
            slug: Proposed slug

        Returns:
            Dict with preview information
        """
        clean_slug = self._sanitize_slug(slug)
        target_path = self.blog_path / f"{clean_slug}.mdx"
        validation = self._validate_frontmatter(content)

        # Extract frontmatter for preview
        frontmatter = self._extract_frontmatter(content)

        return {
            'slug': clean_slug,
            'target_path': str(target_path),
            'would_overwrite': target_path.exists(),
            'validation': validation,
            'frontmatter': frontmatter,
            'word_count': len(content.split()),
            'hero_image_exists': self._check_hero_image_exists(clean_slug),
        }

    def get_existing_slugs(self) -> List[str]:
        """Get list of existing blog post slugs

        Returns:
            List of slug strings
        """
        if not self.blog_path.exists():
            return []

        return [
            f.stem for f in self.blog_path.glob("*.mdx")
            if not f.name.startswith("_")
        ]

    def _sanitize_slug(self, slug: str) -> str:
        """Sanitize slug for filesystem and URL compatibility

        - Lowercase
        - Replace spaces and special chars with hyphens
        - Remove consecutive hyphens
        - Limit length to 60 characters
        """
        # Lowercase and strip
        slug = slug.lower().strip()

        # Replace non-alphanumeric with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)

        # Remove consecutive hyphens
        slug = re.sub(r'-+', '-', slug)

        # Strip leading/trailing hyphens
        slug = slug.strip('-')

        # Limit length (break at word boundary if possible)
        if len(slug) > 60:
            slug = slug[:60]
            last_hyphen = slug.rfind('-')
            if last_hyphen > 40:
                slug = slug[:last_hyphen]

        return slug

    def _ensure_draft_status(self, content: str, draft: bool) -> str:
        """Ensure draft frontmatter field is set correctly

        Args:
            content: MDX content
            draft: Desired draft status

        Returns:
            Content with draft field set correctly
        """
        draft_value = 'true' if draft else 'false'

        # Check if draft field exists
        if re.search(r'^draft:\s*(true|false)\s*$', content, re.MULTILINE):
            # Update existing value
            content = re.sub(
                r'^(draft:\s*)(true|false)(\s*)$',
                f'\\g<1>{draft_value}\\g<3>',
                content,
                flags=re.MULTILINE
            )
        else:
            # Add draft field after title or description
            # Try after description first
            if re.search(r'^description:', content, re.MULTILINE):
                content = re.sub(
                    r'^(description:\s*["\'][^"\']*["\'])\s*$',
                    f'\\g<1>\ndraft: {draft_value}',
                    content,
                    count=1,
                    flags=re.MULTILINE
                )
            # Fallback: add after title
            elif re.search(r'^title:', content, re.MULTILINE):
                content = re.sub(
                    r'^(title:\s*["\'][^"\']*["\'])\s*$',
                    f'\\g<1>\ndraft: {draft_value}',
                    content,
                    count=1,
                    flags=re.MULTILINE
                )

        return content

    def _validate_frontmatter(self, content: str) -> Dict[str, Any]:
        """Validate frontmatter against content.config.ts schema

        Returns:
            Dict with valid bool, errors list, warnings list
        """
        errors = []
        warnings = []

        # Check frontmatter exists
        if not content.startswith('---'):
            return {
                'valid': False,
                'errors': ['Missing frontmatter (must start with ---)'],
                'warnings': [],
            }

        # Extract frontmatter section
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {
                'valid': False,
                'errors': ['Invalid frontmatter structure (missing closing ---)'],
                'warnings': [],
            }

        frontmatter = parts[1]

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if not re.search(rf'^{field}:', frontmatter, re.MULTILINE):
                errors.append(f"Missing required field: {field}")

        # Check recommended fields
        for field in self.RECOMMENDED_FIELDS:
            if not re.search(rf'^{field}:', frontmatter, re.MULTILINE):
                warnings.append(f"Missing recommended field: {field}")

        # SEO validations
        title_match = re.search(r'^title:\s*["\']?([^"\'}\n]+)', frontmatter, re.MULTILINE)
        if title_match:
            title_len = len(title_match.group(1).strip())
            if title_len > 60:
                warnings.append(f"Title exceeds 60 chars ({title_len} chars) - may be truncated in SERPs")

        desc_match = re.search(r'^description:\s*["\']?([^"\'}\n]+)', frontmatter, re.MULTILINE)
        if desc_match:
            desc_len = len(desc_match.group(1).strip())
            if desc_len < 120:
                warnings.append(f"Description too short ({desc_len} chars) - aim for 120-160")
            elif desc_len > 160:
                warnings.append(f"Description too long ({desc_len} chars) - may be truncated")

        # Image path validation
        if 'image:' in frontmatter:
            if '/src/assets/' not in frontmatter and 'src:' in frontmatter:
                warnings.append("Image path should start with /src/assets/")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }

    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract frontmatter fields for preview"""
        import yaml

        if not content.startswith('---'):
            return {}

        try:
            parts = content.split('---', 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1]) or {}
        except Exception:
            pass

        return {}

    def _update_image_paths(self, content: str, slug: str) -> str:
        """Update image paths for Astro asset pipeline

        Ensures hero image path follows convention:
        /src/assets/blog/{slug}-hero.webp
        """
        expected_hero = f"/src/assets/blog/{slug}-hero.webp"

        # Update image src in frontmatter if it exists
        # Pattern: image:\n  src: "..."
        content = re.sub(
            r'(image:\s*\n\s*src:\s*["\'])([^"\']+)(["\'])',
            f'\\g<1>{expected_hero}\\g<3>',
            content
        )

        return content

    def _check_hero_image_exists(self, slug: str) -> bool:
        """Check if hero image exists for the given slug"""
        hero_path = self.assets_path / f"{slug}-hero.webp"
        return hero_path.exists()


# Convenience function for quick publishing
def publish_to_astro(
    content: str,
    slug: str,
    draft: bool = True,
    overwrite: bool = False
) -> Dict[str, Any]:
    """Quick helper to publish content to astro-site

    Args:
        content: MDX content with frontmatter
        slug: URL slug
        draft: Set draft status (default: True)
        overwrite: Overwrite existing (default: False)

    Returns:
        Result dict with success status
    """
    publisher = AstroPublisher()
    return publisher.publish(content, slug, draft=draft, overwrite=overwrite)


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    publisher = AstroPublisher()

    # Show existing slugs
    existing = publisher.get_existing_slugs()
    print(f"\nExisting blog posts ({len(existing)}):")
    for slug in existing[:10]:
        print(f"  - {slug}")

    # Preview test
    test_content = """---
title: "Test Post Title"
description: "This is a test description for the blog post."
publishDate: "2025-01-12"
author: "Brand Team"
tags: ["Test", "Demo"]
---

## Test Content

This is test content.
"""

    preview = publisher.preview(test_content, "test-post-slug")
    print(f"\nPreview:")
    print(f"  Target: {preview['target_path']}")
    print(f"  Would overwrite: {preview['would_overwrite']}")
    print(f"  Valid: {preview['validation']['valid']}")
    if preview['validation']['warnings']:
        print(f"  Warnings: {preview['validation']['warnings']}")
