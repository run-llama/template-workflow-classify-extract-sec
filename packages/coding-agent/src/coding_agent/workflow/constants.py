from coding_agent.agent import AgentType, BaseCodingAgent
from coding_agent.adapters.claude_code import ClaudeCodingAgent
from typing import Type

SUPPORTED_AGENTS: dict[AgentType, Type[BaseCodingAgent]] = {
    "Claude Code": ClaudeCodingAgent
}

CREATE_TABLE_STATEMENT = """CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_role TEXT NOT NULL,
    content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);"""
