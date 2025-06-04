from .main import router, IntegrationBase, IntegrationStatus
from .github import github_router, GitHubMCPRequest, GitHubMCPResponse, check_github_connection_status

# Include all integration routers in the main router
router.include_router(github_router)

# Export commonly used types and functions
__all__ = [
    'router',
    'IntegrationBase',
    'IntegrationStatus',
    'github_router',
    'GitHubMCPRequest',
    'GitHubMCPResponse',
    'check_github_connection_status'
]
