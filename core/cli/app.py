"""Click CLI Application for V2 Brand Content Engine

Provides interactive mode with beautiful Rich output and
Questionary prompts for content generation.
"""
import asyncio
import sys
from functools import wraps
from pathlib import Path
from typing import Optional
import click

# Allow nested event loops (questionary uses asyncio internally)
import nest_asyncio
nest_asyncio.apply()

from .output import OutputManager, OutputMode
from .progress import ProgressManager
from .prompts import (
    prompt_keyword,
    prompt_style,
    prompt_publish_decision,
    prompt_draft_status,
    prompt_overwrite,
    prompt_continue_generation,
    prompt_research_options,
    prompt_brand_mentions,
    prompt_brand_mode,
    prompt_custom_slug,
    prompt_solution_count,
    prompt_icp_injection,
    prompt_solution_selection,
    prompt_competitor_strategy,
    prompt_manual_competitors,
    prompt_confirm_competitors,
)


def async_command(f):
    """Decorator to run async Click commands with proper cleanup"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = asyncio.run(f(*args, **kwargs))
            if isinstance(result, int):
                sys.exit(result)
            return result
        except KeyboardInterrupt:
            click.echo("\n[Cancelled]")
            sys.exit(130)
        except SystemExit:
            raise
        except Exception as e:
            click.echo(f"[Error] {e}", err=True)
            sys.exit(1)
    return wrapper


async def _handle_competitor_selection(
    keyword: str,
    style: str,
    competitors_flag: Optional[str],
    output: 'OutputManager',
    progress: 'ProgressManager'
) -> list:
    """Handle competitor selection with multiple input methods.

    This function GUARANTEES that:
    1. User always sees what competitors will be used
    2. User can always modify the list
    3. Failures are visible, not silent

    Args:
        keyword: Target keyword
        style: Content style
        competitors_flag: Value of --comp flag (comma-separated)
        output: Output manager for display
        progress: Progress manager for spinners

    Returns:
        List of approved competitor names
    """
    from ..ai_router import SmartAIRouter

    ai_router = SmartAIRouter()
    competitors = []

    # ─────────────────────────────────────────────────────────────────────
    # Path 1: --comp flag provided (explicit competitors)
    # ─────────────────────────────────────────────────────────────────────
    if competitors_flag:
        # Parse comma-separated
        competitors = [
            {'name': c.strip(), 'source': 'Manual (--comp)', 'confidence': 1.0}
            for c in competitors_flag.split(',')
            if c.strip()
        ]
        output.success(f"Using {len(competitors)} competitors from --comp flag")

    # ─────────────────────────────────────────────────────────────────────
    # Path 2: Interactive mode - ask user how to specify competitors
    # ─────────────────────────────────────────────────────────────────────
    else:
        strategy = prompt_competitor_strategy()

        if strategy is None:
            raise KeyboardInterrupt("User cancelled competitor selection")

        if strategy == 'manual':
            # User types competitors directly
            names = prompt_manual_competitors()
            if not names:
                output.competitor_error("No competitors entered", recoverable=True)
                names = prompt_manual_competitors()
            competitors = [
                {'name': name, 'source': 'Manual', 'confidence': 1.0}
                for name in names
            ]

        elif strategy == 'ai':
            # AI discovers competitors
            with progress.phase('discovery', 'Finding competitors via AI...'):
                competitors = await ai_router.discover_competitors_intelligent(
                    keyword=keyword,
                    count=10
                )
            if not competitors:
                output.competitor_error("AI couldn't find competitors", recoverable=True)
                names = prompt_manual_competitors()
                competitors = [
                    {'name': name, 'source': 'Manual (fallback)', 'confidence': 1.0}
                    for name in names
                ]

        elif strategy == 'both':
            # AI first, then user can add more
            with progress.phase('discovery', 'Finding competitors via AI...'):
                competitors = await ai_router.discover_competitors_intelligent(
                    keyword=keyword,
                    count=8
                )

            # Show what AI found and let user add more
            existing_names = [c['name'] for c in competitors]
            output.info(f"AI found {len(competitors)} competitors. You can add more:")
            added_names = prompt_manual_competitors(existing_names)

            # Merge manual additions (new ones only)
            for name in added_names:
                if name not in existing_names:
                    competitors.append({
                        'name': name,
                        'source': 'Manual',
                        'confidence': 1.0
                    })

    # ─────────────────────────────────────────────────────────────────────
    # MANDATORY: Confirmation loop (user can refine until satisfied)
    # ─────────────────────────────────────────────────────────────────────
    while True:
        if not competitors:
            output.error("No competitors specified. Cannot proceed.")
            names = prompt_manual_competitors()
            if not names:
                raise KeyboardInterrupt("No competitors provided")
            competitors = [
                {'name': name, 'source': 'Manual', 'confidence': 1.0}
                for name in names
            ]
            continue

        confirmation = prompt_confirm_competitors(competitors, keyword)

        if confirmation['cancel']:
            raise KeyboardInterrupt("User cancelled competitor selection")

        if confirmation['proceed']:
            break

        if confirmation['add_more']:
            existing_names = [c['name'] for c in competitors]
            added = prompt_manual_competitors(existing_names)
            for name in added:
                if name not in existing_names:
                    competitors.append({
                        'name': name,
                        'source': 'Manual',
                        'confidence': 1.0
                    })

        if confirmation['find_alternatives']:
            with progress.phase('discovery', 'Finding alternative competitors...'):
                existing_names = [c['name'] for c in competitors]
                new_competitors = await ai_router.discover_competitors_intelligent(
                    keyword=keyword,
                    existing_competitors=existing_names,
                    count=5
                )
                competitors.extend(new_competitors)
                if new_competitors:
                    output.success(f"Found {len(new_competitors)} additional competitors")
                else:
                    output.warning("Couldn't find more alternatives")

    # Log final selection
    final_names = [c['name'] for c in competitors]
    output.success(f"Proceeding with {len(final_names)} competitors")

    return final_names


@click.command()
@click.option('-k', '--keyword', help='Keyword to generate content for')
@click.option('--style', type=click.Choice([
    'standard', 'guide', 'comparison', 'research', 'news', 'category', 'top-compare', 'feature'
]), help='Content style')
@click.option('--solutions', type=click.Choice(['5', '8', '10', '15']), default='8',
              help='Number of solutions for top-compare style (5/8/10/15)')
@click.option('--nr', '--no-reddit', 'skip_community', is_flag=True,
              help='Skip Reddit/Quora research')
@click.option('--nrl', '--limited', 'limit_community', is_flag=True,
              help='Limited: 3 Reddit + 1 Quora')
@click.option('--nb', '--no-brand', 'no_brand', is_flag=True,
              help='No Brand brand mentions (educational only)')
@click.option('--lb', '--limited-brand', 'limited_brand', is_flag=True,
              help='Limited Brand mentions (2-3 highly natural mentions only)')
@click.option('--no-icp', '--skip-icp', 'skip_icp', is_flag=True,
              help='Skip ICP context (no industry-specific audience targeting)')
@click.option('--augment-serp/--no-augment-serp', 'augment_serp', default=True,
              help='Augment with SERP analysis (enabled by default, uses deep research for research style)')
@click.option('--gsc-check/--no-gsc-check', 'gsc_check', default=True,
              help='GSC cannibalization check (enabled by default)')
@click.option('--gsc-keywords/--no-gsc-keywords', 'gsc_keywords', default=True,
              help='GSC-derived keywords for title/H2 (enabled by default)')
@click.option('--min-tools', 'min_tools', type=int, default=12,
              help='Minimum tools for comparison content (default: 12)')
@click.option('--depth', type=click.Choice(['quick', 'standard', 'comprehensive']),
              default='standard', help='Content depth: quick/standard/comprehensive')
@click.option('--publish', 'auto_publish', is_flag=True,
              help='Auto-publish to astro-site (skip prompt)')
@click.option('--local', 'save_local', is_flag=True,
              help='Save locally only (skip prompt)')
@click.option('--no-draft', 'no_draft', is_flag=True,
              help='Publish without draft status')
@click.option('--json', 'json_output', is_flag=True,
              help='Output as JSON (for automation)')
@click.option('--comp', '--competitors', 'competitors',
              help='Comma-separated competitor names (e.g., "Windsor MCP, Pipeboard MCP")')
@click.option('--use-llama-polish', 'use_llama_polish', is_flag=True,
              help='Use Kimi K2 for polish instead of Qwen3 235B')
@click.option('--save-research', 'save_research', is_flag=True,
              help='Save research data to output folder')
@click.option('--output', 'output_dir', default='output',
              help='Output directory for local saves')
@click.option('--verbose', '-v', 'verbose', is_flag=True,
              help='Show detailed debug logs')
@click.pass_context
@async_command
async def interactive_generate(
    ctx,
    keyword: Optional[str],
    style: Optional[str],
    solutions: str,
    skip_community: bool,
    limit_community: bool,
    no_brand: bool,
    limited_brand: bool,
    skip_icp: bool,
    augment_serp: bool,
    gsc_check: bool,
    gsc_keywords: bool,
    min_tools: int,
    depth: str,
    auto_publish: bool,
    save_local: bool,
    no_draft: bool,
    json_output: bool,
    competitors: Optional[str],
    use_llama_polish: bool,
    save_research: bool,
    output_dir: str,
    verbose: bool,
):
    """Interactive content generation with prompts and progress

    Run without arguments for full interactive mode, or provide
    options to skip specific prompts.
    """
    # Configure logging (suppress noise unless --verbose)
    from ..generator import configure_logging
    configure_logging(verbose=verbose)

    # Initialize output manager
    mode = OutputMode.JSON if json_output else OutputMode.RICH
    output = OutputManager(mode=mode)

    # ─────────────────────────────────────────────────────────────────
    # Step 1: Gather inputs interactively
    # ─────────────────────────────────────────────────────────────────

    # Keyword
    if not keyword:
        keyword = prompt_keyword()
        if not keyword:
            output.error("No keyword provided. Exiting.")
            return 1

    # Style
    if not style:
        style = prompt_style()
        if not style:
            output.error("No style selected. Exiting.")
            return 1

    # Solution count for top-compare style
    solution_count = int(solutions)  # Convert from string
    if style == 'top-compare':
        solution_count = prompt_solution_count(default=solution_count)

    # Research options (if not already set)
    if not skip_community and not limit_community:
        research_opts = prompt_research_options()
        skip_community = research_opts.get('skip_community', False)
        limit_community = research_opts.get('limit_community', False)

    # Brand mentions - convert flags to brand_mode string
    # Priority: --nb > --lb > interactive prompt > default (full)
    if no_brand:
        brand_mode = 'none'
    elif limited_brand:
        brand_mode = 'limited'
    else:
        # If no flag provided, ask interactively with new three-tier prompt
        brand_mode = prompt_brand_mode()

    # ICP context injection (if not already skipped via flag)
    if not skip_icp:
        include_icp = prompt_icp_injection()
        skip_icp = not include_icp

    # ─────────────────────────────────────────────────────────────────
    # Step 2: Show config panel
    # ─────────────────────────────────────────────────────────────────

    # Map depth to solution count
    depth_to_solutions = {'quick': 8, 'standard': 12, 'comprehensive': 15}
    effective_solution_count = depth_to_solutions.get(depth, min_tools)
    if style == 'top-compare':
        effective_solution_count = solution_count

    config = {
        'keyword': keyword,
        'style': style,
        'context_source': 'astro-site repo',
        'skip_community': skip_community,
        'limit_community': limit_community,
        'brand_mode': brand_mode,
        'skip_icp': skip_icp,
        'gsc_check': gsc_check,
        'gsc_keywords': gsc_keywords,
        'depth': depth,
        'publish_target': 'astro' if auto_publish else ('local' if save_local else 'prompt'),
    }
    if style in ['top-compare', 'comparison', 'category']:
        config['solution_count'] = effective_solution_count
    output.config_panel(config)

    # Confirm before starting
    if not auto_publish and not save_local:
        if not prompt_continue_generation():
            output.info("Generation cancelled.")
            return 0

    # ─────────────────────────────────────────────────────────────────
    # Step 3: Run generation with progress tracking
    # ─────────────────────────────────────────────────────────────────

    progress = ProgressManager(output=output)

    try:
        result = await _run_generation(
            keyword=keyword,
            style=style,
            skip_community=skip_community,
            limit_community=limit_community,
            brand_mode=brand_mode,
            skip_icp=skip_icp,
            augment_serp=augment_serp,
            solution_count=effective_solution_count,
            gsc_check=gsc_check,
            gsc_keywords=gsc_keywords,
            progress=progress,
            output=output,
            competitors=competitors,
            use_llama_polish=use_llama_polish,
        )
    except Exception as e:
        output.error(f"Generation failed: {e}")
        return 1

    if not result.get('success'):
        output.error(f"Generation failed: {result.get('error', 'Unknown error')}")
        return 1

    # ─────────────────────────────────────────────────────────────────
    # Step 4: Show result
    # ─────────────────────────────────────────────────────────────────

    output.generation_result(
        title=result.get('title', 'Untitled'),
        word_count=result.get('metrics', {}).get('word_count', 0),
        generation_time=result.get('metrics', {}).get('generation_time', 0),
        slug=result.get('slug', ''),
    )

    # Display full article content for review
    output.article_preview(
        content=result.get('content', ''),
        title=result.get('title', 'Generated Article')
    )

    # ─────────────────────────────────────────────────────────────────
    # Step 5: Handle output decision
    # ─────────────────────────────────────────────────────────────────

    # Determine publish decision
    if auto_publish:
        decision = 'publish'
    elif save_local:
        decision = 'local'
    else:
        decision = prompt_publish_decision()
        if not decision:
            output.info("No output selected. Content discarded.")
            return 0

    if decision == 'publish':
        # Publish to astro-site
        publish_result = await _publish_to_astro(
            result=result,
            draft=not no_draft,
            output=output,
        )

        if publish_result.get('success'):
            output.publish_result(publish_result)
            output.success("Content published successfully!")
        else:
            output.error(f"Publish failed: {publish_result.get('error')}")
            # Fall back to local save
            output.info("Falling back to local save...")
            await _save_local(result, output, output_dir=output_dir, save_research=save_research)

    elif decision == 'local':
        # Save locally
        await _save_local(result, output, output_dir=output_dir, save_research=save_research)

    else:  # preview
        output.info("Content discarded (preview only).")

    # Final JSON output if needed
    output.final_result({
        'title': result.get('title'),
        'slug': result.get('slug'),
        'word_count': result.get('metrics', {}).get('word_count'),
        'decision': decision,
    })

    return 0


async def _run_generation(
    keyword: str,
    style: str,
    skip_community: bool,
    limit_community: bool,
    brand_mode: str,
    progress: ProgressManager,
    output: OutputManager,
    skip_icp: bool = False,
    augment_serp: bool = True,
    solution_count: Optional[int] = None,
    gsc_check: bool = False,
    gsc_keywords: bool = False,
    competitors: Optional[str] = None,
    use_llama_polish: bool = False,
) -> dict:
    """Run the content generation pipeline

    Args:
        keyword: Target keyword
        style: Content style
        skip_community: Skip Reddit/Quora
        limit_community: Limit community research
        brand_mode: Brand mention level - 'none' (--nb), 'limited' (--lb), 'full' (default)
        progress: ProgressManager for tracking
        output: OutputManager for messages
        skip_icp: Skip ICP context injection (generic audience)
        augment_serp: Augment with SERP analysis (uses deep research for research style)
        solution_count: Number of solutions for comparison content
        gsc_check: Run GSC cannibalization check before generation
        gsc_keywords: Use GSC-derived keywords for title/H2 optimization
        competitors: Comma-separated competitor names from --comp flag

    Returns:
        Result dict from ContentGenerator
    """
    from ..repo_extractor import RepoContextExtractor
    from ..generator import ContentGenerator

    # Phase 1: Load context from repo
    with progress.phase('context', 'Loading brand context from repo'):
        extractor = RepoContextExtractor()
        site_context = extractor.extract_context()
        output.info(f"Loaded {len(site_context.get('internal_links', {}))} internal links")

    # Initialize approved_solutions (will be set if comparison-style with interactive selection)
    approved_solutions = None

    # ─────────────────────────────────────────────────────────────────
    # COMPETITOR SELECTION for comparison/top-compare/category styles
    # Uses the new v2 bulletproof flow with --comp flag support
    # ─────────────────────────────────────────────────────────────────
    if style in ['comparison', 'top-compare', 'category']:
        approved_solutions = await _handle_competitor_selection(
            keyword=keyword,
            style=style,
            competitors_flag=competitors,
            output=output,
            progress=progress
        )

    # Phase 2-5: Generation (handled by ContentGenerator)
    with progress.phase('generation', 'Generating content with AI'):
        # Create generator with injected context
        generator = ContentGenerator()

        # Inject repo context
        generator._injected_context = site_context

        # Build generation kwargs
        gen_kwargs = {
            'skip_community': skip_community,
            'limit_community': limit_community,
            'brand_mode': brand_mode,
            'skip_icp': skip_icp,
            'augment_serp': augment_serp,
            'gsc_check': gsc_check,
            'gsc_keywords': gsc_keywords,
            'use_llama_polish': use_llama_polish,
        }

        # Add solution_count for comparison-style content
        if solution_count and style in ['top-compare', 'comparison', 'category']:
            gen_kwargs['solution_count'] = solution_count

        # Inject approved solutions if available
        if approved_solutions:
            gen_kwargs['approved_solutions'] = approved_solutions

        # Pass progress callback to generator for real-time updates
        from .progress import ProgressCallback
        progress_cb = ProgressCallback(progress)
        gen_kwargs['progress_callback'] = progress_cb

        # Run generation
        result = await generator.generate(keyword, style, **gen_kwargs)

    return result


async def _publish_to_astro(
    result: dict,
    draft: bool,
    output: OutputManager,
) -> dict:
    """Publish generated content to astro-site repo

    Args:
        result: Generation result with content
        draft: Set draft status
        output: OutputManager for messages

    Returns:
        Publisher result dict
    """
    from ..publisher import AstroPublisher

    publisher = AstroPublisher()
    content = result.get('content', '')
    slug = result.get('slug', '')

    # Check for existing file
    existing = publisher.get_existing_slugs()
    if slug in existing:
        if not prompt_overwrite(slug):
            # Let user choose different slug
            slug = prompt_custom_slug(slug)

    return publisher.publish(
        content=content,
        slug=slug,
        draft=draft,
        overwrite=True,
    )


async def _save_local(
    result: dict,
    output: OutputManager,
    output_dir: str = 'output',
    save_research: bool = False,
) -> None:
    """Save content to local output directory

    Args:
        result: Generation result
        output: OutputManager for messages
        output_dir: Base output directory (default: 'output')
        save_research: Whether to save research metadata
    """
    from datetime import datetime
    import json

    slug = result.get('slug', 'untitled')
    content = result.get('content', '')
    raw_content = result.get('raw_content', '')

    # Create output directory
    date_str = datetime.now().strftime('%Y-%m-%d')
    generation_dir = Path(output_dir) / 'generations' / f"{date_str}_{slug}"
    generation_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    (generation_dir / 'final.mdx').write_text(content, encoding='utf-8')
    if raw_content:
        (generation_dir / 'raw.mdx').write_text(raw_content, encoding='utf-8')

    # Save research metadata if requested
    if save_research:
        metadata = {
            'keyword': result.get('keyword', ''),
            'style': result.get('style', ''),
            'generated_at': datetime.now().isoformat(),
            'slug': slug,
            'title': result.get('title', ''),
            'research_data': result.get('research_data', {}),
        }
        research_file = generation_dir / 'metadata.json'
        research_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        output.info(f"Research metadata saved: {research_file}")

    output.success(f"Saved to: {generation_dir}/")


# CLI entry point
cli = interactive_generate


if __name__ == "__main__":
    cli()
