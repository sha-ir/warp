# docs/specs Axis-Primary Reorganization — Design

**Date:** 2026-06-14
**Status:** Approved (brainstorm output)
**Scope:** Restructure `docs/specs/` for the improved-keybindings initiative only — a one-time content move, no source-code changes.
**Optimized for:** Navigating by axis, with a reading-order index.

## Problem

All 47 files of the improved-keybindings initiative sit flat under `docs/specs/`,
organized **by phase** (one folder per pipeline stage). This makes the directory hard to
understand:

- The `2026-06-13-improved-keybindings-` prefix repeats across 5 sibling entries.
- Folders don't sort in logical phase order (`code-investigation…`, `decision…`,
  `design-readiness…`, `end-goals`, `spike…` — alpha order ≠ pipeline order).
- There is no top-level index or map.
- The dominant access pattern is **by axis** ("everything about axis-3 layering"), but the
  layout is by phase, so tracing one axis means opening five folders.

## Goal

Make **navigate-by-axis** a filesystem reality, and capture the **reading order** in one index.

## Current state

One initiative with two cross-cutting dimensions:

- **Phase** (current folder dimension): end-goals → design-readiness-questions →
  code-investigation-answers → decision-briefs → spike-designs → results.
- **Axis** (current file dimension): `axis-1` … `axis-6` + `cross-axis-sequencing`
  (named `initiative-wide-cross-axis` in the readiness-questions phase), plus spike IDs
  (`X1`, `X6`, `X9`, `A3-Q4`, …) in `results/`.

The mapping is clean: every axis (and the cross-axis dimension) has exactly **one file per
phase**, so phases collapse into per-axis files without gaps.

## Target structure

```
docs/specs/2026-06-13-improved-keybindings/
├── README.md                       ← NEW index (reading order + phase×axis matrix + status)
├── end-goals.md
├── axis-1-config-portable-live-data/
│   ├── readiness-questions.md
│   ├── code-answers.md
│   ├── decision-brief.md
│   └── spike-design.md
├── axis-2-scope-and-context-control/       (same 4 files)
├── axis-3-layering-precedence-unbinding/   (same 4 files)
├── axis-4-modality-pluggable/              (same 4 files)
├── axis-5-discoverability-and-conflicts/   (same 4 files)
├── axis-6-cross-cutting-foundation/        (same 4 files)
├── cross-axis-sequencing/
│   ├── readiness-questions.md
│   ├── code-answers.md
│   ├── decision-brief.md
│   └── spike-design.md             (existing cross-axis file + appended run-portfolio)
└── spike-results/                  ← old spike-designs/results/, contents unchanged
    ├── README.md
    └── x1-…, x9-…, a3-q4-…, etc.
```

### Phase → filename convention (applied in every axis folder)

| Current phase folder           | becomes file              |
|--------------------------------|---------------------------|
| `design-readiness-questions`   | `readiness-questions.md`  |
| `code-investigation-answers`   | `code-answers.md`         |
| `decision-briefs`              | `decision-brief.md`       |
| `spike-designs`                | `spike-design.md`         |

## Move map

All moves use `git mv` to preserve history. `N` = 1…6.

- `2026-06-13-improved-keybindings-end-goals-design.md` → `…/improved-keybindings/end-goals.md`
- `…-design-readiness-questions/axis-N.md` → `…/axis-N-*/readiness-questions.md`
- `…-design-readiness-questions/initiative-wide-cross-axis.md` → `…/cross-axis-sequencing/readiness-questions.md`
- `…-code-investigation-answers/axis-N.md` → `…/axis-N-*/code-answers.md`
- `…-code-investigation-answers/cross-axis-sequencing.md` → `…/cross-axis-sequencing/code-answers.md`
- `…-decision-briefs/axis-N.md` → `…/axis-N-*/decision-brief.md`
- `…-decision-briefs/cross-axis-sequencing.md` → `…/cross-axis-sequencing/decision-brief.md`
- `…-spike-designs/axis-N.md` → `…/axis-N-*/spike-design.md`
- `…-spike-designs/cross-axis-sequencing.md` → `…/cross-axis-sequencing/spike-design.md`
- `…-spike-designs/results/` → `…/spike-results/` (whole directory, contents and its README unchanged)

Axis folder names keep their full descriptive slug (e.g. `axis-3-layering-precedence-unbinding`),
matching the existing per-file slugs.

## Handling the 4 phase READMEs

The phase READMEs are not moved 1:1; their content is redistributed so nothing valuable is lost:

- **Reading-order narrative** and overall status → top-level `README.md`.
- **Phase × axis matrix** (rows = the 6 axes + cross-axis; cols = the 4 per-axis phases
  `readiness-questions` / `code-answers` / `decision-brief` / `spike-design`; cells = relative
  links to each file) → top-level `README.md`. `end-goals.md` (initiative-wide) and
  `spike-results/` (spike-keyed) are linked separately above/below the matrix. This is the
  by-axis navigation surface.
- **Spike run-portfolio / wave plan** (currently in `spike-designs/README.md`) → appended to
  `cross-axis-sequencing/spike-design.md` (it is inherently a sequencing artifact).
- Any remaining per-phase context that is still useful → folded into the top `README.md`.

After redistribution the 4 phase-level READMEs are deleted.

## Link integrity

Moving files breaks existing relative links between phase folders (e.g. each phase README links
to its sibling phases; spike designs link to `results/`). After all `git mv`s:

1. Update intra-initiative relative links to the new paths.
2. The `end-goals.md` link to `../../.understand-anything/keybindings-architecture-report.md`
   gains one directory level (now `../../../.understand-anything/…`) — fix it.
3. Grep the whole repo for references to the old `docs/specs/2026-06-13-improved-keybindings-*`
   paths (other docs, skills, memory) and update any hits.

## Non-goals

- No changes to file *contents* beyond link fixes and the README redistribution above.
- No new convention for future initiatives (this is a one-off fix for this tree).
- No splitting spike results per axis (Approach B was rejected — spike IDs don't map cleanly
  to axes).

## Verification

- `find docs/specs/2026-06-13-improved-keybindings -type f` shows exactly the target tree.
- No file remains directly under `docs/specs/` except the one initiative folder.
- `git log --follow` works on a moved file (history preserved).
- A repo-wide grep for the old paths returns no stale references.
- Every link in the new `README.md` resolves to an existing file.
