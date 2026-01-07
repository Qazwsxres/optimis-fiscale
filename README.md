# Optimis Fiscale — MVP (backend FastAPI)

Un prototype minimal d'API qui : 
- ingère une **balance (grand livre/Trial Balance) en CSV** (PCG FR approximatif),
- calcule des **indicateurs de performance** (marge, EBITDA approximatif, ratios),
- estime un **IS simplifié (France 2025)** + **contribution sociale de 3,3%** le cas échéant,
- détecte TVA collectée/déductible (si les comptes 445* sont fournis),
- génère une **liste de pistes d’optimisation conformes** (explicables).


## Lancer l'API

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Puis ouvrez `http://127.0.0.1:8000/docs` (Swagger) pour tester.

## Endpoints clés

- `POST /analyze/trial-balance` (multipart/form-data avec un fichier CSV)
- `POST /analyze/json` (JSON structuré)
- `GET /health`

## Format CSV attendu (exemple : `sample/sample_trial_balance.csv`)

Colonnes : 
- `account` (code du compte, ex. 701, 6061, 44571, 512…), 
- `label` (libellé), 
- `debit`, 
- `credit`.

Les soldes sont reconstruits (débit - crédit).

## Paramétrage des taux France 2025

Voir `app/config/rates_fr_2025.yaml`. Modifiez ces valeurs pour vos tests/marchés.
