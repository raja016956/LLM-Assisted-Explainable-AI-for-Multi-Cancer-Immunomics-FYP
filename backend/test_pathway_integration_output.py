from __future__ import annotations

from pathlib import Path
import json


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = (
    BASE_DIR
    / "analysis_data"
    / "pathway_immune_integration"
)


# ============================================================
# HELPERS
# ============================================================

def load_json(filename: str):

    path = OUTPUT_DIR / filename

    if not path.exists():
        print(f"\nERROR: File not found:\n{path}")
        return None

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def print_json(value, indent=2):

    print(
        json.dumps(
            value,
            indent=indent,
            ensure_ascii=False,
        )
    )


# ============================================================
# ASSOCIATIONS
# ============================================================

def inspect_associations():

    print()
    print("=" * 80)
    print("PATHWAY + IMMUNE-STATE ASSOCIATIONS")
    print("=" * 80)

    data = load_json(
        "pathway_immune_associations.json"
    )

    if data is None:
        return

    for pathway, associations in data.items():

        print()
        print("-" * 80)
        print(f"PATHWAY: {pathway}")
        print("-" * 80)

        if isinstance(associations, dict):

            for key, value in associations.items():

                print(f"{key}: ", end="")

                if isinstance(value, (dict, list)):
                    print()
                    print_json(value)
                else:
                    print(value)

        elif isinstance(associations, list):

            for item in associations:
                print_json(item)

        else:

            print(associations)


# ============================================================
# STATE RANKINGS
# ============================================================

def inspect_rankings():

    print()
    print("=" * 80)
    print("PATHWAY RANKINGS BY IMMUNE STATE")
    print("=" * 80)

    data = load_json(
        "pathway_state_rankings.json"
    )

    if data is None:
        return

    for state, rankings in data.items():

        print()
        print("-" * 80)
        print(f"IMMUNE STATE: {state}")
        print("-" * 80)

        if isinstance(rankings, dict):

            for key, value in rankings.items():

                print(f"{key}: ", end="")

                if isinstance(value, (dict, list)):
                    print()
                    print_json(value)
                else:
                    print(value)

        elif isinstance(rankings, list):

            for rank, item in enumerate(
                rankings,
                start=1,
            ):

                print(f"{rank}. ", end="")

                if isinstance(item, (dict, list)):
                    print()
                    print_json(item)
                else:
                    print(item)

        else:

            print(rankings)


# ============================================================
# CLUSTER SUMMARY
# ============================================================

def inspect_clusters():

    print()
    print("=" * 80)
    print("PATHWAY SUMMARY BY CLUSTER")
    print("=" * 80)

    data = load_json(
        "pathway_cluster_summary.json"
    )

    if data is None:
        return

    for cluster_id, cluster_data in data.items():

        print()
        print("-" * 80)
        print(f"CLUSTER {cluster_id}")
        print("-" * 80)

        if isinstance(cluster_data, dict):

            for key, value in cluster_data.items():

                print(f"{key}: ", end="")

                if isinstance(value, (dict, list)):
                    print()
                    print_json(value)
                else:
                    print(value)

        else:

            print_json(cluster_data)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("IMMUNO-XAI PATHWAY INTEGRATION OUTPUT INSPECTOR")
    print("=" * 80)

    print()
    print("Directory:")
    print(OUTPUT_DIR)

    if not OUTPUT_DIR.exists():

        print()
        print("ERROR: Output directory does not exist.")
        return

    inspect_associations()

    inspect_rankings()

    inspect_clusters()

    print()
    print("=" * 80)
    print("DETAILED OUTPUT INSPECTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()