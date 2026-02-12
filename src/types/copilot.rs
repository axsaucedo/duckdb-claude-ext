use serde::Deserialize;

/// Common envelope for all Copilot CLI events.
#[derive(Deserialize, Debug, Clone)]
pub struct CopilotEvent {
    #[serde(rename = "type")]
    pub event_type: String,
    pub id: Option<String>,
    pub timestamp: Option<String>,
    #[serde(rename = "parentId")]
    pub parent_id: Option<String>,
    #[serde(default)]
    pub data: serde_json::Value,
}

/// Parsed from session.start data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct SessionStartData {
    #[serde(rename = "sessionId")]
    pub session_id: Option<String>,
    #[serde(rename = "copilotVersion")]
    pub copilot_version: Option<String>,
    pub context: Option<SessionContext>,
}

#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct SessionContext {
    pub cwd: Option<String>,
    #[serde(rename = "gitRoot")]
    pub git_root: Option<String>,
    pub branch: Option<String>,
    pub repository: Option<String>,
}

/// Parsed from assistant.message data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct AssistantMessageData {
    #[serde(rename = "messageId")]
    pub message_id: Option<String>,
    pub content: Option<String>,
    #[serde(rename = "toolRequests")]
    pub tool_requests: Option<Vec<ToolRequest>>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct ToolRequest {
    #[serde(rename = "toolCallId")]
    pub tool_call_id: Option<String>,
    pub name: Option<String>,
    pub arguments: Option<serde_json::Value>,
}

/// Parsed from tool.execution_start data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct ToolExecutionStartData {
    #[serde(rename = "toolCallId")]
    pub tool_call_id: Option<String>,
    #[serde(rename = "toolName")]
    pub tool_name: Option<String>,
    pub arguments: Option<serde_json::Value>,
}

/// Parsed from tool.execution_complete data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct ToolExecutionCompleteData {
    #[serde(rename = "toolCallId")]
    pub tool_call_id: Option<String>,
    pub success: Option<bool>,
    pub result: Option<ToolResult>,
}

#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct ToolResult {
    pub content: Option<String>,
}

/// Parsed from session.model_change data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct ModelChangeData {
    #[serde(rename = "newModel")]
    pub new_model: Option<String>,
}

/// Parsed from session.truncation data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct TruncationData {
    #[serde(rename = "tokenLimit")]
    pub token_limit: Option<i64>,
    #[serde(rename = "preTruncationTokensInMessages")]
    pub pre_truncation_tokens: Option<i64>,
    #[serde(rename = "postTruncationTokensInMessages")]
    pub post_truncation_tokens: Option<i64>,
}

/// Parsed from user.message data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct UserMessageData {
    pub content: Option<String>,
}

/// Parsed from assistant.reasoning data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct ReasoningData {
    pub content: Option<String>,
}

/// Parsed from session.error data.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct SessionErrorData {
    #[serde(rename = "errorType")]
    pub error_type: Option<String>,
    pub message: Option<String>,
}

/// Copilot command history file.
#[derive(Deserialize, Debug, Clone)]
pub struct CopilotCommandHistory {
    #[serde(rename = "commandHistory", default)]
    pub command_history: Vec<String>,
}

/// workspace.yaml schema.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(default)]
pub struct WorkspaceYaml {
    pub id: Option<String>,
    pub cwd: Option<String>,
    pub git_root: Option<String>,
    pub repository: Option<String>,
    pub branch: Option<String>,
    pub summary: Option<String>,
}
