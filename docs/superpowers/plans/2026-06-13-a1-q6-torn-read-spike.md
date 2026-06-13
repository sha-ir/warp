# A1-Q6 Echo-Tolerance Spike — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Earn (not assert) the A1-Q6 verdict "echo-TOLERANCE via write-free idempotent reload, suppression NOT required" by building one adversarial torn-read repro example, running it hard, finalizing the paper findings, and surviving an adversarial refutation pass.

**Architecture:** A throwaway `examples/` bin (the only code artifact) drives the **real** `save_custom_keybindings` via the public `write_custom_keybinding` in a writer thread while reader threads hammer a byte-faithful replica of the private `read_custom_keybindings`, counting torn reads. Config is redirected to a temp dir via `XDG_CONFIG_HOME` with a hard path-assertion so the user's real `keybindings.yaml` is never touched. Findings land in the standalone results doc; an independent skeptic-agent pass tries to refute each one.

**Tech Stack:** Rust, `warp` app crate (package name `warp`), `warpui::keymap::Keystroke`, `serde_yaml` 0.8, std threads. No new dependencies. No production code changes.

**Key facts locked during planning:**
- App crate package name is **`warp`** (not `app`); run examples with `-p warp`.
- `keyboard` is `pub mod` (`app/src/lib.rs:121`) → `warp::keyboard::{write_custom_keybinding, keybinding_file_path, UserDefinedKeybinding, DISABLE_SAVE_ENV_VAR}` are all reachable from an example. **No visibility changes needed.**
- The real write is `#[cfg(feature = "local_fs")]` and `local_fs` is **NOT** in default features → must pass `--features local_fs`, or the write silently no-ops.
- Under `#[cfg(test)]` the save/read/write fns are stubbed to no-ops → the repro **must** be an `examples/` target, not a unit test.
- `Keystroke::parse(impl AsRef<str>) -> anyhow::Result<Self>`; `Keystroke: Clone`.
- `app/examples/` exists (auto-discovery on; `autobins=false` does not affect examples).

---

### Task 1: Scaffold the example with the safety gate

Prove, before writing any repro logic, that the redirect works and the real keybindings file can never be touched.

**Files:**
- Create: `app/examples/keybindings_torn_read.rs`

- [ ] **Step 1: Create the example with redirect + hard path-assertion only**

```rust
//! A1-Q6 adversarial torn-read repro (spike, throwaway).
//!
//! Safety: redirects XDG_CONFIG_HOME to a fresh temp dir and ASSERTS the resolved
//! keybindings path is under it before any write, so the user's real keybindings.yaml
//! can never be touched.
//!
//! Run: cargo run --release -p warp --example keybindings_torn_read --features local_fs

use std::path::PathBuf;

use warp::keyboard::{keybinding_file_path, DISABLE_SAVE_ENV_VAR};

fn main() {
    // Never let the real save no-op out from under us.
    std::env::remove_var(DISABLE_SAVE_ENV_VAR);

    // Redirect config to an isolated temp dir BEFORE any path is computed.
    let tmp = std::env::temp_dir().join(format!("warp_a1q6_torn_{}", std::process::id()));
    std::fs::create_dir_all(&tmp).expect("create temp dir");
    std::env::set_var("XDG_CONFIG_HOME", &tmp);

    // Safety gate: the resolved file MUST live under our temp dir, else abort.
    let path: PathBuf = keybinding_file_path();
    assert!(
        path.starts_with(&tmp),
        "ABORT: keybinding_file_path() = {path:?} is not under temp XDG_CONFIG_HOME {tmp:?}; \
         refusing to run to avoid clobbering the real keybindings.yaml"
    );
    println!("temp XDG_CONFIG_HOME: {tmp:?}");
    println!("keybindings file:     {path:?}");
    println!("safety gate: PASS (resolved path is under temp dir)");

    let _ = std::fs::remove_dir_all(&tmp);
}
```

- [ ] **Step 2: Record the real keybindings file state (to prove it is untouched later)**

Run: `ls -la "$HOME/.config/warp-terminal/" 2>/dev/null | grep keybindings || echo "(no real keybindings.yaml — fine)"`
Expected: either a line for the real file (note its size/mtime) or the "no real" message.

- [ ] **Step 3: Build the example (expect a long first build — full app crate links)**

Run: `cargo build --release -p warp --example keybindings_torn_read --features local_fs`
Expected: compiles. Use a generous timeout (the warp crate is large; first build can take many minutes). If it fails to **link** (not compile), see Risks → fallback.

- [ ] **Step 4: Run it and verify the safety gate**

Run: `cargo run --release -p warp --example keybindings_torn_read --features local_fs`
Expected output (paths will vary):
```
temp XDG_CONFIG_HOME: "/tmp/warp_a1q6_torn_12345"
keybindings file:     "/tmp/warp_a1q6_torn_12345/warp-terminal/keybindings.yaml"
safety gate: PASS (resolved path is under temp dir)
```
The `keybindings file` path MUST start with the temp dir. If the assert panics instead, the redirect is not honored on this platform — STOP and reconsider (do not proceed to writes).

- [ ] **Step 5: Confirm the real file is unchanged**

Run: `ls -la "$HOME/.config/warp-terminal/" 2>/dev/null | grep keybindings || echo "(still no real keybindings.yaml)"`
Expected: identical to Step 2 (same size/mtime, or still absent).

---

### Task 2: Add the concurrent torn-read repro

**Files:**
- Modify: `app/examples/keybindings_torn_read.rs` (replace the whole file)

- [ ] **Step 1: Replace the file with the full repro**

```rust
//! A1-Q6 adversarial torn-read repro (spike, throwaway).
//!
//! Drives the REAL `save_custom_keybindings` (via the public `write_custom_keybinding`,
//! which read-modify-writes the whole map through the truncating `create_file`) in one
//! writer thread, while several reader threads hammer a byte-faithful replica of the
//! private `read_custom_keybindings`, counting torn/empty/partial/parse-None observations.
//!
//! Why a replica reader: `read_custom_keybindings` is private and `#[cfg(test)]`-stubbed;
//! calling it for real needs production changes this spike forbids. `PersistedTrigger(String)`
//! is a serde-transparent newtype, so the on-disk shape is `map<string,string>`, which the
//! replica deserializes identically. Torn-read is a filesystem property, so this is faithful.
//!
//! Safety: redirects XDG_CONFIG_HOME to a temp dir and ASSERTS the resolved path is under
//! it before any write, so the real keybindings.yaml is never touched.
//!
//! Run:  cargo run --release -p warp --example keybindings_torn_read --features local_fs
//! Tune: SPIKE_SECS (default 10), SPIKE_SEED (default 1500), SPIKE_READERS (default 4)

use std::collections::HashMap;
use std::io::BufReader;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

use warp::keyboard::{
    keybinding_file_path, write_custom_keybinding, UserDefinedKeybinding, DISABLE_SAVE_ENV_VAR,
};
use warpui::keymap::Keystroke;

fn env_usize(key: &str, default: usize) -> usize {
    std::env::var(key).ok().and_then(|v| v.parse().ok()).unwrap_or(default)
}

fn main() {
    let seed_entries = env_usize("SPIKE_SEED", 1500);
    let readers = env_usize("SPIKE_READERS", 4).max(1);
    let secs = env_usize("SPIKE_SECS", 10) as u64;

    std::env::remove_var(DISABLE_SAVE_ENV_VAR);
    let tmp = std::env::temp_dir().join(format!("warp_a1q6_torn_{}", std::process::id()));
    std::fs::create_dir_all(&tmp).expect("create temp dir");
    std::env::set_var("XDG_CONFIG_HOME", &tmp);

    let path: PathBuf = keybinding_file_path();
    assert!(
        path.starts_with(&tmp),
        "ABORT: keybinding_file_path() = {path:?} is not under temp XDG_CONFIG_HOME {tmp:?}; \
         refusing to run to avoid clobbering the real keybindings.yaml"
    );
    println!("temp XDG_CONFIG_HOME: {tmp:?}");
    println!("keybindings file:     {path:?}");
    println!("seed={seed_entries} readers={readers} secs={secs}");

    // Seed a fat map through the REAL public write path.
    let ks = Keystroke::parse("ctrl-a").expect("parse keystroke");
    for i in 0..seed_entries {
        write_custom_keybinding(
            format!("spike:action_{i}"),
            UserDefinedKeybinding::keystroke(ks.clone()),
        );
    }

    let stop = Arc::new(AtomicBool::new(false));
    let reads = Arc::new(AtomicU64::new(0));
    let empty = Arc::new(AtomicU64::new(0));
    let parse_none = Arc::new(AtomicU64::new(0));
    let short_map = Arc::new(AtomicU64::new(0));
    let absent = Arc::new(AtomicU64::new(0));

    let mut handles = Vec::new();
    for _ in 0..readers {
        let path = path.clone();
        let stop = stop.clone();
        let (reads, empty, parse_none, short_map, absent) = (
            reads.clone(),
            empty.clone(),
            parse_none.clone(),
            short_map.clone(),
            absent.clone(),
        );
        handles.push(thread::spawn(move || {
            while !stop.load(Ordering::Relaxed) {
                reads.fetch_add(1, Ordering::Relaxed);
                match std::fs::read(&path) {
                    Err(_) => {
                        absent.fetch_add(1, Ordering::Relaxed);
                        continue;
                    }
                    Ok(b) if b.is_empty() => {
                        empty.fetch_add(1, Ordering::Relaxed);
                        continue;
                    }
                    Ok(_) => {}
                }
                match std::fs::File::open(&path) {
                    Err(_) => {
                        absent.fetch_add(1, Ordering::Relaxed);
                    }
                    Ok(f) => {
                        match serde_yaml::from_reader::<_, HashMap<String, String>>(
                            BufReader::new(f),
                        ) {
                            Err(_) => {
                                parse_none.fetch_add(1, Ordering::Relaxed);
                            }
                            Ok(m) if m.len() < seed_entries => {
                                short_map.fetch_add(1, Ordering::Relaxed);
                            }
                            Ok(_) => {}
                        }
                    }
                }
            }
        }));
    }

    // Writer: tight loop of the REAL truncating save (rewrites the whole fat map each call).
    let deadline = Instant::now() + Duration::from_secs(secs);
    let mut writer_iters: u64 = 0;
    while Instant::now() < deadline {
        write_custom_keybinding(
            "spike:action_0".to_string(),
            UserDefinedKeybinding::keystroke(ks.clone()),
        );
        writer_iters += 1;
    }
    stop.store(true, Ordering::Relaxed);
    for h in handles {
        h.join().expect("join reader");
    }

    let (r, e, p, s, a) = (
        reads.load(Ordering::Relaxed),
        empty.load(Ordering::Relaxed),
        parse_none.load(Ordering::Relaxed),
        short_map.load(Ordering::Relaxed),
        absent.load(Ordering::Relaxed),
    );
    let wipe = e + p;
    println!("\n--- A1-Q6 torn-read repro ---");
    println!("writer iters:     {writer_iters}");
    println!("reader reads:     {r}");
    println!("empty reads:      {e}");
    println!("parse-None reads: {p}");
    println!("short-map reads:  {s}");
    println!("absent reads:     {a}");
    println!("WIPE-class (empty + parse-None -> read()==None -> revert-all): {wipe}");
    println!(
        "VERDICT: {}",
        if wipe >= 1 {
            "torn read OBSERVED -> atomic temp+rename REQUIRED (hand to A1-Q5)"
        } else {
            "no torn read this run -> atomic write defensive-only; rerun with larger SPIKE_SEED/SPIKE_SECS to push harder"
        }
    );

    let _ = std::fs::remove_dir_all(&tmp);
}
```

- [ ] **Step 2: Build**

Run: `cargo build --release -p warp --example keybindings_torn_read --features local_fs`
Expected: compiles clean (no warnings that matter for a throwaway).

- [ ] **Step 3: Run the default pass and capture output**

Run: `cargo run --release -p warp --example keybindings_torn_read --features local_fs 2>&1 | tee /tmp/a1q6_run_default.txt`
Expected: a report block ending in a `VERDICT:` line. Either outcome is a valid result.

- [ ] **Step 4: Push harder (adversarial — genuinely try to PRODUCE a torn read)**

Run: `SPIKE_SECS=30 SPIKE_SEED=4000 SPIKE_READERS=8 cargo run --release -p warp --example keybindings_torn_read --features local_fs 2>&1 | tee /tmp/a1q6_run_hard.txt`
Expected: a second report. A `0` WIPE-class only counts after a genuinely hard run (big map, many readers, long duration). Record both runs.

- [ ] **Step 5: Confirm the real file is STILL unchanged**

Run: `ls -la "$HOME/.config/warp-terminal/" 2>/dev/null | grep keybindings || echo "(still no real keybindings.yaml)"`
Expected: unchanged from Task 1.

---

### Task 3: Record Step B results in the results doc

**Files:**
- Modify: `docs/specs/2026-06-13-improved-keybindings-spike-designs/A1-Q6-spike-results.md` (the `## Step B` → `**Result.**` block)

- [ ] **Step 1: Fill the Step B result with the real numbers**

Replace the `_(filled during execution)_` block under Step B with the actual platform, both runs' parameters, the five counts, and the verdict (≥1 WIPE-class ⇒ atomic temp+rename REQUIRED → A1-Q5; 0 across both hard runs ⇒ atomic write defensive-only). Quote the exact `VERDICT:` lines from `/tmp/a1q6_run_default.txt` and `/tmp/a1q6_run_hard.txt`.

---

### Task 4: Finalize Steps A & C against current code

The drafts already exist in the doc; this task verifies each cited fact still matches the code and corrects any drift.

**Files:**
- Modify: `docs/specs/2026-06-13-improved-keybindings-spike-designs/A1-Q6-spike-results.md`

- [ ] **Step 1: Re-verify the Step A precedent-transfer citations**

Run: `grep -n "avoiding write-back loops" crates/settings/src/manager.rs; grep -n "inhibit_writes_for_key" crates/settings/src/manager.rs; grep -n "RecursiveMode::Recursive" app/src/warp_managed_paths_watcher.rs`
Expected: non-empty hits matching the doc's line refs. Adjust line numbers in the doc if they drifted.

- [ ] **Step 2: Re-verify the Step C capture-buffer citations**

Run: `grep -n "modifying_row\|unsaved_binding" app/src/settings_view/keybindings.rs | head; grep -n "set_custom_trigger\|write_custom_keybinding" app/src/settings_view/keybindings.rs | head`
Expected: hits for `modifying_row`/`unsaved_binding` and the two-step set→write. Confirm the doc's claim "reload mutates the global matcher, not `unsaved_binding`" still holds; fix line refs if drifted.

- [ ] **Step 3: Mark Steps A & C as verified in the doc**

Append a one-line "verified against code on 2026-06-13" note to each of Steps A and C.

---

### Task 5: Adversarial refutation pass (Workflow fan-out)

Each standing finding must survive an independent skeptic. This is the ultracode-budget step.

**Files:**
- Modify: `docs/specs/2026-06-13-improved-keybindings-spike-designs/A1-Q6-spike-results.md` (the `## Adversarial verification pass` block)

- [ ] **Step 1: Dispatch one refuter per finding, in parallel**

Run a Workflow with three independent agents, each prompted to REFUTE (default to "refuted" if uncertain) one claim, reading the real code:
1. "The write-free reload cannot loop" — try to find a reload code path that re-persists (e.g., calls `keyboard.rs::write_custom_keybinding`/`remove_custom_keybinding`).
2. "The torn-read verdict from the repro is sound" — attack the harness: is it actually concurrent, does the replica reader diverge from `read_custom_keybindings`, is the WIPE-class mapping correct?
3. "A reload cannot clobber an uncommitted capture buffer" — try to find a path where applying the reloaded map writes `unsaved_binding` or otherwise destroys in-flight capture.

- [ ] **Step 2: Record each verdict (survived / refuted + evidence) in the doc**

A finding that is refuted with code evidence gets corrected or downgraded; one that survives is marked confirmed. Write the outcomes into the `## Adversarial verification pass` section.

---

### Task 6: Final verdict + commit

**Files:**
- Modify: `docs/specs/2026-06-13-improved-keybindings-spike-designs/A1-Q6-spike-results.md` (the `## Final verdict` block)

- [ ] **Step 1: Write the final verdict**

State the resolved answer (expected: "echo-TOLERANCE via write-free idempotent reload; suppression NOT required"), the torn-read empirical bit and where it goes (A1-Q5), the two surviving spec corrections, and any finding the refutation pass changed.

- [ ] **Step 2: Commit (ONLY after the user approves committing)**

Per the working agreement, do not commit until the user says so. When approved:

```bash
git add app/examples/keybindings_torn_read.rs docs/specs/2026-06-13-improved-keybindings-spike-designs/A1-Q6-spike-results.md docs/superpowers/plans/2026-06-13-a1-q6-torn-read-spike.md
git commit -m "spike(keybindings): A1-Q6 adversarial torn-read repro + echo-tolerance findings"
```

---

## Risks & fallbacks

- **Full-crate example build is heavy.** Building a `warp` example links the entire app crate. Use long timeouts; prefer `--release` only if debug is too slow to produce torn reads (debug is actually *better* at exposing races due to slower writes — try debug first if release shows 0). If **linking** the example fails (missing app-init symbols, GPU/native link errors), the fidelity fallback is a thinner harness that replicates BOTH the truncating write (`File::create` + `serde_yaml::to_writer` over a `HashMap<String,String>`) and the read — clearly labeled as lower-fidelity, since it no longer drives the real `save_custom_keybindings`. Lead with the real-function path; only fall back if forced.
- **Zero torn reads.** A `0` result is meaningful only after the hard run (Task 2 Step 4). If `0`, try a **debug** build (slower writes widen the window) and an even larger `SPIKE_SEED`. Report honestly: "not observed under N" is not "impossible."
- **XDG not honored.** The Task 1 assert is the authoritative guard; if it panics, stop — do not weaken it.

## Spec coverage check (self-review)

- Step A (corrected precedent) → Task 4 Step 1 + pre-written doc section. ✓
- Step B (torn-read repro) → Tasks 1–3. ✓
- Step C (UI-clobber trace) → Task 4 Step 2 + pre-written doc section. ✓
- Adversarial verification → Task 5. ✓
- Two spec corrections (Cracks #1/#2) → already in doc; reconfirmed by Task 4 / Task 5 refuter #1. ✓
- No production wiring → enforced (only `examples/` + docs touched). ✓
