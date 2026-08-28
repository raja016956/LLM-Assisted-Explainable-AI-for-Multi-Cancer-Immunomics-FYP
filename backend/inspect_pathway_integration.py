from __future__ import annotations

from pathlib import Path
import json


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ANALYSIS_DIR = (
    BASE_DIR
    / "analysis_data"
    / "pathway_immune_integration"
)


FILES = [
    "pathway_immune_associations.json",
    "pathway_state_rankings.json",
    "pathway_cluster_summary.json",
]


# ============================================================
# JSON DISPLAY
# ============================================================

def print_json_file(path: Path):

    print()
    print("=" * 80)
    print(path.name)
    print("=" * 80)

    if not path.exists():

        print("ERROR: File not found:")
        print(path)

        return

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:

            data = json.load(handle)

        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
        )

    except json.JSONDecodeError as exc:

        print(
            "ERROR: Invalid JSON:"
        )

        print(exc)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "IMMUNO-XAI PATHWAY INTEGRATION OUTPUT INSPECTOR"
    )
    print("=" * 80)

    print()
    print("Directory:")
    print(ANALYSIS_DIR)

    print()

    for filename in FILES:

        path = (
            ANALYSIS_DIR
            / filename
        )

        print_json_file(path)

    print()
    print("=" * 80)
    print(
        "OUTPUT INSPECTION COMPLETE"
    )
    print("=" * 80)


if __name__ == "__main__":

    main()