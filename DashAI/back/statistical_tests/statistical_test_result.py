from dataclasses import dataclass


@dataclass
class StatisticalTestResult:
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    alpha: float
    details: dict
    interpretation: str
