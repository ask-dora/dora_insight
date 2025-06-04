import os
import httpx
import secrets
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..database import get_db_session
from ..models import User, UserIntegration
from ..utils import encrypt_token, decrypt_token
from .main import IntegrationBase, get_user_by_firebase_uid, get_user_integration, oauth_states

# Initialize GitHub router
github_router = APIRouter(prefix="/github", tags=["github"])

# GitHub OAuth configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:5173/integrations")

# Temporary storage for user tokens (in production, use encrypted database storage)
user_tokens: Dict[str, Dict[str, Any]] = {}

# --- GitHub-specific Pydantic Models ---
class GitHubUser(BaseModel):
    id: int
    login: str
    name: Optional[str]
    email: Optional[str]
    avatar_url: str

class GitHubRepoInfo(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    fork: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    pushed_at: Optional[str] = None
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0

class GitHubCommit(BaseModel):
    sha: str
    commit: Dict[str, Any]
    html_url: str
    author: Optional[Dict[str, Any]] = None
    committer: Optional[Dict[str, Any]] = None
    
class GitHubIssue(BaseModel):
    number: int
    title: str
    state: str
    html_url: str
    created_at: str
    updated_at: str
    closed_at: Optional[str] = None
    body: Optional[str] = None
    user: Dict[str, Any]
    labels: List[Dict[str, Any]] = []

class GitHubMCPRequest(BaseModel):
    """Model for MCP GitHub data retrieval requests"""
    user_identifier: str
    repo: Optional[str] = None
    owner: Optional[str] = None
    issue_number: Optional[int] = None
    query_type: str = Field(..., description="Type of GitHub data to retrieve: 'repos', 'repo_details', 'commits', 'issues', 'issue_details'")
    limit: Optional[int] = 10

class GitHubMCPResponse(BaseModel):
    """Model for MCP GitHub data retrieval responses"""
    success: bool
    data: Any = None
    error: Optional[str] = None

# --- GitHub Helper Functions ---
async def check_github_connection_status(user_identifier: str) -> IntegrationBase:
    """Check GitHub connection status by calling GitHub API directly"""
    print(f"Checking GitHub connection status for user: {user_identifier}")
    
    # Check if we have a stored token for this user
    if user_identifier in user_tokens and "github" in user_tokens[user_identifier]:
        token_data = user_tokens[user_identifier]["github"]
        access_token = token_data.get("access_token")
        
        if access_token:
            print(f"Found stored GitHub token for user")
            # Test the token by calling GitHub API
            try:
                async with httpx.AsyncClient() as client:
                    user_response = await client.get(
                        "https://api.github.com/user",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    if user_response.status_code == 200:
                        github_user = user_response.json()
                        print(f"GitHub connection verified: {github_user.get('login')}")
                        return IntegrationBase(
                            integration_type="github",
                            is_connected=True,
                            connected_at=token_data.get("connected_at"),
                            integration_username=github_user.get("login")
                        )
                    else:
                        print(f"GitHub token invalid or expired: {user_response.status_code}")
                        # Remove invalid token
                        if user_identifier in user_tokens and "github" in user_tokens[user_identifier]:
                            del user_tokens[user_identifier]["github"]
            except Exception as e:
                print(f"Error checking GitHub connection: {e}")
    
    print("No valid GitHub connection found")
    return IntegrationBase(
        integration_type="github",
        is_connected=False,
        connected_at=None,
        integration_username=None
    )

async def get_github_repos(access_token: str, limit: int = 10) -> List[GitHubRepoInfo]:
    """Get GitHub repositories for the authenticated user"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"sort": "updated", "per_page": limit}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to get GitHub repositories")
        
        repos = response.json()
        return [GitHubRepoInfo(**repo) for repo in repos]

async def get_github_repo_details(access_token: str, owner: str, repo: str) -> GitHubRepoInfo:
    """Get details for a specific GitHub repository"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to get details for repo {owner}/{repo}")
        
        repo_data = response.json()
        return GitHubRepoInfo(**repo_data)

async def get_github_commits(access_token: str, owner: str, repo: str, limit: int = 10) -> List[GitHubCommit]:
    """Get recent commits for a GitHub repository"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"per_page": limit}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to get commits for repo {owner}/{repo}")
        
        commits = response.json()
        return [GitHubCommit(**commit) for commit in commits]

async def get_github_issues(access_token: str, owner: str, repo: str, limit: int = 10) -> List[GitHubIssue]:
    """Get issues for a GitHub repository"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"state": "all", "per_page": limit}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to get issues for repo {owner}/{repo}")
        
        issues = response.json()
        return [GitHubIssue(**issue) for issue in issues]

async def get_github_issue_details(access_token: str, owner: str, repo: str, issue_number: int) -> GitHubIssue:
    """Get details for a specific GitHub issue"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, 
                              detail=f"Failed to get issue #{issue_number} for repo {owner}/{repo}")
        
        issue_data = response.json()
        return GitHubIssue(**issue_data)

# --- GitHub API Endpoints ---
@github_router.get("/connect")
async def github_oauth_connect(
    user_identifier: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """Initiate GitHub OAuth flow"""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    user = await get_user_by_firebase_uid(db, user_identifier)
    if not user:
        # Create user if they don't exist
        print(f"Creating new user with Firebase UID: {user_identifier}")
        user = User(user_identifier=user_identifier)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Created user with ID: {user.id}")
    
    # Generate OAuth state
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "user_id": user.id,
        "user_identifier": user_identifier,  # Store Firebase UID for token storage
        "created_at": datetime.utcnow(),
        "integration_type": "github"
    }
    
    # GitHub OAuth URL
    github_oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=user:email,repo"
        f"&state={state}"
    )
    
    return {"auth_url": github_oauth_url}

@github_router.get("/callback")
async def github_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Handle GitHub OAuth callback"""
    print(f"=== OAUTH CALLBACK START ===")
    print(f"Received code: {code[:10]}...")
    print(f"Received state: {state}")
    
    # Validate state
    if state not in oauth_states:
        print(f"ERROR: Invalid OAuth state - {state} not in oauth_states")
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    
    oauth_data = oauth_states[state]
    user_id = oauth_data["user_id"]
    user_identifier = oauth_data["user_identifier"]  # Get Firebase UID
    print(f"Found user_id from state: {user_id}, user_identifier: {user_identifier}")
    
    # Clean up state (remove after 10 minutes anyway)
    del oauth_states[state]
    
    # Exchange code for access token
    print("Exchanging code for access token...")
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            }
        )
        
        print(f"Token response status: {token_response.status_code}")
        if token_response.status_code != 200:
            print(f"Token response error: {token_response.text}")
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        print(f"Access token received: {'Yes' if access_token else 'No'}")
        
        if not access_token:
            print(f"Token data received: {token_data}")
            raise HTTPException(status_code=400, detail="No access token received")
    
    # Get GitHub user info
    print("Getting GitHub user info...")
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        print(f"User response status: {user_response.status_code}")
        if user_response.status_code != 200:
            print(f"User response error: {user_response.text}")
            raise HTTPException(status_code=400, detail="Failed to get GitHub user info")
        
        github_user = user_response.json()
        print(f"GitHub user: {github_user.get('login')} (ID: {github_user.get('id')})")
    
    # Store or update integration
    print("Checking for existing integration...")
    existing_integration = await get_user_integration(db, user_id, "github")
    
    if existing_integration:
        print("Updating existing integration...")
        # Update existing integration
        existing_integration.access_token = encrypt_token(access_token)
        existing_integration.integration_user_id = str(github_user["id"])
        existing_integration.integration_username = github_user["login"]
        existing_integration.connected_at = datetime.utcnow()
        existing_integration.is_active = True
        existing_integration.integration_metadata = {
            "name": github_user.get("name"),
            "email": github_user.get("email"),
            "avatar_url": github_user.get("avatar_url")
        }
        print("Updated existing integration fields")
    else:
        print("Creating new integration...")
        # Create new integration
        new_integration = UserIntegration(
            user_id=user_id,
            integration_type="github",
            access_token=encrypt_token(access_token),
            integration_user_id=str(github_user["id"]),
            integration_username=github_user["login"],
            is_active=True,
            integration_metadata={
                "name": github_user.get("name"),
                "email": github_user.get("email"),
                "avatar_url": github_user.get("avatar_url")
            }
        )
        db.add(new_integration)
        print("Added new integration to session")
    
    print("Committing to database...")
    await db.commit()
    print("Database commit successful!")
    
    # Also store token in memory for immediate status checking
    if user_identifier not in user_tokens:
        user_tokens[user_identifier] = {}
    
    user_tokens[user_identifier]["github"] = {
        "access_token": access_token,
        "connected_at": datetime.utcnow(),
        "github_username": github_user["login"],
        "github_user_id": str(github_user["id"])
    }
    print(f"Stored GitHub token in memory for user: {user_identifier}")
    
    # Redirect to frontend success page
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    redirect_url = f"{frontend_url}/integrations?success=github"
    print(f"Redirecting to: {redirect_url}")
    print("=== OAUTH CALLBACK END ===")
    return RedirectResponse(url=redirect_url)

@github_router.delete("/")
async def disconnect_github(
    user_identifier: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """Disconnect GitHub integration"""
    user = await get_user_by_firebase_uid(db, user_identifier)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    integration = await get_user_integration(db, user.id, "github")
    if integration:
        # Deactivate integration in database
        integration.is_active = False
        await db.commit()
    
    # Remove from in-memory storage
    if user_identifier in user_tokens and "github" in user_tokens[user_identifier]:
        del user_tokens[user_identifier]["github"]
        print(f"Removed GitHub token from memory for user: {user_identifier}")
    
    return {"message": "GitHub integration disconnected successfully"}

@github_router.get("/user")
async def get_github_user_info(
    user_identifier: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get GitHub user information"""
    user = await get_user_by_firebase_uid(db, user_identifier)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    integration = await get_user_integration(db, user.id, "github")
    if not integration or not integration.is_active:
        raise HTTPException(status_code=404, detail="GitHub integration not connected")
    
    try:
        access_token = decrypt_token(integration.access_token)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt access token")
    
    # Get current GitHub user info
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_response.status_code == 401:
            # Token expired or revoked
            integration.is_active = False
            await db.commit()
            raise HTTPException(status_code=401, detail="GitHub token expired")
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get GitHub user info")
        
        github_user = user_response.json()
    
    return GitHubUser(**github_user)

# --- MCP Endpoint ---
@github_router.post("/mcp", response_model=GitHubMCPResponse)
async def github_mcp_handler(
    request: GitHubMCPRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """MCP handler for GitHub data retrieval - fetches data on demand for LLM context"""
    try:
        # Get the user
        user = await get_user_by_firebase_uid(db, request.user_identifier)
        if not user:
            return GitHubMCPResponse(success=False, error="User not found")
        
        # Get GitHub integration
        integration = await get_user_integration(db, user.id, "github")
        if not integration or not integration.is_active:
            return GitHubMCPResponse(success=False, error="GitHub integration not connected")
        
        # Decrypt access token
        try:
            access_token = decrypt_token(integration.access_token)
        except Exception:
            return GitHubMCPResponse(success=False, error="Failed to decrypt access token")
        
        # Handle different query types
        limit = request.limit or 10
        
        if request.query_type == "repos":
            # List user's repositories
            repos = await get_github_repos(access_token, limit)
            return GitHubMCPResponse(success=True, data=repos)
            
        elif request.query_type == "repo_details":
            # Get details for a specific repository
            if not request.owner or not request.repo:
                return GitHubMCPResponse(success=False, error="Owner and repo names are required")
                
            repo_details = await get_github_repo_details(access_token, request.owner, request.repo)
            return GitHubMCPResponse(success=True, data=repo_details)
            
        elif request.query_type == "commits":
            # Get commits for a repository
            if not request.owner or not request.repo:
                return GitHubMCPResponse(success=False, error="Owner and repo names are required")
                
            commits = await get_github_commits(access_token, request.owner, request.repo, limit)
            return GitHubMCPResponse(success=True, data=commits)
            
        elif request.query_type == "issues":
            # Get issues for a repository
            if not request.owner or not request.repo:
                return GitHubMCPResponse(success=False, error="Owner and repo names are required")
                
            issues = await get_github_issues(access_token, request.owner, request.repo, limit)
            return GitHubMCPResponse(success=True, data=issues)
            
        elif request.query_type == "issue_details":
            # Get details for a specific issue
            if not request.owner or not request.repo or not request.issue_number:
                return GitHubMCPResponse(success=False, error="Owner, repo name, and issue number are required")
                
            issue = await get_github_issue_details(access_token, request.owner, request.repo, request.issue_number)
            return GitHubMCPResponse(success=True, data=issue)
            
        else:
            return GitHubMCPResponse(success=False, error=f"Unknown query type: {request.query_type}")
            
    except HTTPException as e:
        return GitHubMCPResponse(success=False, error=f"GitHub API error: {e.detail}")
    except Exception as e:
        return GitHubMCPResponse(success=False, error=f"Error processing request: {str(e)}")
