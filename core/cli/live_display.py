"""Live status display for content generation pipeline

Provides real-time updating status dashboard using Rich Live display.
"""
from typing import List, Optional
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich import box


class LiveStatusDisplay:
    """Real-time status dashboard for generation pipeline

    Displays a live-updating table showing current phase and task statuses.

    Example output:
        ┌─────────────────────── Research in Progress ────────────────────────┐
        │ SERP Analysis       ✓ Complete    12 questions, 54 citations  2.8s │
        │ Reddit Mining       ⏳ Running     Query 7/10                  ...  │
        │ Quora Extraction    ⏸️  Pending    —                           —    │
        │ Quality Filter      ⏸️  Pending    —                           —    │
        └──────────────────────────────────────────────────────────────────────┘
    """

    def __init__(self):
        """Initialize empty display"""
        self.tasks: List[List[str]] = []
        self.current_phase: Optional[str] = None
        self._live: Optional[Live] = None

    def set_phase(self, phase_name: str) -> None:
        """Set the current phase name (shown in panel title)

        Args:
            phase_name: Human-readable phase name (e.g., "Research", "Content Generation")
        """
        self.current_phase = phase_name

    def add_task(self, name: str) -> None:
        """Add a task to the dashboard

        Args:
            name: Task name (e.g., "SERP Analysis", "Reddit Mining")
        """
        self.tasks.append([name, "⏸️  Pending", "—", "—"])

    def update_task(
        self,
        name: str,
        status: str,
        detail: str = "",
        time: str = ""
    ) -> None:
        """Update task status

        Args:
            name: Task name to update
            status: Status emoji/text (e.g., "⏳ Running", "✓ Complete")
            detail: Detail text (e.g., "12 questions found", "Query 5/10")
            time: Time elapsed (e.g., "2.3s", "...")
        """
        for task in self.tasks:
            if task[0] == name:
                task[1] = status
                task[2] = detail or "—"
                task[3] = time or "—"
                break

    def start_task(self, name: str, detail: str = "") -> None:
        """Mark task as running

        Args:
            name: Task name
            detail: Optional detail text (e.g., "Perplexity sonar-deep-research")
        """
        self.update_task(name, "⏳ Running", detail, "...")

    def complete_task(self, name: str, detail: str, time: str) -> None:
        """Mark task as complete

        Args:
            name: Task name
            detail: Summary of what was accomplished
            time: Total time elapsed (e.g., "2.3s")
        """
        self.update_task(name, "✓ Complete", detail, time)

    def skip_task(self, name: str, reason: str = "Skipped") -> None:
        """Mark task as skipped

        Args:
            name: Task name
            reason: Why it was skipped
        """
        self.update_task(name, "⊘ Skipped", reason, "—")

    def generate_table(self) -> Panel:
        """Generate Rich table for display

        Returns:
            Rich Panel containing status table
        """
        table = Table(
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 1),
            expand=True
        )
        table.add_column("Task", style="bold", width=20)
        table.add_column("Status", width=12)
        table.add_column("Detail", style="dim", no_wrap=False)
        table.add_column("Time", width=6, justify="right", style="cyan")

        for task in self.tasks:
            table.add_row(*task)

        title = f"[bold]{self.current_phase or 'Processing'}[/bold]"
        return Panel(table, title=title, border_style="blue", expand=False)

    def start_live(self, refresh_per_second: int = 2) -> Live:
        """Start live display

        Args:
            refresh_per_second: How often to refresh (default: 2)

        Returns:
            Live context manager - use with 'with' statement
        """
        self._live = Live(
            self.generate_table(),
            refresh_per_second=refresh_per_second,
            transient=True  # Clear after completion
        )
        return self._live

    def refresh(self) -> None:
        """Refresh the live display (if active)"""
        if self._live and self._live.is_started:
            self._live.update(self.generate_table())

    def clear_tasks(self) -> None:
        """Clear all tasks (for starting new phase)"""
        self.tasks = []


def create_research_display() -> LiveStatusDisplay:
    """Create pre-configured display for research phase

    Returns:
        LiveStatusDisplay with research tasks added
    """
    display = LiveStatusDisplay()
    display.set_phase("Research")
    display.add_task("SERP Analysis")
    display.add_task("Reddit Mining")
    display.add_task("Quora Extraction")
    display.add_task("Quality Filter")
    return display


def create_generation_display() -> LiveStatusDisplay:
    """Create pre-configured display for generation phase

    Returns:
        LiveStatusDisplay with generation tasks added
    """
    display = LiveStatusDisplay()
    display.set_phase("Content Generation")
    display.add_task("Part 1/3")
    display.add_task("Part 2/3")
    display.add_task("Part 3/3")
    return display


def create_polish_display() -> LiveStatusDisplay:
    """Create pre-configured display for polish phase

    Returns:
        LiveStatusDisplay with polish tasks added
    """
    display = LiveStatusDisplay()
    display.set_phase("Refinement")
    display.add_task("Edit Pass")
    display.add_task("Polish Pass")
    display.add_task("Heading SEO")
    display.add_task("Title SEO")
    return display
