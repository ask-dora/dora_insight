import os
import google.generativeai as genai
import numpy as np
from dotenv import load_dotenv
from typing import List, Dict, Any

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
    if not user_prompt_embedding or not session_messages:
        return ""

    # If session_messages are already pre-filtered by pgvector similarity search,
    # we just need to format them.
    # If not, and we are doing in-memory similarity (less ideal with pgvector),
    # the original logic would apply.

    # For now, let's assume session_messages are the top_k results from a DB query
    # and this function is mostly for formatting.
    # The actual vector search logic will be in main.py using db_session.query(...).l2_distance(...)

    context_parts = []
    for item in session_messages[:top_k]: # Ensure we only take top_k if more were passed
        context_parts.append(f"{item.get('sender', 'unknown').capitalize()}: {item.get('content', '')}")
    
    return "\n".join(context_parts)


async def generate_llm_response(user_prompt: str, context: str) -> str:
    """Generates a response from Gemini LLM with given prompt and context."""
    try:
        system_prompt = "Your name is Dora. You are an AI assistant designed to help users understand their data better, often through visualizations and insightful analysis. Be helpful and friendly."
        
        # Initialize the model with the system instruction
        model = genai.GenerativeModel(
            GENERATION_MODEL,
            system_instruction=system_prompt
        )
        
        # Construct the prompt for the LLM (without manually adding the system_prompt here)
        if context:
            prompt_for_llm = f"""Based on the following context from the current conversation:
---
{context}
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
