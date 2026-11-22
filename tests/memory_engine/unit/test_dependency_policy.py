"""No generative LLM in Raven's processing (CLAUDE.md constraint; plan 8.4 §16 criterion 11).

The locked dependency set is the evidence: no client for a generative model
API and no library that hosts one locally may appear in ``uv.lock``.
"""

import re
from pathlib import Path

LOCKFILE = Path(__file__).resolve().parents[3] / "uv.lock"

# Clients for hosted generative models, and libraries that run them locally.
FORBIDDEN = frozenset(
    {
        "openai",
        "anthropic",
        "google-generativeai",
        "google-genai",
        "mistralai",
        "cohere",
        "groq",
        "together",
        "replicate",
        "ollama",
        "llama-cpp-python",
        "vllm",
        "transformers",
        "langchain",
        "langchain-core",
        "llama-index",
        "litellm",
        "spacy-llm",
        "gpt4all",
        "ctransformers",
    }
)


def _locked_packages() -> set[str]:
    text = LOCKFILE.read_text(encoding="utf-8")
    return {name.lower() for name in re.findall(r'^name = "([^"]+)"', text, flags=re.MULTILINE)}


def test_the_lockfile_is_read() -> None:
    packages = _locked_packages()
    assert {"spacy", "sqlalchemy", "celery"} <= packages  # the check sees real entries


def test_no_generative_llm_package_is_locked() -> None:
    assert _locked_packages() & FORBIDDEN == set()
