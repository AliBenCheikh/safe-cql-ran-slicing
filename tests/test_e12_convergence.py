"""Le script de convergence E12 n'ouvre pas le test et réutilise le critère d'E2 sans le redéfinir."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src" / "checks" / "convergence_e12.py").read_text(encoding="utf-8")


def _code():
    return "\n".join(l.split("#", 1)[0] for l in SRC.split('"""', 2)[2].splitlines())


def test_never_opens_test_results_or_data():
    code = _code()
    assert not re.search(r'(/|Path\()\s*"[^"]*test_results', code)
    assert not re.search(r"read_parquet|read_csv|/ \"data\"", code)


def test_reuses_e2_criterion():
    assert "from src.e2_safe_cql_diagnostic import" in SRC and "convergence" in SRC
    assert "def convergence" not in SRC


def test_synthetic_runs():
    from src.e2_safe_cql_diagnostic import convergence
    ok = convergence([0.5] * 20, [0.028] * 20)
    assert ok["converged"]
    ramp = convergence([0.1 + 0.01 * i for i in range(20)], [0.028] * 20)
    assert not ramp["converged"] and not ramp["c1_lambda_spread"]
    assert not convergence([0.5] * 19, [0.028] * 19)["converged"]
