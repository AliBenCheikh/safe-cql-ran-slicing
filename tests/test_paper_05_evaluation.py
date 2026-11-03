"""Section 05 du papier : chaque identifiant `% REG:` doit exister dans le registre,
et chaque phrase factuelle doit porter un commentaire `% REG:`."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "sections" / "05_evaluation.tex"
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
    for pat in (r"[Aa]daptive", r"guarantee[sd]?\s+safe", r"12\.9", r"outperform", r"validated in Near", r"proves? safe"):
        assert not re.search(pat, code), pat


def test_no_code_or_doc_annotations_left():
    assert "CODE:" not in TEX.read_text(encoding="utf-8") and "DOC:" not in TEX.read_text(encoding="utf-8")


def test_protocol_constants_match_code():
    """B, graine, seuils d'attente et verrou O_EXCL écrits dans la section doivent exister dans le code."""
    code = (ROOT / "src" / "e12_final.py").read_text(encoding="utf-8")
    for frag in ("B_BOOT = 2000", "BOOT_SEED = 0", "PROCHE_REL = 0.10", "PARTIAL_COV = 0.5", "NET_SD = 2.0", "O_EXCL", "MIN_RES_FLAG = 10"):
        assert frag in code, frag
    tex = TEX.read_text(encoding="utf-8")
    for frag in ("2\\,000", "10\\%", "50\\%", "two standard deviations", "O\\_EXCL"):
        assert frag in tex, frag


def _prose():
    return "\n".join(l.split("%", 1)[0] for l in TEX.read_text(encoding="utf-8").splitlines())


def test_no_claim_about_original_notebook_fqe():
    prose = _prose()
    assert not re.search(r"original notebook|incorrect|corrected version", prose)
    assert "No Fitted Q Evaluation and no importance-weighted estimator is used." in prose
