"""
Manager Capacity Model & ROI Engine for ZeroTouch Workforce
Implements the Page 5 capacity model formula:
Gross Capacity Freed = Team Size * Repetitive % * Skill Coverage % * Time Saved %
Net Capacity Freed = Gross * (1 - Oversight %)
"""

from typing import Dict, Any


def compute_capacity_model(
    team_size: int = 10,
    repetitive_pct: float = 0.40,
    skill_coverage_pct: float = 0.60,
    handling_time_saved_pct: float = 0.80,
    oversight_effort_pct: float = 0.20,
    avg_annual_cost_per_employee_inr: float = 850000.0,
) -> Dict[str, Any]:
    """
    Computes capacity freed and cost redeployment metrics based on official formula.
    """
    base_fte = float(team_size)
    repetitive_fte = base_fte * repetitive_pct
    covered_fte = repetitive_fte * skill_coverage_pct
    gross_freed_fte = round(covered_fte * handling_time_saved_pct, 2)
    net_freed_fte = round(gross_freed_fte * (1.0 - oversight_effort_pct), 2)

    annual_value_inr = round(net_freed_fte * avg_annual_cost_per_employee_inr, 0)
    hours_saved_per_month = round(net_freed_fte * 160, 0)

    return {
        "team_size": team_size,
        "repetitive_pct": repetitive_pct,
        "repetitive_fte": round(repetitive_fte, 1),
        "skill_coverage_pct": skill_coverage_pct,
        "handling_time_saved_pct": handling_time_saved_pct,
        "oversight_effort_pct": oversight_effort_pct,
        "gross_freed_fte": gross_freed_fte,
        "net_freed_fte": net_freed_fte,
        "equivalent_colleagues": round(net_freed_fte, 1),
        "annual_value_inr": annual_value_inr,
        "hours_saved_per_month": hours_saved_per_month,
        "day_30_value": "Preparation and drafting time saved across 100% of cases",
        "day_100_value": f"Equivalent of {net_freed_fte} full-time colleagues freed for complex escalations",
        "formula_display": f"{repetitive_fte:.1f} FTE repetitive * {skill_coverage_pct*100:.0f}% covered * {handling_time_saved_pct*100:.0f}% saved = {gross_freed_fte} FTE gross - 20% oversight = {net_freed_fte} FTE net",
    }
