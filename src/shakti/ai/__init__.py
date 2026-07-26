"""Shakti AI — multi-provider chat, streaming, RAG, and agents."""

from shakti.ai.ai import AI, SSEResponse
from shakti.ai.agents import Agent, AgentResult
from shakti.ai.providers.base import AIResponse, BaseProvider, Message
from shakti.ai.providers.anthropic_provider import AnthropicProvider
from shakti.ai.providers.openai_provider import OpenAIProvider
from shakti.ai.rag import RAGStore
from shakti.ai.templates import (
    CODE_REVIEW,
    EXPLAIN_CODE,
    EXTRACT_JSON,
    SQL_QUERY,
    SUMMARIZE,
    TRANSLATE,
    PromptTemplate,
)

__all__ = [
    "AI",
    "AIResponse",
    "Agent",
    "AgentResult",
    "AnthropicProvider",
    "BaseProvider",
    "CODE_REVIEW",
    "EXPLAIN_CODE",
    "EXTRACT_JSON",
    "Message",
    "OpenAIProvider",
    "PromptTemplate",
    "RAGStore",
    "SQL_QUERY",
    "SSEResponse",
    "SUMMARIZE",
    "TRANSLATE",
]
