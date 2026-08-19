---
description: Reusable prompt templates in Shakti Python Framework — variable substitution plus built-in templates for summarization, translation, and code review.
---

# Prompt Templates

`PromptTemplate` is a reusable prompt with `{variable}` placeholders and an optional dedicated system prompt — useful for keeping prompt text out of handler logic.

## Defining and rendering

```python
from shakti.ai.templates import PromptTemplate

tpl = PromptTemplate(
    "Summarize this in {language}: {text}",
    system="You are a helpful summarizer.",
)
prompt = tpl.render(language="French", text="Hello world")
```

`render(**kwargs)` does `str.format(**kwargs)` under the hood and raises `ValueError` naming the missing variable if you forget one. `tpl.variables()` lists the placeholder names found in the template. `defaults` lets you pre-fill variables that are usually the same:

```python
tpl = PromptTemplate("Translate to {language}: {text}", defaults={"language": "Spanish"})
tpl.render(text="Good morning")   # language defaults to "Spanish"
```

## Registering with `AI`

```python
ai.register_template("summarize_fr", tpl)
answer = await ai.ask("summarize_fr", text="Long article text...")
```

`ai.ask(template_name, **variables)` renders the named template and sends it through `ai.chat()`, using the template's own `system` prompt if it has one. Registering by name is optional — you can also just call `tpl.render(...)` yourself and pass the result to `ai.chat()` directly.

## Built-in templates

`shakti.ai.templates` ships a few ready to use or register:

```python
from shakti.ai.templates import SUMMARIZE, TRANSLATE, CODE_REVIEW, EXPLAIN_CODE, EXTRACT_JSON, SQL_QUERY

ai.register_template("summarize", SUMMARIZE)
ai.register_template("translate", TRANSLATE)
```

| Template | Variables | Purpose |
|---|---|---|
| `SUMMARIZE` | `text` | concise summary |
| `TRANSLATE` | `language`, `text` | translation |
| `CODE_REVIEW` | `language`, `code` | quality/bug/improvement review |
| `EXPLAIN_CODE` | `code` | plain-language explanation |
| `EXTRACT_JSON` | `keys`, `text` | structured extraction, JSON-only output |
| `SQL_QUERY` | `request`, `schema` | natural language → SQL |

```python
answer = await ai.ask("code_review", language="python", code=snippet)
```

(after `ai.register_template("code_review", CODE_REVIEW)`.)
