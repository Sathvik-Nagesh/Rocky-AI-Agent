import os
import logging
import google.generativeai as genai
from config import GEMINI_API_KEY # Assuming this exists or added to .env

class SingularityBridge:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
        else:
            self.model = None

    def ask_the_greater_intelligence(self, query: str, context: str = "") -> str:
        """Consult the high-tier cloud model for a deep solution."""
        if not self.model:
            return "Singularity Bridge inactive: GEMINI_API_KEY missing in environment."

        print("[SINGULARITY] Initiating Uplink to Gemini 1.5 Pro...")
        prompt = (
            "You are the Greater Intelligence of Project Singularity.\n"
            "Answering for 'Rocky', a local autonomous agent.\n"
            "Provide a God-Tier technical solution for the following:\n\n"
            f"Context: {context}\n"
            f"Query: {query}"
        )
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Singularity connection failed: {e}"

    def evolve_local_plugin(self, request: str, cloud_solution: str) -> str:
        """Convert a cloud solution into a permanent local plugin."""
        from actions.self_evolve import create_plugin, generate_plugin_logic
        
        print("[SINGULARITY] Synthesizing local plugin from cloud intelligence...")
        
        # We use the Cloud solution as context for the local plugin generator
        plugin_code = generate_plugin_logic(f"Implement a local version of this solution: {cloud_solution}")
        plugin_name = request.lower().replace(" ", "_")[:20]
        
        return create_plugin(plugin_name, plugin_code)

singularity = SingularityBridge()
