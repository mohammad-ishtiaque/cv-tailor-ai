import os
import shutil
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

from modules.ai_tailor import tailor_cv
from modules.compiler import compile_with_overflow_guard
from modules.project_loader import inspect_uploaded_project, stage_uploaded_project

# Load the API key from .env.
load_dotenv()

# Configure the page before rendering any UI.
st.set_page_config(
    page_title="CV Tailor AI",
    page_icon=None,
    layout="centered",
)


# Add lightweight custom styling.
st.markdown(
    """
<style>
    /* Main container */
    .main {
        padding: 2rem;
    }

    /* Success box */
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }

    /* Warning box */
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }

    /* Step indicator */
    .step-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# App title and description.
st.title("CV Tailor AI")
st.markdown(
    """
**Upload `main.tex` or a full `.zip` project -> AI tailors your CV automatically -> Download a ready PDF**

No manual editing is required. The design stays the same.
"""
)

# Divider line.
st.divider()


# Collect the API key in the sidebar.
with st.sidebar:
    st.header("Settings")

    # Use the key from .env when available.
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if env_key:
        st.success("API key loaded from .env")
        api_key = env_key
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-api03-...",
            help="Get your key from console.anthropic.com",
        )

    st.divider()

    st.subheader("Options")

    max_pages = st.selectbox(
        "Maximum CV pages",
        options=[1, 2],
        index=0,
        help="1 page is recommended for most jobs",
    )


# The workflow is split into three steps.
st.markdown(
    '<div class="step-header">Step 1: Upload your CV source</div>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a main.tex file or a .zip export of the full LaTeX project",
    type=["tex", "zip"],
    help="Use .zip when your CV depends on images, extra .tex files, or other project assets",
)

# Show a preview after upload.
if uploaded_file:
    uploaded_bytes = uploaded_file.getvalue()

    try:
        inspected_project = inspect_uploaded_project(
            uploaded_file.name,
            uploaded_bytes,
        )
        tex_content = inspected_project.main_tex_content

        st.success(f"File uploaded: {uploaded_file.name}")
        if inspected_project.upload_kind == "zip":
            st.caption(f"Detected entry file: {inspected_project.main_tex_label}")
        else:
            st.caption(f"Using entry file: {inspected_project.main_tex_label}")

        with st.expander("CV Preview (first 30 lines)"):
            lines = tex_content.split("\n")[:30]
            st.code("\n".join(lines), language="latex")
    except ValueError as error:
        tex_content = None
        uploaded_bytes = None
        st.error(str(error))
else:
    tex_content = None
    uploaded_bytes = None

st.divider()


st.markdown(
    '<div class="step-header">Step 2: Paste the Job Description</div>',
    unsafe_allow_html=True,
)

job_description = st.text_area(
    "Paste the full description from the job posting",
    height=250,
    placeholder="""Example:
We are looking for a Software Engineer with:
- 3+ years of Python experience
- Knowledge of REST APIs
- Experience with AWS
...
""",
    help="More detail helps produce a better tailored CV",
)

# Show the word count.
if job_description:
    word_count = len(job_description.split())

    if word_count < 50:
        st.warning(f"{word_count} words. Add more detail for better results.")
    else:
        st.success(f"{word_count} words. Looks good.")

st.divider()


st.markdown(
    '<div class="step-header">Step 3: Generate</div>',
    unsafe_allow_html=True,
)

# Check whether all required input is present.
ready_to_generate = (
    api_key
    and tex_content
    and job_description
    and len(job_description.split()) >= 20
)

generate_button = st.button(
    "Tailor CV",
    disabled=not ready_to_generate,
    use_container_width=True,
    type="primary",
)

# Show what is still missing.
if not ready_to_generate:
    missing = []
    if not api_key:
        missing.append("API key")
    if not tex_content:
        missing.append(".tex file")
    if not job_description:
        missing.append("Job description")
    elif len(job_description.split()) < 20:
        missing.append("Job description (add more detail)")

    if missing:
        st.info(f"Missing: {', '.join(missing)}")


if generate_button:
    progress_bar = st.progress(0, text="Starting...")
    status_area = st.empty()

    try:
        # Step 1: Tailor the CV with Claude.
        status_area.info("Claude AI is analyzing your CV...")
        progress_bar.progress(20, text="AI processing...")

        modified_latex = tailor_cv(
            latex_content=tex_content,
            job_description=job_description,
            api_key=api_key,
        )

        progress_bar.progress(60, text="AI complete. Compiling PDF...")

        # Step 2: Compile the PDF.
        status_area.info("Compiling PDF...")

        repo_root = Path(__file__).resolve().parent
        temp_root = repo_root / ".runtime_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)

        # Work in a temporary directory so all required assets stay together.
        temp_path = temp_root / f"build_{uuid4().hex}"
        temp_path.mkdir(parents=True, exist_ok=True)

        try:
            staged_project = stage_uploaded_project(
                uploaded_file.name,
                uploaded_bytes,
                temp_path,
                repo_root,
            )

            output_dir = temp_path / "output"
            output_dir.mkdir()

            result = compile_with_overflow_guard(
                tex_content=modified_latex,
                project_dir=str((temp_path / staged_project.main_tex_label).parent),
                output_dir=str(output_dir),
                max_pages=max_pages,
            )

            # Read the PDF bytes before the temporary directory is deleted.
            if result["success"]:
                pdf_path = Path(result["pdf_path"])
                pdf_bytes = pdf_path.read_bytes()
                result["pdf_bytes"] = pdf_bytes
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

        progress_bar.progress(90, text="Almost done...")

        # Step 3: Show the result.
        if result["success"]:
            progress_bar.progress(100, text="Done")
            status_area.success("Your tailored CV is ready.")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Pages", result["pages"])
            with col2:
                st.metric(
                    "File Size",
                    f"{len(pdf_bytes) / 1024:.1f} KB",
                )
            with col3:
                st.metric("Status", "Ready")

            st.download_button(
                label="Download PDF",
                data=result["pdf_bytes"],
                file_name="tailored_cv.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )

            with st.expander("View or download modified LaTeX"):
                st.code(modified_latex[:2000] + "...", language="latex")
                st.download_button(
                    label="Download .tex file",
                    data=modified_latex,
                    file_name="tailored_cv.tex",
                    mime="text/plain",
                )

        else:
            progress_bar.progress(100, text="Error")
            status_area.error(f"Compile error: {result['error']}")

            st.markdown(
                """
            **Troubleshooting:**
            - Check whether MiKTeX is installed correctly.
            - Test whether the .tex file is valid in Overleaf.
            - Review the build log below.
            """
            )

        if result.get("log_content"):
            with st.expander("Build log"):
                st.code(result["log_content"][:12000], language="text")
                st.download_button(
                    label="Download build log",
                    data=result["log_content"],
                    file_name="build.log",
                    mime="text/plain",
                )

    except ValueError as e:
        progress_bar.empty()
        st.error(str(e))

    except Exception as e:
        progress_bar.empty()
        st.error(f"Unexpected error: {str(e)}")
        st.info("Copy this error and share it with the developer.")

st.divider()
st.markdown(
    """
<div style='text-align: center; color: gray; font-size: 0.8rem;'>
    CV Tailor AI - Powered by Claude AI + LaTeX<br>
    Your CV and API key are not stored anywhere
</div>
""",
    unsafe_allow_html=True,
)
