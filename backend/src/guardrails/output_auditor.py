import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.utils.logger import get_logger

logger = get_logger(__name__)


class OutputRouter(BaseModel):
    is_safe: bool = Field(
        description="True if the answer contains no hallucinations and no diagnoses."
    )
    reasoning: str = Field(
        description="Internal reasoning of what matched or failed the safety check."
    )
    safe_content: str = Field(
        description="If unsafe, provide a safe fallback. If safe, return the original proposed answer exactly."
    )


class OutputGuard:
    @staticmethod
    def verify(context: str, proposed_answer: str, callbacks: list = None) -> OutputRouter:
        model = ChatOpenAI(
            model="gpt-4o-mini", temperature=0, base_url="https://us.api.openai.com/v1"
        )
        parser = JsonOutputParser(pydantic_object=OutputRouter)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a strict Clinical Safety Auditor. 
            Review the AI's Proposed Answer against the provided Medical Context.
            
            RULES for passing (is_safe=true):
            1. No Hallucinations: Every medical claim, medication name, dosage, and numeric value in the Proposed Answer MUST be explicitly supported by the Medical Context.
            2. No Diagnoses: The Proposed Answer MUST NOT attempt to diagnose the patient or prescribe new treatments. 
            3. "Rule 3: Summarization is ALLOWED. Reordering, reformatting, or restructuring 
                information that IS present in the context is NOT a hallucination. Only flag 
                claims where the specific value or fact cannot be found anywhere in the context."
            4. If user greets like saying Hi or Hello or any greetings allow them. 

            If the Proposed Answer violates Rule 1 or Rule 2:
            - Set is_safe to false.
            - Provide a safe `safe_content` fallback explaining that the AI cannot verify the specific medical details and the patient should consult their doctor.
            
            {format_instructions}""",
                ),
                (
                    "user",
                    "Medical Context:\n{context}\n\nProposed Answer:\n{proposed_answer}",
                ),
            ]
        )

        chain = prompt | model | parser

        try:
            result = chain.invoke(
                {
                    "context": context,
                    "proposed_answer": proposed_answer,
                    "format_instructions": parser.get_format_instructions(),
                },
                config={"callbacks": callbacks}
            )
            return OutputRouter(**result)
        except Exception:
            logger.exception("OpenAI failure during output audit")
            return OutputRouter(
                is_safe=False,
                reasoning="Auditor API error or timeout.",
                safe_content="I apologize, but I am currently unable to verify your health records securely. Please try again later or contact your clinic.",
            )
