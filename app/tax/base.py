
from typing import Dict, Any

class TaxEngine:
    def estimate(self, *, profit_before_tax: float, turnover: float | None, params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
