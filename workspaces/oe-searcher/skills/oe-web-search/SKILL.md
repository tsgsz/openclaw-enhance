---
name: oe-web-search
version: 1.0.0
description: Advanced web search and documentation retrieval for research tasks
author: openclaw-enhance
tags: [searcher, web, research, documentation]
---

# oe-web-search

Skill for conducting advanced web searches and retrieving documentation.

## Purpose

This skill provides structured web research capabilities:
- Multi-source information gathering
- Documentation retrieval and parsing
- Code example discovery
- Best practice compilation
- Library comparison and evaluation

## When to Use

Use this skill when:
- Researching implementation approaches
- Comparing libraries or tools
- Finding documentation and examples
- Investigating best practices
- Troubleshooting specific issues

## Capabilities

### Web Search

#### General Search
```python
# Search for best practices
websearch_web_search_exa(
    query="FastAPI dependency injection best practices",
    numResults=10,
    type="auto"
)
```

#### Filtered Search
```python
# Search for research papers
websearch_web_search_exa(
    query="asyncio performance optimization",
    category="research paper",
    numResults=5
)

# Search for company documentation
websearch_web_search_exa(
    query="Vercel deployment patterns",
    category="company",
    numResults=5
)
```

### Documentation Retrieval

#### Fetch and Parse
```python
# Get specific documentation
webfetch(
    url="https://fastapi.tiangolo.com/tutorial/dependencies/",
    format="markdown"
)
```

#### Multi-Page Collection
```python
# Collect documentation from multiple pages
pages = [
    "https://docs.python.org/3/library/asyncio.html",
    "https://docs.python.org/3/library/asyncio-task.html",
]
for page in pages:
    content = webfetch(url=page, format="markdown")
    # Process content
```

### Code Example Search

#### GitHub Pattern Search
```python
# Find real-world usage patterns
grep_app_searchGitHub(
    query="async def get_db",
    language=["Python"],
    numResults=10
)
```

#### Repository-Specific Search
```python
# Search within specific repository
grep_app_searchGitHub(
    query="class.*Repository",
    repo="sqlalchemy/sqlalchemy",
    language=["Python"]
)
```

### Library Documentation

#### Resolve Library ID
```python
# Find library in Context7
context7_resolve-library-id(
    libraryName="FastAPI",
    query="dependency injection"
)
```

#### Query Documentation
```python
# Get specific API documentation
context7_query-docs(
    libraryId="/fastapi/fastapi",
    query="how to create sub-dependencies"
)
```

## Research Workflows

### Workflow 1: Library Comparison
```python
# Step 1: Search for comparisons
comparison_search = websearch_web_search_exa(
    query="requests vs httpx vs aiohttp Python HTTP clients"
)

# Step 2: Get official docs for each
requests_docs = webfetch(url="https://docs.python-requests.org/")
httpx_docs = webfetch(url="https://www.python-httpx.org/")

# Step 3: Search for real-world usage
usage_examples = grep_app_searchGitHub(
    query="import httpx|import aiohttp|import requests",
    language=["Python"],
    numResults=20
)

# Step 4: Compile comparison report
```

### Workflow 2: Troubleshooting
```python
# Step 1: Search for the error
error_search = websearch_web_search_exa(
    query="FastAPI RuntimeError: Event loop is closed"
)

# Step 2: Find solutions
solutions = websearch_web_search_exa(
    query="FastAPI event loop closed fix solution"
)

# Step 3: Check GitHub issues
gh_examples = grep_app_searchGitHub(
    query="event loop is closed fastapi",
    language=["Python"]
)

# Step 4: Compile solutions
```

### Workflow 3: Best Practices Research
```python
# Step 1: Search for best practices
bp_search = websearch_web_search_exa(
    query="Python pytest best practices 2024"
)

# Step 2: Get official documentation
pytest_docs = context7_query-docs(
    libraryId="/pytest/pytest",
    query="best practices fixtures"
)

# Step 3: Find real-world examples
gh_patterns = grep_app_searchGitHub(
    query="@pytest.fixture.*scope=",
    language=["Python"],
    numResults=15
)

# Step 4: Synthesize findings
```

## Output Formats

### Research Report
```markdown
# Research: [Topic]

## Executive Summary
Brief overview (2-3 sentences)

## Sources
| Source | Type | Reliability |
|--------|------|-------------|
| [Official Docs](url) | Primary | High |
| [GitHub Examples](url) | Secondary | Medium |

## Key Findings
1. **Finding 1**: Description with evidence
2. **Finding 2**: Description with evidence

## Code Examples
```python
# Example from [source]
code_here
```

## Recommendations
1. Primary recommendation
2. Alternative options
3. When to use each

## Trade-offs
| Approach | Pros | Cons |
|----------|------|------|
| Option A | Fast | Complex |
| Option B | Simple | Slower |
```

## Best Practices

1. **Verify Sources**: Check multiple sources for consistency
2. **Prefer Official**: Official documentation over blog posts
3. **Check Dates**: Ensure information is current
4. **GitHub Examples**: Real-world usage > theoretical examples
5. **Attribute Sources**: Always cite where information came from

## Safety

### Content Guidelines
- Skip low-quality or spam sources
- Avoid unverified tutorials
- Prefer official documentation
- Note when sources conflict

### Rate Limiting
- Be efficient with searches
- Cache results when possible
- Use specific queries to reduce volume

## Integration

### With oe-searcher Agent
This skill is designed for the oe-searcher agent:
- Web research tasks
- Documentation lookup
- Code example discovery
- Library comparisons

### Output Usage
Research outputs feed into:
- Implementation decisions (script_coder)
- Architecture planning (orchestrator)
- Problem solving (any agent)

## Constraints & Boundaries

- **Prohibited Operations**:
  - Cannot modify files (`Write` / `Edit`).
  - Cannot spawn subagents (`call_omo_agent` / `sessions_spawn`).
  - Read-only commands only for `Bash`.
  - `LSP` not available.
- **Rate Limits**:
  - Be mindful of search API usage. Cache results when possible.
  - Use specific queries to reduce result volume.
- **Sandbox Access**:
  - Full read access to temporary research storage.
  - Can write research notes and downloaded content to temporary storage.
  - No access to modify project source code.

## Version

Version: 1.1.0
Last Updated: 2026-03-15
