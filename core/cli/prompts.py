"""Interactive Prompts for CLI

Uses Questionary for beautiful, interactive prompts with
custom Brand brand styling.
"""
import sys
from typing import Optional
import questionary
from questionary import Style


# Custom style matching Brand brand (emerald/jade green)
BRAND_STYLE = Style([
    ('qmark', 'fg:#74BD96 bold'),        # Question mark
    ('question', 'bold'),                 # Question text
    ('answer', 'fg:#A4FED3'),            # Answer text
    ('pointer', 'fg:#74BD96 bold'),      # Selection pointer
    ('highlighted', 'fg:#A4FED3 bold'),  # Highlighted option
    ('selected', 'fg:#74BD96'),          # Selected option
    ('instruction', 'fg:#888888'),       # Instructions
])


def _is_interactive() -> bool:
    """Check if interactive prompts are available"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_keyword(default: Optional[str] = None) -> Optional[str]:
    """Prompt for keyword input

    Args:
        default: Optional default value

    Returns:
        Keyword string or None if cancelled
    """
    if not _is_interactive():
        return default

    try:
        return questionary.text(
            "Enter keyword to generate content for:",
            default=default or "",
            validate=lambda x: len(x.strip()) >= 3 or "Keyword must be at least 3 characters",
            style=BRAND_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return None


def prompt_style(default: str = "standard") -> Optional[str]:
    """Prompt for content style selection

    Args:
        default: Default style to highlight

    Returns:
        Style string or None if cancelled
    """
    if not _is_interactive():
        return default

    choices = [
        questionary.Choice(
            "Standard - Comprehensive overview (2000-2500 words)",
            value="standard"
        ),
        questionary.Choice(
            "Guide - Step-by-step tutorial with 'Manual vs Brand way'",
            value="guide"
        ),
        questionary.Choice(
            "Comparison - Product/solution comparison",
            value="comparison"
        ),
        questionary.Choice(
            "Top-Compare - 'Top X Best' ranked comparison (Omnius-style)",
            value="top-compare"
        ),
        questionary.Choice(
            "Research - Data-driven analysis (3500+ words)",
            value="research"
        ),
        questionary.Choice(
            "News - Trending topic coverage",
            value="news"
        ),
        questionary.Choice(
            "Category - Category overview/listicle",
            value="category"
        ),
        questionary.Choice(
            "Feature - Conversion-focused product page (Hook → Solution → CTA)",
            value="feature"
        ),
    ]

    # Find default choice index
    default_idx = next(
        (i for i, c in enumerate(choices) if c.value == default),
        0
    )

    try:
        return questionary.select(
            "Select content style:",
            choices=choices,
            default=choices[default_idx],
            style=BRAND_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return None


def prompt_publish_decision() -> Optional[str]:
    """Prompt for publish decision after generation

    Returns:
        One of: 'publish', 'local', 'preview', or None if cancelled
    """
    if not _is_interactive():
        return 'local'  # Default to local in non-interactive

    choices = [
        questionary.Choice(
            "Publish to astro-site blog (Recommended)",
            value="publish"
        ),
        questionary.Choice(
            "Save locally to output/generations/",
            value="local"
        ),
        questionary.Choice(
            "Preview content only (don't save)",
            value="preview"
        ),
    ]

    try:
        return questionary.select(
            "What would you like to do with the generated content?",
            choices=choices,
            style=BRAND_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return None


def prompt_draft_status() -> bool:
    """Prompt for draft status when publishing

    Returns:
        True for draft, False for published
    """
    if not _is_interactive():
        return True  # Default to draft in non-interactive

    try:
        return questionary.confirm(
            "Set as draft? (Recommended: Yes, review before going live)",
            default=True,
            style=BRAND_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return True  # Default to draft on cancel


def prompt_overwrite(slug: str) -> bool:
    """Prompt for overwrite confirmation

    Args:
        slug: Existing file slug

    Returns:
        True to overwrite, False to cancel
    """
    if not _is_interactive():
        return False  # Don't overwrite in non-interactive

    try:
        return questionary.confirm(
            f"File '{slug}.mdx' already exists. Overwrite?",
            default=False,
            style=BRAND_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return False


def prompt_continue_generation() -> bool:
    """Prompt to continue after showing config

    Returns:
        True to continue, False to cancel
    """
    if not _is_interactive():
        return True  # Auto-continue in non-interactive

    try:
        return questionary.confirm(
            "Start generation?",
            default=True,
            style=BRAND_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return False


def prompt_research_options() -> dict:
    """Prompt for research options

    Returns:
        Dict with skip_community, limit_community flags
    """
    if not _is_interactive():
        return {'skip_community': False, 'limit_community': False}

    choices = [
        questionary.Choice(
            "Full research (SERP + 10 Reddit + 5 Quora)",
            value="full"
        ),
        questionary.Choice(
            "Limited research (SERP + 3 Reddit + 1 Quora) - Faster",
            value="limited"
        ),
        questionary.Choice(
            "SERP only (skip Reddit/Quora) - Fastest",
            value="serp_only"
        ),
    ]

    try:
        result = questionary.select(
            "Research depth:",
            choices=choices,
            style=BRAND_STYLE,
        ).ask()

        if result == "full":
            return {'skip_community': False, 'limit_community': False}
        elif result == "limited":
            return {'skip_community': False, 'limit_community': True}
        else:
            return {'skip_community': True, 'limit_community': False}

    except KeyboardInterrupt:
        return {'skip_community': False, 'limit_community': False}


def prompt_brand_mentions() -> bool:
    """DEPRECATED: Prompt for brand mention preference (binary)

    This function is maintained for backward compatibility but is deprecated.
    Use prompt_brand_mode() instead for three-tier control.

    Returns:
        True to include Brand mentions, False for educational-only
    """
    if not _is_interactive():
        return True  # Include by default

    try:
        return questionary.confirm(
            "Include Brand brand mentions? (No = educational content only)",
            default=True,
            style=BRAND_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return True


def prompt_brand_mode() -> str:
    """Prompt for Brand mention level (three-tier system)

    Returns:
        'full', 'limited', or 'none' - Brand mention mode
    """
    if not _is_interactive():
        return 'full'  # Full integration by default

    choices = [
        questionary.Choice(
            "Full Integration - Natural mentions where it fits (recommended)",
            value="full"
        ),
        questionary.Choice(
            "Limited - Only 2-3 highly natural mentions",
            value="limited"
        ),
        questionary.Choice(
            "None - Educational content only (no brand mentions)",
            value="none"
        ),
    ]

    try:
        result = questionary.select(
            "Brand mention level:",
            choices=choices,
            default=choices[0],  # Default to full
            style=BRAND_STYLE,
        ).ask()
        return result if result else 'full'
    except KeyboardInterrupt:
        return 'full'


def prompt_custom_slug(default: str) -> Optional[str]:
    """Prompt for custom slug

    Args:
        default: Default slug derived from title

    Returns:
        Custom slug or None to use default
    """
    if not _is_interactive():
        return default

    try:
        result = questionary.text(
            "Custom slug (leave empty for default):",
            default="",
            style=BRAND_STYLE,
        ).ask()

        return result.strip() if result and result.strip() else default

    except KeyboardInterrupt:
        return default


def prompt_icp_injection() -> bool:
    """Prompt for ICP (Ideal Customer Profile) context injection

    ICP context adds industry-specific audience targeting like:
    - Lead sellers, performance marketers
    - Service companies (HVAC, solar, plumbers, etc.)
    - Specific pain points and scenarios

    Returns:
        True to include ICP context, False to skip (generic audience)
    """
    if not _is_interactive():
        return True  # Include by default in non-interactive

    choices = [
        questionary.Choice(
            "Include ICP context (Brand's target audience - lead gen, service companies)",
            value=True
        ),
        questionary.Choice(
            "Skip ICP context (generic audience - broader appeal)",
            value=False
        ),
    ]

    try:
        result = questionary.select(
            "Audience targeting:",
            choices=choices,
            style=BRAND_STYLE,
        ).ask()
        return result if result is not None else True
    except KeyboardInterrupt:
        return True


def prompt_solution_count(default: int = 8) -> int:
    """Prompt for number of solutions in top-compare style

    Args:
        default: Default solution count (8)

    Returns:
        Solution count (5, 8, 10, or 15)
    """
    if not _is_interactive():
        return default

    choices = [
        questionary.Choice(
            "5 solutions - Quick comparison",
            value=5
        ),
        questionary.Choice(
            "8 solutions - Standard (Recommended)",
            value=8
        ),
        questionary.Choice(
            "10 solutions - Comprehensive",
            value=10
        ),
        questionary.Choice(
            "15 solutions - Extensive coverage",
            value=15
        ),
    ]

    # Find default choice index
    default_idx = next(
        (i for i, c in enumerate(choices) if c.value == default),
        1  # Default to 8 (index 1)
    )

    try:
        result = questionary.select(
            "How many solutions to compare?",
            choices=choices,
            default=choices[default_idx],
            style=BRAND_STYLE,
        ).ask()
        return result if result else default
    except KeyboardInterrupt:
        return default


def prompt_solution_selection(
    solutions: list,
    keyword: str,
    round_num: int = 1
) -> dict:
    """Interactive solution selection with multi-select checkboxes.

    Displays extracted solutions and allows user to:
    - Select/deselect individual solutions
    - Approve all solutions
    - Request AI to find more relevant solutions

    Args:
        solutions: List of solution dicts with {name, url, source, confidence, why_relevant}
        keyword: The keyword being researched
        round_num: Selection round (1 = initial, 2 = after discovery)

    Returns:
        Dict with:
        - approved: List of approved solution names
        - rejected: List of rejected solution names
        - find_more: Boolean indicating if user wants more solutions
    """
    if not _is_interactive():
        # Non-interactive: auto-approve all high-confidence solutions
        approved = [s['name'] for s in solutions if s.get('confidence', 0) >= 0.5]
        rejected = [s['name'] for s in solutions if s.get('confidence', 0) < 0.5]
        return {'approved': approved, 'rejected': rejected, 'find_more': False}

    if not solutions:
        return {'approved': [], 'rejected': [], 'find_more': True}

    # Build choices with confidence indicators
    choices = []
    for sol in solutions:
        confidence = sol.get('confidence', 0.5)
        source = sol.get('source', 'Unknown')
        why = sol.get('why_relevant', '')

        # Confidence indicator
        if confidence >= 0.85:
            indicator = "✓ High"
        elif confidence >= 0.7:
            indicator = "◐ Medium"
        else:
            indicator = "⚠ Low"

        # Format: "Solution Name (Source) - Confidence"
        title = f"{sol['name']} ({source}) — {indicator}"
        if why:
            title += f" | {why[:50]}..."

        # Pre-check high-confidence solutions
        checked = confidence >= 0.7

        choices.append(questionary.Choice(
            title=title,
            value=sol['name'],
            checked=checked
        ))

    # Add separator and options
    choices.append(questionary.Separator("─" * 50))

    if round_num == 1:
        choices.append(questionary.Choice(
            "🔍 Find more relevant solutions (AI web search)...",
            value="__FIND_MORE__",
            checked=False
        ))

    choices.append(questionary.Choice(
        "✅ Approve all solutions above",
        value="__APPROVE_ALL__",
        checked=False
    ))

    round_label = "" if round_num == 1 else f" (Round {round_num})"

    try:
        selected = questionary.checkbox(
            f"Select solutions for '{keyword}'{round_label}:",
            choices=choices,
            style=BRAND_STYLE,
            instruction="(Space to toggle, Enter to confirm)"
        ).ask()

        if selected is None:
            # User cancelled
            return {'approved': [], 'rejected': [], 'find_more': False}

        # Handle special options
        find_more = "__FIND_MORE__" in selected
        approve_all = "__APPROVE_ALL__" in selected

        # Remove special options from selection
        selected = [s for s in selected if not s.startswith("__")]

        if approve_all:
            # Approve all solutions
            approved = [sol['name'] for sol in solutions]
            rejected = []
        else:
            approved = selected
            rejected = [sol['name'] for sol in solutions if sol['name'] not in selected]

        return {
            'approved': approved,
            'rejected': rejected,
            'find_more': find_more
        }

    except KeyboardInterrupt:
        return {'approved': [], 'rejected': [], 'find_more': False}


def prompt_competitor_strategy() -> Optional[str]:
    """Ask user how they want to specify competitors.

    Returns one of:
    - 'manual': User will type competitors
    - 'ai': Let AI discover competitors
    - 'both': AI discovers + user can add more
    - None: User cancelled
    """
    if not _is_interactive():
        return 'ai'  # Default to AI discovery in non-interactive

    choices = [
        questionary.Choice(
            "🤖 Let AI discover competitors (SERP + web search)",
            value="ai"
        ),
        questionary.Choice(
            "✏️  Enter competitors manually",
            value="manual"
        ),
        questionary.Choice(
            "🔄 Both: AI discovers + I'll add more",
            value="both"
        ),
    ]

    try:
        return questionary.select(
            "How do you want to specify competitors?",
            choices=choices,
            style=BRAND_STYLE
        ).ask()
    except KeyboardInterrupt:
        return None


def prompt_manual_competitors(existing: list = None) -> list:
    """Text input for manual competitor entry.

    Args:
        existing: Optional list of AI-discovered competitor names to show

    Returns:
        List of competitor names (deduped, stripped)
    """
    if not _is_interactive():
        return existing or []

    existing_str = ', '.join(existing) if existing else ''

    try:
        result = questionary.text(
            "Enter competitors (comma-separated):",
            default=existing_str,
            validate=lambda x: len(x.strip()) >= 2 or "Enter at least one competitor",
            style=BRAND_STYLE
        ).ask()

        if not result:
            return existing or []

        # Parse comma-separated, strip whitespace, deduplicate
        competitors = [c.strip() for c in result.split(',') if c.strip()]
        unique_competitors = list(dict.fromkeys(competitors))  # Preserve order, remove dupes

        # Warn about vague/category-like entries
        from rich.console import Console
        console = Console()
        vague_patterns = ['open source', 'generic', 'any', 'various', 'multiple', 'free', 'paid']

        for name in unique_competitors:
            if any(pattern in name.lower() for pattern in vague_patterns):
                console.print(f"[yellow]⚠ '{name}' looks like a category, not a specific product.[/yellow]")
                console.print(f"[dim]  Tip: Use specific product names (e.g., 'Claude MCP' not 'open source MCPs')[/dim]")

        return unique_competitors

    except KeyboardInterrupt:
        return existing or []


def prompt_confirm_competitors(competitors: list, keyword: str) -> dict:
    """MANDATORY confirmation of competitors before generation.

    This ALWAYS runs and shows the competitors table with choices.

    Args:
        competitors: List of dicts with {name, source, confidence}
        keyword: The target keyword

    Returns:
        Dict with:
        - proceed: True to continue with listed competitors
        - add_more: True to add more competitors manually
        - find_alternatives: True to run AI discovery again
        - cancel: True to abort
        - competitors: Final list of competitor names
    """
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()

    # Display table of competitors
    table = Table(
        title=f"[bold cyan]Competitors for '{keyword}'[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("#", justify="center", width=3)
    table.add_column("Competitor", style="bold white", width=30)
    table.add_column("Source", justify="center", width=15)
    table.add_column("Confidence", justify="center", width=12)

    for i, comp in enumerate(competitors, 1):
        # Handle both dict and string formats
        if isinstance(comp, dict):
            name = comp.get('name', str(comp))
            source = comp.get('source', 'Unknown')
            confidence = comp.get('confidence', 0.8)
        else:
            name = str(comp)
            source = 'Manual'
            confidence = 1.0

        if confidence >= 0.8:
            conf_str = "[green]✓ High[/green]"
        elif confidence >= 0.5:
            conf_str = "[yellow]◐ Medium[/yellow]"
        else:
            conf_str = "[red]⚠ Low[/red]"

        # Source styling
        if source in ['Manual', 'Manual (--comp)']:
            source_str = f"[cyan]{source}[/cyan]"
        elif source == 'SERP':
            source_str = "[magenta]SERP[/magenta]"
        elif source == 'Web Search':
            source_str = "[blue]Web Search[/blue]"
        else:
            source_str = f"[dim]{source}[/dim]"

        table.add_row(str(i), name, source_str, conf_str)

    console.print()
    console.print(table)
    console.print()

    if not _is_interactive():
        # Non-interactive: auto-proceed
        return {
            'proceed': True,
            'add_more': False,
            'find_alternatives': False,
            'cancel': False,
            'competitors': [c['name'] if isinstance(c, dict) else c for c in competitors]
        }

    # Confirmation choices
    choices = [
        questionary.Choice(
            "✅ Proceed with these competitors",
            value="proceed"
        ),
        questionary.Choice(
            "✏️  Add more competitors manually",
            value="add_more"
        ),
        questionary.Choice(
            "🔍 Find alternatives (AI web search)",
            value="find_alternatives"
        ),
        questionary.Choice(
            "❌ Cancel generation",
            value="cancel"
        ),
    ]

    try:
        result = questionary.select(
            "What would you like to do?",
            choices=choices,
            style=BRAND_STYLE
        ).ask()

        if result is None:
            result = "cancel"

        return {
            'proceed': result == 'proceed',
            'add_more': result == 'add_more',
            'find_alternatives': result == 'find_alternatives',
            'cancel': result == 'cancel',
            'competitors': [c['name'] if isinstance(c, dict) else c for c in competitors]
        }

    except KeyboardInterrupt:
        return {
            'proceed': False,
            'add_more': False,
            'find_alternatives': False,
            'cancel': True,
            'competitors': []
        }
