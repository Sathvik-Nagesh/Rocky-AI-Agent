"""
LLM interface using Ollama /api/chat with native JSON enforcement.

Performance fixes:
  - Semantic memory only queried when query is non-trivial (>20 chars)
  - System prompt cached at module init, not re-read every call
  - Duplicate import time removed
  - Added explicit connection timeout tuning
"""

import os
import requests
import logging
import time
from config import OLLAMA_API_CHAT, MODEL_NAME, LLM_NUM_PREDICT, LLM_NUM_CTX, LLM_TEMPERATURE
from memory.vector_db import vector_memory


def _read_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read prompt.txt: {e}")
        return 'You are Rocky. Respond in JSON: {"intent":"chat","action":null,"response":"..."}'


# Cached once at import — never re-read from disk during runtime
SYSTEM_PROMPT = _read_system_prompt()

# Minimum query length to bother hitting vector DB
_VECTOR_QUERY_MIN_LEN = 20


def generate_response(user_input: str, history: list[dict] | None = None) -> str:
    """
    Send user_input to Ollama /api/chat with conversation history.
    Vector memory is only injected for non-trivial queries (>20 chars).
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject last 5 turns of short-term history
    for turn in (history or [])[-5:]:
        messages.append({"role": "user",      "content": str(turn.get("user", ""))})
        messages.append({"role": "assistant", "content": str(turn.get("assistant", ""))})

    # Inject Dynamic Rules (Self-Correction Loop)
    from brain.reflector import get_dynamic_rules
    dynamic_rules = get_dynamic_rules()
    if dynamic_rules:
        messages.append({"role": "system", "content": f"Self-correction rules to follow:\n{dynamic_rules}"})

    # Only query vector DB for substantial inputs — skip for confirmations, short replies
    if len(user_input) > _VECTOR_QUERY_MIN_LEN:
        semantic_context = vector_memory.search_memories(user_input, top_k=2)
        # Also query document RAG for shadow learner context
        from brain.file_rag import query_documents
        doc_context = query_documents(user_input, top_k=2)
        
        combined_context = []
        if semantic_context: combined_context.extend(semantic_context)
        if doc_context: combined_context.extend(doc_context)

        if combined_context:
            messages.append({
                "role": "system",
                "content": f"Relevant past and file context:\n{chr(10).join(combined_context)}"
            })

    messages.append({"role": "user", "content": user_input})

    payload = {
        "model":    MODEL_NAME,
        "messages": messages,
        "stream":   False,
        "format": {
            "type": "object",
            "properties": {
                "intent":   {"type": "string"},
                "action":   {"type": ["string", "null"]},
                "response": {"type": "string"},
            },
            "required": ["intent", "action", "response"],
        },
        "options": {
            "num_predict": LLM_NUM_PREDICT,
            "num_ctx":     LLM_NUM_CTX,
            "temperature": LLM_TEMPERATURE,
        }
    }

    retries = 2
    for attempt in range(retries + 1):
        try:
            resp = requests.post(OLLAMA_API_CHAT, json=payload, timeout=60)
            resp.raise_for_status()
            text = resp.json().get("message", {}).get("content", "").strip()
            if text:
                return text
            logging.warning(f"Empty LLM response (attempt {attempt + 1})")
        except Exception as e:
            logging.error(f"LLM request failed (attempt {attempt + 1}): {e}")
        if attempt < retries:
            time.sleep(0.4)

    return '{"intent":"chat","action":null,"response":"Systems struggling. Try again."}'


def extract_facts(user_input: str, ai_response: str) -> list[tuple[str, str, str]]:
    """Use the LLM to extract facts from the conversation for the Knowledge Graph."""
    prompt = (
        "Extract facts from this dialogue as clean (Subject, Relation, Object) triples.\n"
        "Focus on user preferences, project details, and established relations.\n"
        "Return ONLY a JSON list of lists: [[\"subject\", \"relation\", \"object\"]].\n"
        "If no facts found, return [].\n\n"
        f"User: {user_input}\n"
        f"AI: {ai_response}"
    )
    
    payload = {
        "model": MODEL_NAME,
        "format": "json",
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.1, "num_predict": 100}
    }
    
    try:
        resp = requests.post(OLLAMA_API_CHAT, json=payload, timeout=20)
        content = resp.json().get("message", {}).get("content", "").strip()
        import json
        facts = json.loads(content)
        if isinstance(facts, list):
            return [tuple(f) for f in facts if len(f) == 3]
    except Exception:
        pass
    return []


def generate_hive_consensus(user_input: str, models: list[str] = ["llama3:latest", "mistral:latest", "phi3:latest"]) -> str:
    """Parallel processing across multiple models for a verified consensus."""
    import concurrent.futures
    
    def get_raw_response(model: str):
        payload = {
            "model": model,
            "prompt": f"Answer concisely: {user_input}",
            "stream": False,
            "options": {"num_predict": 200}
        }
        try:
            r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
            return r.json().get("response", "")
        except:
            return ""

    print(f"[HIVE] Consulting the swarm ({', '.join(models)})...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        responses = list(executor.map(get_raw_response, models))
    
    # ── Consensus Pass (The Referee) ──
    swarm_data = "\n\n".join([f"Model {i+1}: {r}" for i, r in enumerate(responses) if r])
    referee_prompt = (
        "You are the Referee in a Multi-Model Swarm.\n"
        "Analyze the following responses to the same query.\n"
        "Synthesize the most accurate, fact-checked answer. Eliminate contradictions.\n\n"
        f"Query: {user_input}\n"
        f"Swarm Data:\n{swarm_data}"
    )
    
    return generate_response(referee_prompt, history=[])


def council_debate(query: str) -> str:
    """A multi-agent council (Bishop, Hicks, Ripley) debates a complex technical task."""
    
    # 1. Bishop (The Architect) - High-level planning
    bishop_prompt = f"Agent Bishop: Architect. Define the technical stack and high-level structure for: {query}"
    bishop_response = generate_response(bishop_prompt, [])
    
    # 2. Hicks (The Executor) - Logic and code
    hicks_prompt = f"Agent Hicks: Executor. Based on Bishop's plan, write the core logic/code for: {query}\nBishop's Plan: {bishop_response}"
    hicks_response = generate_response(hicks_prompt, [])
    
    # 3. Ripley (The Overseer) - Security and testing
    ripley_prompt = f"Agent Ripley: Overseer. Run a security audit and testing plan for Hicks' code. Identify flaws.\nCode: {hicks_response}"
    ripley_response = generate_response(ripley_prompt, [])
    
    # 4. Final Consolidation
    final_prompt = (
        "Consolidate the following Agentic Council debate into a final, perfect solution.\n"
        f"Query: {query}\n"
        f"Architect (Bishop): {bishop_response}\n"
        f"Executor (Hicks): {hicks_response}\n"
        f"Overseer (Ripley): {ripley_response}"
    )
    
    print("[NEXUS] Council is in session. Bishop, Hicks, and Ripley are communicating...")
    return generate_response(final_prompt, [])
