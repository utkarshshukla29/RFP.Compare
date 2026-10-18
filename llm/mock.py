import json
import re


class MockLLMClient:
    """Deterministic demo client; produces illustrative scores and quotes only source text."""

    def complete_json(self, system: str, user: str) -> str:
        criteria_block = user.split("ACTIVE CRITERIA:\n", 1)[-1].split("\n\nSUPPLIER NAME:", 1)[0]
        supplier_name = user.split("SUPPLIER NAME:\n", 1)[-1].split("\n\nSUPPLIER DOCUMENT", 1)[0].strip()
        document = user.split("SUPPLIER DOCUMENT TEXT:\n", 1)[-1]
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", document) if part.strip()]
        criteria = []
        for line in criteria_block.splitlines():
            match = re.match(r"Criterion (\d+): (.*?) \| max_score ([\d.]+) \| inspect: (.*)", line)
            if not match:
                continue
            criterion_id, name, maximum, description = match.groups()
            keywords = {word.casefold() for word in re.findall(r"[a-zA-Z]{5,}", f"{name} {description}")}
            evidence_sentence = next((sentence for sentence in sentences
                                      if any(keyword in sentence.casefold() for keyword in keywords)), None)
            score = float(maximum) * 0.65 if evidence_sentence else 0
            criteria.append({
                "criterion_id": int(criterion_id),
                "score": score,
                "max_score": float(maximum),
                "justification": "Demo-mode illustrative assessment; replace with a real provider for evaluation.",
                "evidence": evidence_sentence or "No matching supporting text found in the uploaded document.",
            })
        return json.dumps({
            "supplier_name": supplier_name,
            "criteria": criteria,
            "risks": ["Scores are illustrative mock output and are not a procurement recommendation."],
            "overall_summary": "Demo mode generated illustrative scores using document text matches.",
        })
