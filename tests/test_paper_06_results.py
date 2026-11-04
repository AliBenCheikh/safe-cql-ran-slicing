"""Section 06 du papier : identifiants `% REG:` existants, phrases sourcées, affirmations interdites absentes,
tableaux recopiés de docs/e12_rapport_final.md, script de figure en lecture seule sur l'entraînement."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "sections" / "06_results.tex"
REGISTRE = ROOT / "docs" / "registre_affirmations.md"
RAPPORT = ROOT / "docs" / "e12_rapport_final.md"
FIG = ROOT / "src" / "figures" / "courbes_apprentissage.py"


def _registry_ids():
    txt = REGISTRE.read_text(encoding="utf-8")
    ids = set(re.findall(r"^\|\s*([A-Za-z0-9-]+)\s*\|", txt, flags=re.M))
    return ids | set(re.findall(r"id\s*:\s*(NO-[a-z]+)", txt))


def _prose():
    return "\n".join(l.split("%", 1)[0] for l in TEX.read_text(encoding="utf-8").splitlines())


def test_every_reg_id_exists_in_registry():
    known = _registry_ids()
    ids = []
    for line in TEX.read_text(encoding="utf-8").splitlines():
        if "% REG:" in line and not line.lstrip().startswith("%"):
            ids += [t.strip() for t in line.split("% REG:", 1)[1].split(";", 1)[0].split(",") if t.strip()]
    assert ids and not sorted({i for i in ids if i not in known})


def test_sentences_carry_reg_comment():
    bad = []
    for n, line in enumerate(TEX.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("%"):
            continue
        body = line.split("%", 1)[0].rstrip()
        if re.search(r"[A-Za-z0-9)}]\.$", body) and "% REG:" not in line and "% STRUCT" not in line:
            bad.append(n)
    assert not bad, bad


def test_no_forbidden_claims():
    prose = _prose()
    for pat in (r"[Aa]daptive", r"guarantees? safe", r"12\.9", r"outperform", r"validated in Near", r"proves? safe",
                r"converges? to the budget", r"\bBC\b", r"significantly"):
        assert not re.search(pat, prose), pat
    assert "TODO" not in prose or "\\cite{TODO-" in prose


def test_main_table_rows_copied_from_report():
    """Chaque ligne de la table principale reprend (reward, coût DM, IC) de la ligne c40f2fe7 du rapport gelé."""
    rapport = RAPPORT.read_text(encoding="utf-8")
    tex = TEX.read_text(encoding="utf-8")
    sec = tex.split("\\label{tab:e12_main}")[1].split("\\end{table*}")[0]
    rows = 0
    for m in re.finditer(r"^(.+?) & ([\d.]+) & ([\d.]+) \[([\d.]+), ([\d.]+)\] & ([\d.]+) & ([\d.]+)\\% & ([\d.]+) & no \\\\", sec, flags=re.M):
        _, rew, cost, lo, hi, mat, cov = m.groups()[:7]
        pat = rf"c40f2fe7\s+\S+\s+{rew} {cost} \[{lo},{hi}\] {mat} cov {cov}%"
        assert re.search(pat, rapport), m.group(0)
        rows += 1
    assert rows == 10


def test_other_scripts_table_values_in_report():
    rapport = RAPPORT.read_text(encoding="utf-8")
    sec = TEX.read_text(encoding="utf-8").split("\\label{tab:e12_other}")[1].split("\\end{table*}")[0]
    nums = re.findall(r"(\d+\.\d{3,4}) \[(\d\.\d{4}), (\d\.\d{4})\]", sec)
    assert len(nums) == 30
    for _, lo, hi in nums:
        assert f"[{lo},{hi}]" in rapport


def test_refs_resolve_and_figure_included():
    prose = _prose()
    labels = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "paper" / "sections").glob("*.tex"))
    for ref in re.findall(r"\\ref\{([^}]+)\}", prose):
        assert f"\\label{{{ref}}}" in labels, ref
    assert "figures/courbes_apprentissage.pdf" in prose
    assert "does not converge by the criterion" in prose


def test_figure_script_reads_training_artifacts_only():
    code = FIG.read_text(encoding="utf-8")
    body = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith(("#",)))
    assert "lambda_history" in code and "test_split_read" in code
    assert not re.search(r"(open|read_text|load)\([^)]*test_results", body.replace('"""', ""))
    assert "data/" not in body.split('"""')[2] if body.count('"""') >= 2 else True


def test_main_tex_inputs_sections_in_order_and_no_dangling_refs():
    main = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    inputs = re.findall(r"\\input\{sections/([^}]+)\}", main)
    assert inputs == ["02_data_audit", "03_formulation", "04_methods", "05_evaluation", "06_results"]
    assert "\\documentclass[conference]{IEEEtran}" in main and "\\bibliography{refs}" in main
    text = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "paper" / "sections").glob("*.tex")))
    code = "\n".join(l.split("%", 1)[0] for l in text.splitlines())
    labels = set(re.findall(r"\\label\{([^}]+)\}", text))
    assert {"sec:audit", "sec:method", "sec:eval", "sec:results", "sec:leakage"} <= labels
    assert not (set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", code)) - labels)
    bib = (ROOT / "paper" / "refs.bib").read_text(encoding="utf-8")
    for key in re.findall(r"\\cite\{([^}]+)\}", code):
        assert f"@misc{{{key}," in bib, key


def test_windup_is_secondary_hypothesis_after_observation():
    prose = _prose()
    i, j = prose.index("keeps rising while the in-sample cost"), prose.index("windup")
    assert i < j and "untested hypothesis" in prose[j - 80:j]
    assert prose.count("windup") == 1


def test_figure_has_e2_300_epoch_panel_and_caption():
    assert "current_300ep" in FIG.read_text(encoding="utf-8")
    prose = _prose()
    assert "in-sample" in prose and "does not converge by the criterion" in prose
