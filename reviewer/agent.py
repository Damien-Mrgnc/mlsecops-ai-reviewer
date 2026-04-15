"""
Agent IA de Code Review.

Mode 1 (dev) : appelle Gemini directement via GEMINI_API_KEY
Mode 2 (prod) : appelle l'API MLSecOps (Projet 1) via MLSECOPS_API_URL
Le mode est sélectionné automatiquement selon les variables d'env présentes.
"""
import json
import os
import sys
import textwrap

import requests
from dotenv import load_dotenv

GEMINI_REST_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

load_dotenv()

from github_client import get_pr_diff, post_review_with_decision

# ---- Config ----
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")
MLSECOPS_API_URL = os.getenv("MLSECOPS_API_URL")   # optionnel — Projet 1
MLSECOPS_API_KEY = os.getenv("MLSECOPS_API_KEY")
GITHUB_REPO      = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER        = int(os.environ["PR_NUMBER"])
MAX_DIFF_CHARS   = 8000


def load_reporules() -> str:
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    rules_path = os.path.join(workspace, ".reporules")
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Applique les bonnes pratiques générales de sécurité et de qualité de code."


def truncate_diff(diff: str, max_chars: int) -> str:
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars] + "\n\n[... diff tronqué ...]"


def build_prompt(rules: str, diff: str) -> str:
    return textwrap.dedent(f"""
        Tu es un expert en sécurité et qualité logicielle effectuant une code review.

        Règles de l'équipe à appliquer STRICTEMENT :
        {rules}

        ---
        Diff de la Pull Request :
        {diff}

        ---
        Analyse ce code et retourne UNIQUEMENT un JSON valide avec cette structure exacte :
        {{
            "decision": "APPROVE" ou "REQUEST_CHANGES",
            "summary": "résumé en 2-3 phrases",
            "critical_issues": [
                {{
                    "file": "fichier.py",
                    "line_hint": "ligne ou description",
                    "description": "problème critique",
                    "fix": "correction suggérée"
                }}
            ],
            "warnings": [
                {{
                    "file": "fichier.py",
                    "description": "avertissement qualité",
                    "fix": "suggestion"
                }}
            ]
        }}

        RÈGLES :
        - decision = "REQUEST_CHANGES" si au moins un problème critique
        - decision = "APPROVE" si aucun problème critique
        - Réponds UNIQUEMENT avec le JSON, sans markdown, sans texte autour
    """).strip()


def call_gemini(prompt: str) -> str:
    """Appelle Gemini 2.0 Flash via REST API avec retry sur 429."""
    import time

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    for attempt in range(4):
        response = requests.post(
            GEMINI_REST_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=60,
        )
        if response.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"[AGENT] Rate limit 429, attente {wait}s (tentative {attempt + 1}/4)...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    response.raise_for_status()  # lève l'erreur après 4 tentatives


def call_mlsecops_api(prompt: str) -> str:
    """Appelle l'API MLSecOps (Projet 1)."""
    response = requests.post(
        f"{MLSECOPS_API_URL}/v1/chat",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": MLSECOPS_API_KEY,
        },
        json={"message": prompt, "max_tokens": 2000},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["response"]


def get_llm_response(prompt: str) -> str:
    """Sélectionne automatiquement le bon backend LLM."""
    if MLSECOPS_API_URL:
        print(f"[AGENT] Mode PROD — API MLSecOps : {MLSECOPS_API_URL}")
        return call_mlsecops_api(prompt)
    print("[AGENT] Mode DEV — Gemini 1.5 Flash")
    return call_gemini(prompt)


def format_review_comment(data: dict) -> str:
    lines = ["## 🤖 Review IA — MLSecOps Agent\n"]
    emoji = "✅" if data["decision"] == "APPROVE" else "❌"
    lines.append(f"**Décision : {emoji} {data['decision']}**\n")
    lines.append(f"{data['summary']}\n")

    if data.get("critical_issues"):
        lines.append("\n### Problèmes Critiques (bloquants)\n")
        for issue in data["critical_issues"]:
            lines.append(f"**`{issue['file']}`** — {issue.get('line_hint', '')}")
            lines.append(f"> {issue['description']}")
            lines.append(f"**Correction :** {issue['fix']}\n")

    if data.get("warnings"):
        lines.append("\n### Avertissements\n")
        for warn in data["warnings"]:
            lines.append(f"**`{warn['file']}`**")
            lines.append(f"> {warn['description']}")
            lines.append(f"**Suggestion :** {warn['fix']}\n")

    lines.append("\n---")
    lines.append("*Propulsé par [mlsecops-ai-reviewer](https://github.com/Damien-Mrgnc/mlsecops-ai-reviewer)*")
    return "\n".join(lines)


def main():
    print(f"[AGENT] PR #{PR_NUMBER} sur {GITHUB_REPO}")

    rules = load_reporules()
    print(f"[AGENT] .reporules chargé ({len(rules)} chars)")

    diff_files = get_pr_diff(GITHUB_REPO, PR_NUMBER)
    if not diff_files:
        print("[AGENT] Aucun fichier modifié, skip.")
        return

    diff_parts = []
    for filename, info in diff_files.items():
        diff_parts.append(
            f"### {filename} ({info['status']})\n```diff\n{info['patch']}\n```"
        )
    diff_summary = truncate_diff("\n\n".join(diff_parts), MAX_DIFF_CHARS)
    print(f"[AGENT] Diff : {len(diff_summary)} chars, {len(diff_files)} fichier(s)")

    prompt = build_prompt(rules, diff_summary)

    print("[AGENT] Appel LLM...")
    raw = get_llm_response(prompt)
    print(f"[AGENT] Réponse reçue ({len(raw)} chars)")

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        review_data = json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[AGENT ERROR] JSON invalide : {e}\nRaw: {raw}")
        sys.exit(1)

    comment_body = format_review_comment(review_data)
    approve = review_data["decision"] == "APPROVE"

    post_review_with_decision(
        repo_name=GITHUB_REPO,
        pr_number=PR_NUMBER,
        body=comment_body,
        approve=approve,
    )

    print(f"[AGENT] Review postée — {review_data['decision']}")

    if not approve:
        print("[AGENT] Problèmes critiques → exit 1 (PR bloquée)")
        sys.exit(1)


if __name__ == "__main__":
    main()
