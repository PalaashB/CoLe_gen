"""
Display helpers, input handling, and terminal formatting utilities.
Uses colorama for cross-platform colour support.
"""

import sys

from colorama import Fore, Style, init as colorama_init

from config.settings import HEADER_WIDTH, SEPARATOR

colorama_init(autoreset=True)


# ==================================================================
# Colours
# ==================================================================
def cyan(text: str) -> str:
    return f"{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}"


def green(text: str) -> str:
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}"


def red(text: str) -> str:
    return f"{Fore.RED}{text}{Style.RESET_ALL}"


def yellow(text: str) -> str:
    return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"


def blue(text: str) -> str:
    return f"{Fore.BLUE}{text}{Style.RESET_ALL}"


def dim(text: str) -> str:
    return f"{Style.DIM}{text}{Style.RESET_ALL}"


def bold(text: str) -> str:
    return f"{Style.BRIGHT}{text}{Style.RESET_ALL}"


# ==================================================================
# Status indicators
# ==================================================================
def success(msg: str) -> None:
    print(f"  {green('✓')} {msg}")


def error(msg: str) -> None:
    print(f"  {red('✗')} {msg}")


def warn(msg: str) -> None:
    print(f"  {yellow('⚠')} {msg}")


def info(msg: str) -> None:
    print(f"  {blue('ℹ')} {msg}")


# ==================================================================
# Decorative output
# ==================================================================
def print_header(title: str) -> None:
    """Display a centred section header."""
    line = "═" * HEADER_WIDTH
    print()
    print(f"  {cyan(line)}")
    print(f"  {cyan(title.center(HEADER_WIDTH))}")
    print(f"  {cyan(line)}")
    print()


def print_banner() -> None:
    """Print the application welcome banner."""
    print()
    print(f"  {cyan('=' * HEADER_WIDTH)}")
    print(f"  {cyan('AI Cover Letter Generator'.center(HEADER_WIDTH))}")
    print(f"  {cyan('Powered by NVIDIA Nemotron 120B'.center(HEADER_WIDTH))}")
    print(f"  {cyan('=' * HEADER_WIDTH)}")
    print()


def print_separator() -> None:
    print(f"  {dim(SEPARATOR)}")


def print_menu() -> None:
    """Print the main menu options."""
    options = [
        ("1", "Generate cover letter (paste URL or text)"),
        ("2", "View past applications"),
        ("3", "Edit my profile"),
        ("4", "Settings"),
        ("5", "Exit"),
    ]
    for num, label in options:
        print(f"   {bold(num)}. {label}")
    print()


# ==================================================================
# Input helpers
# ==================================================================
def get_choice(prompt: str = "  Choose option: ") -> str:
    """Read a single-line user choice."""
    try:
        return input(f"{bold(prompt)}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "5"  # treat interrupts as exit


def get_multiline_input(prompt_text: str = "Paste job posting URL or description below.") -> str:
    """Accept multi-line input terminated by two blank lines, Ctrl-D, or 'END'."""
    print(f"\n  {bold(prompt_text)}")
    print(f"  {dim('(Press Enter twice on an empty line when done, or Ctrl+D)')}")
    print()

    lines: list[str] = []
    empty_count = 0

    while True:
        try:
            line = input("  > ")
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append(line)
            elif line.strip().upper() == "END":
                break
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            return ""

    return "\n".join(lines).strip()


def confirm(prompt: str = "Proceed?", default_yes: bool = True) -> bool:
    """Ask a yes/no question. Returns bool."""
    hint = "(Y/n)" if default_yes else "(y/N)"
    try:
        answer = input(f"  {bold(prompt)} {hint}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default_yes
    if answer == "":
        return default_yes
    return answer.startswith("y")


def confirm_or_edit(prompt: str = "Does this look correct?") -> str:
    """Ask y/n/edit. Returns 'y', 'n', or 'edit'."""
    try:
        answer = input(f"  {bold(prompt)} (y/n/edit): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "y"
    if answer.startswith("e"):
        return "edit"
    if answer.startswith("n"):
        return "n"
    return "y"


# ==================================================================
# Display structured data
# ==================================================================
def print_job_details(job: dict) -> None:
    """Pretty-print extracted job details."""
    print()
    print_separator()
    print(f"  {cyan('Extracted Job Details')}")
    print_separator()
    fields = [
        ("Company", job.get("company_name", "—")),
        ("Position", job.get("position_title", "—")),
        ("Location", job.get("location", "—")),
        ("Type", job.get("employment_type", "—")),
        ("Experience", job.get("experience_years", "—")),
        ("Salary", job.get("salary_range") or "Not specified"),
        ("Remote", job.get("remote_policy", "—")),
    ]
    for label, value in fields:
        print(f"  {label + ':':<14} {value}")

    skills = job.get("required_skills", [])
    if skills:
        print(f"  {'Skills:':<14} {', '.join(skills[:8])}")

    tech = job.get("tech_stack", [])
    if tech:
        print(f"  {'Tech Stack:':<14} {', '.join(tech[:8])}")

    print_separator()
    print()


def print_research_summary(research: dict) -> None:
    """Pretty-print research insights."""
    print()
    print_separator()
    print(f"  {cyan('Research Summary')}")
    print_separator()

    fields = [
        ("Momentum", research.get("company_momentum", "—")),
        ("Culture", ", ".join(research.get("cultural_keywords", [])[:5]) or "—"),
        ("Pain Points", ", ".join(research.get("pain_points", [])[:3]) or "—"),
        ("Initiatives", ", ".join(research.get("recent_initiatives", [])[:3]) or "—"),
    ]
    for label, value in fields:
        print(f"  {label + ':':<14} {value}")

    print_separator()
    print()


def print_quality_score(quality: dict) -> None:
    """Display the cover letter quality evaluation."""
    score = quality.get("score", 0)
    if score >= 80:
        colour = green
    elif score >= 60:
        colour = yellow
    else:
        colour = red

    print()
    print_separator()
    print(f"  {cyan('Quality Score:')} {colour(f'{score}/100')}")
    print_separator()

    checks = quality.get("checks", {})
    for label, passed in checks.items():
        icon = green("✓") if passed else red("✗")
        nice_label = label.replace("_", " ").title()
        print(f"  {icon} {nice_label}")

    recs = quality.get("recommendations", [])
    if recs:
        print()
        for rec in recs:
            print(f"  {yellow('→')} {rec}")

    print_separator()
    print()


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a simple table."""
    if not rows:
        print("  No data.")
        return

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(val)))

    # Header
    header_line = "  " + " │ ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "  " + "─┼─".join("─" * w for w in widths)
    print(header_line)
    print(sep_line)

    # Rows
    for row in rows:
        line = "  " + " │ ".join(str(v).ljust(widths[i]) for i, v in enumerate(row))
        print(line)

    print()


def score_color(score: int) -> str:
    """Return a coloured score string."""
    if score >= 80:
        return green(str(score))
    elif score >= 60:
        return yellow(str(score))
    return red(str(score))
