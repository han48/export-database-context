"""AI-powered database schema analyzer using Qwen3-1.7B.

This module uses the Hugging Face transformers library with the Qwen/Qwen3-1.7B
model to analyze exported schema Markdown files and produce detailed insights
about database structure, table purposes, and relationships.

Usage:
    python -m db_schema_export.ai_analyzer docs/mydb_schema.md

Requirements:
    pip install transformers torch accelerate
"""

from __future__ import annotations

import argparse
import os
import sys
import time


MODEL_ID = "Qwen/Qwen3-1.7B"

SYSTEM_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "system_prompt.txt")


def load_system_prompt() -> str:
    """Load the system prompt from the external text file.

    Returns:
        The system prompt string.

    Raises:
        SystemExit: If the prompt file is not found.
    """
    if not os.path.isfile(SYSTEM_PROMPT_FILE):
        print(
            f"[ERROR] System prompt file not found: {SYSTEM_PROMPT_FILE}",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_model():
    """Load the Qwen3-1.7B model and tokenizer.

    Returns:
        Tuple of (model, tokenizer).

    Raises:
        ImportError: If transformers or torch is not installed.
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        print(
            "[ERROR] transformers library not installed.\n"
            "  → Install with: pip install transformers torch accelerate",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Loading model: {MODEL_ID}...")
    start = time.time()

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=".cache")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype="auto",
        device_map="auto",
        cache_dir=".cache",
    )

    elapsed = time.time() - start
    print(f"Model loaded in {elapsed:.1f}s")

    return model, tokenizer


def read_schema_file(filepath: str) -> str:
    """Read and return the content of a schema Markdown file.

    Args:
        filepath: Path to the .md file.

    Returns:
        File content as string.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    if not os.path.isfile(filepath):
        print(f"[ERROR] File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    return content


def truncate_content(content: str, max_chars: int = 12000) -> str:
    """Truncate schema content to fit within model context window.

    Prioritizes keeping the ERD section, table structure, and relationships.
    Removes verbose SQL definitions and long column lists if needed.

    Args:
        content: Full markdown content.
        max_chars: Maximum character count to keep.

    Returns:
        Truncated content string.
    """
    if len(content) <= max_chars:
        return content

    # Try to keep the most important sections
    lines = content.split("\n")
    result_lines: list[str] = []
    current_size = 0
    in_code_block = False
    skip_section = False

    # Priority sections to keep
    priority_sections = ["# ", "## Table of Contents", "## ERD Diagram", "## Tables"]

    for line in lines:
        # Track code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block

        # Skip Views/Functions SQL definitions if we're running out of space
        if current_size > max_chars * 0.7:
            if line.startswith("## Views") or line.startswith("## Operators"):
                skip_section = True
            elif line.startswith("## ") and skip_section:
                skip_section = False

        if skip_section:
            continue

        result_lines.append(line)
        current_size += len(line) + 1

        if current_size >= max_chars:
            result_lines.append("\n... (truncated for analysis)")
            break

    return "\n".join(result_lines)


def analyze_schema(model, tokenizer, schema_content: str, output_path: str | None = None) -> str:
    """Run AI analysis on the schema content with streaming output.

    Uses TextIteratorStreamer to stream tokens as they are generated:
    - Logs each token to stdout immediately (real-time feedback)
    - Appends to output file in chunks (every ~500 chars) for performance

    Args:
        model: The loaded language model.
        tokenizer: The loaded tokenizer.
        schema_content: The schema markdown content to analyze.
        output_path: Optional path to write streaming output to file.

    Returns:
        AI-generated analysis text (full response).
    """
    from threading import Thread

    try:
        from transformers import TextIteratorStreamer
    except ImportError:
        print("[ERROR] transformers not installed.", file=sys.stderr)
        return ""

    # Truncate content to fit model context
    truncated = truncate_content(schema_content)

    user_message = (
        f"Analyze the following database schema:\n\n"
        f"```markdown\n{truncated}\n```\n\n"
        f"Produce a detailed analysis report for this schema."
    )

    messages = [
        {"role": "system", "content": load_system_prompt()},
        {"role": "user", "content": user_message},
    ]

    # Apply chat template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True,
    )

    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    # Setup streamer
    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    # Generation kwargs
    generation_kwargs = dict(
        **inputs,
        max_new_tokens=4096,
        temperature=0.6,
        top_p=0.95,
        top_k=20,
        do_sample=True,
        streamer=streamer,
    )

    # Run generation in a separate thread
    thread = Thread(target=model.generate, kwargs=generation_kwargs)

    print("\nGenerating analysis (streaming)...\n")
    print("-" * 60)
    start = time.time()
    thread.start()

    # Collect full response and stream to console + file
    full_response: list[str] = []
    chunk_buffer: list[str] = []
    chunk_size = 0
    CHUNK_THRESHOLD = 500  # Flush to file every ~500 chars
    in_thinking = True  # Track if we're still in <think> block
    file_handle = None

    # Open file for writing if output_path provided
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        file_handle = open(output_path, "w", encoding="utf-8")
        file_handle.write(f"# Database Schema Analysis\n\n")
        file_handle.write(f"_Generated by AI (Model: {MODEL_ID})_\n\n")
        file_handle.write("---\n\n")

    try:
        for token_text in streamer:
            full_response.append(token_text)

            # Detect end of thinking block
            current_text = "".join(full_response)
            if in_thinking:
                if "</think>" in current_text:
                    in_thinking = False
                    # Get content after </think>
                    after_think = current_text.split("</think>")[-1]
                    # Reset buffer with post-think content
                    full_response = [after_think]
                    chunk_buffer = [after_think]
                    chunk_size = len(after_think)
                    # Print what we have so far
                    sys.stdout.write(after_think)
                    sys.stdout.flush()
                continue

            # Stream to console immediately
            sys.stdout.write(token_text)
            sys.stdout.flush()

            # Buffer for file writing
            if file_handle:
                chunk_buffer.append(token_text)
                chunk_size += len(token_text)

                # Flush chunk to file when threshold reached
                if chunk_size >= CHUNK_THRESHOLD:
                    file_handle.write("".join(chunk_buffer))
                    file_handle.flush()
                    chunk_buffer = []
                    chunk_size = 0

    finally:
        # Flush remaining buffer to file
        if file_handle:
            if chunk_buffer:
                file_handle.write("".join(chunk_buffer))
            file_handle.close()

    thread.join()

    elapsed = time.time() - start
    print(f"\n{'-'*60}")
    print(f"Analysis generated in {elapsed:.1f}s")

    # Return the full response (post-thinking)
    response = "".join(full_response)
    if "</think>" in response:
        response = response.split("</think>")[-1].strip()

    return response


def get_output_path(input_path: str, output_dir: str | None = None) -> str:
    """Determine the output file path for the analysis.

    Args:
        input_path: Path to the input schema file.
        output_dir: Output directory. If None, uses same directory as input.

    Returns:
        Path for the analysis output file.
    """
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    analysis_filename = f"{base_name}_analysis.md"

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, analysis_filename)
    else:
        input_dir = os.path.dirname(input_path) or "."
        return os.path.join(input_dir, analysis_filename)


def save_analysis(analysis: str, input_path: str, output_dir: str | None = None) -> str:
    """Save the analysis to a markdown file (non-streaming fallback).

    Args:
        analysis: The generated analysis text.
        input_path: Path to the input schema file.
        output_dir: Output directory. If None, uses same directory as input.

    Returns:
        Path to the saved analysis file.
    """
    # Determine output path
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    analysis_filename = f"{base_name}_analysis.md"

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, analysis_filename)
    else:
        output_path = os.path.join(os.path.dirname(input_path), analysis_filename)

    # Write analysis
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Database Schema Analysis\n\n")
        f.write(f"_Source: {os.path.basename(input_path)}_\n\n")
        f.write(f"_Generated by AI (Model: {MODEL_ID})_\n\n")
        f.write("---\n\n")
        f.write(analysis)

    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the AI analyzer.

    Args:
        argv: Argument list. If None, uses sys.argv[1:].

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="db_schema_export.ai_analyzer",
        description="Analyze database schema Markdown files using AI (Qwen3-1.7B).",
    )

    parser.add_argument(
        "input",
        type=str,
        help="Path to the schema Markdown file to analyze",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for the analysis file (default: same as input)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=MODEL_ID,
        help=f"Hugging Face model ID to use (default: {MODEL_ID})",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum tokens to generate (default: 4096)",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the AI analyzer.

    Args:
        argv: Argument list. If None, uses sys.argv[1:].

    Returns:
        Exit code (0=success, 1=error).
    """
    global MODEL_ID

    args = parse_args(argv)

    # Allow model override
    if args.model != MODEL_ID:
        MODEL_ID = args.model

    # Read input file
    print(f"\n{'='*60}")
    print("Database Schema AI Analyzer")
    print(f"{'='*60}\n")
    print(f"Input: {args.input}")
    print(f"Model: {MODEL_ID}")
    print()

    schema_content = read_schema_file(args.input)
    print(f"Schema file loaded: {len(schema_content):,} characters")

    # Load model
    model, tokenizer = load_model()

    # Determine output path
    output_path = get_output_path(args.input, args.output)

    # Run analysis with streaming (writes to file in chunks)
    analysis = analyze_schema(model, tokenizer, schema_content, output_path)

    if not analysis.strip():
        print("[ERROR] Model generated empty response.", file=sys.stderr)
        return 1

    print(f"\n✓ Analysis saved to: {output_path}")
    print(f"  ({len(analysis):,} characters)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
