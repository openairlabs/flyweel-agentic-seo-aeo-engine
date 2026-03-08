"""Progress Manager for CLI

Provides Rich progress bars and phase tracking for the generation pipeline.
Gracefully degrades in non-TTY environments.
"""
import sys
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.console import Console

from .output import OutputManager, OutputMode


@dataclass
class PhaseConfig:
    """Configuration for a pipeline phase"""
    name: str
    steps: int = 1
    description: str = ""


# Pipeline phases in order
PIPELINE_PHASES: Dict[str, PhaseConfig] = {
    'context': PhaseConfig('Loading Context', steps=1, description='Extracting brand context from repo'),
    'research': PhaseConfig('Research', steps=4, description='SERP analysis & community mining'),
    'generation': PhaseConfig('Generation', steps=5, description='Research → Generate → Polish → Optimize → Complete'),
    'polishing': PhaseConfig('Polishing', steps=3, description='Edit, Polish & Optimize'),
    'formatting': PhaseConfig('Formatting', steps=1, description='Astro MDX formatting'),
}


class ProgressManager:
    """Track progress through generation phases

    Provides context managers for phase tracking with automatic
    timing and status updates.
    """

    def __init__(
        self,
        output: Optional[OutputManager] = None,
        console: Optional[Console] = None
    ):
        """Initialize progress manager

        Args:
            output: OutputManager for mode detection
            console: Rich Console for output
        """
        self.output = output or OutputManager()
        self.console = console or Console()
        self._is_tty = sys.stdout.isatty()

        # Phase tracking
        self._current_phase: Optional[str] = None
        self._phase_start: Optional[datetime] = None
        self._phase_times: Dict[str, float] = {}

        # Progress bar state
        self._progress: Optional[Progress] = None
        self._task_id: Optional[int] = None

    def _can_use_rich(self) -> bool:
        """Check if we can use Rich progress bars"""
        return (
            self.output.mode == OutputMode.RICH
            and self._is_tty
            and self.console is not None
        )

    @contextmanager
    def phase(self, phase_key: str, description: Optional[str] = None):
        """Context manager for tracking a pipeline phase

        Args:
            phase_key: Key from PIPELINE_PHASES
            description: Optional override description

        Yields:
            self for chaining
        """
        config = PIPELINE_PHASES.get(phase_key, PhaseConfig(phase_key))
        desc = description or config.description or config.name

        self._current_phase = phase_key
        self._phase_start = datetime.now()

        if self._can_use_rich():
            # Start spinner for this phase
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=20),
                TimeElapsedColumn(),
                console=self.console,
                transient=True,
            ) as progress:
                self._progress = progress
                self._task_id = progress.add_task(desc, total=config.steps)
                try:
                    yield self
                finally:
                    # Complete the task
                    progress.update(self._task_id, completed=config.steps)
        else:
            # Non-TTY mode - just log
            if self.output.mode == OutputMode.PLAIN:
                print(f"[PHASE] {config.name}: {desc}")
            try:
                yield self
            finally:
                pass

        # Record timing
        elapsed = (datetime.now() - self._phase_start).total_seconds()
        self._phase_times[phase_key] = elapsed

        # Log completion
        if self._can_use_rich():
            self.console.print(f"[green]✓[/green] {config.name} ({elapsed:.1f}s)")
        elif self.output.mode == OutputMode.PLAIN:
            print(f"[DONE] {config.name} ({elapsed:.1f}s)")

        self._current_phase = None
        self._phase_start = None

    def update(self, message: str, advance: int = 0) -> None:
        """Update current phase progress

        Args:
            message: Status message
            advance: Steps to advance (0 for message only)
        """
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                description=message,
                advance=advance
            )

    @contextmanager
    def spinner(self, message: str):
        """Simple spinner for single operations

        Args:
            message: Spinner message

        Yields:
            None
        """
        if self._can_use_rich():
            with Progress(
                SpinnerColumn(),
                TextColumn("[dim]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                progress.add_task(message, total=None)
                yield
        else:
            if self.output.mode == OutputMode.PLAIN:
                print(f"[...] {message}")
            yield

    @contextmanager
    def full_pipeline(self):
        """Context manager for full pipeline tracking

        Shows overall progress across all phases.

        Yields:
            self for chaining
        """
        total_phases = len(PIPELINE_PHASES)
        completed = 0

        if self._can_use_rich():
            self.console.print()
            self.console.print("[bold cyan]Starting generation pipeline...[/bold cyan]")
            self.console.print()

        yield self

        # Show summary
        total_time = sum(self._phase_times.values())
        if self._can_use_rich():
            self.console.print()
            self.console.print(f"[bold green]Pipeline complete[/bold green] ({total_time:.1f}s)")
        elif self.output.mode == OutputMode.PLAIN:
            print(f"\n[COMPLETE] Pipeline finished in {total_time:.1f}s")

    def get_phase_times(self) -> Dict[str, float]:
        """Get recorded phase times

        Returns:
            Dict mapping phase keys to elapsed seconds
        """
        return self._phase_times.copy()


class ProgressCallback:
    """Callback wrapper for passing progress updates to core modules

    Allows core generation logic to report progress without
    direct coupling to CLI.
    """

    def __init__(self, manager: ProgressManager):
        """Initialize callback

        Args:
            manager: ProgressManager instance
        """
        self._manager = manager

    def __call__(self, message: str, advance: int = 0) -> None:
        """Report progress update

        Args:
            message: Status message
            advance: Steps to advance
        """
        self._manager.update(message, advance)
