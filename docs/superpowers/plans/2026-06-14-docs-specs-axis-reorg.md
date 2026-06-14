# docs/specs Axis-Primary Reorganization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `docs/specs/` so the improved-keybindings initiative is navigable by axis (one folder per axis, one file per phase) under a single dated initiative folder, with a top-level reading-order index.

**Architecture:** Pure documentation move. `git mv` every file into the new tree, redistribute the four phase READMEs into a new top-level `README.md` index (+ append the spike run-portfolio to `cross-axis-sequencing/spike-design.md`), then repair the links the move breaks. No source code changes.

**Tech Stack:** git, bash, markdown. Spec: `docs/superpowers/specs/2026-06-14-docs-specs-axis-reorg-design.md`.

---

## Reference: path mapping

Initiative folder: `docs/specs/2026-06-13-improved-keybindings/` (called `$INIT` below).

Axis slugs (unchanged from existing per-file slugs):

| Axis | slug |
|------|------|
| 1 | `axis-1-config-portable-live-data` |
| 2 | `axis-2-scope-and-context-control` |
| 3 | `axis-3-layering-precedence-unbinding` |
| 4 | `axis-4-modality-pluggable` |
| 5 | `axis-5-discoverability-and-conflicts` |
| 6 | `axis-6-cross-cutting-foundation` |
| cross | `cross-axis-sequencing` |

Phase → filename:

| Old phase folder | new filename |
|------------------|--------------|
| `…-design-readiness-questions` | `readiness-questions.md` |
| `…-code-investigation-answers` | `code-answers.md` |
| `…-decision-briefs` | `decision-brief.md` |
| `…-spike-designs` | `spike-design.md` |

Special: readiness-questions' cross-axis file is named `initiative-wide-cross-axis.md` (not `cross-axis-sequencing.md`).

---

## Task 1: Create the initiative tree and move all content files

**Files:** moves only; no edits yet.

- [ ] **Step 1: Create folders**

```bash
cd /home/mhb/warp/docs/specs
INIT=2026-06-13-improved-keybindings
mkdir -p "$INIT"/{axis-1-config-portable-live-data,axis-2-scope-and-context-control,axis-3-layering-precedence-unbinding,axis-4-modality-pluggable,axis-5-discoverability-and-conflicts,axis-6-cross-cutting-foundation,cross-axis-sequencing}
```

- [ ] **Step 2: Move end-goals**

```bash
git mv 2026-06-13-improved-keybindings-end-goals-design.md "$INIT/end-goals.md"
```

- [ ] **Step 3: Move the six axis files for each phase**

```bash
for n in 1-config-portable-live-data 2-scope-and-context-control 3-layering-precedence-unbinding 4-modality-pluggable 5-discoverability-and-conflicts 6-cross-cutting-foundation; do
  git mv "2026-06-13-improved-keybindings-design-readiness-questions/axis-$n.md" "$INIT/axis-$n/readiness-questions.md"
  git mv "2026-06-13-improved-keybindings-code-investigation-answers/axis-$n.md" "$INIT/axis-$n/code-answers.md"
  git mv "2026-06-13-improved-keybindings-decision-briefs/axis-$n.md"           "$INIT/axis-$n/decision-brief.md"
  git mv "2026-06-13-improved-keybindings-spike-designs/axis-$n.md"             "$INIT/axis-$n/spike-design.md"
done
```

- [ ] **Step 4: Move the cross-axis files**

```bash
git mv 2026-06-13-improved-keybindings-design-readiness-questions/initiative-wide-cross-axis.md "$INIT/cross-axis-sequencing/readiness-questions.md"
git mv 2026-06-13-improved-keybindings-code-investigation-answers/cross-axis-sequencing.md       "$INIT/cross-axis-sequencing/code-answers.md"
git mv 2026-06-13-improved-keybindings-decision-briefs/cross-axis-sequencing.md                  "$INIT/cross-axis-sequencing/decision-brief.md"
git mv 2026-06-13-improved-keybindings-spike-designs/cross-axis-sequencing.md                    "$INIT/cross-axis-sequencing/spike-design.md"
```

- [ ] **Step 5: Move the results directory wholesale**

```bash
git mv 2026-06-13-improved-keybindings-spike-designs/results "$INIT/spike-results"
```

- [ ] **Step 6: Verify only READMEs remain in the old phase folders, then sanity-check the tree**

```bash
find 2026-06-13-improved-keybindings-* -maxdepth 1 -type f
# Expected: only the four README.md files (one per old phase folder)
find "$INIT" -type f | sort
# Expected: end-goals.md, 6 axis dirs × 4 files, cross-axis-sequencing × 4 files, spike-results/* (15 files incl its README)
```

- [ ] **Step 7: Commit the moves**

```bash
git add -A && git commit -m "docs(specs): move keybindings tree into axis-primary layout"
```

---

## Task 2: Fix `.understand-anything/` link depth in moved files

Moved axis/cross-axis files are now one directory deeper, so `../../../.understand-anything/` must become `../../../../.understand-anything/`, and `end-goals.md` (was at `docs/specs/`, used `../../`) must become `../../../`. Absolute paths (`/home/mhb/warp/.understand-anything/...`) and inline-code mentions without a link target are left alone.

- [ ] **Step 1: See current relative report links**

```bash
cd /home/mhb/warp/docs/specs/2026-06-13-improved-keybindings
grep -rnoE "\((\.\./)+\.understand-anything/[^)]*\)" .
```

- [ ] **Step 2: Bump depth in the axis + cross-axis files (3 ups → 4 ups)**

```bash
grep -rlE "\((\.\./){3}\.understand-anything/" axis-*/ cross-axis-sequencing/ \
  | xargs -r sed -i 's#(\.\./\.\./\.\./\.understand-anything/#(../../../../.understand-anything/#g'
```

- [ ] **Step 3: Fix end-goals.md (2 ups → 3 ups)**

```bash
sed -i 's#(\.\./\.\./\.understand-anything/#(../../../.understand-anything/#g' end-goals.md
```

- [ ] **Step 4: Verify every relative report link now resolves**

```bash
for f in $(grep -rlE "\((\.\./)+\.understand-anything/" .); do
  d=$(dirname "$f")
  grep -oE "\((\.\./)+\.understand-anything/[^):]*" "$f" | sed 's/^(//' | while read -r rel; do
    [ -f "$d/$rel" ] && echo "OK  $f -> $rel" || echo "BROKEN $f -> $rel"
  done
done | grep BROKEN || echo "all report links resolve"
```

Expected: `all report links resolve`.

---

## Task 3: Write the top-level `README.md` index

**Files:** Create `docs/specs/2026-06-13-improved-keybindings/README.md`.

Before writing, harvest reusable framing from the four phase READMEs (status lines, phase descriptions) so the index is faithful:

```bash
cd /home/mhb/warp/docs/specs
head -20 2026-06-13-improved-keybindings-*/README.md
```

- [ ] **Step 1: Create the index file**

Write `docs/specs/2026-06-13-improved-keybindings/README.md` with this content (adjust the per-phase one-liners only if the harvested READMEs describe them differently):

```markdown
# Improved Keybindings — Initiative

A multi-project initiative decomposing **"Improved keybindings"** across three fronts
(engine, settings UI, modal modes) into per-axis design work. Grounded in the adversarial
architecture report at
[`.understand-anything/keybindings-architecture-report.md`](../../../.understand-anything/keybindings-architecture-report.md).

**Start here:** [`end-goals.md`](end-goals.md) — the north-star laddered end goals.

## Reading order

1. [`end-goals.md`](end-goals.md) — what we're building and why (initiative-wide).
2. **Readiness questions** — the open design-readiness questions per axis.
3. **Code answers** — verified, code-grounded answers to those questions.
4. **Decision briefs** — the resulting design decisions per axis.
5. **Spike designs** — throwaway-build designs that de-risk the decisions.
6. [`spike-results/`](spike-results/README.md) — empirical outcomes, keyed by spike ID.

For the cross-cutting sequencing / run-portfolio across all axes, see
[`cross-axis-sequencing/spike-design.md`](cross-axis-sequencing/spike-design.md).

## Phase × axis matrix

Each axis folder holds its whole journey. Columns are the four per-axis phases.

| Axis | Readiness questions | Code answers | Decision brief | Spike design |
|------|---------------------|--------------|----------------|--------------|
| 1 · config-portable-live-data | [q](axis-1-config-portable-live-data/readiness-questions.md) | [a](axis-1-config-portable-live-data/code-answers.md) | [b](axis-1-config-portable-live-data/decision-brief.md) | [s](axis-1-config-portable-live-data/spike-design.md) |
| 2 · scope-and-context-control | [q](axis-2-scope-and-context-control/readiness-questions.md) | [a](axis-2-scope-and-context-control/code-answers.md) | [b](axis-2-scope-and-context-control/decision-brief.md) | [s](axis-2-scope-and-context-control/spike-design.md) |
| 3 · layering-precedence-unbinding | [q](axis-3-layering-precedence-unbinding/readiness-questions.md) | [a](axis-3-layering-precedence-unbinding/code-answers.md) | [b](axis-3-layering-precedence-unbinding/decision-brief.md) | [s](axis-3-layering-precedence-unbinding/spike-design.md) |
| 4 · modality-pluggable | [q](axis-4-modality-pluggable/readiness-questions.md) | [a](axis-4-modality-pluggable/code-answers.md) | [b](axis-4-modality-pluggable/decision-brief.md) | [s](axis-4-modality-pluggable/spike-design.md) |
| 5 · discoverability-and-conflicts | [q](axis-5-discoverability-and-conflicts/readiness-questions.md) | [a](axis-5-discoverability-and-conflicts/code-answers.md) | [b](axis-5-discoverability-and-conflicts/decision-brief.md) | [s](axis-5-discoverability-and-conflicts/spike-design.md) |
| 6 · cross-cutting-foundation | [q](axis-6-cross-cutting-foundation/readiness-questions.md) | [a](axis-6-cross-cutting-foundation/code-answers.md) | [b](axis-6-cross-cutting-foundation/decision-brief.md) | [s](axis-6-cross-cutting-foundation/spike-design.md) |
| cross-axis-sequencing | [q](cross-axis-sequencing/readiness-questions.md) | [a](cross-axis-sequencing/code-answers.md) | [b](cross-axis-sequencing/decision-brief.md) | [s](cross-axis-sequencing/spike-design.md) |

## Empirical results

Spike results are keyed by spike ID (cross-cutting), not by axis — see
[`spike-results/`](spike-results/README.md).
```

- [ ] **Step 2: Verify every link in the index resolves**

```bash
cd docs/specs/2026-06-13-improved-keybindings
grep -oE "\]\(([^)]+)\)" README.md | sed -E 's/^\]\(//; s/\)$//' | while read -r rel; do
  case "$rel" in /*|http*) continue;; esac
  [ -e "$rel" ] && echo "OK  $rel" || echo "BROKEN $rel"
done | grep BROKEN || echo "all index links resolve"
```

Expected: `all index links resolve`.

---

## Task 4: Append run-portfolio to cross-axis spike-design, then delete phase READMEs

The spike run-portfolio / wave plan currently lives in `…-spike-designs/README.md`. It is a sequencing artifact and belongs in `cross-axis-sequencing/spike-design.md` (per the spec).

- [ ] **Step 1: Inspect the spike-designs README to identify the run-portfolio section**

```bash
cd /home/mhb/warp/docs/specs
sed -n '1,40p' 2026-06-13-improved-keybindings-spike-designs/README.md
```

- [ ] **Step 2: Append the run-portfolio to the cross-axis spike-design**

Append a clearly-delimited section to `2026-06-13-improved-keybindings/cross-axis-sequencing/spike-design.md`. Start it with a separator and heading, then paste the run-portfolio content (the "Run portfolio", "Run order", "Prerequisites" sections) from the spike-designs README verbatim:

```markdown

---

## Spike run portfolio (moved from the spike-designs phase index)

<paste the Run portfolio / Run order / Prerequisites sections here>
```

- [ ] **Step 3: Confirm no unique, still-relevant content remains only in the phase READMEs**

```bash
cd /home/mhb/warp/docs/specs
for f in 2026-06-13-improved-keybindings-*/README.md; do echo "===== $f ====="; cat "$f"; done | less -FX
```

Anything still useful (status framing, phase intent) should already be reflected in the new top `README.md` from Task 3 — fold in anything missing before deleting.

- [ ] **Step 4: Delete the four phase READMEs and the now-empty phase folders**

```bash
git rm 2026-06-13-improved-keybindings-design-readiness-questions/README.md \
       2026-06-13-improved-keybindings-code-investigation-answers/README.md \
       2026-06-13-improved-keybindings-decision-briefs/README.md \
       2026-06-13-improved-keybindings-spike-designs/README.md
rmdir 2026-06-13-improved-keybindings-design-readiness-questions \
      2026-06-13-improved-keybindings-code-investigation-answers \
      2026-06-13-improved-keybindings-decision-briefs \
      2026-06-13-improved-keybindings-spike-designs
```

- [ ] **Step 5: Verify docs/specs now contains exactly one entry**

```bash
ls docs/specs
# Expected: only  2026-06-13-improved-keybindings
```

---

## Task 5: Repair remaining internal cross-file links

After Tasks 1–4, the only broken internal links left are: (a) date-prefixed links that pointed at the now-deleted phase READMEs, and (b) sibling links that used the old flat filenames (e.g. `(./axis-4-modality-pluggable.md)`, `(../cross-axis-sequencing.md#anchor)`). Note: links *inside* `spike-results/` that point at sibling result files (e.g. `(./x9-tombstone-spike-results.md)`) are still valid because the folder moved as a unit — leave those.

- [ ] **Step 1: List every remaining stale internal reference**

```bash
cd /home/mhb/warp/docs/specs/2026-06-13-improved-keybindings
echo "--- date-prefixed (point at deleted phase folders) ---"
grep -rnoE "\([^)]*2026-06-13-improved-keybindings-[^)]*\)" .
echo "--- old flat sibling filenames ---"
grep -rnoE "\(\.\.?/(axis-[0-9]|cross-axis-sequencing|initiative-wide-cross-axis)[^)]*\)" .
```

- [ ] **Step 2: Rewrite each hit using the Reference path mapping at the top of this plan**

For each match, point it at the new location. Rules:
- A date-prefixed link to a phase folder's `README.md` → point at the top index `README.md` (e.g. from an axis file: `../README.md`) or, if it clearly meant a specific axis+phase, that file.
- A link `(./axis-K-<slug>.md)` from within a phase context → the same axis, same phase as the *linking* file's phase: e.g. inside `axis-2-*/code-answers.md`, a link to `(./axis-4-modality-pluggable.md)` becomes `(../axis-4-modality-pluggable/code-answers.md)`.
- A link `(../cross-axis-sequencing.md#anchor)` → `(../cross-axis-sequencing/<same-phase>.md#anchor)`.
- Preserve any `#anchor` fragment unchanged.

Edit the files directly (use the Edit tool / `sed` per file). The candidate set is small — from the pre-move survey: `code-answers` axis-2 (4), axis-4 (1); `decision-brief` axis-2 (2), axis-4 (3); plus any sibling-style links surfaced in Step 1.

- [ ] **Step 3: Verify zero stale internal references remain**

```bash
cd /home/mhb/warp/docs/specs/2026-06-13-improved-keybindings
grep -rnoE "\([^)]*2026-06-13-improved-keybindings-[^)]*\)" . && echo "STILL STALE" || echo "no date-prefixed stale links"
```

Expected: `no date-prefixed stale links`.

- [ ] **Step 4: Resolve-check all relative markdown links in the initiative tree**

```bash
cd /home/mhb/warp/docs/specs/2026-06-13-improved-keybindings
fail=0
grep -rln "]\(" . | while read -r f; do
  d=$(dirname "$f")
  grep -oE "\]\(([^)]+)\)" "$f" | sed -E 's/^\]\(//; s/\)$//' | while read -r rel; do
    case "$rel" in /*|http*|\#*) continue;; esac
    target="${rel%%#*}"
    [ -z "$target" ] && continue
    [ -e "$d/$target" ] || echo "BROKEN in $f -> $rel"
  done
done | sort -u | tee /tmp/broken_links.txt
test ! -s /tmp/broken_links.txt && echo "all internal links resolve" || echo "see /tmp/broken_links.txt"
```

Expected: `all internal links resolve`. (Pre-existing broken links to non-co-located `*-plan.md` files in `spike-results/`, if any, are out of scope — confirm they predate this change with `git log` before dismissing.)

- [ ] **Step 5: Commit**

```bash
cd /home/mhb/warp
git add -A && git commit -m "docs(specs): add initiative index, fold phase READMEs, fix links"
```

---

## Task 6: Fix external references in docs/superpowers/plans

Two plan files reference the old paths.

- [ ] **Step 1: Show the references**

```bash
cd /home/mhb/warp
grep -n "2026-06-13-improved-keybindings" \
  docs/superpowers/plans/2026-06-13-a2-q4-targeting-relation-spike.md \
  docs/superpowers/plans/2026-06-13-a1-q6-torn-read-spike.md
```

- [ ] **Step 2: Rewrite each old path to the new location** using the Reference mapping (e.g. `…-code-investigation-answers/axis-2-scope-and-context-control.md` → `…-improved-keybindings/axis-2-scope-and-context-control/code-answers.md`; a spike-results path keeps its filename under `…-improved-keybindings/spike-results/`). Edit the two files directly.

- [ ] **Step 3: Verify no repo file outside the initiative references old phase paths**

```bash
cd /home/mhb/warp
grep -rn "2026-06-13-improved-keybindings-\(design-readiness-questions\|code-investigation-answers\|decision-briefs\|spike-designs\)" \
  --include=*.md . | grep -v "docs/superpowers/specs/2026-06-14-docs-specs-axis-reorg" \
  | grep -v "docs/superpowers/plans/2026-06-14-docs-specs-axis-reorg" \
  && echo "STILL STALE" || echo "no stale external refs"
```

Expected: `no stale external refs` (the design + this plan legitimately mention old paths in their mapping tables; they are filtered out).

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "docs(plans): update keybindings paths after specs reorg"
```

---

## Task 7: Final verification

- [ ] **Step 1: Tree matches the spec**

```bash
cd /home/mhb/warp
find docs/specs -type f | sort
```

Expected: `docs/specs/2026-06-13-improved-keybindings/` containing `README.md`, `end-goals.md`, six `axis-*/` dirs each with the 4 phase files, `cross-axis-sequencing/` with 4 phase files, and `spike-results/` with its 14 results + README. Nothing else directly under `docs/specs/`.

- [ ] **Step 2: File count is conserved (no content lost)**

```bash
find docs/specs/2026-06-13-improved-keybindings -type f | wc -l
# Expected: 44 = end-goals 1 + axis 6×4=24 + cross-axis 4 + spike-results 14 (13 results + its README) + top README 1.
# The 4 old phase READMEs are deleted and not counted.
```

Adjust the expected count after Step 1 if the harvested inventory differs; the invariant is: every pre-move content file is present exactly once and only the 4 phase READMEs are gone.

- [ ] **Step 3: History preserved on a sample moved file**

```bash
git log --follow --oneline -- docs/specs/2026-06-13-improved-keybindings/axis-3-layering-precedence-unbinding/decision-brief.md | head
```

Expected: shows commits from before the move.

- [ ] **Step 4: No stale references anywhere in the repo**

```bash
grep -rn "improved-keybindings-\(design-readiness-questions\|code-investigation-answers\|decision-briefs\|spike-designs\)/" \
  --include=*.md /home/mhb/warp \
  | grep -vE "docs/superpowers/(specs|plans)/2026-06-14-docs-specs-axis-reorg" \
  && echo "STALE FOUND" || echo "clean"
```

Expected: `clean`.

- [ ] **Step 5: (Optional) update memory** — if `/home/mhb/.claude/projects/-home-mhb-warp/memory/keybindings-improvement-initiative.md` references any old `docs/specs/...` path, update it to the new layout.
