#!/usr/bin/env python
"""Every path the front-matter documentation names must exist.

WHY.  This repository shipped a public documentation site that was five months stale, a
documentation index pointing at a directory that had been deleted, and test messages naming
`docs/troubleshooting.md` after that file was gone.  None of it was caught, because prose is not
compiled.  A document that maps claims to artifacts is worth exactly as much as the paths in it
are real, so the paths are checked and the prose is not.

Checked files are the ones a reader is sent to first: the entry point, the deposit map, and the
orientation documents.  A path is anything that looks like a repository path inside backticks --
prose is ignored, so the check has no opinion about what the sentences say.

    python scripts/analysis/check_doc_paths.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = ["README.md", "DEPOSITS.md", "CLAUDE.md", "AGENTS.md", "ZENODO_DEPOSIT.md",
        "PROJECT_DESCRIPTION.md"]

#: The directories a documented path may start with. NAMED, NOT INFERRED: the first version matched
#: any `word/word`, which made `beta/T` -- a ratio in the thermodynamics section -- a missing path.
#: Prose is full of slashes that are not paths.
TOP = "paper|src|scripts|configs|results|tests|notebooks|checkpoints|figures|data|web|logs"
#: A backticked token that looks like a path into this repository: either it carries a file
#: extension we recognise, or it starts at one of the directories above.
PATH_RE = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_./*-]*\.(?:py|sh|md|tex|pdf|json|csv|ya?ml|txt)"
                     rf"|(?:{TOP})/[A-Za-z0-9_./*-]*)`")
#: Named on purpose without existing yet, or standing for a family rather than a file.
EXEMPT = {
    "paper/grounding_paradox.pdf", "paper/grounding_paradox_si.pdf",   # build products
}


def main() -> int:
    missing: list[tuple[str, str]] = []
    checked = 0
    for doc in DOCS:
        p = REPO / doc
        if not p.exists():
            missing.append((doc, "(the document itself is missing)"))
            continue
        for m in PATH_RE.finditer(p.read_text(encoding="utf8")):
            raw = m.group(1).rstrip("/")
            if raw in EXEMPT or raw.startswith("http"):
                continue
            checked += 1
            if any(c in raw for c in "*?"):          # a glob stands for a family
                hits = list(REPO.glob(raw))
            elif "/" in raw:                          # a path is a path
                hits = [REPO / raw] if (REPO / raw).exists() else []
            else:
                # A BARE FILENAME IS A NAME, NOT A PATH.  The orientation docs say "loss.py" and
                # "comparison.json" meaning the file wherever it lives, and resolving those against
                # the repository root reported forty false failures on the first run. Satisfy them
                # from anywhere in the tree.
                hits = [p for p in REPO.rglob(raw) if ".git" not in p.parts][:1]
                if not hits:
                    # A KIND OF FILE, NOT ONE FILE.  The docs say `model_card.json` meaning the
                    # per-run card, which is written as `<arm>_<seed>.model_card.json`. Naming the
                    # kind is correct prose; requiring an exact basename would force the docs to
                    # name one arbitrary instance.
                    hits = [p for p in REPO.rglob(f"*{raw}") if ".git" not in p.parts][:1]
            if not hits:
                missing.append((doc, raw))
    if missing:
        print(f"FAIL: {len(missing)} path(s) named in the front-matter docs do not exist\n")
        for doc, raw in missing:
            print(f"  {doc:<18} {raw}")
        return 1
    print(f"ok: {checked} documented paths all exist, across {len(DOCS)} documents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
