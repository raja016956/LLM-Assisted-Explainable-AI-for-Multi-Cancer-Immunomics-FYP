import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


# ============================================================
# VALIDATE KEY
# ============================================================

api_key = os.getenv("GROQ_API_KEY")

print("=" * 70)
print("GROQ MODEL ACCESS TEST")
print("=" * 70)

print()
print("ENV FILE:")
print(ENV_PATH)

print()
print("GROQ API KEY AVAILABLE:")
print(bool(api_key))

if not api_key:
    raise EnvironmentError(
        "GROQ_API_KEY was not found."
    )


# ============================================================
# CONNECT
# ============================================================

client = Groq(
    api_key=api_key
)


# ============================================================
# LIST MODELS
# ============================================================

print()
print("AVAILABLE MODELS")
print("-" * 70)

models = client.models.list()

for model in models.data:

    print(
        model.id
    )


print()
print("=" * 70)
print("MODEL ACCESS TEST COMPLETE")
print("=" * 70)