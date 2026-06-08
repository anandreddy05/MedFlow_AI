from enum import Enum
import re


class RetrieverIntent(Enum):
    CURRENT_CONTEXT = "CurrentContextRetriever"
    HISTORICAL = "HistoricalRetriever"


class IntentRouter:
    """
    Determines which retrieval strategy should be used.

    ```
    CURRENT_CONTEXT:
        Latest report
        Latest prescription
        Current medications
        Latest nurse notes

    HISTORICAL:
        Full RAG search over historical records.
    """

    def __init__(self):

        self.current_patterns = [
            r"\blatest\b",
            r"\bcurrent\b",
            r"\brecent\b",
            r"\btoday\b",
            r"\bstatus\b",
            r"\bsummary\b",
            r"\bmedications\b",
            r"\breports\b",
            r"\bprescription\b",
            r"\bcurrent medications\b",
            r"\blatest report\b",
            r"\blatest prescription\b",
        ]

        self.historical_patterns = [
            r"\bacross all\b",
            r"\ball reports\b",
            r"\ball values\b",
            r"\bover time\b",
            r"\btrend\b",
            r"\btrends\b",
            r"\bcompare\b",
            r"\bhistory\b",
            r"\bpast\b",
            r"\bprevious\b",
            r"\bearlier\b",
            r"\bchanges\b",
            r"\bprogression\b",
            r"\bago\b",
        ]

    def route_query(self, query: str) -> RetrieverIntent:

        query = query.lower().strip()

        for pattern in self.historical_patterns:
            if re.search(pattern, query):
                return RetrieverIntent.HISTORICAL

        for pattern in self.current_patterns:
            if re.search(pattern, query):
                return RetrieverIntent.CURRENT_CONTEXT

        # Safe default:
        # Physicians usually care about current state
        return RetrieverIntent.CURRENT_CONTEXT
