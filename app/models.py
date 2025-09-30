
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TrialBalanceRow(BaseModel):
    account: str
    label: Optional[str] = None
    debit: float = 0.0
    credit: float = 0.0

class Suggestion(BaseModel):
    id: str
    title: str
    rationale: str
    impact: Optional[str] = None
    references: Optional[List[str]] = None

class TaxEstimate(BaseModel):
    country: str = "FR"
    year: int = 2025
    profit_before_tax: float
    eligible_sme_reduced_rate: Optional[bool] = None
    turnover: Optional[float] = None
    corporate_income_tax: float = 0.0
    social_contribution_on_cit: float = 0.0
    vat_balance: Optional[float] = None
    notes: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

class KPI(BaseModel):
    revenue: float
    gross_margin: float
    ebitda_approx: float
    ebitda_margin_pct: Optional[float] = None
    net_result: float
    working_capital_need: Optional[float] = None
    dso_days: Optional[float] = None
    dpo_days: Optional[float] = None
    cash: Optional[float] = None

class AnalysisResult(BaseModel):
    kpi: KPI
    tax: TaxEstimate
    suggestions: List[Suggestion] = []
    warnings: List[str] = []
