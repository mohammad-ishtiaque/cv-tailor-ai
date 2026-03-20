import re
import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def compile_latex(tex_file_path: str, output_dir: str = "output") -> dict:
    """
    Compile a .tex file into a PDF.

    tex_file_path: Path to the main.tex file
    output_dir: Directory where the PDF should be saved

    return: {
        "success": True/False,
        "pdf_path": Path to the PDF file,
        "error": Error message when available,
        "pages": Number of pages
    }
    """

    tex_path = Path(tex_file_path)

    # Check whether the file exists.
    if not tex_path.exists():
        return {
            "success": False,
            "pdf_path": None,
            "error": f"File not found: {tex_file_path}",
            "pages": 0,
        }

    # Use the .tex file's directory as the working directory.
    working_dir = str(tex_path.parent)

    console.print(f"Compiling: {tex_path.name}", style="yellow")


def _run_pdflatex(tex_path: Path, working_dir: str) -> dict:
    """
    Run xelatex twice so references are resolved correctly.
    """

    command = [
        "xelatex",
        "-interaction=nonstopmode",
        "-output-directory",
        working_dir,
        str(tex_path),
    ]

    try:
        for run_number in range(2):
            console.print(
                f"  xelatex run {run_number + 1}/2...",
                style="dim",
            )

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=working_dir,
                timeout=300,
            )

            if result.returncode != 0:
                log_file = tex_path.with_suffix(".log")
                error_details = ""

                if log_file.exists():
                    log_content = log_file.read_text(encoding="utf-8", errors="ignore")
                    error_lines = [
                        line for line in log_content.split("\n") if line.startswith("!")
                    ]
                    error_details = "\n".join(error_lines[:5])

                return {
                    "success": False,
                    "error": f"xelatex error:\n{error_details}",
                }

        return {"success": True, "error": None}

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Compile timeout. The process took longer than 300 seconds.",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "xelatex was not found. Check whether MiKTeX is installed correctly.",
        }


def _get_page_count(pdf_path: Path) -> int:
    """
    Read the page count from the LaTeX log file.
    """

    log_path = pdf_path.with_suffix(".log")

    if not log_path.exists():
        return 0

    try:
        log_content = log_path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"Output written on .+?\((\d+) page", log_content)

        if match:
            return int(match.group(1))

        return 1

    except Exception:
        return 1


def _fix_overflow(tex_content: str, attempt: int) -> str:
    """
    Make small layout reductions when the CV exceeds the page limit.

    attempt 1: reduce font size
    attempt 2: reduce section spacing
    attempt 3: reduce item spacing
    attempt 4: reduce margins
    """

    console.print(
        f"  Overflow detected. Fix attempt {attempt}/4...",
        style="yellow",
    )

    if attempt == 1:
        # Reduce the document font size.
        tex_content = re.sub(
            r"\\documentclass\[(\d+)pt\]",
            lambda m: f"\\documentclass[{max(9, int(m.group(1)) - 1)}pt]",
            tex_content,
        )
        console.print("  Font size reduced by 1pt", style="dim")

    elif attempt == 2:
        # Reduce vertical spacing in section breaks.
        tex_content = re.sub(
            r"\\vspace\{(\d+(?:\.\d+)?)mm\}",
            lambda m: f"\\vspace{{{max(0, float(m.group(1)) - 1):.1f}mm}}",
            tex_content,
        )
        console.print("  Section spacing reduced", style="dim")

    elif attempt == 3:
        # Reduce spacing between list items.
        tex_content = re.sub(
            r"\\itemsep\s*(\d+)pt",
            lambda m: f"\\itemsep {max(0, int(m.group(1)) - 1)}pt",
            tex_content,
        )
        console.print("  Item spacing reduced", style="dim")

    elif attempt == 4:
        # Reduce the top margin as a last resort.
        tex_content = re.sub(
            r"\\geometry\{(.+?)\}",
            lambda m: m.group(0).replace("top=", "top=0.3in,_REMOVE_top="),
            tex_content,
        )
        tex_content = tex_content.replace(",_REMOVE_top=", "")
        console.print("  Margins adjusted", style="dim")

    return tex_content


def compile_with_overflow_guard(
    tex_content: str,
    project_dir: str,
    output_dir: str = "output",
    max_pages: int = 1,
) -> dict:
    """
    Compile a tailored LaTeX CV and try small layout fixes if it overflows.

    tex_content: Modified LaTeX content
    project_dir: Directory that contains the class file and fonts
    output_dir: Directory where the final PDF should be written
    max_pages: Maximum allowed page count
    """

    project_path = Path(project_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Write to a temporary file so the original main.tex is not touched.
    temp_tex = project_path / "temp_cv.tex"

    current_content = tex_content

    for attempt in range(5):
        if attempt == 0:
            console.print(
                Panel("Starting PDF compilation...", style="bold blue")
            )

        temp_tex.write_text(current_content, encoding="utf-8")
        compile_result = _run_pdflatex(temp_tex, str(project_path))

        if not compile_result["success"]:
            _cleanup_temp_files(project_path)
            return {
                "success": False,
                "pdf_path": None,
                "error": compile_result["error"],
                "pages": 0,
            }

        temp_pdf = project_path / "temp_cv.pdf"
        pages = _get_page_count(temp_pdf)

        console.print(f"  Page count: {pages}", style="dim")

        if pages <= max_pages:
            final_pdf = output_path / "tailored_cv.pdf"
            shutil.copy2(temp_pdf, final_pdf)
            _cleanup_temp_files(project_path)

            console.print(
                Panel(
                    f"PDF created successfully: {final_pdf}",
                    style="bold green",
                )
            )

            return {
                "success": True,
                "pdf_path": str(final_pdf),
                "error": None,
                "pages": pages,
            }

        if attempt < 4:
            current_content = _fix_overflow(current_content, attempt + 1)
        else:
            console.print(
                "Overflow could not be fully fixed. Returning the best attempt.",
                style="bold yellow",
            )
            final_pdf = output_path / "tailored_cv.pdf"
            shutil.copy2(temp_pdf, final_pdf)
            _cleanup_temp_files(project_path)

            return {
                "success": True,
                "pdf_path": str(final_pdf),
                "error": None,
                "pages": pages,
            }


def _cleanup_temp_files(project_path: Path):
    """
    Remove temporary files created during compilation.
    """
    temp_extensions = [".aux", ".log", ".out", ".fls", ".fdb_latexmk"]

    for ext in temp_extensions:
        temp_file = project_path / f"temp_cv{ext}"
        if temp_file.exists():
            temp_file.unlink()

    for temp_name in ["temp_cv.tex", "temp_cv.pdf"]:
        temp_file = project_path / temp_name
        if temp_file.exists():
            temp_file.unlink()
