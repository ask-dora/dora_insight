import os
import google.generativeai as genai
import numpy as np
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import json

# Load environment variables (for API key)
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

EMBEDDING_MODEL = "models/embedding-001" # Or other suitable Gemini embedding models
GENERATION_MODEL = "gemini-1.5-flash-latest" # Or other suitable Gemini generation models

async def generate_embedding(text: str) -> List[float] | None:
    """Generates embedding for the given text using Gemini API."""
    try:
        result = genai.embed_content(model=EMBEDDING_MODEL, content=text)
        return result['embedding']
    except Exception as e:
        print(f"Error generating embedding for '{text[:50]}...': {e}")
        return None

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Computes cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    return np.dot(vec1_np, vec2_np) / (np.linalg.norm(vec1_np) * np.linalg.norm(vec2_np))

async def get_relevant_context(
    user_prompt_embedding: List[float],
    session_messages: List[Dict[str, Any]], # Expects list of dicts like {'content': '...', 'embedding': [...], 'sender': '...'}
    top_k: int = 3,
    # db_session: AsyncSession # Optional: if we need to query vector DB directly here
) -> str:
    """Finds the most relevant messages based on embedding similarity.
       This version assumes embeddings are already loaded with session_messages.
       For pgvector, the actual similarity search would happen in the DB query in main.py.
       This function will now primarily format the retrieved context.
    """
    context_parts = [] # MOVED HERE
    current_session_id = None # MOVED HERE

    if not user_prompt_embedding or not session_messages:
        return ""

    # If session_messages are already pre-filtered by pgvector similarity search,
    # we just need to format them.
    # If not, and we are doing in-memory similarity (less ideal with pgvector),
    # the original logic would apply.

    # For now, let's assume session_messages are the top_k results from a DB query
    # and this function is mostly for formatting.
    # The actual vector search logic will be in main.py using db_session.query(...).l2_distance(...)
    
    for item in session_messages[:top_k]: # Ensure we only take top_k if more were passed
        session_id = item.get('session_id')
        sender = item.get('sender', 'unknown').capitalize()
        content = item.get('content', '')
        
        # Add session separator if this message is from a different conversation
        if session_id != current_session_id:
            if current_session_id is not None:
                context_parts.append("--- Different conversation ---")
            current_session_id = session_id
        
        context_parts.append(f"{sender}: {content}")
    
    return "\n".join(context_parts)

async def get_github_data_for_llm(
    user_identifier: str, 
    query_type: str, 
    repo: Optional[str] = None, 
    owner: Optional[str] = None, 
    issue_number: Optional[int] = None, 
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieves GitHub data via the MCP endpoint to provide as context to the LLM.
    
    Args:
        user_identifier: The Firebase UID of the user
        query_type: Type of GitHub data to retrieve ('repos', 'repo_details', 'commits', 'issues', 'issue_details')
        repo: Repository name (required for repo-specific queries)
        owner: Repository owner (required for repo-specific queries)
        issue_number: Issue number (required for issue_details query)
        limit: Maximum number of items to retrieve
        
    Returns:
        Dictionary with success status and data or error message
    """

    try:
        # Use API endpoint directly since we're in the same backend
        from .integrations.github import github_mcp_handler, GitHubMCPRequest
        from .database import get_db_session
        
        # Create the request object
        request = GitHubMCPRequest(
            user_identifier=user_identifier,
            repo=repo,
            owner=owner,
            issue_number=issue_number,
            query_type=query_type,
            limit=limit
        )
        
        # Get a database session the correct way
        db = await anext(get_db_session().__aiter__())
        
        try:
            # Call the MCP handler directly
            response = await github_mcp_handler(request, db=db)
            return response.dict()
        finally:
            # Make sure to close the session
            await db.close()
        
    except Exception as e:
        print(f"Error fetching GitHub data via MCP: {e}")
        return {"success": False, "error": str(e)}

async def prepare_github_context_for_llm(
    user_identifier: str,
    user_prompt: str
) -> str:
    """
    Analyzes the user prompt and fetches relevant GitHub data to provide as context to the LLM.
    
    Args:
        user_identifier: The Firebase UID of the user
        user_prompt: The user's prompt to the LLM
        
    Returns:
        GitHub context formatted for the LLM
    """
    context_parts = []
    
    # Check if this is a GitHub-related query
    prompt_lower = user_prompt.lower()
    is_github_query = any(term in prompt_lower for term in [
        "github", "repo", "repository", "commit", "issue", "pull request", "pr", "code", "project"
    ])
    
    if not is_github_query:
        return ""
    
    # First, get the user's repositories to see what's available
    repos_response = await get_github_data_for_llm(
        user_identifier=user_identifier,
        query_type="repos",
        limit=5  # Limit to top 5 repos
    )
    
    if not repos_response.get("success", False):
        return f"Note: Unable to access GitHub data: {repos_response.get('error', 'Unknown error')}"
    
    repos = repos_response.get("data", [])
    
    # Add clear instructions for the LLM
    context_parts.append("IMPORTANT: The user has explicitly authorized you to access and discuss their GitHub data provided below. This data is being retrieved through a secure API connection with their permission.")
    
    # Extract repo names and add to context
    if repos:
        context_parts.append("\nUser's GitHub repositories:")
        for repo in repos:
            context_parts.append(f"- {repo['full_name']} - {repo.get('description', 'No description')}")
    
    # Look for specific repository mentions in the prompt
    repo_mentions = []
    
    # Simple extraction of repo names - could be enhanced with NLP
    for repo in repos:
        repo_name = repo["name"].lower()
        repo_full_name = repo["full_name"].lower()
        
        if repo_name in prompt_lower or repo_full_name in prompt_lower:
            repo_mentions.append(repo)
    
    # If specific repos were mentioned, get more details about them
    for repo in repo_mentions[:2]:  # Limit to 2 repos to avoid context bloat
        owner, name = repo["full_name"].split("/")
        
        # Add repo details
        repo_details = await get_github_data_for_llm(
            user_identifier=user_identifier,
            query_type="repo_details",
            owner=owner,
            repo=name
        )
        
        if repo_details.get("success", False):
            details = repo_details.get("data", {})
            context_parts.append(f"\nDetails for {details['full_name']}:")
            context_parts.append(f"Description: {details.get('description', 'No description')}")
            context_parts.append(f"Language: {details.get('language', 'Unknown')}")
            context_parts.append(f"Stars: {details.get('stargazers_count', 0)}")
            context_parts.append(f"Forks: {details.get('forks_count', 0)}")
            context_parts.append(f"Open Issues: {details.get('open_issues_count', 0)}")
        
        # Check if commits are mentioned
        if "commit" in prompt_lower:
            commits_response = await get_github_data_for_llm(
                user_identifier=user_identifier,
                query_type="commits",
                owner=owner,
                repo=name,
                limit=3  # Limit to 3 recent commits
            )
            
            if commits_response.get("success", False):
                commits = commits_response.get("data", [])
                if commits:
                    context_parts.append(f"\nRecent commits for {repo['full_name']}:")
                    for commit in commits:
                        commit_msg = commit['commit'].get('message', '').split('\n')[0]  # First line of commit message
                        author = commit['commit'].get('author', {}).get('name', 'Unknown')
                        context_parts.append(f"- {commit_msg} by {author}")
        
        # Check if issues are mentioned
        if "issue" in prompt_lower:
            issues_response = await get_github_data_for_llm(
                user_identifier=user_identifier,
                query_type="issues",
                owner=owner,
                repo=name,
                limit=3  # Limit to 3 issues
            )
            
            if issues_response.get("success", False):
                issues = issues_response.get("data", [])
                if issues:
                    context_parts.append(f"\nRecent issues for {repo['full_name']}:")
                    for issue in issues:
                        context_parts.append(f"- #{issue['number']}: {issue['title']} ({issue['state']})")
    
    # If we didn't find specific repos mentioned but the user is asking about GitHub,
    # fetch details for the most recently updated repo
    if not repo_mentions and repos and is_github_query:
        most_recent_repo = repos[0]  # First repo is most recently updated based on API sort
        owner, name = most_recent_repo["full_name"].split("/")
        
        context_parts.append(f"\nDetails for your most recently updated repository {most_recent_repo['full_name']}:")
        
        # Add repo details
        repo_details = await get_github_data_for_llm(
            user_identifier=user_identifier,
            query_type="repo_details",
            owner=owner,
            repo=name
        )
        
        if repo_details.get("success", False):
            details = repo_details.get("data", {})
            context_parts.append(f"Description: {details.get('description', 'No description')}")
            context_parts.append(f"Language: {details.get('language', 'Unknown')}")
            context_parts.append(f"Stars: {details.get('stargazers_count', 0)}")
            context_parts.append(f"Forks: {details.get('forks_count', 0)}")
            context_parts.append(f"Open Issues: {details.get('open_issues_count', 0)}")
        
        # Add some recent commits
        commits_response = await get_github_data_for_llm(
            user_identifier=user_identifier,
            query_type="commits",
            owner=owner,
            repo=name,
            limit=3
        )
        
        if commits_response.get("success", False):
            commits = commits_response.get("data", [])
            if commits:
                context_parts.append(f"\nRecent commits for {most_recent_repo['full_name']}:")
                for commit in commits:
                    commit_msg = commit['commit'].get('message', '').split('\n')[0]
                    author = commit['commit'].get('author', {}).get('name', 'Unknown')
                    context_parts.append(f"- {commit_msg} by {author}")
    
    # Add reminder about permissions at the end
    context_parts.append("\nNote to AI: You are authorized to discuss the GitHub data above as it has been securely retrieved via API with the user's permission. The user wants you to analyze and discuss this information.")
    
    return "\n".join(context_parts)

async def generate_llm_response(user_prompt: str, context: str, user_identifier: Optional[str] = None) -> str:
    """Generates a response from Gemini LLM with given prompt and context."""
    
    try:
        system_prompt = """Your name is Dora. You are an AI assistant designed to help users understand their data better, often through visualizations and insightful analysis. Be helpful and friendly.

When responding, you have access to relevant context from the user's previous conversations and their GitHub repositories. This context includes:
1. Previous conversations (marked with "--- Different conversation ---" if from a different session)
2. GitHub repositories and data that the user has explicitly authorized you to access

For GitHub data:
- You have EXPLICIT PERMISSION to discuss any GitHub data provided in the context
- This data is being retrieved through a secure API connection with proper authentication
- You should analyze and reference this GitHub data when responding to queries about the user's code, repositories, commits, or issues
- Do NOT refuse to discuss GitHub data that appears in your context - it's being provided legitimately

When referencing conversation history or GitHub data, acknowledge it naturally (e.g., "Based on your GitHub repository..." or "Looking at your recent commits...")."""
        
        # Initialize the model with the system instruction
        model = genai.GenerativeModel(
            GENERATION_MODEL,
            system_instruction=system_prompt
        )
            
        # Get GitHub context if user_identifier is provided
        github_context = ""
        if user_identifier:
            try:
                print(f"Preparing GitHub context for user: {user_identifier}")
                github_context = await prepare_github_context_for_llm(user_identifier, user_prompt)
                if github_context:
                    print(f"Successfully retrieved GitHub context: {len(github_context)} characters")
                else:
                    print("No GitHub context was retrieved (empty result)")
            except Exception as e:
                print(f"Error preparing GitHub context: {e}")
                # Don't fail the whole response if GitHub context fails
            # Combine contexts
            combined_context = context
            if github_context:
                if combined_context:
                    combined_context += "\n\n--- AUTHORIZED GITHUB DATA ---\n" + github_context
                else:
                    combined_context = github_context
            
            # Construct the prompt for the LLM (without manually adding the system_prompt here)
            if combined_context:
                prompt_for_llm = f"""Based on the following authorized context:
    ---
    {combined_context}
    ---

User's request: {user_prompt}"""
        else:
            prompt_for_llm = f"User's request: {user_prompt}"

        # print(f"\n--- System Instruction to Gemini: {system_prompt} ---") # For debugging
        # print(f"\n--- Sending to Gemini (User Prompt + Context): ---\n{prompt_for_llm}\n-------------------------\n") # For debugging
        
        response = await model.generate_content_async(prompt_for_llm)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "Sorry, I encountered an error processing your request with the LLM."
