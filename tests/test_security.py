#!/usr/bin/env python3
"""Offline security regression tests for MDX sanitization, URL safety, and XML parsing."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.formatter import AstroFormatter
from core.mdx_security import MdxSecurityError, assert_safe_mdx, sanitize_content_url
from core.publisher import AstroPublisher
from core.site_extractor import SiteContextExtractor
from core.url_safety import UnsafeUrlError, validate_public_http_url


class TestMdxSecurity:
    """Verify fail-closed MDX / JSX / link sanitization."""

    def test_blocks_script_tag(self):
        mdx = "---\ntitle: 'Test'\n---\n\nHello <script>alert(1)</script> world\n"
        with pytest.raises(MdxSecurityError):
            assert_safe_mdx(mdx)

    def test_blocks_unapproved_esm_import_and_export(self):
        with pytest.raises(MdxSecurityError):
            assert_safe_mdx("---\ntitle: 'T'\n---\n\nimport fs from 'node:fs';\n\nBody\n")
        with pytest.raises(MdxSecurityError):
            assert_safe_mdx("---\ntitle: 'T'\n---\n\nexport const pwn = process.env;\n\nBody\n")

    def test_blocks_jsx_expression_and_link_tail_bypass(self):
        with pytest.raises(MdxSecurityError):
            assert_safe_mdx("---\ntitle: 'T'\n---\n\nValue: {process.env.SECRET}\n")
        with pytest.raises(MdxSecurityError):
            assert_safe_mdx("---\ntitle: 'T'\n---\n\n[Click](https://example.com \"{process.env.SECRET}\")\n")
        with pytest.raises(MdxSecurityError):
            assert_safe_mdx("---\ntitle: 'T'\n---\n\n[Click](https://example.com \"<script>alert(1)</script>\")\n")

    def test_blocks_javascript_and_data_urls(self):
        with pytest.raises(MdxSecurityError):
            sanitize_content_url("javascript:alert(1)")
        with pytest.raises(MdxSecurityError):
            sanitize_content_url("data:text/html,<script>alert(1)</script>")
        with pytest.raises(MdxSecurityError):
            assert_safe_mdx("---\ntitle: 'T'\n---\n\n[bad](javascript:alert(1))\n")

    def test_formatter_rejects_injected_payload_and_drops_unsafe_citations(self):
        formatter = AstroFormatter()
        with pytest.raises(MdxSecurityError):
            formatter.format(
                content="# Title\n\n<script>alert(1)</script>\n",
                keyword="security test",
                style="standard",
                research_data={},
            )

        res = formatter.format(
            content=(
                "# Research\n\n"
                "Our analysis reveals lead costs rose 15%.\n"
                "Data demonstrates an average cost of $50 per lead.\n"
            ),
            keyword="lead costs",
            style="research",
            research_data={
                "serp": {
                    "serp_analysis": {
                        "citations": [
                            "javascript:alert(1)",
                            "https://example.com/valid-source-1",
                            "https://example.com/valid-source-2",
                        ]
                    }
                }
            },
        )
        assert "javascript:" not in res["content"].lower()
        assert_safe_mdx(res["content"])

    def test_publisher_refuses_unsafe_mdx_and_guards_empty_slug(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        publisher = AstroPublisher(blog_path=blog_dir, assets_path=tmp_path / "assets")

        unsafe_mdx = "---\ntitle: 'Safe Title'\ndescription: 'Valid description for testing.'\n---\n\n{process.env}\n"
        result = publisher.publish(unsafe_mdx, slug="unsafe-post")
        assert result["success"] is False
        assert not (blog_dir / "unsafe-post.mdx").exists()

        safe_mdx = "---\ntitle: 'Safe Title'\ndescription: 'Valid description for testing.'\n---\n\n## Hello\n\nSafe body.\n"
        ok = publisher.publish(safe_mdx, slug="!!!")
        assert ok["success"] is True
        assert ok["slug"] == "untitled"
        assert (blog_dir / "untitled.mdx").exists()


class TestUrlAndXmlSafety:
    """Verify SSRF validation, same-host sitemap policy, and defusedxml parsing."""

    @pytest.mark.parametrize(
        "bad_url",
        [
            "file:///etc/passwd",
            "ftp://example.com/file",
            "http://localhost/admin",
            "http://127.0.0.1:8080/",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/internal",
            "https://user:pass@example.com/",
        ],
    )
    def test_validate_public_http_url_rejects_unsafe_targets(self, bad_url):
        with pytest.raises(UnsafeUrlError):
            validate_public_http_url(bad_url, resolve_dns=False)

    def test_validate_public_http_url_accepts_public_https(self):
        assert validate_public_http_url("https://example.com/blog", resolve_dns=False) == "https://example.com/blog"

    def test_site_extractor_enforces_same_host_and_safe_cache(self, monkeypatch):
        monkeypatch.setenv("GSC_SITE_URL", "https://example.com")
        extractor = SiteContextExtractor()
        assert extractor._is_same_target_host("https://example.com/pricing") is True
        assert extractor._is_same_target_host("https://www.example.com/blog") is True
        assert extractor._is_same_target_host("https://evil.example.org/payload") is False
        assert extractor._is_same_target_host("http://169.254.169.254/latest/meta-data/") is False
        assert not extractor._cache_file.startswith("/tmp/")

    def test_site_extractor_blocks_xml_entity_expansion(self):
        import defusedxml.ElementTree as ET
        from defusedxml.common import DefusedXmlException

        bomb = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>&lol2;</loc></url></urlset>'
        )
        with pytest.raises(DefusedXmlException):
            ET.fromstring(bomb)

    def test_site_extractor_rejects_offhost_page_extract(self, monkeypatch):
        monkeypatch.setenv("GSC_SITE_URL", "https://example.com")
        extractor = SiteContextExtractor()
        res = asyncio.run(extractor._extract_page_content("http://169.254.169.254/latest/meta-data/"))
        assert "error" in res
