#!/usr/bin/env bash
# Full pipeline: extract (LLM per chapter) → enrich (one LLM call) → merge.
#
# Run in a FREE TMUX PANE in the current window — extract + enrich make many
# LLM calls and can take 10+ minutes. Never run in the Claude shell.
#
# Usage:
#   ./build.sh                            # full pipeline, book 1, all chapters
#   ./build.sh --only merge               # just rebuild data.json (no LLM calls)
#   ./build.sh --chapters 28              # re-extract one chapter, then enrich + merge
#   ./build.sh --chapters 1-20            # re-extract a range
#   ./build.sh --chapters 4,9,28          # specific chapters
#   ./build.sh --skip-existing            # only fill in chapters not yet extracted
#   ./build.sh --skip-extract             # enrich + merge using current extractions
#   ./build.sh --dry-run                  # preview the plan without running

set -euo pipefail

BOOK=1
CHAPTERS=""
SKIP_EXTRACT=0
SKIP_ENRICH=0
SKIP_MERGE=0
SKIP_EXISTING=0
DRY_RUN=0

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
  cat <<'EOF'

Options:
  --book N             Book number (default: 1)
  --chapters SPEC      N, A-B, or A,B,C; default = all chapters >= 1
  --skip-existing      Skip chapters whose extracted JSON already exists
  --skip-extract       Skip the per-chapter LLM stage
  --skip-enrich        Skip the global LLM enrichment stage
  --skip-merge         Skip the deterministic merge stage
  --only STAGE         Run only one stage (extract|enrich|merge)
  --dry-run            Print the plan, don't execute
  -h, --help           Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --book) BOOK="$2"; shift 2 ;;
    --chapters) CHAPTERS="$2"; shift 2 ;;
    --skip-existing) SKIP_EXISTING=1; shift ;;
    --skip-extract) SKIP_EXTRACT=1; shift ;;
    --skip-enrich) SKIP_ENRICH=1; shift ;;
    --skip-merge) SKIP_MERGE=1; shift ;;
    --only)
      case "$2" in
        extract) SKIP_ENRICH=1; SKIP_MERGE=1 ;;
        enrich)  SKIP_EXTRACT=1; SKIP_MERGE=1 ;;
        merge)   SKIP_EXTRACT=1; SKIP_ENRICH=1 ;;
        *) echo "Invalid --only stage: $2" >&2; exit 1 ;;
      esac
      shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage >&2; exit 1 ;;
  esac
done

cd "$(dirname "${BASH_SOURCE[0]}")"

discover_chapters() {
  for f in "Books/$BOOK"/*.md; do
    [[ -e "$f" ]] || continue
    local name="${f##*/}"
    local n="${name%% *}"
    [[ "$n" =~ ^[0-9]+$ ]] || continue
    (( n >= 1 )) || continue   # skip ch 0 (intro) by default
    echo "$n"
  done | sort -n
}

expand_spec() {
  local spec="$1"
  if [[ "$spec" == *-* ]]; then
    seq "${spec%-*}" "${spec#*-}"
  elif [[ "$spec" == *,* ]]; then
    echo "$spec" | tr ',' '\n' | sed '/^$/d'
  else
    echo "$spec"
  fi
}

CHAPTERS_TO_EXTRACT=()
if [[ -z "$CHAPTERS" ]]; then
  while read -r n; do CHAPTERS_TO_EXTRACT+=("$n"); done < <(discover_chapters)
else
  while read -r n; do CHAPTERS_TO_EXTRACT+=("$n"); done < <(expand_spec "$CHAPTERS")
fi

if (( SKIP_EXISTING == 1 )); then
  KEPT=()
  for n in "${CHAPTERS_TO_EXTRACT[@]}"; do
    f=$(printf "extracted/%d/%02d.json" "$BOOK" "$n")
    [[ -f "$f" ]] || KEPT+=("$n")
  done
  CHAPTERS_TO_EXTRACT=()
  (( ${#KEPT[@]} > 0 )) && CHAPTERS_TO_EXTRACT=("${KEPT[@]}")
fi

echo "=== Plan ==="
echo "  book:     $BOOK"
if (( SKIP_EXTRACT == 1 )); then
  echo "  extract:  SKIP"
else
  echo "  extract:  ${#CHAPTERS_TO_EXTRACT[@]} chapters"
  (( ${#CHAPTERS_TO_EXTRACT[@]} > 0 )) && echo "            chapters: ${CHAPTERS_TO_EXTRACT[*]}"
fi
echo "  enrich:   $([[ $SKIP_ENRICH == 1 ]] && echo SKIP || echo YES)"
echo "  merge:    $([[ $SKIP_MERGE == 1 ]] && echo SKIP || echo YES)"
(( DRY_RUN == 1 )) && echo "  DRY RUN - no commands will execute"
echo

run() {
  echo "$ $*"
  (( DRY_RUN == 0 )) && "$@"
}

if (( SKIP_EXTRACT == 0 )); then
  if (( ${#CHAPTERS_TO_EXTRACT[@]} == 0 )); then
    echo "=== Extract: nothing to do"
  else
    echo "=== Extract: book $BOOK, ${#CHAPTERS_TO_EXTRACT[@]} chapters"
    for n in "${CHAPTERS_TO_EXTRACT[@]}"; do
      run uv run extract.py --book "$BOOK" --ch "$n"
    done
  fi
fi

(( SKIP_ENRICH == 0 )) && { echo "=== Enrich: book $BOOK"; run uv run enrich.py --book "$BOOK"; }
(( SKIP_MERGE  == 0 )) && { echo "=== Merge";              run uv run merge.py; }

echo "=== DONE"
