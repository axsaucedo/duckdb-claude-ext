use std::path::Path;

/// Supported data providers.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Provider {
    Claude,
    Copilot,
    Unknown,
}

/// Auto-detect provider from directory structure.
/// - `projects/` directory → Claude
/// - `session-state/` directory → Copilot
pub fn detect_provider(path: &Path) -> Provider {
    if path.join("projects").is_dir() {
        return Provider::Claude;
    }
    if path.join("session-state").is_dir() {
        return Provider::Copilot;
    }
    Provider::Unknown
}

/// Parse an explicit source string into a Provider.
pub fn parse_source(source: &str) -> Provider {
    match source.to_lowercase().as_str() {
        "claude" => Provider::Claude,
        "copilot" => Provider::Copilot,
        _ => Provider::Unknown,
    }
}

/// Resolve provider: explicit source overrides auto-detection.
pub fn resolve_provider(path: &Path, source: Option<&str>) -> Provider {
    if let Some(s) = source {
        let p = parse_source(s);
        if p != Provider::Unknown {
            return p;
        }
    }
    detect_provider(path)
}
