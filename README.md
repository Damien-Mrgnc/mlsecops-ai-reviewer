# mlsecops-ai-reviewer

Agent IA de code review automatique — analyse chaque Pull Request, détecte les vulnérabilités de sécurité et les violations de qualité, et bloque les merges non conformes via GitHub Actions.

Conçu comme le second projet du système MLSecOps : l'agent peut fonctionner en mode autonome (Gemini) ou être routé via l'[infrastructure MLSecOps](https://github.com/Damien-Mrgnc/aws-mlsecops-infrastructure) en production.

---

## Fonctionnement

```
Pull Request ouverte
       │
       ▼
[GitHub Actions]
       │
       ▼
[Agent Python]
  1. Lit .reporules du repo cible
  2. Récupère le diff de la PR (GitHub API)
  3. Construit le prompt (règles + diff)
  4. Appelle le LLM
       │
       ├── Mode DEV  → Gemini 2.5 Flash (GEMINI_API_KEY)
       └── Mode PROD → API MLSecOps (MLSECOPS_API_URL + MLSECOPS_API_KEY)
       │
       ▼
  5. Parse la réponse JSON
  6. Poste un commentaire structuré sur la PR
  7. APPROVE ou REQUEST_CHANGES (exit 1 → merge bloqué)
```

---

## Exemple de review

> PR `feat/add-ip-rate-limiting` sur `aws-mlsecops-infrastructure`

```
## 🤖 Review IA — MLSecOps Agent

Décision : ❌ REQUEST_CHANGES

Le diff introduit un rate limiting basé sur l'IP source, ce qui est
explicitement interdit par les règles du projet (.reporules).

### Problèmes Critiques (bloquants)

`go-proxy/main.go` — ligne 45
> Rate limiting par IP : violation de la règle de sécurité définie
  dans .reporules (IP spoofing trivial, contournement facile).
Correction : Utiliser un rate limiting par clé API (déjà en place).
```

---

## Structure

```
mlsecops-ai-reviewer/
├── reviewer/
│   ├── agent.py          # Agent principal — prompt, LLM call, parsing
│   ├── github_client.py  # Récupération diff + post review via API GitHub
│   └── requirements.txt  # requests, python-dotenv
├── .github/workflows/
│   └── ai-review.yml     # Déclenchement sur chaque PR
├── .reporules            # Règles de review de ce repo (utilisées sur les PRs internes)
├── example_bad_code.py   # Exemple de code avec vulnérabilités (demo)
└── example_good_code.py  # Même code corrigé (demo)
```

---

## Intégrer l'agent dans un repo

**1. Copier le workflow**

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize, reopened]
permissions:
  contents: read
  pull-requests: write
jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with:
          repository: Damien-Mrgnc/mlsecops-ai-reviewer
          path: ai-reviewer
      - run: pip install -r ai-reviewer/reviewer/requirements.txt
      - run: python ai-reviewer/reviewer/agent.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
```

**2. Ajouter un `.reporules` à la racine du repo**

```markdown
# Règles de review

## Sécurité (CRITIQUE — REQUEST_CHANGES obligatoire)
- INTERDICTION de hardcoder des secrets ou clés API.
- INTERDICTION de désactiver la validation SSL (verify=False).
- Les requêtes SQL DOIVENT utiliser des paramètres préparés.

## Qualité (AVERTISSEMENT)
- Les exceptions DOIVENT être catchées spécifiquement.
```

**3. Configurer les secrets GitHub**

| Secret | Description |
|---|---|
| `GEMINI_API_KEY` | Clé API Google Gemini (mode dev) |
| `MLSECOPS_API_URL` | URL de l'API MLSecOps (mode prod, optionnel) |
| `MLSECOPS_API_KEY` | Clé API MLSecOps (mode prod, optionnel) |

---

## Stack

| Composant | Techno |
|---|---|
| LLM (dev) | Gemini 2.5 Flash (Google AI) |
| LLM (prod) | API MLSecOps → GPT-4o-mini via infra sécurisée |
| Runtime | Python 3.11, GitHub Actions |
| Intégration | GitHub API (diff + PR review) |

---

## Repos utilisant cet agent

- [aws-mlsecops-infrastructure](https://github.com/Damien-Mrgnc/aws-mlsecops-infrastructure) — infrastructure MLSecOps principale
- [mlsecops-test-target](https://github.com/Damien-Mrgnc/mlsecops-test-target) — repo de démonstration
