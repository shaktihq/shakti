"""Prompt templates with variable substitution."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptTemplate:
    """A reusable prompt with {variable} placeholders.

    Usage::

        tpl = PromptTemplate(
            "Summarize this in {language}: {text}",
            system="You are a helpful summarizer."
        )
        prompt = tpl.render(language="French", text="Hello world")
    """
    template: str
    system: str | None = None
    defaults: dict[str, Any] = field(default_factory=dict)

    def render(self, **kwargs: Any) -> str:
        merged = {**self.defaults, **kwargs}
        try:
            return self.template.format(**merged)
        except KeyError as e:
            raise ValueError(f"PromptTemplate missing variable: {e}") from e

    def variables(self) -> list[str]:
        return re.findall(r"\{(\w+)\}", self.template)

    def __repr__(self) -> str:
        return f"PromptTemplate(variables={self.variables()})"


# Built-in templates
SUMMARIZE = PromptTemplate(
    "Summarize the following text concisely:\n\n{text}",
    system="You are an expert at creating clear, concise summaries.",
)

TRANSLATE = PromptTemplate(
    "Translate the following text to {language}:\n\n{text}",
    system="You are an expert translator. Translate accurately and naturally.",
)

CODE_REVIEW = PromptTemplate(
    "Review this {language} code and provide feedback on quality, bugs, and improvements:\n\n```{language}\n{code}\n```",
    system="You are a senior software engineer doing a thorough code review.",
)

EXPLAIN_CODE = PromptTemplate(
    "Explain what this code does in simple terms:\n\n```\n{code}\n```",
    system="You are a patient teacher who explains code clearly.",
)

EXTRACT_JSON = PromptTemplate(
    "Extract the following information from this text and return ONLY valid JSON with these keys: {keys}\n\nText:\n{text}",
    system="You extract structured data from text. Return ONLY valid JSON, no explanation.",
)

SQL_QUERY = PromptTemplate(
    "Write a SQL query for the following request:\n{request}\n\nSchema:\n{schema}",
    system="You are a SQL expert. Write clean, optimized SQL queries.",
)
