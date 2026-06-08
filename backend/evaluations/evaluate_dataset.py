import os
import json
import sys
import requests

from datasets import Dataset
from dotenv import load_dotenv

from ragas import evaluate

from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from langfuse import get_client, observe
from langfuse.langchain import CallbackHandler

load_dotenv(override=True)

langfuse = get_client()
langfuse_handler = CallbackHandler()

API_BASE_URL = "http://127.0.0.1:8000"

TEST_USER_EMAIL = "pat1@gmial.com"
TEST_USER_PASSWORD = "123456"

# TEST_USER_EMAIL = "f1@hos.com"
# TEST_USER_PASSWORD = "123456"


def get_auth_token():
    response = requests.post(
        f"{API_BASE_URL}/auth/token",
        data={
            "username": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def load_dataset(dataset_name: str):
    dataset_path = f"evaluations/datasets/{dataset_name}.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ask_question(token: str, question: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": question,
        "history": [],
    }
    response = requests.post(
        f"{API_BASE_URL}/chat",
        headers=headers,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


@observe(name="ragas_evaluation", as_type="span")
def main():
    # Parse arguments
    if len(sys.argv) != 2:
        print(
            "\nUsage:"
            "\npython evaluations/evaluate_dataset.py general_health_gold"
            "\npython evaluations/evaluate_dataset.py finance_documents_gold"
            "\npython evaluations/evaluate_dataset.py guardrails_gold\n"
        )
        return

    dataset_name = sys.argv[1]

    # Load data
    print(f"Loading dataset: {dataset_name}")
    samples = load_dataset(dataset_name)
    token = get_auth_token()

    questions = []
    answers = []
    contexts = []
    ground_truths = []
    total = len(samples)

    print(f"\nRunning {total} evaluation questions...\n")

    # Start the Langfuse trace that covers EVERYTHING
    with langfuse.start_as_current_observation(
        as_type="span", name=f"evaluation_{dataset_name}"
    ) as eval_span:
        eval_span.update(
            input={
                "dataset": dataset_name,
                "num_questions": total,
                "test_user": TEST_USER_EMAIL,
            }
        )

        # Run all questions INSIDE the trace
        for idx, sample in enumerate(samples, start=1):
            question = sample["question"]
            print(f"[{idx}/{total}] {question[:80]}")

            try:
                result = ask_question(token=token, question=question)
                answer = result.get("final_answer", "")
                retrieved_contexts = [
                    source.get("raw_content", "")
                    for source in result.get("sources", [])
                ]
            except Exception as e:
                print(f"FAILED: {e}")
                answer = "ERROR"
                retrieved_contexts = []

            questions.append(question)
            answers.append(answer)
            contexts.append(retrieved_contexts)
            ground_truths.append(sample["ground_truth"])

        # Build dataset
        ragas_dataset = Dataset.from_dict(
            {
                "question": questions,
                "answer": answers,
                "contexts": contexts,
                "ground_truth": ground_truths,
            }
        )

        print("\nBooting RAGAS Evaluator...")

        evaluator_llm = LangchainLLMWrapper(
            ChatOpenAI(
                model="gpt-4o",
                base_url="https://us.api.openai.com/v1",
                temperature=0,
            )
        )

        evaluator_embeddings = LangchainEmbeddingsWrapper(
            OpenAIEmbeddings(
                model="text-embedding-3-small",
                base_url="https://us.api.openai.com/v1",
            )
        )

        print("\nRunning Evaluation...")

        result = evaluate(
            dataset=ragas_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )

        print("\n=== RESULTS ===")
        print(result)

        
        # Calculate mean of each list
        scores = {
            "faithfulness": sum(result["faithfulness"]) / len(result["faithfulness"]),
            "answer_relevancy": sum(result["answer_relevancy"]) / len(result["answer_relevancy"]),
            "context_precision": sum(result["context_precision"]) / len(result["context_precision"]),
            "context_recall": sum(result["context_recall"]) / len(result["context_recall"]),
        }

        for metric_name, metric_value in scores.items():
            langfuse.create_score(
                name=metric_name, value=float(metric_value), trace_id=eval_span.trace_id
            )

        eval_span.update(output=scores)

        # Save results to CSV
        os.makedirs("evaluations/results", exist_ok=True)
        result_df = result.to_pandas()
        output_path = f"evaluations/results/{dataset_name}_results.csv"
        result_df.to_csv(output_path, index=False)
        print(f"\nDetailed results saved to:\n{output_path}")

    # Flush after the with block
    langfuse.flush()


if __name__ == "__main__":
    main()
