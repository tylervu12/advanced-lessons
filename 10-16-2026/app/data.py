"""Synthetic historical applications and a separate repayment simulator."""
import numpy as np

FEATURES = ["income", "credit_score", "debt_ratio", "loan_amount", "employment_years"]
SCENARIOS = {"baseline", "input_shift", "concept_shift"}


def applications(count: int, seed: int, scenario: str = "baseline") -> list[dict]:
    rng = np.random.default_rng(seed)
    income = np.clip(rng.lognormal(11.05, .43, count), 18000, 220000)
    credit = np.clip(rng.normal(685, 55, count), 420, 840)
    debt = np.clip(rng.beta(3, 7, count), .02, .85)
    amount = np.clip(rng.lognormal(9.65, .48, count), 2000, 65000)
    employment = np.clip(rng.gamma(2, 3, count), 0, 30)
    if scenario == "input_shift":
        # Change P(X), keeping the repayment mechanism P(Y|X) unchanged.
        income = np.maximum(income * .78, 15000)
        credit = np.maximum(credit - 48, 350)
        debt = np.minimum(debt + .16, .95)
    return [dict(income=round(float(income[i]), 2), credit_score=int(credit[i]),
                 debt_ratio=round(float(debt[i]), 4), loan_amount=round(float(amount[i]), 2),
                 employment_years=round(float(employment[i]), 1)) for i in range(count)]


def matrix(records):
    return np.array([[r[f] for f in FEATURES] for r in records], dtype=float)


def repayments(records: list[dict], seed: int, scenario: str = "baseline") -> list[str]:
    rng = np.random.default_rng(seed)
    x = matrix(records)
    # These hidden probabilities belong to the simulator, never the predictor.
    log_odds = (-2.25 + (680 - x[:, 1]) / 65 + 4 * (x[:, 2] - .3)
                + .8 * (x[:, 3] / x[:, 0] - .25) - .035 * (x[:, 4] - 5))
    if scenario == "concept_shift":
        # Same applicants, changed repayment behavior: P(Y|X) changes.
        log_odds += 1.4 + .7 * (x[:, 4] < 3)
    default_p = 1 / (1 + np.exp(-log_odds))
    late_p = np.clip(.09 + .25 * x[:, 2] + (.12 if scenario == "concept_shift" else 0), 0, .8)
    default_draw, late_draw = rng.random(len(records)), rng.random(len(records))
    return ["defaulted" if default_draw[i] < default_p[i] else
            "late" if late_draw[i] < late_p[i] else "on_time" for i in range(len(records))]
