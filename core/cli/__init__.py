"""Interactive CLI for V2 Brand Content Engine

Provides Click-based interactive mode with Rich output and Questionary prompts.
Activated via: python generate.py -i / --interactive
"""
from .app import cli, interactive_generate
from .output import OutputManager, OutputMode
from .progress import ProgressManager
from .prompts import (
    prompt_keyword,
    prompt_style,
    prompt_publish_decision,
    prompt_draft_status,
    prompt_overwrite,
)

__all__ = [
    'cli',
    'interactive_generate',
    'OutputManager',
    'OutputMode',
    'ProgressManager',
    'prompt_keyword',
    'prompt_style',
    'prompt_publish_decision',
    'prompt_draft_status',
    'prompt_overwrite',
]
