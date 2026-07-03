"""Model API calls, prompt assembly, and <file> block parsing.

Never imports anything from oracles/ (see BUILD_SPEC.md section 7).
"""
import json
import os
import re
from pathlib import Path

from harness import config

FILE_BLOCK_RE = re.compile(r'<file path="([^"]+)">\n?(.*?)</file>', re.DOTALL)

OUTPUT_FORMAT_INSTRUCTIONS = """
Return your solution as one or more complete files, using this exact format:

<file path="relative/path/to/file.py">
...entire file contents...
</file>

You may include multiple <file> blocks in your response, one per file that
needs to change. Always return the COMPLETE contents of each file you
touch, never a diff or a partial snippet. Do not include anything else
wrapped in <file> tags.
""".strip()


def parse_file_blocks(response_text: str) -> dict:
    """Returns {relative_path: file_contents}. Empty dict if no valid block found."""
    blocks = {}
    for match in FILE_BLOCK_RE.finditer(response_text):
        rel_path, content = match.group(1), match.group(2)
        if content.startswith("\n"):
            content = content[1:]
        blocks[rel_path] = content
    return blocks


def write_file_blocks(workspace: Path, blocks: dict) -> list:
    written = []
    for rel_path, content in blocks.items():
        target = workspace / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def build_task_prompt(task_def: dict) -> str:
    return (
        f"Task {task_def['id']}: {task_def['title']}\n\n"
        f"{task_def['prompt'].strip()}\n\n"
        f"{OUTPUT_FORMAT_INSTRUCTIONS}"
    )


def build_parse_failure_message() -> str:
    return (
        "Your response did not contain any valid "
        '<file path="...">...</file> block. Please resend your complete '
        "solution using that exact format."
    )


def build_repair_message(failing_tests: list) -> str:
    lines = ["Your previous solution failed verification.", "Failing tests:"]
    lines += [f"- {t}" for t in failing_tests] if failing_tests else ["- (no test names captured)"]
    lines.append(
        "Please fix the implementation and return the complete updated "
        'file(s) again, using the same <file path="...">...</file> format.'
    )
    return "\n".join(lines)


def _serialize_prompt(system_prompt: str, messages: list) -> str:
    return json.dumps({"system": system_prompt, "messages": messages}, indent=2)


class RealSolver:
    """Calls the Anthropic API. API key is read from ANTHROPIC_API_KEY at
    call time and is never logged or hardcoded."""

    def __init__(self, logger):
        import anthropic  # local import so --dry-run never requires the package to be configured

        api_key = os.environ.get(config.ANTHROPIC_API_KEY_ENV_VAR)
        if not api_key:
            raise RuntimeError(
                f"{config.ANTHROPIC_API_KEY_ENV_VAR} is not set in the environment"
            )
        client_kwargs = {"api_key": api_key}
        if config.ANTHROPIC_BASE_URL:
            client_kwargs["base_url"] = config.ANTHROPIC_BASE_URL
        self.client = anthropic.Anthropic(**client_kwargs)
        self.logger = logger

    def call(self, system_prompt: str, messages: list, task_id: str, iteration: int) -> str:
        response = self.client.messages.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
            system=system_prompt,
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        prompt_full = _serialize_prompt(system_prompt, messages)
        self.logger.log_api_call(task_id, iteration, prompt_full, text, usage)
        return text

    def call_summary(self, system_prompt: str, messages: list, session_boundary_after: str) -> str:
        response = self.client.messages.create(
            model=config.MODEL,
            max_tokens=config.ARM_A_SUMMARY_MAX_TOKENS,
            temperature=config.TEMPERATURE,
            system=system_prompt,
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        prompt_full = _serialize_prompt(system_prompt, messages)
        self.logger.log_summary_call(session_boundary_after, prompt_full, text, usage)
        return text


class DryRunSolver:
    """Replaces the API with a canned, hand-written correct solution per
    task, read from harness/fixtures/<task_id>.txt. Used by --dry-run.
    Always returns the same fixture regardless of repair messages, which is
    exactly what should happen with a real, unretractable correct solution:
    it either satisfies verification or it structurally can't (e.g. T7
    against stale Arm B ledger assertions)."""

    def __init__(self, logger):
        self.logger = logger

    def _fixture_text(self, task_id: str) -> str:
        path = config.FIXTURES_DIR / f"{task_id}.txt"
        return path.read_text(encoding="utf-8")

    def call(self, system_prompt: str, messages: list, task_id: str, iteration: int) -> str:
        text = self._fixture_text(task_id)
        prompt_full = _serialize_prompt(system_prompt, messages)
        usage = {"input_tokens": 0, "output_tokens": 0}
        self.logger.log_api_call(task_id, iteration, prompt_full, text, usage)
        return text

    def call_summary(self, system_prompt: str, messages: list, session_boundary_after: str) -> str:
        text = "[dry-run summary placeholder]"
        prompt_full = _serialize_prompt(system_prompt, messages)
        usage = {"input_tokens": 0, "output_tokens": 0}
        self.logger.log_summary_call(session_boundary_after, prompt_full, text, usage)
        return text
