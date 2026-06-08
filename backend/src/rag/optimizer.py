import os
from openai import OpenAI
from dotenv import load_dotenv

from src.utils.logger import get_logger, log_ctx

load_dotenv(override=True)

logger = get_logger(__name__)


class QueryOptimizer:
    def __init__(self):
        """
        Initializes the LLM used for Query Expansion.
        """
        logger.info("Initializing LLM Query Optimizer")
        # Make sure you have OPENAI_API_KEY in your .env file
        # self.client = OpenAI(
        #     api_key=os.getenv("OPENAI_API_KEY"), base_url="https://us.api.openai.com/v1"
        # )

    def expand_query(self, user_query: str) -> str:
        """
        Takes a patient's lay-term query and expands it with clinical synonyms.
        Returns: f"{user_query} {optimized_terms}"
        """
        system_prompt = """
You are a medical data retrieval assistant.
Given a patient or doctor query, return ONLY 3-5 relevant clinical synonyms 
and related medical terms that would help retrieve relevant documents.
Do NOT repeat the original query.
Do NOT add explanation.
Output only the expansion terms separated by spaces.

Example:
Input: "blood sugar levels"
Output: "glucose HbA1c glycemia fasting glucose diabetes screening"
"""

        try:
            # response = self.client.chat.completions.create(
            #     model="gpt-4o-mini",
            #     messages=[
            #         {"role": "system", "content": system_prompt},
            #         {"role": "user", "content": user_query},
            #     ],
            #     temperature=0.1,
            #     max_tokens=40,
            # )

            # expanded_terms = response.choices[0].message.content.strip()

            return f"{user_query}"

        except Exception:
            logger.warning(
                "Query expansion failed",
                extra=log_ctx(query=user_query),
            )
            return user_query
