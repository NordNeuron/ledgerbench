"""Constants for the LedgerBench Phase 0 harness. No secrets live here —
the API key is read from the ANTHROPIC_API_KEY environment variable at
call time by agent.py, never hardcoded or logged."""
import os
from pathlib import Path

# BUILD_SPEC.md pins these to claude-sonnet-4-6 against the standard
# Anthropic endpoint. Both are overridable via env vars so a run can point
# at any Anthropic-API-compatible provider/model (e.g. DeepSeek's
# /anthropic-compatible endpoint) without editing code; unset, they fall
# back to the spec's defaults.
MODEL = os.environ.get("LEDGERBENCH_MODEL", "claude-sonnet-4-6")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL")  # None = default Anthropic endpoint

# Model backend. "anthropic" (default) uses the Anthropic Messages API.
# "openai" uses any OpenAI-compatible /v1/chat/completions endpoint, which
# is how local servers expose a model — e.g. a local Qwen served through
# Ollama, vLLM, or LM Studio. Selecting "openai" changes only the transport;
# the prompts, <file>-block parsing, oracles, and logging are identical, so a
# run is directly comparable across backends apart from the model itself.
BACKEND = os.environ.get("LEDGERBENCH_BACKEND", "anthropic").lower()

# OpenAI-compatible endpoint (used only when BACKEND == "openai"). Point
# OPENAI_BASE_URL at the local server's /v1 root, for example:
#   http://localhost:11434/v1   (Ollama)
#   http://localhost:8000/v1    (vLLM / LM Studio / llama.cpp server)
# and set LEDGERBENCH_MODEL to the served model tag (e.g. "qwen2.5-coder:32b").
# Local servers usually ignore the API key, but the client requires a
# non-empty one, so OPENAI_API_KEY falls back to a dummy value at call time.
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"

TEMPERATURE = 0.2
# Spec default 8000; overridable because reasoning models (e.g. DeepSeek)
# spend part of the output budget on thinking blocks before the file text.
MAX_TOKENS = int(os.environ.get("LEDGERBENCH_MAX_TOKENS", "8000"))

REPAIR_BUDGET = 4  # k = 4 repair iterations before a task is marked FAILED

ARM_A_SUMMARY_MAX_TOKENS = 1500

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT_DIR / "projects"
TASKS_DIR = ROOT_DIR / "tasks"
ORACLES_DIR = ROOT_DIR / "oracles"
RUNS_DIR = ROOT_DIR / "runs"
RESULTS_DIR = ROOT_DIR / "results"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

PROJECT_NAME = "taskcli"
SEED_PROJECT_DIR = PROJECTS_DIR / PROJECT_NAME
TASK_DEFS_DIR = TASKS_DIR / PROJECT_NAME
ASSERTIONS_DIR = TASK_DEFS_DIR / "assertions"
ORACLE_DIR = ORACLES_DIR / PROJECT_NAME

# Phase 1: 24 tasks, sessions of 3 (boundary = context clear + Arm A
# summary + Arm C audit pool). LEDGERBENCH_TASKS=8 reproduces the pilot
# sequence exactly.
_N_TASKS = int(os.environ.get("LEDGERBENCH_TASKS", "24"))
TASK_IDS = [f"T{i}" for i in range(1, _N_TASKS + 1)]
SESSION_BOUNDARY_AFTER = {f"T{i}" for i in range(3, _N_TASKS, 3)}

# Env var used to tell assertion/oracle test files which workspace directory
# to operate against (see tasks/taskcli/assertions/_helpers.py).
WORKSPACE_ENV_VAR = "LEDGERBENCH_WORKSPACE"

ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
