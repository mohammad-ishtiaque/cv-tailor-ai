# CV Tailor AI

CV Tailor AI is a Streamlit app that takes an existing LaTeX CV, rewrites the content for a target job description using Claude AI, and compiles the result into a ready-to-download PDF.

The goal is simple: keep the original LaTeX design and structure, but improve the wording so the CV matches the job posting more closely.

## What This Project Does

- Accepts either a single `main.tex` file or a full `.zip` LaTeX project
- Uses Claude AI to tailor the CV content to a job description
- Preserves the original LaTeX format and layout as much as possible
- Compiles the tailored LaTeX into PDF using `xelatex`
- Tries small overflow fixes automatically if the result exceeds the page limit
- Lets the user download the final PDF, modified `.tex`, and build log when available

## User Journey

This is the expected flow for a user:

1. Open the Streamlit app.
2. Enter an Anthropic API key in the sidebar, or load it from `.env`.
3. Upload either:
   - a single `main.tex` file, or
   - a `.zip` export of the full LaTeX CV project
4. Paste the target job description into the text area.
5. Click `Tailor CV`.
6. The app:
   - reads the LaTeX project
   - sends the CV and job description to Claude
   - generates a tailored LaTeX version
   - compiles the result into PDF
   - applies basic overflow reduction if needed
7. Download the generated PDF.
8. Optionally inspect or download:
   - the tailored `.tex` file
   - the LaTeX build log for debugging

## How It Works

The app is built around three main steps:

1. Content tailoring
   Claude analyzes the job description and rewrites selected CV sections to better match the role.

2. LaTeX compilation
   The tailored LaTeX is compiled with `xelatex` inside a temporary workspace.

3. Result delivery
   The app shows the final PDF, reports page count and file size, and exposes logs if compilation fails.

## Requirements

Before running the project, make sure you have:

- Python 3.12 or compatible
- An Anthropic API key
- `xelatex` available on your system path
- MiKTeX installed if you are on Windows

## Installation

Clone or open the project folder, then install dependencies:

```bash
pip install -r requirements.txt
```

Optional: create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

## Run the App

Start the Streamlit app with:

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit in your terminal.

## Project Structure

```text
cv-automation/
├─ app.py
├─ requirements.txt
├─ deedy-resume-openfont.cls
├─ fonts/
├─ modules/
│  ├─ ai_tailor.py
│  ├─ compiler.py
│  └─ project_loader.py
├─ main.tex
└─ backup/
```

## Main Components

- `app.py`
  Streamlit UI and end-to-end workflow

- `modules/ai_tailor.py`
  Claude API integration and CV tailoring prompt logic

- `modules/compiler.py`
  `xelatex` compilation, page counting, and overflow handling

- `modules/project_loader.py`
  Upload inspection, ZIP extraction, and LaTeX entry file detection

## Input and Output

### Input

- A LaTeX CV as `main.tex` or a `.zip` project
- A target job description
- An Anthropic API key

### Output

- Tailored PDF CV
- Tailored LaTeX source
- Build log when available

## Notes

- The app is designed to keep the original CV layout intact.
- If your CV depends on extra files like images, split `.tex` files, or assets, upload the full `.zip` project instead of only `main.tex`.
- The app does not intentionally store the uploaded CV or API key after the session workflow completes.

## Troubleshooting

- If compilation fails, check that `xelatex` is installed and accessible.
- On Windows, confirm MiKTeX is installed correctly.
- If your project includes additional files, upload the full `.zip` project.
- If the UI shows a build log, review it to identify LaTeX errors.

## License

This project includes [LICENSE.txt](LICENSE.txt).
