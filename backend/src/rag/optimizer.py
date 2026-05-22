# backend/src/rag/optimizer.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

class QueryOptimizer:
    def __init__(self):
        """
        Initializes the LLM used for Query Expansion.
        """
        print("Initializing LLM Query Optimizer...")
        # Make sure you have OPENAI_API_KEY in your .env file
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"), base_url="https://us.api.openai.com/v1"
        )

    def expand_query(self, user_query: str) -> str:
        """
        Takes a patient's lay-term query and expands it with clinical synonyms.
        Returns: f"{user_query} {optimized_terms}"
        """
        system_prompt = (
            "You are a medical data retrieval assistant. Your job is to take a patient's "
            "natural language query and generate a list of exact clinical synonyms, "
            "related biomarkers, and medical terminology that a doctor would use in a clinical note. "
            "DO NOT answer the question. ONLY output a space-separated list of keywords."
        )

        try:
            # Using a fast, cheap model since this needs to happen in milliseconds
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.1,  # Keep it highly deterministic
                max_tokens=40,
            )

            expanded_terms = response.choices[0].message.content.strip()

            # The exact architecture you requested: Original + Expansion
            final_query = f"{user_query} {expanded_terms}"
            return final_query

        except Exception as e:
            print(f"Query expansion failed: {e}")
            # FALLBACK: If the API goes down, gracefully degrade to the original query
            return user_query
