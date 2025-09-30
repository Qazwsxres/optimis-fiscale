
import io
import pandas as pd
from typing import Dict, Any, List, Tuple
import yaml
from .models import TrialBalanceRow, AnalysisResult, KPI, TaxEstimate, Suggestion
from .tax.france_2025 import France2025TaxEngine

def load_params(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def normalize_trial_balance(df: pd.DataFrame) -> pd.DataFrame:
    req = {"account", "debit", "credit"}
    if not req.issubset(set(df.columns)):
        raise ValueError(f"Colonnes requises manquantes: {req}")
    df = df.copy()
    df["account"] = df["account"].astype(str).str.strip()
    for col in ["debit", "credit"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["balance"] = df["debit"] - df["credit"]
    return df

def prefix_sum(df: pd.DataFrame, prefixes: List[str]) -> float:
    if not prefixes:
        return 0.0
    mask = pd.Series(False, index=df.index)
    for p in prefixes:
        mask = mask | df["account"].str.startswith(p)
    return float(df.loc[mask, "balance"].sum())

def compute_kpi(df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[KPI, Dict[str, float]]:
    pcg = params["pcg_mapping"]
    revenue = prefix_sum(df, pcg["sales_prefix"]) * -1  # sens comptable (produits au crédit)
    purchases = prefix_sum(df, pcg["purchases_prefix"])
    external = prefix_sum(df, pcg["external_charges_prefix"])
    taxes = prefix_sum(df, pcg["taxes_prefix"])
    payroll = prefix_sum(df, pcg["payroll_prefix"])
    depreciation = prefix_sum(df, pcg["depreciation_prefix"])
    fin_income = prefix_sum(df, pcg["financial_income_prefix"]) * -1
    fin_exp = prefix_sum(df, pcg["financial_expenses_prefix"])
    excep_income = prefix_sum(df, pcg["exceptional_income_prefix"]) * -1
    excep_exp = prefix_sum(df, pcg["exceptional_expenses_prefix"])

    gross_margin = revenue - purchases
    ebitda_approx = revenue - purchases - external - taxes - payroll
    net_result = ebitda_approx - depreciation + fin_income - fin_exp + excep_income - excep_exp

    cash = prefix_sum(df, pcg["cash_prefix"])
    receivables = prefix_sum(df, pcg["receivables_prefix"])
    payables = prefix_sum(df, pcg["payables_prefix"])
    working_capital_need = receivables - payables

    ebitda_margin = (ebitda_approx / revenue * 100.0) if revenue else None

    components = dict(
        revenue=revenue, purchases=purchases, external=external, taxes=taxes, payroll=payroll,
        depreciation=depreciation, fin_income=fin_income, fin_exp=fin_exp,
        excep_income=excep_income, excep_exp=excep_exp, cash=cash, receivables=receivables, payables=payables
    )

    kpi = KPI(
        revenue=round(revenue, 2),
        gross_margin=round(gross_margin, 2),
        ebitda_approx=round(ebitda_approx, 2),
        ebitda_margin_pct=round(ebitda_margin, 2) if ebitda_margin is not None else None,
        net_result=round(net_result, 2),
        working_capital_need=round(working_capital_need, 2),
        dso_days=None, dpo_days=None, cash=round(cash, 2),
    )
    return kpi, components

def compute_vat(df: pd.DataFrame, params: Dict[str, Any]) -> float | None:
    vat = params["vat"]
    collected = prefix_sum(df, vat["collected_accounts_prefix"])
    deductible = prefix_sum(df, vat["deductible_accounts_prefix"])
    if abs(collected) + abs(deductible) < 1e-6:
        return None
    # Comptablement : 44571 (collectée) est au crédit -> solde négatif dans notre convention
    # On renvoie le solde à décaisser (>0) ou crédit de TVA (<0)
    return round(-(collected) - deductible, 2)

def suggestions(kpi: KPI, tax: TaxEstimate, components: Dict[str, float]) -> List[Suggestion]:
    out: List[Suggestion] = []

    # EBITDA faible
    if kpi.ebitda_margin_pct is not None and kpi.ebitda_margin_pct < 10:
        out.append(Suggestion(
            id="EBITDA_LOW",
            title="Marge d'exploitation faible : prioriser pricing & achats",
            rationale=(
                "Votre EBITDA/CA est < 10%. Travaillez les prix (élasticité, mix) et renégociez achats (60/61/62). "
                "Vérifiez aussi la structure coûts fixes/variables."
            ),
            impact="Amélioration directe du cash-flow opérationnel."
        ))

    # BFR élevé
    if (kpi.working_capital_need or 0) > 0.1 * (kpi.revenue or 1):
        out.append(Suggestion(
            id="WCR_HIGH",
            title="BFR élevé : accélérez l’encaissement et sécurisez les délais",
            rationale=(
                "Les créances clients dépassent les dettes fournisseurs. Mettez en place acomptes, relances "
                "systématiques, pénalités de retard, escompte/factoring, et préparez la facturation électronique (e-invoicing)."
            ),
            impact="Réduction du besoin de financement court terme."
        ))

    # Eligibilité 15% IS (à confirmer)
    if tax.eligible_sme_reduced_rate is True:
        out.append(Suggestion(
            id="CIT_15_SME",
            title="Confirmez les critères pour le taux réduit d’IS à 15%",
            rationale=(
                "Si CA ≤ 10 M€, capital libéré et ≥ 75% détenu par des personnes physiques, la 1ère tranche de 42 500 € "
                "de bénéfice est imposée à 15% (reste à 25%). Assurez la conformité (cap table, libération du capital)."
            ),
            references=[
                "https://www.impots.gouv.fr/international-professionnel/tax4busines",
                "https://bofip.impots.gouv.fr/bofip/2062-PGP.html/identifiant=BOI-IS-LIQ-20-10-20210303"
            ]
        ))

    # CIR/CII détectables (très heuristiques)
    r_and_d_like = (components.get("external", 0) + components.get("payroll", 0)) > 0.4 * (kpi.revenue or 1)
    if r_and_d_like:
        out.append(Suggestion(
            id="CIR_CII_CHECK",
            title="Vérifiez l’éligibilité CIR/CII",
            rationale=(
                "Poids élevé des charges de personnel et prestations techniques : vos projets peuvent être éligibles au CIR "
                "(30% métropole dans la limite de 100 M€) ou CII (20% PME jusqu’à fin 2027, sous conditions). "
                "Sécurisez via rescrit et dossier technique."
            ),
            references=[
                "https://entreprendre.service-public.fr/vosdroits/F23533",
                "https://entreprendre.service-public.fr/vosdroits/F35494"
            ]
        ))

    # TVA : solde à payer important
    if tax.vat_balance is not None and tax.vat_balance > 0:
        out.append(Suggestion(
            id="VAT_NET_PAYABLE",
            title="TVA à décaisser élevée : optimisez le cycle de TVA",
            rationale=(
                "Révisez les taux appliqués, maximisez la déductibilité (factures fournisseurs conformes), "
                "utilisez l’auto-liquidation si éligible. Anticipez le passage à la facturation électronique (2026/2027)."
            ),
            references=[
                "https://www.economie.gouv.fr/actualites/facturation-electronique-les-entreprises-accompagnees-tout-au-long-du-deploiement"
            ]
        ))

    return out

def analyze_trial_balance(df: pd.DataFrame, *, turnover: float | None = None, params_path: str = "app/config/rates_fr_2025.yaml") -> AnalysisResult:
    params = load_params(params_path)
    df = normalize_trial_balance(df)
    kpi, components = compute_kpi(df, params)

    # Estimation IS
    tax_engine = France2025TaxEngine()
    tax_dict = tax_engine.estimate(profit_before_tax=kpi.net_result, turnover=turnover, params=params)
    # TVA
    vat_balance = compute_vat(df, params)
    tax = TaxEstimate(
        profit_before_tax=kpi.net_result,
        turnover=turnover,
        corporate_income_tax=tax_dict["corporate_income_tax"],
        social_contribution_on_cit=tax_dict["social_contribution_on_cit"],
        eligible_sme_reduced_rate=tax_dict["eligible_sme_reduced_rate"],
        vat_balance=vat_balance,
        notes=tax_dict["notes"],
        details=tax_dict["details"],
    )

    suggs = suggestions(kpi, tax, components)

    warnings = []
    if turnover is None:
        warnings.append("Le chiffre d’affaires n’a pas été fourni : l’éligibilité au taux réduit d’IS et la contribution sociale sont inférées de manière limitée.")
    return AnalysisResult(kpi=kpi, tax=tax, suggestions=suggs, warnings=warnings)
