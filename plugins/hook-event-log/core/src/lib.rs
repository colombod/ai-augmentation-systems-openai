//! Event types plus explicitly allowlisted host subagent identity/transcript-path metadata.
//! General payload content and transcript contents are never read, retained or included in errors.
//! Native subagent events remain routed by the host session ID; agent IDs are not session IDs.
use sha2::{Digest, Sha256};
use std::io::{self, Read};
use std::path::Path;

pub const MAX_INPUT_BYTES: usize = 1_048_576;
pub const MAX_SESSION_BYTES: usize = 1024;
pub const EVENTS: [&str; 12] = [
    "SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PermissionRequest", "SubagentStart", "SubagentStop", "PreCompact", "PostCompact",
    "Stop", "Interrupt",
];

/// Intentionally carries no input, path or operating-system diagnostic content.
#[derive(Debug)]
pub struct LogError;
impl From<io::Error> for LogError {
    fn from(_: io::Error) -> Self { Self }
}

pub fn read_bounded(reader: impl Read) -> Result<Vec<u8>, LogError> {
    let mut bytes = Vec::new();
    reader.take((MAX_INPUT_BYTES + 1) as u64).read_to_end(&mut bytes)?;
    if bytes.len() > MAX_INPUT_BYTES { return Err(LogError); }
    Ok(bytes)
}

pub fn append_event(input: &[u8], data_root: &Path) -> Result<(), LogError> {
    if input.len() > MAX_INPUT_BYTES { return Err(LogError); }
    let value: serde_json::Value = serde_json::from_slice(input).map_err(|_| LogError)?;
    let object = value.as_object().ok_or(LogError)?;
    let event = object.get("hook_event_name").and_then(|v| v.as_str()).ok_or(LogError)?;
    let session = object.get("session_id").and_then(|v| v.as_str()).ok_or(LogError)?;
    if !EVENTS.contains(&event) || session.trim().is_empty() || session.len() > MAX_SESSION_BYTES {
        return Err(LogError);
    }
    // Start from an empty record: unknown payload fields can never leak by copying input.
    let mut record = serde_json::Map::new();
    record.insert("event_type".into(), serde_json::Value::String(event.into()));
    if matches!(event, "SubagentStart" | "SubagentStop") {
        for (name, limit) in [("agent_id", 1024), ("agent_type", 256)] {
            if let Some(value) = optional_metadata(object, name, limit) {
                record.insert(name.into(), serde_json::Value::String(value.into()));
            }
        }
        if event == "SubagentStop" {
            if let Some(path) = optional_metadata(object, "agent_transcript_path", 4096) {
                // The host path is metadata only; never inspect or open the transcript.
                if Path::new(path).is_absolute() {
                    record.insert("agent_transcript_path".into(), serde_json::Value::String(path.into()));
                }
            }
        }
    }
    let filename = format!("{:x}.jsonl", Sha256::digest(session.as_bytes()));
    let mut bytes = serde_json::to_vec(&record).map_err(|_| LogError)?;
    bytes.push(b'\n');
    secure_append(data_root, &filename, &bytes)
}

fn optional_metadata<'a>(
    input: &'a serde_json::Map<String, serde_json::Value>, name: &str, max_bytes: usize,
) -> Option<&'a str> {
    let value = input.get(name)?.as_str()?;
    if value.trim().is_empty() || value.len() > max_bytes || value.chars().any(char::is_control) {
        return None;
    }
    Some(value)
}

#[cfg(unix)]
fn secure_append(data_root: &Path, filename: &str, record: &[u8]) -> Result<(), LogError> {
    use std::ffi::CString;
    use std::fs::File;
    use std::io::Write;
    use std::os::fd::{AsRawFd, FromRawFd};
    use std::os::unix::ffi::OsStrExt;
    use std::path::Component;
    use std::time::{Duration, Instant};

    fn open_dir(parent: libc::c_int, name: &CString) -> Result<File, LogError> {
        // O_NOFOLLOW pins each directory traversal to a real directory, including data_root.
        let fd = unsafe { libc::openat(parent, name.as_ptr(), libc::O_RDONLY | libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC) };
        if fd < 0 { return Err(LogError); }
        Ok(unsafe { File::from_raw_fd(fd) })
    }
    fn private_owned(fd: libc::c_int, directory: bool) -> Result<(), LogError> {
        let mut stat = std::mem::MaybeUninit::<libc::stat>::uninit();
        if unsafe { libc::fstat(fd, stat.as_mut_ptr()) } != 0 { return Err(LogError); }
        let stat = unsafe { stat.assume_init() };
        let kind = if directory { libc::S_IFDIR } else { libc::S_IFREG };
        if stat.st_mode & libc::S_IFMT != kind || stat.st_uid != unsafe { libc::geteuid() }
            || stat.st_mode & 0o077 != 0 || (!directory && stat.st_nlink != 1) {
            return Err(LogError);
        }
        Ok(())
    }
    if !data_root.is_absolute() { return Err(LogError); }
    let mut directory = open_dir(libc::AT_FDCWD, &CString::new("/").unwrap())?;
    for component in data_root.components() {
        match component {
            Component::RootDir => continue,
            Component::Normal(name) => {
                let name = CString::new(name.as_bytes()).map_err(|_| LogError)?;
                let result = unsafe { libc::mkdirat(directory.as_raw_fd(), name.as_ptr(), 0o700) };
                if result != 0 && io::Error::last_os_error().raw_os_error() != Some(libc::EEXIST) { return Err(LogError); }
                directory = open_dir(directory.as_raw_fd(), &name)?;
            }
            _ => return Err(LogError),
        }
    }
    let name = CString::new("event-types").unwrap();
    let result = unsafe { libc::mkdirat(directory.as_raw_fd(), name.as_ptr(), 0o700) };
    if result != 0 && io::Error::last_os_error().raw_os_error() != Some(libc::EEXIST) { return Err(LogError); }
    directory = open_dir(directory.as_raw_fd(), &name)?;
    private_owned(directory.as_raw_fd(), true)?;
    let filename = CString::new(filename).map_err(|_| LogError)?;
    // Concurrent O_CREAT opens returned transient ENOENT in macOS testing.
    // Retry only ENOENT and EINTR against the pinned directory, with a deadline.
    let open_deadline = Instant::now() + Duration::from_millis(300);
    let fd = loop {
        let fd = unsafe { libc::openat(directory.as_raw_fd(), filename.as_ptr(),
            libc::O_WRONLY | libc::O_APPEND | libc::O_CREAT | libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_CLOEXEC, 0o600) };
        if fd >= 0 { break fd; }
        if !matches!(io::Error::last_os_error().raw_os_error(), Some(libc::ENOENT) | Some(libc::EINTR))
            || Instant::now() >= open_deadline { return Err(LogError); }
        std::thread::sleep(Duration::from_millis(5));
    };
    let mut file = unsafe { File::from_raw_fd(fd) };
    private_owned(file.as_raw_fd(), false)?;
    let deadline = Instant::now() + Duration::from_millis(300);
    loop {
        if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } == 0 { break; }
        let error = io::Error::last_os_error();
        if !matches!(error.raw_os_error(), Some(libc::EWOULDBLOCK) | Some(libc::EINTR)) || Instant::now() >= deadline {
            return Err(LogError);
        }
        std::thread::sleep(Duration::from_millis(5));
    }
    // The descriptor owns the advisory lock until drop, including on write failure.
    file.write_all(record)?;
    Ok(())
}

#[cfg(not(unix))]
fn secure_append(_: &Path, _: &str, _: &[u8]) -> Result<(), LogError> { Err(LogError) }

/// Resolve helper location without changing normal hook invocation's requirements.
/// A present-but-invalid override always fails; it never selects another root.
pub fn resolve_data_root(
    plugin_data: Option<&std::ffi::OsStr>,
    codex_home: Option<&std::ffi::OsStr>,
    home: Option<&std::ffi::OsStr>,
) -> Result<std::path::PathBuf, LogError> {
    fn absolute(value: &std::ffi::OsStr) -> Result<std::path::PathBuf, LogError> {
        let path = std::path::PathBuf::from(value);
        if value.is_empty() || !path.is_absolute() { return Err(LogError); }
        Ok(path)
    }
    if let Some(value) = plugin_data { return absolute(value); }
    let base = match codex_home {
        Some(value) => absolute(value)?,
        None => absolute(home.ok_or(LogError)?)?.join(".codex"),
    };
    Ok(base.join("plugins/data/hook-event-log-ai-augmentation-systems-openai"))
}

/// Inspect directory entries and metadata only; never read log contents or create paths.
/// Filename ties select the lexicographically greatest name.
#[cfg(any(target_os = "macos", target_os = "linux"))]
pub fn latest_log(data_root: &Path) -> Result<std::path::PathBuf, LogError> {
    use std::ffi::{CStr, CString};
    use std::fs::File;
    use std::os::fd::{AsRawFd, FromRawFd, IntoRawFd};
    use std::os::unix::ffi::OsStrExt;
    use std::path::Component;
    fn directory(parent: libc::c_int, name: &CString) -> Result<File, LogError> {
        let fd = unsafe { libc::openat(parent, name.as_ptr(), libc::O_RDONLY | libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC) };
        if fd < 0 { return Err(LogError); }
        Ok(unsafe { File::from_raw_fd(fd) })
    }
    fn clear_errno() {
        #[cfg(target_os = "macos")]
        unsafe { *libc::__error() = 0; }
        #[cfg(target_os = "linux")]
        unsafe { *libc::__errno_location() = 0; }
    }
    struct DirectoryStream(*mut libc::DIR);
    impl Drop for DirectoryStream {
        fn drop(&mut self) { unsafe { libc::closedir(self.0); } }
    }
    if !data_root.is_absolute() { return Err(LogError); }
    let mut dir = directory(libc::AT_FDCWD, &CString::new("/").unwrap())?;
    for component in data_root.components() {
        match component {
            Component::RootDir => continue,
            Component::Normal(value) => {
                dir = directory(dir.as_raw_fd(), &CString::new(value.as_bytes()).map_err(|_| LogError)?)?;
            }
            _ => return Err(LogError),
        }
    }
    dir = directory(dir.as_raw_fd(), &CString::new("event-types").unwrap())?;
    let fd = dir.into_raw_fd();
    let stream_ptr = unsafe { libc::fdopendir(fd) };
    if stream_ptr.is_null() {
        unsafe { libc::close(fd); }
        return Err(LogError);
    }
    let stream = DirectoryStream(stream_ptr);
    let mut selected: Option<(i64, i64, String)> = None;
    loop {
        clear_errno();
        let entry = unsafe { libc::readdir(stream.0) };
        if entry.is_null() {
            if io::Error::last_os_error().raw_os_error() != Some(0) { return Err(LogError); }
            break;
        }
        let name = unsafe { CStr::from_ptr((*entry).d_name.as_ptr()) };
        if name.to_bytes() == b"." || name.to_bytes() == b".." { continue; }
        let mut stat = std::mem::MaybeUninit::<libc::stat>::uninit();
        if unsafe { libc::fstatat(fd, name.as_ptr(), stat.as_mut_ptr(), libc::AT_SYMLINK_NOFOLLOW) } != 0 {
            return Err(LogError);
        }
        let stat = unsafe { stat.assume_init() };
        if stat.st_mode & libc::S_IFMT == libc::S_IFLNK { return Err(LogError); }
        let bytes = name.to_bytes();
        if stat.st_mode & libc::S_IFMT != libc::S_IFREG || bytes.len() != 70
            || &bytes[64..] != b".jsonl" || !bytes[..64].iter().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(b)) {
            continue;
        }
        #[cfg(target_os = "macos")]
        let nanos = stat.st_mtime_nsec;
        #[cfg(target_os = "linux")]
        let nanos = stat.st_mtime_nsec;
        let candidate = (stat.st_mtime as i64, nanos as i64,
            String::from_utf8(bytes.to_vec()).map_err(|_| LogError)?);
        if selected.as_ref().map(|previous| &candidate > previous).unwrap_or(true) {
            selected = Some(candidate);
        }
    }
    let (_, _, name) = selected.ok_or(LogError)?;
    Ok(data_root.join("event-types").join(name))
}

#[cfg(not(any(target_os = "macos", target_os = "linux")))]
pub fn latest_log(_: &Path) -> Result<std::path::PathBuf, LogError> { Err(LogError) }
