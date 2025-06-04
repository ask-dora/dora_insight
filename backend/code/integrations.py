"""
Compatibility module for existing integrations code.
This file now imports and re-exports from the new modular structure in the 'integrations' package.
"""

# Re-export from modular structure
from .integrations import (
    router,
    IntegrationBase,
    IntegrationStatus,
    github_router,
    GitHubMCPRequest,
    GitHubMCPResponse
)

# Import specific GitHub MCP handler for backward compatibility
from .integrations.github import github_mcp_handler

# These are re-exported for backward compatibility
__all__ = [
    'router',
    'IntegrationBase',
    'IntegrationStatus',
    'github_mcp_handler',
    'GitHubMCPRequest',
    'GitHubMCPResponse'
]
