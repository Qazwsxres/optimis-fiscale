
from .base import TaxEngine
from typing import Dict, Any

class France2025TaxEngine(TaxEngine):
    def estimate(self, *, profit_before_tax: float, turnover: float | None, params: Dict[str, Any]) -> Dict[str, Any]:
        p = params["cit"]
        profit = max(0.0, profit_before_tax)  # IS uniquement si bénéfice > 0 (simplifié)

        # Hypothèses par défaut (à affiner côté front/paramétrage)
        eligible = None
        if turnover is not None:
            eligible = turnover <= p.get("sme_turnover_ceiling", 10_000_000)
        # Montant à 15% si éligible (hypothèse prudente : conditions de détention du capital à vérifier côté utilisateur)
        reduced_cap = p.get("sme_reduced_threshold", 42_500)
        standard_rate = p.get("standard_rate", 0.25)
        reduced_rate = p.get("sme_reduced_rate", 0.15)

        reduced_base = min(profit, reduced_cap) if (eligible is True) else 0.0
        standard_base = profit - reduced_base
        cit = reduced_base * reduced_rate + standard_base * standard_rate

        # Contribution sociale de 3,3% si CA > 7,63 M€ et IS > abattement (simplifié)
        sc_rate = p.get("social_contribution_rate", 0.033)
        sc_turnover_thr = p.get("social_contribution_turnover_threshold", 7_630_000)
        sc_allowance = p.get("social_contribution_allowance", 763_000)
        sc = 0.0
        if turnover is not None and turnover > sc_turnover_thr and cit > sc_allowance:
            sc = sc_rate * (cit - sc_allowance)

        return {
            "eligible_sme_reduced_rate": eligible,
            "corporate_income_tax": round(cit, 2),
            "social_contribution_on_cit": round(sc, 2),
            "notes": "Calcul pédagogique simplifié, à valider avec un expert-comptable.",
            "details": {
                "reduced_base": reduced_base,
                "standard_base": standard_base,
                "standard_rate": standard_rate,
                "reduced_rate": reduced_rate,
                "sc_rate": sc_rate,
            }
        }
