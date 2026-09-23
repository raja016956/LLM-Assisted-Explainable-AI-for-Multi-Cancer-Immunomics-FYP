from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any

from dotenv import load_dotenv


# ============================================================
# LOAD BACKEND ENVIRONMENT VARIABLES
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)

print(
    "DEBUG ENV FILE:",
    ENV_FILE
)

print(
    "DEBUG ENV EXISTS:",
    ENV_FILE.exists()
)

print(
    "DEBUG GROQ KEY LOADED:",
    bool(os.getenv("GROQ_API_KEY"))
)


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class LLMReasoningConfig:

    provider: str = "groq"

    # Free Groq model confirmed by your model-access test.
    model: str = "openai/gpt-oss-20b"

    temperature: float = 0.2

    # Keep output moderate.
    max_tokens: int = 2500

    # Maximum approximate characters sent to the LLM.
    max_input_chars: int = 45000


# ============================================================
# JSON LOADING
# ============================================================

def _load_json(
    path: Path,
    description: str,
) -> Any:

    if not path.exists():

        raise FileNotFoundError(
            f"{description} not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(handle)


# ============================================================
# EXTRACT ANALYSIS PACKAGE
# ============================================================

def _extract_analysis_package(
    data: Any,
) -> dict:

    if not isinstance(data, dict):

        raise ValueError(
            "LLM reasoning input must contain a JSON object."
        )

    expected_analysis_keys = {
        "pipeline",
        "purpose",
        "input_cells",
        "immune_state_summary",
        "cluster_summary",
        "immune_score_summary",
        "ml_summary",
        "pathway_summary",
        "xai_summary",
    }

    # --------------------------------------------------------
    # CASE 1
    # --------------------------------------------------------

    if expected_analysis_keys.intersection(
        data.keys()
    ):

        return data

    # --------------------------------------------------------
    # CASE 2
    # --------------------------------------------------------

    possible_keys = [
        "analysis_package",
        "analysis",
        "final_analysis",
        "package",
        "results",
    ]

    for key in possible_keys:

        value = data.get(key)

        if isinstance(value, dict):

            if expected_analysis_keys.intersection(
                value.keys()
            ):

                return value

    # --------------------------------------------------------
    # CASE 3
    # --------------------------------------------------------

    def recursive_search(
        obj: Any,
    ) -> dict | None:

        if isinstance(obj, dict):

            if expected_analysis_keys.intersection(
                obj.keys()
            ):

                return obj

            for value in obj.values():

                found = recursive_search(
                    value
                )

                if found is not None:

                    return found

        elif isinstance(obj, list):

            for item in obj:

                found = recursive_search(
                    item
                )

                if found is not None:

                    return found

        return None

    found = recursive_search(
        data
    )

    if found is not None:

        return found

    # --------------------------------------------------------
    # FAILURE
    # --------------------------------------------------------

    raise ValueError(
        "Could not locate the computational analysis package "
        "inside llm_reasoning_input.json.\n\n"
        f"Top-level keys found: {list(data.keys())}"
    )


# ============================================================
# VALIDATION
# ============================================================

def _validate_analysis_package(
    package: dict,
) -> None:

    required_keys = [
        "pipeline",
        "purpose",
        "input_cells",
        "immune_state_summary",
        "cluster_summary",
        "immune_score_summary",
        "ml_summary",
        "pathway_summary",
        "xai_summary",
    ]

    missing = [
        key
        for key in required_keys
        if key not in package
    ]

    if missing:

        raise ValueError(
            "Computational analysis package is incomplete.\n"
            "Missing keys: "
            + ", ".join(missing)
            + "\n\n"
            "This indicates that final_analysis.py should be "
            "checked rather than the Groq API."
        )


# ============================================================
# COMPACT ANALYSIS PACKAGE
# ============================================================

def _compact_analysis_package(
    package: dict,
) -> dict:

    """
    Prepare a compact representation of the computational
    analysis for the biological reasoning layer.

    IMPORTANT:

    This function does NOT modify the original analysis files.

    It only removes redundant cell-level information that is
    unnecessary for biological interpretation.

    The computational workflow and results remain unchanged.
    """

    compact = {}

    # --------------------------------------------------------
    # CORE INFORMATION
    # --------------------------------------------------------

    compact["pipeline"] = package.get(
        "pipeline"
    )

    compact["purpose"] = package.get(
        "purpose"
    )

    compact["input_cells"] = package.get(
        "input_cells"
    )

    # --------------------------------------------------------
    # IMMUNE STATE SUMMARY
    # --------------------------------------------------------

    compact["immune_state_summary"] = package.get(
        "immune_state_summary"
    )

    # --------------------------------------------------------
    # CLUSTER SUMMARY
    # --------------------------------------------------------

    compact["cluster_summary"] = package.get(
        "cluster_summary"
    )

    # --------------------------------------------------------
    # IMMUNE SCORES
    # --------------------------------------------------------

    compact["immune_score_summary"] = package.get(
        "immune_score_summary"
    )

    # --------------------------------------------------------
    # MACHINE LEARNING
    # --------------------------------------------------------

    compact["ml_summary"] = package.get(
        "ml_summary"
    )

    # --------------------------------------------------------
    # PATHWAYS
    # --------------------------------------------------------

    compact["pathway_summary"] = package.get(
        "pathway_summary"
    )

    # --------------------------------------------------------
    # XAI
    # --------------------------------------------------------

    xai = package.get(
        "xai_summary"
    )

    if isinstance(xai, dict):

        compact_xai = {}

        for key, value in xai.items():

            # Keep scalar metadata.
            if isinstance(
                value,
                (
                    str,
                    int,
                    float,
                    bool,
                    type(None),
                ),
            ):

                compact_xai[key] = value

            # Keep feature importance.
            elif key in {
                "features",
                "top_features",
                "feature_importance",
            }:

                if isinstance(value, list):

                    compact_xai[key] = value[:20]

                else:

                    compact_xai[key] = value

        compact["xai_summary"] = compact_xai

    else:

        compact["xai_summary"] = xai

    # --------------------------------------------------------
    # DO NOT SEND LARGE CELL-LEVEL STRUCTURES
    # --------------------------------------------------------
    #
    # We intentionally do NOT copy:
    #
    # - cell_states
    # - cluster_states
    # - cell-by-cell predictions
    # - raw SHAP matrices
    # - raw pathway matrices
    # - raw immune-score matrices
    #
    # These are already summarized by final_analysis.py.
    #
    # The LLM is an interpretation layer, not the computational
    # analysis engine.
    # --------------------------------------------------------

    return compact


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are the biological reasoning layer of IMMUNO-XAI.

IMMUNO-XAI is a computational single-cell RNA-seq analysis
system designed to identify and characterize immune states.

Your job is to interpret computational evidence produced by
the pipeline.

You are NOT the computational analysis engine.

You MUST follow these rules:

1. Use ONLY information contained in the supplied analysis
   package.

2. Do NOT invent genes, pathways, cell states, statistics,
   clusters, mechanisms, or experimental findings.

3. Do NOT modify computational results.

4. Do NOT create new predictions.

5. Do NOT treat correlation as causation.

6. Distinguish clearly between:
   - computational finding
   - biological interpretation
   - possible explanation
   - limitation

7. Pay particular attention to:
   - Insufficient-Evidence
   - class imbalance
   - confidence
   - cluster composition
   - ML limitations
   - XAI feature importance

8. Do not interpret a machine-learning feature as a biological
   cause merely because it has high SHAP importance.

9. Do not claim clinical significance unless the supplied
   analysis explicitly supports it.

10. If the evidence is weak, explicitly state that the evidence
    is insufficient.

11. Do not force an interpretation.

12. The goal is scientifically cautious biological reasoning,
    not making the results appear stronger than they are.

13. The computational analysis has already been performed.
    Your task is ONLY to explain the supplied results.

14. Do not attempt to reconstruct cell-level predictions that
    are not present in the supplied compact analysis package.
"""


# ============================================================
# USER PROMPT
# ============================================================

def _build_reasoning_prompt(
    package: dict,
    config: LLMReasoningConfig,
) -> str:

    compact_package = _compact_analysis_package(
        package
    )

    package_json = json.dumps(
        compact_package,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    )

    # --------------------------------------------------------
    # SAFETY LIMIT
    # --------------------------------------------------------

    if len(package_json) > config.max_input_chars:

        # Preserve the most important computational summaries
        # while reducing XAI feature list if necessary.

        reduced_package = dict(
            compact_package
        )

        xai = reduced_package.get(
            "xai_summary"
        )

        if isinstance(xai, dict):

            for key in [
                "features",
                "top_features",
                "feature_importance",
            ]:

                if isinstance(
                    xai.get(key),
                    list,
                ):

                    xai[key] = xai[key][:10]

        package_json = json.dumps(
            reduced_package,
            separators=(
                ",",
                ":",
            ),
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # FINAL HARD SAFETY CHECK
    # --------------------------------------------------------

    if len(package_json) > config.max_input_chars:

        raise ValueError(
            "The compact LLM analysis package is still too large "
            f"({len(package_json)} characters). "
            "Reduce the size of final_analysis.py outputs before "
            "sending them to the LLM."
        )

    return f"""
Interpret the following IMMUNO-XAI computational analysis.

Give ONLY a concise biological interpretation in 2-3 sentences.
Keep it to the point and directly connected to the supplied results.
Mention the most important immune-state finding and the strongest
supporting immune/pathway/XAI evidence. If evidence is weak,
say so briefly. Do not invent findings, causes, clinical meaning,
or mechanisms. Do not use headings, bullet points, Markdown,
tables, or a separate conclusion.

COMPUTATIONAL ANALYSIS PACKAGE

{package_json}
"""


# ============================================================
# GROQ
# ============================================================

def _run_groq(
    system_prompt: str,
    user_prompt: str,
    config: LLMReasoningConfig,
) -> str:

    try:

        from groq import Groq

    except ImportError as exc:

        raise ImportError(
            "The 'groq' package is required.\n"
            "Install it with:\n\n"
            "python -m pip install groq"
        ) from exc

    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:

        raise EnvironmentError(
            "GROQ_API_KEY is not available."
        )

    client = Groq(
        api_key=api_key
    )

    response = client.chat.completions.create(

        model=config.model,

        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        temperature=config.temperature,

        max_tokens=config.max_tokens,
    )

    if not response.choices:

        raise RuntimeError(
            "Groq returned no response choices."
        )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    if not content:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    return content.strip()


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_llm_reasoning(
    analysis_input_path: str | Path,
    output_dir: str | Path,
    config: LLMReasoningConfig | None = None,
) -> dict:

    config = (
        config
        or LLMReasoningConfig()
    )

    analysis_input_path = Path(
        analysis_input_path
    )

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # LOAD INPUT
    # --------------------------------------------------------

    raw_input = _load_json(
        analysis_input_path,
        "LLM reasoning input",
    )

    # --------------------------------------------------------
    # EXTRACT PACKAGE
    # --------------------------------------------------------

    package = _extract_analysis_package(
        raw_input
    )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    _validate_analysis_package(
        package
    )

    # --------------------------------------------------------
    # BUILD COMPACT PROMPT
    # --------------------------------------------------------

    user_prompt = _build_reasoning_prompt(
        package,
        config,
    )

    print(
        "DEBUG LLM INPUT CHARACTERS:",
        len(user_prompt)
    )

    print(
        "DEBUG LLM MODEL:",
        config.model
    )

    # --------------------------------------------------------
    # RUN LLM
    # --------------------------------------------------------

    reasoning = _run_groq(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        config=config,
    )

    # --------------------------------------------------------
    # OUTPUT PATHS
    # --------------------------------------------------------

    reasoning_output = (
        output_dir
        / "biological_interpretation.json"
    )

    report_output = (
        output_dir
        / "biological_report.md"
    )

    metadata_output = (
        output_dir
        / "llm_reasoning_metadata.json"
    )

    # --------------------------------------------------------
    # JSON OUTPUT
    # --------------------------------------------------------

    result = {

        "pipeline": "IMMUNO-XAI",

        "task": (
            "Biological interpretation of "
            "computational immune-state analysis"
        ),

        "input_cells": package.get(
            "input_cells"
        ),

        "provider": config.provider,

        "model": config.model,

        "temperature": config.temperature,

        "max_tokens": config.max_tokens,

        "reasoning": reasoning,
    }

    with open(
        reasoning_output,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            result,
            handle,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # MARKDOWN REPORT
    # --------------------------------------------------------

    report = f"""# IMMUNO-XAI Biological Interpretation

## Computational Analysis

- **Pipeline:** IMMUNO-XAI
- **Input cells:** {package.get("input_cells")}
- **LLM:** {config.model}

---

{reasoning}

---

## Interpretation Disclaimer

This report interprets computational single-cell RNA-seq
analysis results. It does not establish causality, clinical
diagnosis, treatment response, or experimental validation.
"""

    with open(
        report_output,
        "w",
        encoding="utf-8",
    ) as handle:

        handle.write(
            report
        )

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    metadata = {

        "pipeline": "IMMUNO-XAI",

        "analysis_input": str(
            analysis_input_path
        ),

        "input_cells": package.get(
            "input_cells"
        ),

        "provider": config.provider,

        "model": config.model,

        "temperature": config.temperature,

        "max_tokens": config.max_tokens,

        "llm_input_characters": len(
            user_prompt
        ),

        "analysis_package_extracted": True,

        "compact_analysis_package": True,

        "biological_interpretation_generated": True,
    }

    with open(
        metadata_output,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            metadata,
            handle,
            indent=2,
        )

    return {

        "input_cells": package.get(
            "input_cells"
        ),

        "provider": config.provider,

        "model": config.model,

        "reasoning": reasoning,

        "reasoning_output": str(
            reasoning_output
        ),

        "report_output": str(
            report_output
        ),

        "metadata_output": str(
            metadata_output
        ),
    }