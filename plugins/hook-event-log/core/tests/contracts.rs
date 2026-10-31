#![cfg(unix)]
use event_log_core::{append_event, read_bounded, EVENTS, MAX_INPUT_BYTES};
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::Write;
use std::os::fd::AsRawFd;
use std::os::unix::fs::{symlink, DirBuilderExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

struct Fixture(PathBuf);
impl Fixture {
    fn new() -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let root = std::env::temp_dir().canonicalize().unwrap().join(format!(
            "event-core-{}-{}-{}", std::process::id(),
            std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos(),
            NEXT.fetch_add(1, Ordering::Relaxed)));
        fs::DirBuilder::new().mode(0o700).create(&root).unwrap();
        Self(root)
    }
    fn log(&self, session: &str) -> PathBuf {
        self.0.join("event-types").join(format!("{:x}.jsonl", Sha256::digest(session.as_bytes())))
    }
}
impl Drop for Fixture { fn drop(&mut self) { let _ = fs::remove_dir_all(&self.0); } }
fn input(event: &str, session: &str) -> Vec<u8> {
    serde_json::to_vec(&serde_json::json!({"hook_event_name": event, "session_id": session,
        "prompt":"PAYLOAD_SECRET", "tool_input": {"credentials":"SECRET_TOKEN"}})).unwrap()
}
fn run(data: Option<&Path>, bytes: &[u8]) -> std::process::Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_event-log-core"));
    command.env_remove("PLUGIN_DATA").stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    if let Some(data) = data { command.env("PLUGIN_DATA", data); }
    let mut child = command.spawn().unwrap();
    child.stdin.take().unwrap().write_all(bytes).unwrap();
    child.wait_with_output().unwrap()
}

#[test]
fn every_supported_event_serializes_one_key_only_and_routes_by_hash() {
    let fixture = Fixture::new();
    for event in EVENTS { append_event(&input(event, "private-session"), &fixture.0).unwrap(); }
    let actual = fs::read_to_string(fixture.log("private-session")).unwrap();
    let expected: String = EVENTS.iter().map(|event| format!("{{\"event_type\":\"{event}\"}}\n")).collect();
    assert_eq!(actual, expected);
    let names: Vec<_> = fs::read_dir(fixture.0.join("event-types")).unwrap().collect();
    assert_eq!(names.len(), 1);
    assert_eq!(fs::metadata(fixture.log("private-session")).unwrap().permissions().mode() & 0o777, 0o600);
    assert_eq!(fs::metadata(fixture.0.join("event-types")).unwrap().permissions().mode() & 0o777, 0o700);
    append_event(&input("Stop", "different-session"), &fixture.0).unwrap();
    assert!(fixture.log("different-session").exists());
}

#[test]
fn malformed_unsupported_or_missing_identifiers_create_nothing() {
    let fixture = Fixture::new();
    for invalid in [b"not-json".as_slice(), b"[]", b"{}", b"{\"hook_event_name\":\"Stop\",\"session_id\":0}",
        b"{\"hook_event_name\":\"Stop\",\"session_id\":\" \"}"] {
        assert!(append_event(invalid, &fixture.0).is_err());
    }
    assert!(append_event(&input("StopSECRET_TOKEN", "s"), &fixture.0).is_err());
    assert!(append_event(&input("Stop", &"s".repeat(1025)), &fixture.0).is_err());
    assert_eq!(fs::read_dir(&fixture.0).unwrap().count(), 0);
}

#[test]
fn exact_byte_boundary_accepted_and_one_extra_byte_rejected() {
    let fixture = Fixture::new();
    let mut payload = input("Stop", "s");
    payload.resize(MAX_INPUT_BYTES, b' ');
    assert_eq!(read_bounded(payload.as_slice()).unwrap().len(), MAX_INPUT_BYTES);
    append_event(&payload, &fixture.0).unwrap();
    payload.push(b' ');
    assert!(read_bounded(payload.as_slice()).is_err());
    assert!(append_event(&payload, &fixture.0).is_err());
    assert_eq!(fs::read_to_string(fixture.log("s")).unwrap().lines().count(), 1);
}

#[test]
fn process_contract_quiet_success_fixed_private_failures() {
    let fixture = Fixture::new();
    let good = run(Some(&fixture.0), &input("Stop", "s"));
    assert!(good.status.success()); assert!(good.stdout.is_empty()); assert!(good.stderr.is_empty());
    for result in [run(None, b"SECRET_TOKEN"), run(Some(Path::new("relative")), &input("Stop", "s")),
        run(Some(&fixture.0), b"SECRET_TOKEN")] {
        assert_eq!(result.status.code(), Some(1)); assert!(result.stdout.is_empty());
        assert_eq!(result.stderr, b"event-log-core: logging failed\n");
    }
}

#[test]
fn thirty_two_processes_append_complete_records() {
    let fixture = Fixture::new();
    let mut children = Vec::new();
    for _ in 0..32 {
        let mut child = Command::new(env!("CARGO_BIN_EXE_event-log-core")).env("PLUGIN_DATA", &fixture.0)
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
        child.stdin.take().unwrap().write_all(&input("PreToolUse", "s")).unwrap();
        children.push(child);
    }
    let results: Vec<_> = children.into_iter().map(|child| child.wait_with_output().unwrap()).collect();
    for result in &results { assert!(result.stdout.is_empty()); assert!(result.stderr.is_empty()); }
    assert!(results.iter().all(|result| result.status.success()));
    let data = fs::read_to_string(fixture.log("s")).unwrap();
    assert_eq!(data, "{\"event_type\":\"PreToolUse\"}\n".repeat(32));
}

#[test]
fn symlink_directories_targets_hardlinks_and_insecure_files_rejected() {
    let fixture = Fixture::new();
    let external = Fixture::new();
    symlink(&external.0, fixture.0.join("alias")).unwrap();
    assert!(append_event(&input("Stop", "s"), &fixture.0.join("alias")).is_err());
    symlink(&external.0, fixture.0.join("event-types")).unwrap();
    assert!(append_event(&input("Stop", "s"), &fixture.0).is_err());
    fs::remove_file(fixture.0.join("event-types")).unwrap();
    fs::DirBuilder::new().mode(0o700).create(fixture.0.join("event-types")).unwrap();
    let target = external.0.join("untouched"); fs::write(&target, b"ORIGINAL").unwrap();
    symlink(&target, fixture.log("s")).unwrap();
    assert!(append_event(&input("Stop", "s"), &fixture.0).is_err());
    assert_eq!(fs::read(&target).unwrap(), b"ORIGINAL");
    fs::remove_file(fixture.log("s")).unwrap();
    fs::hard_link(&target, fixture.log("s")).unwrap();
    assert!(append_event(&input("Stop", "s"), &fixture.0).is_err());
    fs::remove_file(fixture.log("s")).unwrap();
    fs::write(fixture.log("s"), b"ORIGINAL").unwrap();
    fs::set_permissions(fixture.log("s"), fs::Permissions::from_mode(0o644)).unwrap();
    assert!(append_event(&input("Stop", "s"), &fixture.0).is_err());
    assert_eq!(fs::read(fixture.log("s")).unwrap(), b"ORIGINAL");
}

#[test]
fn lock_contention_is_bounded_and_does_not_write() {
    let fixture = Fixture::new();
    append_event(&input("Stop", "s"), &fixture.0).unwrap();
    let locked = File::open(fixture.log("s")).unwrap();
    assert_eq!(unsafe { libc::flock(locked.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) }, 0);
    let start = Instant::now();
    let output = run(Some(&fixture.0), &input("Stop", "s"));
    assert_eq!(output.status.code(), Some(1));
    assert!(start.elapsed().as_millis() >= 250 && start.elapsed().as_secs() < 2);
    assert_eq!(fs::read_to_string(fixture.log("s")).unwrap().lines().count(), 1);
}

#[test]
fn helper_root_precedence_rejects_invalid_overrides_without_fallback() {
    use event_log_core::resolve_data_root;
    use std::ffi::OsStr;
    let os = |value| Some(OsStr::new(value));
    assert_eq!(resolve_data_root(os("/plugin"), os("/codex"), os("/home")).unwrap(), Path::new("/plugin"));
    assert_eq!(resolve_data_root(None, os("/codex"), os("/home")).unwrap(),
        Path::new("/codex/plugins/data/hook-event-log-ai-augmentation-systems-openai"));
    assert_eq!(resolve_data_root(None, None, os("/home")).unwrap(),
        Path::new("/home/.codex/plugins/data/hook-event-log-ai-augmentation-systems-openai"));
    for invalid in ["", "relative"] {
        assert!(resolve_data_root(os(invalid), os("/codex"), os("/home")).is_err());
        assert!(resolve_data_root(None, os(invalid), os("/home")).is_err());
        assert!(resolve_data_root(None, None, os(invalid)).is_err());
    }
    assert!(resolve_data_root(None, None, None).is_err());
}

#[test]
fn helper_selects_mtime_then_filename_without_reading_or_writing_logs() {
    use event_log_core::latest_log;
    use std::time::{Duration, UNIX_EPOCH};
    let fixture = Fixture::new();
    let directory = fixture.0.join("event-types");
    fs::create_dir(&directory).unwrap();
    let write_log = |letter: char, seconds: u64| {
        let path = directory.join(format!("{}.jsonl", letter.to_string().repeat(64)));
        fs::write(&path, b"PRIVATE_CONTENT_SENTINEL").unwrap();
        File::options().write(true).open(&path).unwrap().set_times(
            fs::FileTimes::new().set_accessed(UNIX_EPOCH + Duration::from_secs(100))
                .set_modified(UNIX_EPOCH + Duration::from_secs(seconds))).unwrap();
        path
    };
    let older = write_log('f', 200);
    let smaller = write_log('a', 300);
    let latest = write_log('b', 300);
    fs::write(directory.join("not-a-session.jsonl"), b"IGNORED").unwrap();
    fs::create_dir(directory.join(format!("{}.jsonl", "e".repeat(64)))).unwrap();
    let before: Vec<_> = [&older, &smaller, &latest].iter().map(|path| {
        // Make contents unreadable: metadata-only selection still succeeds.
        fs::set_permissions(path, fs::Permissions::from_mode(0o000)).unwrap();
        let meta = fs::metadata(path).unwrap();
        (meta.modified().unwrap(), meta.len(), meta.permissions().mode())
    }).collect();
    assert_eq!(latest_log(&fixture.0).unwrap(), latest);
    for (path, expected) in [&older, &smaller, &latest].iter().zip(before) {
        let meta = fs::metadata(path).unwrap();
        assert_eq!((meta.modified().unwrap(), meta.len(), meta.permissions().mode()), expected);
        fs::set_permissions(path, fs::Permissions::from_mode(0o600)).unwrap();
        assert_eq!(fs::read(path).unwrap(), b"PRIVATE_CONTENT_SENTINEL");
    }
    assert_eq!(fs::read_dir(&directory).unwrap().count(), 5);
}

#[test]
fn helper_missing_empty_and_symlink_paths_fail_without_creating_paths() {
    use event_log_core::latest_log;
    let fixture = Fixture::new();
    let missing = fixture.0.join("missing");
    assert!(latest_log(&missing).is_err()); assert!(!missing.exists());
    assert!(latest_log(&fixture.0).is_err()); assert_eq!(fs::read_dir(&fixture.0).unwrap().count(), 0);
    let external = Fixture::new();
    fs::create_dir(external.0.join("event-types")).unwrap();
    assert!(latest_log(&external.0).is_err());
    symlink(&external.0, fixture.0.join("alias")).unwrap();
    assert!(latest_log(&fixture.0.join("alias")).is_err());
    symlink(external.0.join("event-types"), fixture.0.join("event-types")).unwrap();
    assert!(latest_log(&fixture.0).is_err());
    fs::remove_file(fixture.0.join("event-types")).unwrap();
    fs::create_dir(fixture.0.join("event-types")).unwrap();
    let target = external.0.join("target"); fs::write(&target, b"UNCHANGED").unwrap();
    symlink(&target, fixture.log("s")).unwrap();
    assert!(latest_log(&fixture.0).is_err());
    assert_eq!(fs::read(&target).unwrap(), b"UNCHANGED");
    assert!(latest_log(Path::new("relative")).is_err());
}

#[test]
fn helper_cli_is_read_only_ignores_stdin_and_keeps_normal_hook_root_requirement() {
    let fixture = Fixture::new();
    append_event(&input("Stop", "s"), &fixture.0).unwrap();
    let mut child = Command::new(env!("CARGO_BIN_EXE_event-log-core")).arg("--latest-log")
        .env("PLUGIN_DATA", &fixture.0).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped())
        .spawn().unwrap();
    // Keep stdin open: the helper must complete without waiting for EOF or reading bytes.
    let stdin = child.stdin.take().unwrap();
    let deadline = Instant::now() + std::time::Duration::from_secs(2);
    loop {
        if child.try_wait().unwrap().is_some() { break; }
        if Instant::now() >= deadline { child.kill().unwrap(); panic!("helper waited for stdin"); }
        std::thread::sleep(std::time::Duration::from_millis(5));
    }
    let output = child.wait_with_output().unwrap(); drop(stdin);
    assert!(output.status.success()); assert!(output.stderr.is_empty());
    assert_eq!(String::from_utf8(output.stdout).unwrap(), format!("{}\n", fixture.log("s").display()));
    for args in [vec!["--unknown"], vec!["--latest-log", "extra"]] {
        let output = Command::new(env!("CARGO_BIN_EXE_event-log-core")).args(args)
            .env("PLUGIN_DATA", &fixture.0).output().unwrap();
        assert_eq!(output.status.code(), Some(1)); assert!(output.stdout.is_empty());
        assert_eq!(output.stderr, b"event-log-core: logging failed\n");
    }
    let output = Command::new(env!("CARGO_BIN_EXE_event-log-core"))
        .env_remove("PLUGIN_DATA").env("CODEX_HOME", &fixture.0).stdin(Stdio::null()).output().unwrap();
    assert_eq!(output.status.code(), Some(1)); assert!(output.stdout.is_empty());
    assert_eq!(fs::read_to_string(fixture.log("s")).unwrap(), "{\"event_type\":\"Stop\"}\n");
}

#[test]
fn helper_cli_fallback_locations_and_invalid_override_never_fall_through() {
    let fixture = Fixture::new();
    let suffix = "plugins/data/hook-event-log-ai-augmentation-systems-openai";
    let codex = fixture.0.join("custom-codex");
    let home = fixture.0.join("user-home");
    let custom_root = codex.join(suffix);
    let home_root = home.join(".codex").join(suffix);
    append_event(&input("Stop", "custom"), &custom_root).unwrap();
    append_event(&input("Stop", "home"), &home_root).unwrap();
    let invoke = |plugin: Option<&str>, custom: Option<&str>| {
        let mut command = Command::new(env!("CARGO_BIN_EXE_event-log-core"));
        command.arg("--latest-log").env_remove("PLUGIN_DATA").env_remove("CODEX_HOME").env("HOME", &home);
        if let Some(plugin) = plugin { command.env("PLUGIN_DATA", plugin); }
        if let Some(custom) = custom { command.env("CODEX_HOME", custom); }
        command.output().unwrap()
    };
    let output = invoke(None, Some(codex.to_str().unwrap()));
    assert!(output.status.success());
    assert!(String::from_utf8(output.stdout).unwrap().starts_with(custom_root.to_str().unwrap()));
    let output = invoke(None, None);
    assert!(output.status.success());
    assert!(String::from_utf8(output.stdout).unwrap().starts_with(home_root.to_str().unwrap()));
    for output in [invoke(Some(""), Some(codex.to_str().unwrap())), invoke(Some("relative"), None),
        invoke(None, Some("")), invoke(None, Some("relative"))] {
        assert_eq!(output.status.code(), Some(1)); assert!(output.stdout.is_empty());
        assert_eq!(output.stderr, b"event-log-core: logging failed\n");
    }
}

#[test]
fn subagent_allowlist_is_scoped_and_json_escapes_metadata() {
    let fixture = Fixture::new();
    for event in EVENTS {
        let payload = serde_json::json!({
            "hook_event_name": event, "session_id":"parent-session",
            "agent_id":"child-\\\"quoted", "agent_type":"worker\\role",
            "agent_transcript_path":"/nonexistent/host transcript.jsonl",
            "parent_agent_id":"EXCLUDED_PARENT", "last_assistant_message":"EXCLUDED_OUTPUT",
            "prompt":"EXCLUDED_PROMPT", "tool_input":{"token":"EXCLUDED_ARGUMENTS"},
            "tool_response":"EXCLUDED_RESULTS", "unknown":"EXCLUDED_UNKNOWN",
            "event_log_path":"EXCLUDED_INVENTED_LINK"
        });
        append_event(&serde_json::to_vec(&payload).unwrap(), &fixture.0).unwrap();
    }
    let raw = fs::read_to_string(fixture.log("parent-session")).unwrap();
    assert!(!raw.contains("EXCLUDED"));
    assert_eq!(raw.lines().count(), EVENTS.len());
    for (line, event) in raw.lines().zip(EVENTS) {
        let actual: serde_json::Value = serde_json::from_str(line).unwrap();
        let mut expected = serde_json::json!({"event_type":event});
        if matches!(event, "SubagentStart" | "SubagentStop") {
            expected["agent_id"] = serde_json::json!("child-\\\"quoted");
            expected["agent_type"] = serde_json::json!("worker\\role");
        }
        if event == "SubagentStop" {
            expected["agent_transcript_path"] = serde_json::json!("/nonexistent/host transcript.jsonl");
        }
        assert_eq!(actual, expected);
    }
    assert_eq!(fs::read_dir(fixture.0.join("event-types")).unwrap().count(), 1);
    assert!(!fixture.log("child-\\\"quoted").exists());
}

#[test]
fn malformed_optional_metadata_is_omitted_without_losing_event() {
    let fixture = Fixture::new();
    let generic_bad = vec![serde_json::Value::Null, serde_json::json!(42), serde_json::json!(false),
        serde_json::json!([]), serde_json::json!({"secret":"EXCLUDED"}), serde_json::json!(""),
        serde_json::json!("  "), serde_json::json!("bad\nfield"), serde_json::json!("bad\u{0085}field"),
        serde_json::json!("bad\u{0000}field")];
    let mut count = 0;
    for (field, limit) in [("agent_id", 1024), ("agent_type", 256), ("agent_transcript_path", 4096)] {
        let mut invalid = generic_bad.clone();
        invalid.push(serde_json::json!("/".to_owned() + &"x".repeat(limit)));
        // Limits count UTF-8 bytes, not Unicode scalar count.
        invalid.push(serde_json::json!("/".to_owned() + &"é".repeat(limit / 2)));
        if field == "agent_transcript_path" { invalid.push(serde_json::json!("relative/transcript.jsonl")); }
        for value in invalid {
            let mut payload = serde_json::json!({"hook_event_name":"SubagentStop", "session_id":"s"});
            payload[field] = value;
            append_event(&serde_json::to_vec(&payload).unwrap(), &fixture.0).unwrap();
            count += 1;
        }
    }
    let raw = fs::read_to_string(fixture.log("s")).unwrap();
    assert_eq!(raw, "{\"event_type\":\"SubagentStop\"}\n".repeat(count));
    let boundary = serde_json::json!({"hook_event_name":"SubagentStop", "session_id":"s",
        "agent_id":"i".repeat(1024), "agent_type":"t".repeat(256),
        "agent_transcript_path":"/".to_owned() + &"p".repeat(4095)});
    append_event(&serde_json::to_vec(&boundary).unwrap(), &fixture.0).unwrap();
    let raw = fs::read_to_string(fixture.log("s")).unwrap();
    let last: serde_json::Value = serde_json::from_str(raw.lines().last().unwrap()).unwrap();
    assert_eq!(last.as_object().unwrap().len(), 4);
    assert_eq!(last["agent_id"], boundary["agent_id"]);
    assert_eq!(last["agent_type"], boundary["agent_type"]);
    assert_eq!(last["agent_transcript_path"], boundary["agent_transcript_path"]);
}

#[test]
fn mixed_history_preserved_and_host_transcript_not_read_or_created() {
    let fixture = Fixture::new();
    let external = Fixture::new();
    let transcript = external.0.join("host.jsonl");
    fs::write(&transcript, b"TRANSCRIPT_CONTENT_MUST_NOT_APPEAR").unwrap();
    fs::set_permissions(&transcript, fs::Permissions::from_mode(0o000)).unwrap();
    append_event(&input("SessionStart", "parent"), &fixture.0).unwrap();
    let original = fs::read(fixture.log("parent")).unwrap();
    let payload = serde_json::json!({"hook_event_name":"SubagentStop", "session_id":"parent",
        "agent_id":"child", "agent_transcript_path":transcript.to_str().unwrap()});
    append_event(&serde_json::to_vec(&payload).unwrap(), &fixture.0).unwrap();
    let nonexistent = external.0.join("must-not-be-created.jsonl");
    let mut absent_payload = payload.clone();
    absent_payload["agent_transcript_path"] = serde_json::json!(nonexistent.to_str().unwrap());
    append_event(&serde_json::to_vec(&absent_payload).unwrap(), &fixture.0).unwrap();
    append_event(&input("Stop", "parent"), &fixture.0).unwrap();
    let records = fs::read(fixture.log("parent")).unwrap();
    assert!(records.starts_with(&original));
    let raw = String::from_utf8(records).unwrap();
    assert_eq!(raw.lines().count(), 4);
    assert!(!raw.contains("TRANSCRIPT_CONTENT_MUST_NOT_APPEAR"));
    assert!(!nonexistent.exists());
    assert_eq!(fs::metadata(&transcript).unwrap().permissions().mode() & 0o777, 0o000);
    fs::set_permissions(&transcript, fs::Permissions::from_mode(0o600)).unwrap();
    assert_eq!(fs::read(&transcript).unwrap(), b"TRANSCRIPT_CONTENT_MUST_NOT_APPEAR");
    assert!(!fixture.log("child").exists());
    assert_eq!(fs::read_dir(fixture.0.join("event-types")).unwrap().count(), 1);
}

#[test]
fn concurrent_large_subagent_metadata_keeps_whole_records() {
    let fixture = Fixture::new();
    let mut children = Vec::new();
    for index in 0..32 {
        let payload = serde_json::json!({"hook_event_name":"SubagentStop", "session_id":"parent",
            "agent_id":format!("{index}-{}", "\\\"".repeat(500)), "agent_type":"t".repeat(256),
            "agent_transcript_path":"/".to_owned() + &"p".repeat(4095)});
        let mut child = Command::new(env!("CARGO_BIN_EXE_event-log-core")).env("PLUGIN_DATA", &fixture.0)
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
        child.stdin.take().unwrap().write_all(&serde_json::to_vec(&payload).unwrap()).unwrap();
        children.push(child);
    }
    let outputs: Vec<_> = children.into_iter().map(|child| child.wait_with_output().unwrap()).collect();
    for output in outputs { assert!(output.status.success()); assert!(output.stdout.is_empty()); assert!(output.stderr.is_empty()); }
    let raw = fs::read_to_string(fixture.log("parent")).unwrap();
    let rows: Vec<serde_json::Value> = raw.lines().map(|line| serde_json::from_str(line).unwrap()).collect();
    assert_eq!(rows.len(), 32);
    let ids: std::collections::HashSet<_> = rows.iter().map(|row| row["agent_id"].as_str().unwrap()).collect();
    assert_eq!(ids.len(), 32);
    for row in rows { assert_eq!(row.as_object().unwrap().len(), 4); assert_eq!(row["event_type"], "SubagentStop"); }
}
