"""Severity bands from the brief: Low <1 ha, Medium 1-5, High 5-20, Critical >20."""

SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def severity_for(area_ha: float) -> str:
    if area_ha < 1:
        return "Low"
    if area_ha < 5:
        return "Medium"
    if area_ha <= 20:
        return "High"
    return "Critical"


def default_priority(severity: str) -> int:
    """Placeholder for priority formula v1 (severity only for now).
    The weekly job will add: inside park, growth, near road, high-value zone."""
    return SEVERITY_RANK[severity]
