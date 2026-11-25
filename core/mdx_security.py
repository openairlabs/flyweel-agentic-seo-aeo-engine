"""Fail-closed security checks for generated Markdown / MDX / Svelte / Nuxt content.

Generated content is untrusted even when produced by an LLM we invoked. This module
blocks active scripts, unsafe HTML/Svelte directives, protocol-smuggled URLs, unapproved
ESM imports/exports, and arbitrary JS/Svelte brace expressions before writing to disk.
"""
from __future__ import annotations

import ast
import html
import json
import re
from typing import Any
from urllib.parse import quote, unquote, urlsplit


class MdxSecurityError(ValueError):
    """Raised when generated content contains active or ambiguous markup/expressions."""


_ALLOWED_IMPORTS = {
    "import { Image } from 'astro:assets';",
    "import { Icon } from 'astro-icon/components';",
    "import Button from '@/components/ui/Button.astro';",
    "import FAQSection from '@/components/sections/FAQSectionAstro.astro';",
    "import ComparisonTable from '@/components/sections/ComparisonTable.astro';",
    "import CitationsSection from '@/components/content/CitationsSection.astro';",
    "import { SolutionCard } from '@/components/mdx';",
    "import { ComparisonSummary } from '@/components/mdx';",
    "import { ServicesList } from '@/components/mdx';",
    "import { MetadataBadges } from '@/components/mdx';",
}
_ALLOWED_MDX_EXPORTS = {"SolutionCard", "ComparisonSummary", "ServicesList", "MetadataBadges"}
_ALLOWED_COMPONENTS = {
    "Image",
    "Icon",
    "Button",
    "Callout",
    "FAQSection",
    "ComparisonTable",
    "CitationsSection",
    *_ALLOWED_MDX_EXPORTS,
}
_ALLOWED_HTML_ELEMENTS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "caption",
    "cite",
    "code",
    "col",
    "colgroup",
    "dd",
    "del",
    "details",
    "div",
    "dl",
    "dt",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "ins",
    "kbd",
    "li",
    "mark",
    "ol",
    "p",
    "pre",
    "q",
    "rp",
    "rt",
    "ruby",
    "s",
    "samp",
    "section",
    "small",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "time",
    "tr",
    "u",
    "ul",
    "var",
    "wbr",
}
_GLOBAL_SAFE_ATTRIBUTES = {
    "id",
    "class",
    "classname",
    "title",
    "lang",
    "dir",
    "role",
    "tabindex",
    "open",
    "colspan",
    "rowspan",
    "scope",
    "align",
    "datetime",
    "start",
    "hidden",
}
_ELEMENT_SAFE_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "width", "height", "loading", "decoding"},
    "ol": {"type", "reversed"},
    "li": {"value"},
    "td": {"headers", "abbr"},
    "th": {"headers", "abbr"},
    "col": {"span"},
    "colgroup": {"span"},
    "blockquote": {"cite"},
    "q": {"cite"},
    "del": {"cite"},
    "ins": {"cite"},
}
_COMPONENT_SAFE_ATTRIBUTES = {
    "src",
    "alt",
    "width",
    "height",
    "loading",
    "decoding",
    "format",
    "quality",
    "href",
    "target",
    "rel",
    "variant",
    "size",
    "icon",
    "name",
    "type",
    "title",
    "items",
    "rating",
    "pricing",
    "bestfor",
    "pros",
    "cons",
    "url",
    "badge",
    "category",
    "rank",
    "number",
    "description",
    "summary",
    "primaryname",
    "competitorname",
}
_URL_BEARING_ATTRIBUTES = {"href", "src", "cite", "url"}
_DANGEROUS_ATTRIBUTE = re.compile(
    r"(?i)(?:\bon[a-z0-9_-]+\s*=|\bstyle\s*=|\bdangerouslySetInnerHTML\s*=|\bset:html\s*=|\bis:raw\s*=|\bclient:[a-z0-9_-]+\s*=|\bv-html\s*=|\bformaction\s*=|\bxlink:href\s*=|\bsrcdoc\s*=|\baction\s*=|\bvalues\s*=)"
)
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\n]*)$")
_INLINE_SPAN_BLOCK_INTERRUPT = re.compile(
    r"\r?\n(?:"
    r"[ \t]*(?:\r?\n|$)"
    r"| {0,3}#{1,6}(?:[ \t\r\n]|$)"
    r"| {0,3}(?:`{3,}|~{3,})"
    r"| {0,3}>"
    r"| {0,3}(?:-[ \t]*-[ \t]*-[-\t ]*|\*[ \t]*\*[ \t]*\*[\*\t ]*|_[ \t]*_[ \t]*_[_\t ]*)(?:\r?\n|$)"
    r"| {0,3}(?:[-+*]|\d{1,9}[.)])(?:[ \t\r\n]|$)"
    r"| {0,3}(?:<!--|</?[A-Za-z][A-Za-z0-9.:_-]*(?:[\s/>]|$))"
    r")"
)


def _inline_code_search_limit(content: str, pos: int, hard_limit: int) -> int:
    m = _INLINE_SPAN_BLOCK_INTERRUPT.search(content, pos, hard_limit)
    return m.start() if m else hard_limit
_ESM_LINE = re.compile(r"(?m)^\s*(import|export)\b.*$")
_ESM_STATEMENT_RE = re.compile(
    r"^(?:import(?:\s+\S|\s*[\{'\"*])|export(?:\s+(?:default|async|const|let|var|function|class)\b|\s*[\{*]))"
)
_UNPARSEABLE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029\ufeff]|\r(?!\n)|<!--|<\?|<!\[CDATA\[|<![A-Za-z]|<(?![ \t\r\n])\s"
)
_MARKDOWN_LINK = re.compile(r"(!?\[[^\]\n]*\])\((<[^>\n]*>|[^()\n]*(?:\([^()\n]*\)[^()\n]*)*)\)")
_LEFTOVER_LINK_START = re.compile(r"!?\[[^\]\n]*\]\(([^\n]*)")
_REF_LINK_DEF = re.compile(r"(?m)^(\s{0,3}\[[^\]\n]+\]):[ \t]*(?:\n[ \t]*)?([^\n]+)$")
_URL_ATTRIBUTE = re.compile(r"(?is)\b(href|src)\s*=\s*(?:([\"'])(.*?)\2|([^\s\"'=<>`{}]+))")
_COMPARISON = re.compile(r"(?is)<ComparisonTable\b(.*?)/>")


def _without_frontmatter(content: str) -> str:
    opener = re.match(r"^---[ \t]*(?:\r?\n|$)", content)
    if not opener:
        return content
    if opener.end() == len(content):
        raise MdxSecurityError("MDX security: unterminated frontmatter")
    match = re.search(r"(?m)^---[ \t]*\r?$", content[opener.end() :])
    if not match:
        raise MdxSecurityError("MDX security: unterminated frontmatter")
    return content[opener.end() + match.end() :]


def markdown_code_spans(content: str, *, start: int = 0) -> list[tuple[int, int]]:
    """Return sorted non-overlapping (start, end) spans for CommonMark fenced and inline code."""
    fences: list[tuple[int, int]] = []
    lines = content[start:].splitlines(keepends=True)
    idx = 0
    offset = start
    while idx < len(lines):
        line = lines[idx]
        m = re.match(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)", line)
        if m and (m.group(1)[0] != "`" or "`" not in m.group(2)):
            char, flen = m.group(1)[0], len(m.group(1))
            close_re = re.compile(rf"^ {{0,3}}{re.escape(char)}{{{flen},}}[ \t]*\r?\n?$")
            s_off = offset
            offset += len(line)
            idx += 1
            while idx < len(lines):
                offset += len(lines[idx])
                if close_re.match(lines[idx]):
                    idx += 1
                    break
                idx += 1
            end_off = offset - (1 if content[s_off:offset].endswith("\n") else 0)
            fences.append((s_off, end_off))
            continue
        offset += len(line)
        idx += 1

    spans = list(fences)
    n, f_idx, i = len(content), 0, start
    while i < n:
        while f_idx < len(fences) and fences[f_idx][1] <= i:
            f_idx += 1
        if f_idx < len(fences) and fences[f_idx][0] <= i < fences[f_idx][1]:
            i = fences[f_idx][1]
            continue
        if content[i] == "`":
            j = i
            while j > start and content[j - 1] == "\\":
                j -= 1
            if (i - j) % 2 == 1:
                i += 1
                continue
            run_end = i
            while run_end < n and content[run_end] == "`":
                run_end += 1
            tick_len = run_end - i
            next_f = fences[f_idx][0] if f_idx < len(fences) else n
            limit = _inline_code_search_limit(content, run_end, next_f)
            scan = run_end
            matched: int | None = None
            while scan < limit:
                if content[scan] == "`":
                    c_end = scan
                    while c_end < limit and content[c_end] == "`":
                        c_end += 1
                    if c_end - scan == tick_len:
                        matched = c_end
                        break
                    scan = c_end
                else:
                    scan += 1
            if matched is not None:
                spans.append((i, matched))
                i = matched
                continue
            i = run_end
            continue
        i += 1
    spans.sort()
    return spans


def _decoded_url_for_policy(value: str) -> str:
    decoded = html.unescape(value).strip()
    for _ in range(3):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return re.sub(r"[\x00-\x20\x7f]+", "", decoded)


def sanitize_content_url(value: str) -> str:
    """Return a safely encoded content URL or reject an unsafe scheme."""
    if not isinstance(value, str) or not value.strip():
        raise MdxSecurityError("MDX security: URL is empty")
    raw = html.unescape(value).strip()
    decoded = _decoded_url_for_policy(raw)
    if "\\" in decoded or decoded.startswith("//"):
        raise MdxSecurityError("MDX security: unsafe URL")
    parsed = urlsplit(decoded)
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https", "mailto"}:
        raise MdxSecurityError("MDX security: unsafe URL scheme")
    if parsed.scheme.lower() in {"http", "https"} and not parsed.netloc:
        raise MdxSecurityError("MDX security: URL host is required")
    return quote(raw, safe="/:#?&=@[]!$'()*+,;%-._~")


def escape_markdown_link_text(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\")
    for character in "[]()":
        escaped = escaped.replace(character, "\\" + character)
    return escaped.replace("\r", " ").replace("\n", " ")


def _validate_json_value(value: Any) -> None:
    if isinstance(value, (str, bool)) or value is None:
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            _validate_json_value(item)
        return
    raise MdxSecurityError("MDX security: ComparisonTable expression contains a non-static value")


_AUTOLINK_RE = re.compile(r"^<([A-Za-z][A-Za-z0-9+.-]*:[^\s<>]+)>$")
_ATTR_TOKEN_RE = re.compile(
    r"""\s*([A-Za-z_:][A-Za-z0-9_.:-]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|(\{[^}]*\})|([^\s"'=<>`{}]+)))?""",
    re.DOTALL,
)


def _iter_raw_tags(body: str) -> list[str]:
    tags: list[str] = []
    n = len(body)
    i = 0
    while i < n:
        if body[i] == "<" and i + 1 < n and (body[i + 1].isalpha() or body[i + 1] == "/"):
            k = i + 1
            quote_char: str | None = None
            brace_depth = 0
            while k < n:
                ck = body[k]
                if quote_char is not None:
                    if ck == quote_char:
                        quote_char = None
                else:
                    if ck in ('"', "'"):
                        quote_char = ck
                    elif ck == "{":
                        brace_depth += 1
                    elif ck == "}" and brace_depth > 0:
                        brace_depth -= 1
                    elif ck == ">" and brace_depth == 0:
                        if re.search(r"<[A-Za-z/!?]", body[i + 1 : k]):
                            raise MdxSecurityError("MDX security: nested tag start inside tag")
                        tags.append(body[i : k + 1])
                        i = k + 1
                        break
                k += 1
            else:
                raise MdxSecurityError("MDX security: malformed or unclosed HTML/JSX tag")
            continue
        i += 1
    return tags


def _validate_tag_and_attributes(raw_tag: str) -> None:
    autolink = _AUTOLINK_RE.match(raw_tag)
    if autolink:
        sanitize_content_url(autolink.group(1))
        return

    m = re.match(r"(?s)^<\s*(/?)\s*([A-Za-z][A-Za-z0-9.:_-]*)(.*?)\s*(/?)>$", raw_tag)
    if not m:
        raise MdxSecurityError("MDX security: unclassified raw HTML tag")
    is_closing, tag, attr_tail, _self_closing = m.group(1), m.group(2), m.group(3), m.group(4)

    if tag.lower() == "script":
        raise MdxSecurityError("MDX security: script elements are forbidden")
    if tag[:1].isupper():
        if tag not in _ALLOWED_COMPONENTS:
            raise MdxSecurityError(f"MDX security: unapproved component <{tag}>")
        allowed_specific = _COMPONENT_SAFE_ATTRIBUTES
    else:
        tag_low = tag.lower()
        if tag_low not in _ALLOWED_HTML_ELEMENTS:
            raise MdxSecurityError(f"MDX security: unsafe element <{tag}>")
        allowed_specific = _ELEMENT_SAFE_ATTRIBUTES.get(tag_low, set())

    if is_closing:
        if attr_tail.strip():
            raise MdxSecurityError("MDX security: closing tag cannot carry attributes")
        return

    pos = 0
    while pos < len(attr_tail):
        if not attr_tail[pos:].strip():
            break
        am = _ATTR_TOKEN_RE.match(attr_tail, pos)
        if not am:
            raise MdxSecurityError("MDX security: unsafe JSX attribute")
        attr_name = am.group(1)
        attr_low = attr_name.lower()
        if _DANGEROUS_ATTRIBUTE.match(f"{attr_name}="):
            raise MdxSecurityError("MDX security: unsafe JSX attribute")
        is_aria_or_data = (attr_low.startswith("aria-") or attr_low.startswith("data-")) and len(attr_low) > 5
        if not (is_aria_or_data or attr_low in _GLOBAL_SAFE_ATTRIBUTES or attr_low in allowed_specific):
            raise MdxSecurityError(f"MDX security: unsafe JSX attribute {attr_name}")
        if am.group(4) is not None:
            raise MdxSecurityError("MDX security: arbitrary expression is forbidden")
        val = am.group(2) if am.group(2) is not None else (am.group(3) if am.group(3) is not None else am.group(5))
        if attr_low in _URL_BEARING_ATTRIBUTES:
            sanitize_content_url(val or "")
        pos = am.end()


def _parse_markdown_destination_and_tail(raw_destination: str) -> tuple[str, str]:
    destination = raw_destination.strip()
    if not destination:
        raise MdxSecurityError("MDX security: URL is empty")
    if destination.startswith("<"):
        close_idx = destination.find(">")
        if close_idx == -1:
            raise MdxSecurityError("MDX security: unterminated angle-bracket URL")
        return destination[1:close_idx], destination[close_idx + 1 :]
    parts = destination.split(maxsplit=1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def _parse_markdown_destination(raw_destination: str) -> str:
    return _parse_markdown_destination_and_tail(raw_destination)[0]


def parse_static_js_array(raw_expr: str) -> list[Any]:
    """Safely parse a static JS/JSON array literal (supporting single or double quotes) without eval."""
    out: list[str] = []
    n = len(raw_expr)
    i = 0
    while i < n:
        ch = raw_expr[i]
        if ch in ('"', "'"):
            quote_ch = ch
            j = i + 1
            while j < n:
                if raw_expr[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if raw_expr[j] == quote_ch:
                    j += 1
                    break
                j += 1
            else:
                raise MdxSecurityError("MDX security: ComparisonTable expression has unterminated string")
            out.append(raw_expr[i:j])
            i = j
            continue
        # Scan until next quote
        j = i
        while j < n and raw_expr[j] not in ('"', "'"):
            j += 1
        seg = raw_expr[i:j]
        seg = re.sub(r"([\{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)", r'\1"\2"\3', seg)
        seg = re.sub(r"\btrue\b", "True", seg)
        seg = re.sub(r"\bfalse\b", "False", seg)
        seg = re.sub(r"\bnull\b", "None", seg)
        out.append(seg)
        i = j

    py_src = "".join(out)
    try:
        value = ast.literal_eval(py_src)
    except (ValueError, SyntaxError) as exc:
        raise MdxSecurityError("MDX security: ComparisonTable expression is not static data") from exc
    if not isinstance(value, list):
        raise MdxSecurityError("MDX security: ComparisonTable items must be an array")
    _validate_json_value(value)
    return value


def _validate_comparison(match: re.Match[str]) -> str:
    attributes = match.group(1)
    expression = re.search(r"(?is)\bitems\s*=\s*\{(\[.*\])\}\s*$", attributes)
    if not expression:
        raise MdxSecurityError("MDX security: ComparisonTable items expression is invalid")
    parse_static_js_array(expression.group(1))
    prefix = attributes[: expression.start()]
    if "{" in prefix or "}" in prefix:
        raise MdxSecurityError("MDX security: unexpected component expression")
    return "<ComparisonTable />"


def validate_mdx_security(content: str) -> list[str]:
    """Return security issues for a generated Markdown/MDX document without mutating it."""
    if not isinstance(content, str) or not content.strip():
        return ["MDX security: content is empty"]
    try:
        # ponytail: no code masking, so braces/tags/ESM lines inside code blocks are rejected too.
        # Upgrade path if brace-bearing code samples are needed: validate the real MDX AST from the Node side.
        if _UNPARSEABLE.search(content):
            raise MdxSecurityError("MDX security: forbidden control character or markup")
        body = _without_frontmatter(content)
        for match in _ESM_LINE.finditer(body):
            line = match.group(0).strip()
            # Only treat lines that look like JS/ESM import/export as ESM, not normal prose starting with "Export your CSV..."
            if not _ESM_STATEMENT_RE.match(line):
                continue
            if line in _ALLOWED_IMPORTS:
                continue
            named = re.fullmatch(r"import \{ ([A-Za-z]+(?:, [A-Za-z]+)*) \} from '@/components/mdx';", line)
            if named and set(named.group(1).split(", ")).issubset(_ALLOWED_MDX_EXPORTS):
                continue
            kind = match.group(1).upper()
            raise MdxSecurityError(f"MDX security: unapproved ESM {kind} import/export")

        body = re.sub(
            r"(?m)^\s*(?:import(?:\s+\S|\s*[\{'\"*])|export(?:\s+(?:default|async|const|let|var|function|class)\b|\s*[\{*])).*$",
            "",
            body,
        )
        body = _COMPARISON.sub(_validate_comparison, body)

        for m in re.finditer(r"\]\([ \t]*\r?\n?[ \t]*(<[^>\r\n]*>|[^\s)]*)", body):
            sanitize_content_url(m.group(1).strip("<>"))
        for m in re.finditer(r"\]:[ \t]*\r?\n?[ \t]*(<[^>\r\n]*>|\S+)", body):
            sanitize_content_url(m.group(1).strip("<>"))

        for match in _MARKDOWN_LINK.finditer(body):
            dest, tail = _parse_markdown_destination_and_tail(match.group(2))
            sanitize_content_url(dest)
            if "{" in match.group(0) or "}" in match.group(0):
                raise MdxSecurityError("MDX security: arbitrary expression is forbidden")
            if "<" in dest or ">" in dest or "<" in tail or ">" in tail:
                raise MdxSecurityError("MDX security: raw markup in Markdown link is forbidden")
        for match in _REF_LINK_DEF.finditer(body):
            raw_ref = match.group(2).strip()
            # Ignore footnote prose lines if any, validate URL-shaped or angle-bracket reference defs
            dest, tail = _parse_markdown_destination_and_tail(raw_ref)
            sanitize_content_url(dest)
            if "{" in match.group(0) or "}" in match.group(0):
                raise MdxSecurityError("MDX security: arbitrary expression is forbidden")
            if "<" in dest or ">" in dest or "<" in tail or ">" in tail:
                raise MdxSecurityError("MDX security: raw markup in Markdown link is forbidden")

        unmatched_links = _MARKDOWN_LINK.sub("", body)
        for leftover in _LEFTOVER_LINK_START.finditer(unmatched_links):
            sanitize_content_url(_parse_markdown_destination(leftover.group(1)))
            raise MdxSecurityError("MDX security: malformed Markdown link destination")
        body = _MARKDOWN_LINK.sub(r"\1(https://validated.example/)", body)
        body = _REF_LINK_DEF.sub(r"\1: https://validated.example/", body)

        if re.search(r"(?i)<\s*script\b", body):
            raise MdxSecurityError("MDX security: script elements are forbidden")
        if re.search(r"\{\s*@html\b", body):
            raise MdxSecurityError("MDX security: Svelte {@html} directive is forbidden")
        if _DANGEROUS_ATTRIBUTE.search(body):
            raise MdxSecurityError("MDX security: unsafe JSX attribute")
        for raw_tag in _iter_raw_tags(body):
            _validate_tag_and_attributes(raw_tag)

        for match in _URL_ATTRIBUTE.finditer(body):
            value = match.group(3) if match.group(2) else match.group(4)
            sanitize_content_url(value)

        if "{" in body or "}" in body:
            raise MdxSecurityError("MDX security: arbitrary expression is forbidden")
    except MdxSecurityError as exc:
        return [str(exc)]
    return []


_PROSE_PLACEHOLDER_RE = re.compile(r"\{([a-z][a-z0-9_-]{0,39})\}")


def escape_prose_placeholders(content: str) -> str:
    """Escape simple single-token prose placeholders like ``{cost}`` outside frontmatter, code, ESM, and tags."""
    if not isinstance(content, str) or "{" not in content:
        return content

    fm_head = ""
    body = content
    fm_open = re.match(r"^---[ \t]*(?:\r?\n|$)", content)
    if fm_open:
        m_fm = re.search(r"(?m)^---[ \t]*\r?$", content[fm_open.end() :])
        if m_fm:
            split_idx = fm_open.end() + m_fm.end()
            fm_head = content[:split_idx]
            body = content[split_idx:]
        else:
            return content

    lines = body.splitlines(keepends=True)
    out_lines: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in lines:
        m_f = _FENCE_OPEN.match(line)
        if m_f:
            run = m_f.group(1)
            info = m_f.group(2)
            if not in_fence and (run[0] != "`" or "`" not in info):
                in_fence = True
                fence_char = run[0]
                fence_len = len(run)
                out_lines.append(line)
                continue
            if in_fence and run[0] == fence_char and len(run) >= fence_len and not info.strip():
                in_fence = False
                out_lines.append(line)
                continue
        if in_fence or _ESM_STATEMENT_RE.match(line.lstrip()):
            out_lines.append(line)
            continue

        # Mask inline code spans and HTML/JSX tags before escaping `{token}` in prose
        chunks = re.split(r"(`+[^`]*`+|<[^>]*>)", line)
        for idx in range(0, len(chunks), 2):
            chunks[idx] = _PROSE_PLACEHOLDER_RE.sub(r"&#123;\1&#125;", chunks[idx])
        out_lines.append("".join(chunks))

    return fm_head + "".join(out_lines)


def assert_safe_mdx(content: str) -> str:
    issues = validate_mdx_security(content)
    if issues:
        raise MdxSecurityError(issues[0])
    return content


__all__ = [
    "MdxSecurityError",
    "assert_safe_mdx",
    "escape_markdown_link_text",
    "escape_prose_placeholders",
    "parse_static_js_array",
    "sanitize_content_url",
    "validate_mdx_security",
]
