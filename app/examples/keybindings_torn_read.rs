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

    // Counters classify each read by what the REAL `read_custom_keybindings` would return,
    // judged from the SAME bytes (one read -> no TOCTOU between "is it empty" and "does it parse"):
    //   absent      = File::open Err            -> read() == None
    //   none_empty  = 0 bytes AND serde Err     -> read() == None  (empty-file torn read)
    //   none_partial= >0 bytes AND serde Err    -> read() == None  (partial-file torn read)
    //   some_empty  = 0 bytes BUT serde Ok      -> read() == Some(<map>)  (empty parses OK!)
    //   short_map   = serde Ok, map smaller     -> read() == Some(partial map)
    //   clean       = serde Ok, full map        -> read() == Some(full map)
    let stop = Arc::new(AtomicBool::new(false));
    let reads = Arc::new(AtomicU64::new(0));
    let absent = Arc::new(AtomicU64::new(0));
    let none_empty = Arc::new(AtomicU64::new(0));
    let none_partial = Arc::new(AtomicU64::new(0));
    let some_empty = Arc::new(AtomicU64::new(0));
    let short_map = Arc::new(AtomicU64::new(0));
    let clean = Arc::new(AtomicU64::new(0));

    let mut handles = Vec::new();
    for _ in 0..readers {
        let path = path.clone();
        let stop = stop.clone();
        let (reads, absent, none_empty, none_partial, some_empty, short_map, clean) = (
            reads.clone(),
            absent.clone(),
            none_empty.clone(),
            none_partial.clone(),
            some_empty.clone(),
            short_map.clone(),
            clean.clone(),
        );
        handles.push(thread::spawn(move || {
            while !stop.load(Ordering::Relaxed) {
                reads.fetch_add(1, Ordering::Relaxed);
                let bytes = match std::fs::read(&path) {
                    Err(_) => {
                        absent.fetch_add(1, Ordering::Relaxed);
                        continue;
                    }
                    Ok(b) => b,
                };
                let is_empty = bytes.is_empty();
                match serde_yaml::from_slice::<HashMap<String, String>>(&bytes) {
                    Err(_) if is_empty => {
                        none_empty.fetch_add(1, Ordering::Relaxed);
                    }
                    Err(_) => {
                        none_partial.fetch_add(1, Ordering::Relaxed);
                    }
                    Ok(_) if is_empty => {
                        some_empty.fetch_add(1, Ordering::Relaxed);
                    }
                    Ok(m) if m.len() < seed_entries => {
                        short_map.fetch_add(1, Ordering::Relaxed);
                    }
                    Ok(_) => {
                        clean.fetch_add(1, Ordering::Relaxed);
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

    let r = reads.load(Ordering::Relaxed);
    let absent = absent.load(Ordering::Relaxed);
    let none_empty = none_empty.load(Ordering::Relaxed);
    let none_partial = none_partial.load(Ordering::Relaxed);
    let some_empty = some_empty.load(Ordering::Relaxed);
    let short_map = short_map.load(Ordering::Relaxed);
    let clean = clean.load(Ordering::Relaxed);
    // read_custom_keybindings() == None  <=>  open failed OR serde failed.
    let none_total = absent + none_empty + none_partial;
    println!("\n--- A1-Q6 torn-read repro ---");
    println!("writer iters:        {writer_iters}");
    println!("reader reads:        {r}");
    println!("clean (full map):    {clean}");
    println!("short-map (partial): {short_map}   [Some(partial) -> partial apply]");
    println!("some_empty:          {some_empty}   [0 bytes BUT serde Ok -> Some(empty map)]");
    println!("none_empty:          {none_empty}   [0 bytes AND serde Err -> None]");
    println!("none_partial:        {none_partial}   [>0 bytes AND serde Err -> None]");
    println!("absent (open Err):   {absent}   [-> None]");
    println!("NONE-total (read()==None -> revert-all wipe): {none_total}");
    println!(
        "VERDICT: {}",
        if none_total >= 1 {
            "torn read -> read()==None OBSERVED -> atomic temp+rename REQUIRED (hand to A1-Q5)"
        } else if some_empty >= 1 || short_map >= 1 {
            "no None observed, but Some(empty)/Some(partial) observed -> still a wrong-apply hazard; atomic write recommended"
        } else {
            "no torn read this run -> atomic write defensive-only; rerun with larger SPIKE_SEED/SPIKE_SECS to push harder"
        }
    );

    let _ = std::fs::remove_dir_all(&tmp);
}
