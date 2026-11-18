"""Local lexical retrieval with stable citations and extractive answers.

Demo documents are synthetic, not manufacturer instructions. Retrieved text is
untrusted evidence; it is never executed or used as a tool instruction.
"""
from dataclasses import asdict, dataclass
import math
import re
from collections import Counter


@dataclass(frozen=True)
class Passage:
    source_id: str
    section: str
    text: str


DEMO_DOCUMENTS = (
    Passage("synthetic-pump-manual", "bearing-inspection",
            "Bearing wear can cause elevated vibration and temperature under normal load. "
            "Check lubrication condition and inspect bearings. Similar symptoms can arise from misalignment."),
    Passage("synthetic-pump-manual", "cavitation",
            "Cavitation can cause vibration and unstable discharge pressure. Check suction pressure, "
            "inlet restrictions and available suction head before concluding bearing damage."),
    Passage("synthetic-maintenance-log", "pump-01-previous-service",
            "Pump pump-01: prior inspection recorded bearing lubrication deterioration. "
            "This historical observation does not confirm the cause of a new vibration or temperature event."),
    Passage("synthetic-pump-manual", "operating-envelope",
            "High speed, load and ambient temperature affect pump temperature and vibration. "
            "Check operating conditions before attributing a deviation to equipment damage."),
)


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class Retriever:
    def __init__(self, passages=DEMO_DOCUMENTS):
        self.passages = tuple(passages)
        if len({(p.source_id, p.section) for p in self.passages}) != len(self.passages):
            raise ValueError("Passage citations must be unique")
        self.counts = [Counter(tokens(p.text)) for p in self.passages]

    def search(self, query: str, limit: int = 3) -> list[dict]:
        if not 1 <= limit <= 10:
            raise ValueError("limit must be between 1 and 10")
        query_tokens = set(tokens(query))
        total = len(self.passages)
        average = sum(sum(c.values()) for c in self.counts) / max(total, 1)
        matches = []
        for passage, counts in zip(self.passages, self.counts):
            score = 0.0
            for token in query_tokens:
                frequency = counts[token]
                document_frequency = sum(token in c for c in self.counts)
                idf = math.log(1 + (total - document_frequency + 0.5) / (document_frequency + 0.5))
                if frequency:
                    score += idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * sum(counts.values()) / max(average, 1)))
            if score > 0:
                matches.append({**asdict(passage), "score": score,
                                "citation": f"{passage.source_id}#{passage.section}"})
        return sorted(matches, key=lambda m: (-m["score"], m["citation"]))[:limit]
