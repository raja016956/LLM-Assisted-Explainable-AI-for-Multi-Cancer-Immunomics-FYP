from __future__ import annotations

from pathlib import Path

from app.pipeline.llm_reasoning import (
    run_llm_reasoning,
    LLMReasoningConfig,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

ANALYSIS_DIR = (
    BASE_DIR
    / "analysis_data"
)

LLM_INPUT_PATH = (
    ANALYSIS_DIR
    / "final_analysis"
    / "llm_reasoning_input.json"
)

OUTPUT_DIR = (
    ANALYSIS_DIR
    / "llm_reasoning"
)


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)

    print(
        "IMMUNO-XAI LLM BIOLOGICAL REASONING TEST"
    )

    print("=" * 70)

    print()

    print(
        "INPUT FILE"
    )

    print("-" * 70)

    print(
        "LLM reasoning input:",
        LLM_INPUT_PATH
    )

    print(
        "Output:",
        OUTPUT_DIR
    )

    print()

    # --------------------------------------------------------
    # INPUT VALIDATION
    # --------------------------------------------------------

    if not LLM_INPUT_PATH.exists():

        raise FileNotFoundError(
            f"LLM reasoning input not found: "
            f"{LLM_INPUT_PATH}"
        )

    print(
        "INPUT VALIDATION"
    )

    print("-" * 70)

    print(
        "✓ llm_reasoning_input.json exists"
    )

    print()

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    result = run_llm_reasoning(

        analysis_input_path=LLM_INPUT_PATH,

        output_dir=OUTPUT_DIR,

        config=LLMReasoningConfig(

            provider="groq",

            model="groq/compound-mini",

            temperature=0.2,

            max_tokens=4000,
        ),
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print(
        "PIPELINE SUMMARY"
    )

    print("-" * 70)

    print(
        "Input cells:",
        result["input_cells"]
    )

    print(
        "Provider:",
        result["provider"]
    )

    print(
        "Model:",
        result["model"]
    )

    # --------------------------------------------------------
    # OUTPUT VALIDATION
    # --------------------------------------------------------

    print()

    print(
        "OUTPUT VALIDATION"
    )

    print("-" * 70)

    required_outputs = [

        OUTPUT_DIR
        / "biological_interpretation.json",

        OUTPUT_DIR
        / "biological_report.md",

        OUTPUT_DIR
        / "llm_reasoning_metadata.json",
    ]

    for output in required_outputs:

        if not output.exists():

            raise RuntimeError(
                f"Missing output: {output}"
            )

        print(
            "✓",
            output.name,
            "exists"
        )

    # --------------------------------------------------------
    # DISPLAY REASONING
    # --------------------------------------------------------

    print()

    print(
        "BIOLOGICAL REASONING"
    )

    print("-" * 70)

    print(
        result["reasoning"]
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print()

    print("=" * 70)

    print(
        "LLM BIOLOGICAL REASONING TEST COMPLETE"
    )

    print("=" * 70)

    print()

    print(
        "The computational analysis has been "
        "interpreted by the LLM."
    )


if __name__ == "__main__":
    main()