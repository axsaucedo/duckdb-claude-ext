use serde::Deserialize;

// ─── Conversation Messages (JSONL) ───

#[derive(Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum ConversationMessage {
    #[serde(rename = "user")]
    User(UserMessage),
    #[serde(rename = "assistant")]
    Assistant(AssistantMessage),
    #[serde(rename = "system")]
    System(SystemMessage),
    #[serde(rename = "file-history-snapshot")]
    FileHistorySnapshot {},
    #[serde(rename = "queue-operation")]
    QueueOperation(QueueOperationMessage),
    #[serde(rename = "summary")]
    Summary(SummaryMessage),
}

#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct BaseFields {
    pub uuid: Option<String>,
    #[serde(rename = "parentUuid")]
    pub parent_uuid: Option<String>,
    pub timestamp: Option<String>,
    #[serde(rename = "sessionId")]
    pub session_id: Option<String>,
    pub cwd: Option<String>,
    pub version: Option<String>,
    pub slug: Option<String>,
    #[serde(rename = "gitBranch")]
    pub git_branch: Option<String>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct UserMessage {
    #[serde(flatten)]
    pub base: BaseFields,
    pub message: Option<UserMessageContent>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct UserMessageContent {
    pub content: Option<serde_json::Value>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct AssistantMessage {
    #[serde(flatten)]
    pub base: BaseFields,
    pub message: Option<AssistantMessageContent>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct AssistantMessageContent {
    pub model: Option<String>,
    pub content: Option<Vec<ContentBlock>>,
    pub stop_reason: Option<String>,
    pub usage: Option<UsageInfo>,
}

#[derive(Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum ContentBlock {
    #[serde(rename = "text")]
    Text { text: String },
    #[serde(rename = "thinking")]
    Thinking {},
    #[serde(rename = "tool_use")]
    ToolUse {
        id: Option<String>,
        name: Option<String>,
        input: Option<serde_json::Value>,
    },
    #[serde(rename = "tool_result")]
    ToolResult {},
}

#[derive(Deserialize, Debug, Clone)]
pub struct UsageInfo {
    pub input_tokens: Option<i64>,
    pub output_tokens: Option<i64>,
    pub cache_creation_input_tokens: Option<i64>,
    pub cache_read_input_tokens: Option<i64>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct SystemMessage {
    #[serde(flatten)]
    pub base: BaseFields,
    pub content: Option<serde_json::Value>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct QueueOperationMessage {
    pub timestamp: Option<String>,
    #[serde(rename = "sessionId")]
    pub session_id: Option<String>,
    pub content: Option<String>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct SummaryMessage {
    pub summary: Option<String>,
}

// ─── History (JSONL) ───

#[derive(Deserialize, Debug, Clone)]
pub struct HistoryEntry {
    pub display: Option<String>,
    #[serde(rename = "pastedContents")]
    pub pasted_contents: Option<serde_json::Value>,
    pub timestamp: Option<f64>,
    pub project: Option<String>,
    #[serde(rename = "sessionId")]
    pub session_id: Option<String>,
}

// ─── Todos (JSON) ───

#[derive(Deserialize, Debug, Clone)]
pub struct TodoItem {
    pub content: Option<String>,
    pub status: Option<String>,
    #[serde(rename = "activeForm")]
    pub active_form: Option<String>,
}

// ─── Stats Cache (JSON) ───

#[derive(Deserialize, Debug, Clone)]
pub struct StatsCache {
    #[serde(rename = "dailyActivity")]
    pub daily_activity: Option<Vec<DailyStats>>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct DailyStats {
    pub date: Option<String>,
    #[serde(rename = "messageCount")]
    pub message_count: Option<i64>,
    #[serde(rename = "sessionCount")]
    pub session_count: Option<i64>,
    #[serde(rename = "toolCallCount")]
    pub tool_call_count: Option<i64>,
}
