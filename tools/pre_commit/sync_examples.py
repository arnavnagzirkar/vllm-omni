#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pre-commit hook: sync examples/ READMEs to docs/user_guide/examples/.

Two behaviours depending on what is staged:
- If docs/user_guide/examples/ files are staged but no examples/ files are
  staged, the hook aborts the commit and tells the author to edit examples/
  instead.
- If examples/ files are staged, the hook regenerates docs/user_guide/examples/
  and docs/.nav.yml, then stages the generated files so they are included in
  the same commit.

To skip in CI or locally: SKIP=sync-examples-docs git commit ...
"""

import logging
import subprocess
import sys
from pathlib import Path


def get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    # Normalize to forward slashes for portable prefix checks
    return [p.replace("\\", "/") for p in result.stdout.splitlines() if p]


def run_generation() -> int:
    hooks_dir = Path(__file__).parent.parent.parent / "docs" / "mkdocs" / "hooks"
    sys.path.insert(0, str(hooks_dir))

    # Configure the logger that generate_examples.py uses
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        from generate_examples import (  # noqa: PLC0415
            EXAMPLE_DOC_DIR,
            NAV_FILE,
            ROOT_DIR,
            on_startup,
        )
    except ImportError as exc:
        print(f"error: could not import generate_examples: {exc}", file=sys.stderr)
        return 1

    on_startup("build", dirty=False)

    # Stage both the generated docs and the updated nav file
    to_stage = [
        str(EXAMPLE_DOC_DIR.relative_to(ROOT_DIR)),
        str(NAV_FILE.relative_to(ROOT_DIR)),
    ]
    result = subprocess.run(["git", "add"] + to_stage, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"error: git add failed: {result.stderr}", file=sys.stderr)
        return 1

    return 0


def main() -> int:
    staged = get_staged_files()

    examples_changed = any(f.startswith("examples/") for f in staged)
    docs_examples_changed = any(f.startswith("docs/user_guide/examples/") for f in staged)

    if docs_examples_changed and not examples_changed:
        print(
            "error: do not edit docs/user_guide/examples/ directly.\n"
            "Those files are auto-generated from examples/.\n"
            "Edit the corresponding file under examples/ instead.\n"
            "To regenerate: python tools/pre_commit/sync_examples.py --run",
            file=sys.stderr,
        )
        return 1

    if not examples_changed:
        return 0

    return run_generation()


if __name__ == "__main__":
    if "--run" in sys.argv:
        # Allow manual invocation to regenerate without a git commit
        sys.exit(run_generation())
    else:
        sys.exit(main())
