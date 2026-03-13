# Searcher Tools Configuration

This TOOLS.md defines the available tools and their usage patterns for the `oe-searcher` workspace.

## Research Tools

### websearch_web_search_exa
**Purpose**: Search the web for current information

**Usage Patterns**:
- Research best practices and design patterns
- Find library documentation and comparisons
- Look up troubleshooting guides
- Discover new tools and technologies

**Best Practices**:
- Use specific queries for better results
- Filter by category when appropriate (research_paper, company, people)
- Prefer auto search type for balanced results

**Example**:
```python
# Search for FastAPI best practices
websearch_web_search_exa(
    query="FastAPI dependency injection best practices",
    numResults=5
)
```

### webfetch
**Purpose**: Fetch specific web pages for detailed content

**Usage Patterns**:
- Retrieve API documentation pages
- Get specific tutorial content
- Fetch library reference docs
- Download code examples

**Best Practices**:
- Use markdown format for structured content
- Check if page is accessible before fetching
- Handle timeouts for slow pages

**Example**:
```python
# Fetch FastAPI documentation
webfetch(
    url="https://fastapi.tiangolo.com/tutorial/dependencies/",
    format="markdown"
)
```

### grep_app_searchGitHub
**Purpose**: Search real-world code examples on GitHub

**Usage Patterns**:
- Find implementation patterns for libraries
- See how others structure similar code
- Discover common usage patterns
- Verify best practices in production code

**Best Practices**:
- Search for specific code patterns, not keywords
- Use language filters for relevant results
- Look at popular repositories for quality examples

**Example**:
```python
# Find FastAPI dependency examples
grep_app_searchGitHub(
    query="Depends(get_db)",
    language=["Python"],
    repo="fastapi"
)
```

### context7_resolve-library-id
**Purpose**: Resolve library names to Context7-compatible IDs

**Usage Patterns**:
- Find library documentation in Context7
- Verify library availability
- Get exact library identifiers

**Example**:
```python
# Resolve FastAPI library ID
context7_resolve-library-id(
    libraryName="FastAPI",
    query="How to use FastAPI dependencies"
)
```

### context7_query-docs
**Purpose**: Query library documentation from Context7

**Usage Patterns**:
- Get up-to-date API documentation
- Find code examples from official docs
- Verify function signatures and parameters

**Example**:
```python
# Query FastAPI documentation
context7_query-docs(
    libraryId="/fastapi/fastapi",
    query="How to create dependencies with yield"
)
```

## File Tools

### Read
**Purpose**: Read files for local documentation

**Usage Patterns**:
- Read local README files
- Check project documentation
- Review existing research notes

**Constraints**:
- Read-only access
- Cannot modify files

**Example**:
```python
# Read local documentation
Read(filePath="/path/to/README.md")
```

## Tool Selection Guide

### By Research Task

| Task Type | Primary Tool | Secondary Tools |
|-----------|--------------|-----------------|
| General Research | websearch_web_search_exa | webfetch |
| API Documentation | context7_query-docs | webfetch |
| Code Examples | grep_app_searchGitHub | websearch_web_search_exa |
| Library Comparison | websearch_web_search_exa | context7_query-docs |
| Troubleshooting | websearch_web_search_exa | grep_app_searchGitHub |
| Best Practices | websearch_web_search_exa | grep_app_searchGitHub |

### Research Workflow

1. **Start with web search** for broad topic understanding
2. **Fetch specific documentation** for detailed reference
3. **Search GitHub** for real-world examples
4. **Query Context7** for official API docs
5. **Compile findings** into structured report

## Output Formats

### Research Report Structure
```markdown
# Research: [Topic]

## Summary
Brief overview of findings

## Sources
- [Title](url) - Brief description

## Key Findings
1. Finding with evidence
2. Finding with evidence

## Code Examples
```python
# Example from GitHub/source
```

## Recommendations
1. Recommended approach
2. Alternative options
```

## Constraints

### Read-Only Operations
- **Cannot Write**: No file modifications
- **Cannot Edit**: No file updates
- **Cannot Bash**: No command execution
- **Sandbox Only**: Research artifacts in temp storage

### Rate Limits
- Be mindful of search API usage
- Cache results when possible
- Use specific queries to reduce result volume

## Safety

### Content Filtering
- Skip irrelevant or low-quality sources
- Verify information from multiple sources
- Note when sources conflict

### Source Attribution
- Always cite sources
- Include URLs for verification
- Note source quality/reliability

## Version

Version: 1.0.0
Last Updated: 2026-03-13
