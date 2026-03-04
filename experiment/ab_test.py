import math
from dataclasses import dataclass


@dataclass
class ABResult:
    metric: str
    control_n: int
    control_converted: int
    treatment_n: int
    treatment_converted: int
    control_rate: float
    treatment_rate: float
    absolute_lift: float
    relative_lift: float
    z_stat: float
    p_value_2sided: float
    ci95_low: float
    ci95_high: float


def _norm_cdf(x: float) -> float:
    # Standard normal CDF via error function
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def two_proportion_ztest(
    control_converted: int,
    control_n: int,
    treatment_converted: int,
    treatment_n: int,
    metric: str = "activation_rate",
) -> ABResult:
    if control_n <= 0 or treatment_n <= 0:
        raise ValueError("Sample sizes must be > 0.")
    if not (0 <= control_converted <= control_n) or not (0 <= treatment_converted <= treatment_n):
        raise ValueError("Converted counts must be within [0, n].")

    p1 = control_converted / control_n
    p2 = treatment_converted / treatment_n

    # pooled proportion
    p_pool = (control_converted + treatment_converted) / (control_n + treatment_n)

    denom = math.sqrt(p_pool * (1 - p_pool) * (1 / control_n + 1 / treatment_n))
    z = 0.0 if denom == 0 else (p2 - p1) / denom

    # two-sided p-value
    p_val = 2.0 * (1.0 - _norm_cdf(abs(z)))

    # 95% CI for difference in proportions (unpooled SE)
    se_unpooled = math.sqrt((p1 * (1 - p1)) / control_n + (p2 * (1 - p2)) / treatment_n)
    ci_low = (p2 - p1) - 1.96 * se_unpooled
    ci_high = (p2 - p1) + 1.96 * se_unpooled

    abs_lift = p2 - p1
    rel_lift = (abs_lift / p1) if p1 > 0 else float("inf")

    return ABResult(
        metric=metric,
        control_n=control_n,
        control_converted=control_converted,
        treatment_n=treatment_n,
        treatment_converted=treatment_converted,
        control_rate=p1,
        treatment_rate=p2,
        absolute_lift=abs_lift,
        relative_lift=rel_lift,
        z_stat=z,
        p_value_2sided=p_val,
        ci95_low=ci_low,
        ci95_high=ci_high,
    )