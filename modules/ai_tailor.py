import os

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()
console = Console()


def get_client(api_key: str = None):
    """
    Return an Anthropic client using the provided API key or the key from .env.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    if not key:
        raise ValueError("API key not found.")

    return anthropic.Anthropic(api_key=key)


def tailor_cv(latex_content: str, job_description: str, api_key: str = None) -> str:
    """
    Tailor a LaTeX CV for a specific job description using Claude.
    """
    console.print(Panel("Tailor CV with Claude AI", style="bold blue"))

    client = get_client(api_key)
    system_prompt = """You are an expert CV/Resume writer and LaTeX specialist with deep knowledge of ATS (Applicant Tracking Systems) and hiring practices.

    Your ONLY job is to tailor an existing LaTeX CV to match a specific job description.

    === WHAT YOU MUST DO ===
    1. ANALYZE the job description thoroughly:
    - Extract required technical skills, tools, and technologies
    - Identify key responsibilities and action verbs used
    - Note any specific qualifications or domain knowledge required

    2. TAILOR these CV sections ONLY if they exist in the original:
    - Summary/Objective: Rewrite to directly mirror the job's language and needs
    - Skills: Reorder so job-relevant skills appear first
    - Experience bullets: Rephrase using the job's keywords and action verbs
    - Projects: Highlight aspects most relevant to this role

    3. KEYWORD OPTIMIZATION:
    - Naturally embed important keywords from the job description
    - Match the exact terminology used in the job posting
    - Ensure ATS systems can detect skill matches

    === STRICT RULES - NEVER VIOLATE THESE ===
    1. NEVER modify \\documentclass, \\usepackage, or any preamble content
    2. NEVER change custom commands, macros, or style definitions
    3. NEVER alter the document structure, layout, columns, or formatting
    4. NEVER add new sections that do not exist in the original
    5. NEVER invent or fabricate any information; only reframe what exists
    6. NEVER remove any existing sections or experiences
    7. NEVER change contact information, dates, company names, or job titles
    8. NEVER add markdown formatting, code blocks, or explanations to the output
    9. NEVER wrap the output in ```latex or any other code block markers

    === OUTPUT RULES ===
    - Return ONLY the complete, valid LaTeX source code
    - Start directly with \\documentclass or the first line of the original file
    - The output must be fully compilable LaTeX with no broken syntax
    - Preserve ALL special characters and LaTeX commands exactly
    - If a section has no relevant content to tailor, keep it exactly as-is

    === QUALITY CHECK (do this mentally before responding) ===
    - The output starts with valid LaTeX
    - All original sections are preserved
    - The preamble is identical to the original
    - All dates, names, and titles remain unchanged
    - No information is fabricated
    - The output is not wrapped in markdown"""
    user_prompt = f"""Tailor the following LaTeX CV for the job description provided.

    === JOB DESCRIPTION ===
    {job_description}

    === ORIGINAL LaTeX CV ===
    {latex_content}

    Return ONLY the complete modified LaTeX source. No explanations. No markdown. Start directly with the LaTeX code."""
    try:
        console.print("Sending request to Claude API...", style="yellow")

        # Make the API call.
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=8000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract the text from the first content block.
        modified_latex = message.content[0].text

        console.print("CV tailoring completed successfully.", style="bold green")

        return modified_latex

    except anthropic.AuthenticationError:
        raise ValueError("Invalid API key. Please provide a correct key.")

    except anthropic.RateLimitError:
        raise ValueError("API rate limit reached. Please try again in a few minutes.")

    except Exception as e:
        raise ValueError(f"Claude API error: {str(e)}")
