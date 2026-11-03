"""Section 04 du papier : chaque identifiant `% REG:` doit exister dans le registre,
et chaque phrase factuelle doit porter un commentaire `% REG:`."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "sections" / "04_methods.tex"
REGISTRE = ROOT / "docs" / "registre_affirmations.md"

# Identifiants de lignes du registre : tableaux (| id |) et titres NO-* (id : NO-xxx).
def _registry_ids():
    txt = REGISTRE.read_text(encoding="utf-8")
    ids = set(re.findall(r"^\|\s*([A-Za-z0-9-]+)\s*\|", txt, flags=re.M))
    ids |= set(re.findall(r"id\s*:\s*(NO-[a-z]+)", txt))
    return ids


def _reg_ids_in_tex():
    out = []
    for line in TEX.read_text(encoding="utf-8").splitlines():
        if "% REG:" not in line or line.lstrip().startswith("%"):
            continue
        tail = line.split("% REG:", 1)[1].split(";", 1)[0]
        out += [t.strip() for t in tail.split(",") if t.strip()]
    return out


def test_every_reg_id_exists_in_registry():
    known = _registry_ids()
    missing = sorted({i for i in _reg_ids_in_tex() if i not in known})
    assert not missing, f"identifiants absents du registre : {missing}"


def test_sentences_carry_reg_comment():
    bad = []
    for n, line in enumerate(TEX.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("%"):
            continue
        body = line.split("%", 1)[0].rstrip()
        # une ligne qui se termine une phrase (point final) doit citer le registre
        if re.search(r"[A-Za-z)}]\.$", body) and "% REG:" not in line and "% STRUCT" not in line:
            bad.append(n)
    assert not bad, f"phrases sans % REG: lignes {bad}"


def test_no_forbidden_claims():
    txt = TEX.read_text(encoding="utf-8")
    code = "\n".join(l.split("%", 1)[0] for l in txt.splitlines())
    for pat in (r"[Aa]daptive", r"guarantee[sd]?\s+safe", r"12\.9", r"converges?\s+(near|to|at)", r"outperform", r"we use clipped", r"shadow price"):
        assert not re.search(pat, code), pat


def test_config_values_match_code():
    """Les hyperparamètres écrits dans la section doivent figurer dans le code des agents."""
    tex = TEX.read_text(encoding="utf-8")
    cql = (ROOT / "src" / "agents" / "cql.py").read_text(encoding="utf-8")
    safe = (ROOT / "src" / "agents" / "safe_cql.py").read_text(encoding="utf-8")
    iql = (ROOT / "src" / "agents" / "iql.py").read_text(encoding="utf-8")
    for code in ('"hidden": 256', '"batch": 1024', '"lr": 3e-4', '"tau": 0.005', '"epochs": 100'):
        assert code in cql, code
    assert '"eta": 0.1' in safe
    assert '"expectile": 0.7' in iql and '"beta": 3.0' in iql and '"w_max": 100.0' in iql
    for frag in ("256", "1\\,024", "3\\times10^{-4}", "0.005", "$\\eta=0.1$", "0.7", "3.0"):
        assert frag in tex, frag


def _sentences_with(txt, start):
    return [l.split("%", 1)[0].strip() for l in txt.splitlines() if l.startswith(start)]


def test_gamma_sentences_identical_in_03_and_04():
    t03 = (ROOT / "paper" / "sections" / "03_formulation.tex").read_text(encoding="utf-8")
    t04 = TEX.read_text(encoding="utf-8")
    for start in ("The agents of the main comparison are trained", "The variant with $\\gamma=0$"):
        a, b = _sentences_with(t03, start), _sentences_with(t04, start)
        assert len(a) == 1 and a == b, start


def test_no_code_or_doc_annotations_left():
    for name in ("03_formulation.tex", "04_methods.tex"):
        txt = (ROOT / "paper" / "sections" / name).read_text(encoding="utf-8")
        assert "CODE:" not in txt and "DOC:" not in txt, name


def test_artefact_reader_never_opens_test_results():
    src = (ROOT / "src" / "checks" / "lit_artefacts_entrainement.py").read_text(encoding="utf-8")
    # aucun chemin construit vers test_results, aucune lecture : seul train_summary.json est ouvert
    assert not re.search(r'(/|Path\(|open\()[^\n]*"test_results', src)
    assert 'SUMMARY = E12 / "train_summary.json"' in src and 'assert meta["test_split_read"] is False' in src
