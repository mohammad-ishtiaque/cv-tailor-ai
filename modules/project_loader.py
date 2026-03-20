import io
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


IGNORED_DIRECTORIES = {
    "__MACOSX",
    "__pycache__",
    ".git",
    ".streamlit",
    "backup",
    "logs",
    "output",
    "venv",
}


@dataclass
class ProjectInspection:
    upload_kind: str
    main_tex_label: str
    main_tex_content: str


def decode_text_content(file_bytes: bytes, file_name: str) -> str:
    """
    Decode uploaded text content using a small set of common encodings.
    """
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(
        f"Could not decode {file_name}. Please export the file using UTF-8 encoding."
    )


def inspect_uploaded_project(upload_name: str, upload_bytes: bytes) -> ProjectInspection:
    """
    Inspect an uploaded .tex file or .zip project and return the detected entry file.
    """
    suffix = Path(upload_name).suffix.lower()

    if suffix == ".tex":
        return ProjectInspection(
            upload_kind="tex",
            main_tex_label=Path(upload_name).name,
            main_tex_content=decode_text_content(upload_bytes, upload_name),
        )

    if suffix != ".zip":
        raise ValueError("Unsupported file type. Upload a .tex file or a .zip project.")

    temp_root = Path.cwd() / ".runtime_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)

    temp_path = temp_root / f"inspect_{uuid4().hex}"
    temp_path.mkdir(parents=True, exist_ok=True)

    try:
        _extract_zip_safely(upload_bytes, temp_path)
        main_tex_path = _find_main_tex_file(temp_path)
        main_tex_label = main_tex_path.relative_to(temp_path).as_posix()
        main_tex_content = decode_text_content(
            main_tex_path.read_bytes(),
            main_tex_path.name,
        )
        return ProjectInspection(
            upload_kind="zip",
            main_tex_label=main_tex_label,
            main_tex_content=main_tex_content,
        )
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def stage_uploaded_project(
    upload_name: str,
    upload_bytes: bytes,
    destination: Path,
    asset_root: Path,
) -> ProjectInspection:
    """
    Stage an uploaded project into a workspace and return the detected entry file.
    """
    suffix = Path(upload_name).suffix.lower()

    if suffix == ".tex":
        _copy_fallback_assets(asset_root, destination)
        return ProjectInspection(
            upload_kind="tex",
            main_tex_label=Path(upload_name).name,
            main_tex_content=decode_text_content(upload_bytes, upload_name),
        )

    if suffix != ".zip":
        raise ValueError("Unsupported file type. Upload a .tex file or a .zip project.")

    _extract_zip_safely(upload_bytes, destination)
    main_tex_path = _find_main_tex_file(destination)
    _copy_fallback_assets(asset_root, main_tex_path.parent)

    return ProjectInspection(
        upload_kind="zip",
        main_tex_label=main_tex_path.relative_to(destination).as_posix(),
        main_tex_content=decode_text_content(
            main_tex_path.read_bytes(),
            main_tex_path.name,
        ),
    )


def _extract_zip_safely(zip_bytes: bytes, destination: Path):
    """
    Extract a zip archive while blocking path traversal entries.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            for member in archive.infolist():
                relative_path = Path(member.filename.replace("\\", "/"))

                if not member.filename:
                    continue

                if relative_path.is_absolute() or ".." in relative_path.parts:
                    raise ValueError("The uploaded ZIP file contains unsafe paths.")

                target_path = destination / relative_path

                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target_path.open("wb") as target:
                    shutil.copyfileobj(source, target)
    except zipfile.BadZipFile as error:
        raise ValueError("The uploaded file is not a valid ZIP archive.") from error


def _find_main_tex_file(project_root: Path) -> Path:
    """
    Find the best LaTeX entry file in an extracted project.
    """
    tex_candidates = [
        candidate
        for candidate in project_root.rglob("*.tex")
        if not any(
            part.lower() in IGNORED_DIRECTORIES
            for part in candidate.relative_to(project_root).parts
        )
    ]

    if not tex_candidates:
        raise ValueError(
            "No .tex file was found in the uploaded project. Please upload a full LaTeX source zip."
        )

    scored_candidates = []
    for candidate in tex_candidates:
        relative_path = candidate.relative_to(project_root)
        content = candidate.read_text(encoding="utf-8", errors="ignore")

        score = 0
        if candidate.name.lower() == "main.tex":
            score += 100
        if candidate.parent == project_root:
            score += 20
        if "\\documentclass" in content:
            score += 20
        if "\\begin{document}" in content:
            score += 10
        if any(part.lower() == "backup" for part in relative_path.parts):
            score -= 40

        scored_candidates.append(
            (
                score,
                len(relative_path.parts),
                relative_path.as_posix().lower(),
                candidate,
            )
        )

    scored_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    best_candidate = scored_candidates[0]

    if len(scored_candidates) > 1:
        second_candidate = scored_candidates[1]
        if best_candidate[:2] == second_candidate[:2]:
            raise ValueError(
                "Multiple possible LaTeX entry files were found. Please upload a project with a single clear main.tex file."
            )

    return best_candidate[3]


def _copy_fallback_assets(asset_root: Path, destination: Path):
    """
    Copy local class files and fonts when the staged project does not include them.
    """
    for cls_file in asset_root.glob("*.cls"):
        target_path = destination / cls_file.name
        if not target_path.exists():
            shutil.copy2(cls_file, target_path)

    fonts_source = asset_root / "fonts"
    fonts_target = destination / "fonts"
    if fonts_source.exists() and not fonts_target.exists():
        shutil.copytree(fonts_source, fonts_target)
