"""Rich Output Manager for CLI

Provides unified output handling with three modes:
- RICH: Beautiful terminal output with panels, tables, colors
- JSON: Structured JSON for automation/CI
- PLAIN: Simple text for pipes and logs
"""
import json
import sys
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich import box


class OutputMode(Enum):
    """Output mode for CLI"""
    RICH = "rich"
    JSON = "json"
    PLAIN = "plain"


class OutputManager:
    """Unified output handling with mode detection

    Automatically detects TTY for rich output, falls back to plain for pipes.
    JSON mode can be forced for automation.
    """

    def __init__(self, mode: Optional[OutputMode] = None):
        """Initialize output manager

        Args:
            mode: Force specific output mode, or auto-detect if None
        """
        self.console = Console()
        self.mode = mode or self._detect_mode()
        self._start_time = datetime.now()
        self._json_logs: List[Dict] = []

    def _detect_mode(self) -> OutputMode:
        """Auto-detect output mode based on terminal"""
        if not sys.stdout.isatty():
            return OutputMode.PLAIN
        return OutputMode.RICH

    def _is_tty(self) -> bool:
        """Check if running in TTY"""
        return sys.stdout.isatty()

    def get_elapsed(self) -> float:
        """Get elapsed time since start"""
        return (datetime.now() - self._start_time).total_seconds()

    # ─────────────────────────────────────────────────────────────────
    # Basic Messages
    # ─────────────────────────────────────────────────────────────────

    def info(self, message: str, data: Optional[Dict] = None) -> None:
        """Info message"""
        if self.mode == OutputMode.JSON:
            self._log("info", message, data)
        elif self.mode == OutputMode.PLAIN:
            print(f"[INFO] {message}")
        else:
            self.console.print(f"[dim]ℹ[/dim] {message}")

    def success(self, message: str, data: Optional[Dict] = None) -> None:
        """Success message"""
        if self.mode == OutputMode.JSON:
            self._log("success", message, data)
        elif self.mode == OutputMode.PLAIN:
            print(f"[OK] {message}")
        else:
            self.console.print(f"[green]✓[/green] {message}")

    def warning(self, message: str, data: Optional[Dict] = None) -> None:
        """Warning message"""
        if self.mode == OutputMode.JSON:
            self._log("warning", message, data)
        elif self.mode == OutputMode.PLAIN:
            print(f"[WARN] {message}")
        else:
            self.console.print(f"[yellow]⚠[/yellow] {message}")

    def error(self, message: str, data: Optional[Dict] = None) -> None:
        """Error message"""
        if self.mode == OutputMode.JSON:
            self._log("error", message, data)
        elif self.mode == OutputMode.PLAIN:
            print(f"[ERROR] {message}", file=sys.stderr)
        else:
            self.console.print(f"[red]✗[/red] {message}")

    def _log(self, level: str, message: str, data: Optional[Dict] = None) -> None:
        """Add to JSON log buffer"""
        self._json_logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data,
        })

    def competitor_error(self, message: str, recoverable: bool = True) -> None:
        """Display competitor-related error prominently with fallback hint

        Args:
            message: The error message
            recoverable: If True, show fallback hint; if False, show as fatal
        """
        if self.mode == OutputMode.JSON:
            self._log("competitor_error" if not recoverable else "competitor_warning", message)
        elif self.mode == OutputMode.PLAIN:
            prefix = "[WARN]" if recoverable else "[ERROR]"
            print(f"{prefix} {message}")
            if recoverable:
                print("  Falling back to manual input...")
        else:
            if recoverable:
                self.console.print(f"[yellow]⚠ {message}[/yellow]")
                self.console.print("[dim]  Falling back to manual input...[/dim]")
            else:
                self.console.print(f"[red]✗ {message}[/red]")

    # ─────────────────────────────────────────────────────────────────
    # Panels & Tables
    # ─────────────────────────────────────────────────────────────────

    def config_panel(self, config: Dict[str, Any]) -> None:
        """Display configuration panel before generation

        Args:
            config: Dict with keyword, style, context_source, etc.
        """
        if self.mode == OutputMode.JSON:
            print(json.dumps({"type": "config", "data": config}))
            return

        if self.mode == OutputMode.PLAIN:
            print("\n--- Generation Config ---")
            for k, v in config.items():
                print(f"  {k}: {v}")
            print("-------------------------\n")
            return

        # Rich mode
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Setting", style="cyan", width=20)
        table.add_column("Value", style="white")

        table.add_row("Keyword", f"[bold]{config.get('keyword', '')}[/bold]")
        table.add_row("Style", config.get('style', 'standard'))
        table.add_row("Context Source", config.get('context_source', 'repo'))

        if config.get('skip_community'):
            table.add_row("Community Research", "[dim]Skipped[/dim]")
        else:
            table.add_row("Community Research", "[green]Enabled[/green]")

        # Three-tier Brand mention mode display
        brand_mode = config.get('brand_mode', 'full')
        brand_labels = {
            'none': '[dim]None[/dim] (Educational only)',
            'limited': '[yellow]Limited[/yellow] (2-3 mentions)',
            'full': '[green]Full Integration[/green]'
        }
        table.add_row("Brand Mentions", brand_labels.get(brand_mode, '[green]Full Integration[/green]'))

        publish_target = config.get('publish_target', 'local')
        if publish_target == 'astro':
            table.add_row("Output", "[cyan]→ astro-site/content/blog/[/cyan]")
        else:
            table.add_row("Output", "[dim]→ output/generations/[/dim]")

        self.console.print(Panel(
            table,
            title="[bold cyan]Generation Config[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        ))

    def validation_report(self, result: Dict[str, Any]) -> None:
        """Display validation report after generation

        Args:
            result: Dict with validation checks and metrics
        """
        if self.mode == OutputMode.JSON:
            print(json.dumps({"type": "validation", "data": result}))
            return

        if self.mode == OutputMode.PLAIN:
            print("\n--- Validation Report ---")
            print(f"  Valid: {result.get('valid', False)}")
            print(f"  Word Count: {result.get('word_count', 0)}")
            if result.get('errors'):
                print(f"  Errors: {result['errors']}")
            if result.get('warnings'):
                print(f"  Warnings: {result['warnings']}")
            print("-------------------------\n")
            return

        # Rich mode
        table = Table(show_header=True, box=box.SIMPLE)
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center", width=8)
        table.add_column("Details")

        # Build checks from result
        checks = [
            ("Frontmatter", result.get('frontmatter_valid', True), ""),
            ("Word Count", result.get('word_count', 0) >= 1000,
             f"{result.get('word_count', 0):,} words"),
            ("SEO Title", result.get('title_valid', True),
             f"{result.get('title_length', 0)} chars"),
            ("Meta Description", result.get('description_valid', True),
             f"{result.get('description_length', 0)} chars"),
            ("Internal Links", result.get('internal_link_count', 0) >= 3,
             f"{result.get('internal_link_count', 0)} links"),
            ("FAQ Section", result.get('has_faq', False), ""),
        ]

        for name, passed, details in checks:
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(name, status, details)

        # Add warnings if any
        warnings = result.get('warnings', [])
        if warnings:
            self.console.print()
            for warning in warnings[:5]:
                self.console.print(f"[yellow]⚠[/yellow] {warning}")

        self.console.print(Panel(
            table,
            title="[bold cyan]Validation Report[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        ))

    def generation_result(
        self,
        title: str,
        word_count: int,
        generation_time: float,
        slug: str
    ) -> None:
        """Display generation result summary

        Args:
            title: Generated content title
            word_count: Final word count
            generation_time: Time taken in seconds
            slug: Content slug
        """
        if self.mode == OutputMode.JSON:
            print(json.dumps({
                "type": "result",
                "title": title,
                "word_count": word_count,
                "generation_time": generation_time,
                "slug": slug,
            }))
            return

        if self.mode == OutputMode.PLAIN:
            print(f"\n[DONE] {title}")
            print(f"  Words: {word_count}")
            print(f"  Time: {generation_time:.1f}s")
            print(f"  Slug: {slug}\n")
            return

        # Rich mode
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Metric", style="cyan", width=15)
        table.add_column("Value", style="white")

        table.add_row("Title", f"[bold]{title[:50]}...[/bold]" if len(title) > 50 else f"[bold]{title}[/bold]")
        table.add_row("Word Count", f"[green]{word_count:,}[/green] words")
        table.add_row("Generation Time", f"{generation_time:.1f}s")
        table.add_row("Slug", f"[dim]{slug}[/dim]")

        self.console.print(Panel(
            table,
            title="[bold green]Generation Complete[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        ))

    def article_preview(self, content: str, title: str = "Generated Article") -> None:
        """Display full article content rendered as Markdown

        Args:
            content: The full MDX/Markdown content to display
            title: Title for the preview panel
        """
        if not content:
            return

        if self.mode == OutputMode.JSON:
            # JSON mode: content already in result, just log preview event
            self._log("preview", "Article content rendered", {"title": title})
            return

        if self.mode == OutputMode.PLAIN:
            # Plain mode: print with separators
            print("\n" + "=" * 60)
            print(f"ARTICLE PREVIEW: {title}")
            print("=" * 60)
            print(content)
            print("=" * 60 + "\n")
            return

        # Rich mode: render as Markdown in a panel
        self.console.print()
        md = Markdown(content)
        self.console.print(Panel(
            md,
            title=f"[bold blue]📄 {title}[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2),
        ))
        self.console.print()

    def publish_result(self, result: Dict[str, Any]) -> None:
        """Display publish result

        Args:
            result: Result from AstroPublisher
        """
        if self.mode == OutputMode.JSON:
            print(json.dumps({"type": "publish", "data": result}))
            return

        if result.get('success'):
            path = result.get('path', '')

            if self.mode == OutputMode.PLAIN:
                print(f"[PUBLISHED] {path}")
                if result.get('hero_image_needed'):
                    print(f"[INFO] Hero image needed: {result.get('hero_image_path')}")
                return

            # Rich mode
            self.console.print()
            self.console.print(f"[green]✓ Published to:[/green] {path}")

            if result.get('hero_image_needed'):
                self.console.print(f"[yellow]⚠ Hero image needed:[/yellow] {result.get('hero_image_path')}")

            if result.get('draft'):
                self.console.print("[dim]  Status: draft (set draft: false to publish)[/dim]")
        else:
            error = result.get('error', 'Unknown error')
            if self.mode == OutputMode.PLAIN:
                print(f"[ERROR] Publish failed: {error}")
            else:
                self.console.print(f"[red]✗ Publish failed:[/red] {error}")

    def final_result(self, data: Dict[str, Any], success: bool = True) -> None:
        """Output final structured result (for JSON mode)

        Args:
            data: Result data
            success: Overall success status
        """
        if self.mode == OutputMode.JSON:
            output = {
                "success": success,
                "result": data,
                "elapsed_seconds": self.get_elapsed(),
                "logs": self._json_logs,
            }
            print(json.dumps(output, indent=2, default=str))
        elif self.mode == OutputMode.PLAIN:
            status = "SUCCESS" if success else "FAILED"
            print(f"\n[{status}] Generation completed in {self.get_elapsed():.1f}s")
        # Rich mode handled by other methods

    def solutions_panel(self, solutions: List[Dict[str, Any]], keyword: str) -> None:
        """Display extracted solutions in a rich table

        Args:
            solutions: List of solution dicts with {name, url, source, confidence, why_relevant}
            keyword: The keyword being researched
        """
        if self.mode == OutputMode.JSON:
            print(json.dumps({
                "type": "solutions",
                "keyword": keyword,
                "solutions": solutions,
            }))
            return

        if self.mode == OutputMode.PLAIN:
            print(f"\n--- Solutions Found for '{keyword}' ---")
            for i, sol in enumerate(solutions, 1):
                conf = sol.get('confidence', 0)
                conf_str = f"[{conf:.0%}]"
                print(f"  {i}. {sol['name']} ({sol.get('source', 'Unknown')}) {conf_str}")
            print("----------------------------------------\n")
            return

        # Rich mode - beautiful table
        table = Table(
            show_header=True,
            box=box.ROUNDED,
            header_style="bold cyan",
            title_style="bold",
        )
        table.add_column("#", justify="center", width=3)
        table.add_column("Solution", style="white", width=25)
        table.add_column("Source", justify="center", width=10)
        table.add_column("Confidence", justify="center", width=12)
        table.add_column("Relevance", width=40)

        for i, sol in enumerate(solutions, 1):
            confidence = sol.get('confidence', 0.5)

            # Confidence with color coding
            if confidence >= 0.85:
                conf_style = "[green]✓ High[/green]"
            elif confidence >= 0.7:
                conf_style = "[yellow]◐ Medium[/yellow]"
            else:
                conf_style = "[red]⚠ Low[/red]"

            # Source badge
            source = sol.get('source', 'Unknown')
            if source == 'SERP':
                source_style = "[cyan]SERP[/cyan]"
            elif source == 'Reddit':
                source_style = "[orange1]Reddit[/orange1]"
            elif source == 'Quora':
                source_style = "[blue]Quora[/blue]"
            elif source == 'Web Search':
                source_style = "[magenta]Web[/magenta]"
            else:
                source_style = f"[dim]{source}[/dim]"

            why = sol.get('why_relevant', '')
            if len(why) > 50:
                why = why[:47] + "..."

            table.add_row(
                str(i),
                f"[bold]{sol['name']}[/bold]",
                source_style,
                conf_style,
                why
            )

        self.console.print()
        self.console.print(Panel(
            table,
            title=f"[bold cyan]📋 Solutions for '{keyword}'[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        ))
        self.console.print()

    # ─────────────────────────────────────────────────────────────────
    # Separators & Headers
    # ─────────────────────────────────────────────────────────────────

    def header(self, text: str) -> None:
        """Display section header"""
        if self.mode == OutputMode.RICH:
            self.console.print()
            self.console.print(f"[bold cyan]━━━ {text} ━━━[/bold cyan]")
            self.console.print()
        elif self.mode == OutputMode.PLAIN:
            print(f"\n=== {text} ===\n")

    def newline(self) -> None:
        """Print newline"""
        if self.mode != OutputMode.JSON:
            print()
