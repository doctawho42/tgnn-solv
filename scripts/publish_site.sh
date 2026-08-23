#!/usr/bin/env bash
# Publish web/index.html and the two compiled PDFs to the gh-pages branch.
#
# Dry by default.  Publishing is outward-facing and the previous site sat five months stale, so
# this prints exactly what would change and does nothing until told twice.
#
#     scripts/publish_site.sh            what would change
#     scripts/publish_site.sh --push     do it
set -euo pipefail
cd "$(dirname "$0")/.."

PUSH=0
[ "${1:-}" = "--push" ] && PUSH=1

ART="paper/grounding_paradox.pdf"
SI="paper/grounding_paradox_si.pdf"

# A PAGE WHOSE LINKS 404 IS WORSE THAN NO PAGE.  index.html links both PDFs by name, so refuse to
# publish unless both were actually built.
for f in "$ART" "$SI" web/index.html; do
  [ -f "$f" ] || { echo "missing: $f  (run ./verify.sh to build the PDFs)" >&2; exit 1; }
done

# The abstract on the page is copied prose. If the manuscript's abstract has moved, the page is
# lying to every reader who does not open the PDF, and that is the one drift worth blocking on.
python - <<'PY' || exit 1
import re, sys, unicodedata
def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower())).strip()
tex = open("paper/grounding_paradox.tex", encoding="utf8").read()
m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S)
a = re.sub(r"%.*", "", m.group(1))
a = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", a)
a = norm(re.sub(r"\\[a-zA-Z]+", "", a))
page = open("web/index.html", encoding="utf8").read()
body = norm(re.sub(r"<[^>]+>", " ", page))
missing = [s for s in (a[:180], a[-180:]) if s not in body]
if missing:
    print("REFUSING: the page's abstract has drifted from paper/grounding_paradox.tex.",
          file=sys.stderr)
    print("  update web/index.html, then publish.", file=sys.stderr)
    sys.exit(1)
print("  abstract on the page matches the manuscript")
PY

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git worktree add -q --detach "$TMP/gh" origin/gh-pages 2>/dev/null || {
  echo "no gh-pages branch on origin; creating an orphan one" >&2
  git worktree add -q --detach "$TMP/gh"
  git -C "$TMP/gh" checkout -q --orphan gh-pages
  git -C "$TMP/gh" rm -rq --cached . 2>/dev/null || true
  rm -rf "$TMP/gh"/* 2>/dev/null || true
}

# The old MkDocs deployment is replaced wholesale, not merged into: leaving its assets behind
# means every stale page it generated stays reachable by URL.
find "$TMP/gh" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp web/index.html "$TMP/gh/index.html"
cp "$ART" "$TMP/gh/grounding_paradox.pdf"
cp "$SI"  "$TMP/gh/grounding_paradox_si.pdf"
touch "$TMP/gh/.nojekyll"

git -C "$TMP/gh" add -A
echo
echo "== what would change on gh-pages"
git -C "$TMP/gh" status --short | sed 's/^/  /'
echo

if [ "$PUSH" -eq 0 ]; then
  echo "dry run. re-run with --push to publish."
  git worktree remove --force "$TMP/gh" 2>/dev/null || true
  exit 0
fi

git -C "$TMP/gh" -c user.name="$(git config user.name)" \
    -c user.email="$(git config user.email)" \
    commit -q -m "site: single page for the submission, replacing the April MkDocs deployment"
git -C "$TMP/gh" push -q --force-with-lease origin HEAD:gh-pages
echo "published to gh-pages."
git worktree remove --force "$TMP/gh" 2>/dev/null || true
