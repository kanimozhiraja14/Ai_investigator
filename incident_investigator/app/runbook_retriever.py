"""
Runbook retrieval engine with BM25 / TF-IDF scoring and metadata filtering.
"""

import os
import re
import math
from typing import List, Dict, Any, Optional
from collections import Counter
from pathlib import Path
from .models import Runbook

RUNBOOKS_DIR = Path(__file__).parent / "runbooks"


class RunbookRetriever:
    def __init__(self, runbooks_dir: Optional[Path] = None):
        self.runbooks_dir = runbooks_dir or RUNBOOKS_DIR
        self.runbooks: Dict[str, Runbook] = {}
        self.doc_tokens: Dict[str, List[str]] = {}
        self.doc_freq: Dict[str, int] = Counter()
        self.avg_doc_len: float = 0.0
        self._load_runbooks()

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"[a-zA-Z0-9_\-\.]+", text.lower())
        # Filter tiny words
        return [w for w in words if len(w) > 2]

    def _load_runbooks(self):
        if not self.runbooks_dir.exists():
            return

        total_length = 0
        for md_file in self.runbooks_dir.glob("*.md"):
            runbook_id = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            
            # Parse title
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else runbook_id.replace("_", " ").title()

            # Parse service
            service_match = re.search(r"\*\*Service:\*\*\s*([a-zA-Z0-9_\-]+)", content)
            service = service_match.group(1).strip() if service_match else "unknown"

            # Parse symptoms
            symptoms = []
            symptoms_section = re.search(r"## Symptoms(.*?)(?=##|$)", content, re.DOTALL)
            if symptoms_section:
                symptoms = [line.strip("- *").strip() for line in symptoms_section.group(1).strip().split("\n") if line.strip()]

            # Parse diagnostic steps
            diagnostic_steps = []
            diag_section = re.search(r"## Diagnostic Steps(.*?)(?=##|$)", content, re.DOTALL)
            if diag_section:
                diagnostic_steps = [re.sub(r"^\d+\.\s*", "", line).strip() for line in diag_section.group(1).strip().split("\n") if line.strip()]

            # Parse mitigation steps
            mitigation_steps = []
            mit_section = re.search(r"## Mitigation(.*?)(?=##|$)", content, re.DOTALL)
            if mit_section:
                mitigation_steps = [re.sub(r"^\d+\.\s*", "", line).strip() for line in mit_section.group(1).strip().split("\n") if line.strip()]

            runbook = Runbook(
                id=runbook_id,
                title=title,
                service=service,
                description=f"Runbook for {service} incidents regarding {title}",
                symptoms=symptoms,
                diagnostic_steps=diagnostic_steps,
                mitigation_steps=mitigation_steps,
                raw_markdown=content
            )
            self.runbooks[runbook_id] = runbook

            # Indexing tokens for BM25
            tokens = self._tokenize(content)
            self.doc_tokens[runbook_id] = tokens
            total_length += len(tokens)
            
            unique_terms = set(tokens)
            for term in unique_terms:
                self.doc_freq[term] += 1

        doc_count = len(self.runbooks)
        self.avg_doc_len = (total_length / doc_count) if doc_count > 0 else 1.0

    def search(self, query: str, service: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Rank runbooks using BM25 scoring over query terms with service boosting.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        doc_count = len(self.runbooks)
        k1 = 1.5
        b = 0.75

        scores = {}
        for r_id, runbook in self.runbooks.items():
            # Service matching boost
            service_boost = 1.0
            if service and runbook.service.lower() == service.lower():
                service_boost = 2.5

            tokens = self.doc_tokens[r_id]
            doc_len = len(tokens)
            term_counts = Counter(tokens)
            score = 0.0

            for q_term in query_tokens:
                if q_term in term_counts:
                    freq = term_counts[q_term]
                    df = self.doc_freq.get(q_term, 1)
                    idf = math.log((doc_count - df + 0.5) / (df + 0.5) + 1.0)
                    tf = (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * (doc_len / self.avg_doc_len)))
                    score += idf * tf

            score *= service_boost
            if score > 0:
                scores[r_id] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for r_id, score in ranked:
            rb = self.runbooks[r_id]
            results.append({
                "runbook_id": r_id,
                "title": rb.title,
                "service": rb.service,
                "score": round(score, 3),
                "symptoms": rb.symptoms,
                "diagnostic_steps": rb.diagnostic_steps,
                "mitigation_steps": rb.mitigation_steps,
                "raw_excerpt": rb.raw_markdown[:400] + "..."
            })
        return results

    def get_runbook(self, runbook_id: str) -> Optional[Runbook]:
        return self.runbooks.get(runbook_id)


# Singleton instance
retriever = RunbookRetriever()
