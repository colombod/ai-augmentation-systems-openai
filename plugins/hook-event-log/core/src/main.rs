use event_log_core::{append_event, latest_log, read_bounded, resolve_data_root, LogError};
use std::path::PathBuf;

fn run() -> Result<(), LogError> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.as_slice() == [std::ffi::OsStr::new("--latest-log")] {
        let root = resolve_data_root(
            std::env::var_os("PLUGIN_DATA").as_deref(),
            std::env::var_os("CODEX_HOME").as_deref(),
            std::env::var_os("HOME").as_deref(),
        )?;
        let path = latest_log(&root)?;
        use std::io::Write;
        let mut output = std::io::stdout().lock();
        writeln!(output, "{}", path.to_str().ok_or(LogError)?)?;
        return Ok(());
    }
    if !args.is_empty() { return Err(LogError); }
    let root = std::env::var_os("PLUGIN_DATA").ok_or(LogError)?;
    let input = read_bounded(std::io::stdin().lock())?;
    append_event(&input, &PathBuf::from(root))
}
fn main() {
    // Unexpected panics must not print payloads, file paths, or backtraces.
    std::panic::set_hook(Box::new(|_| {}));
    if !matches!(std::panic::catch_unwind(run), Ok(Ok(()))) {
        eprintln!("event-log-core: logging failed");
        std::process::exit(1);
    }
}
