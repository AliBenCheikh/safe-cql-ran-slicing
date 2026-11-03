"""Section 03 du papier : chaque identifiant `% REG:` doit exister dans le registre,
et chaque phrase factuelle doit porter un commentaire `% REG:`."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "sections" / "03_formulation.tex"
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
    for pat in (r"xApp\s+of\s+the\s+Near-RT\s+is", r"guarantee[sd]?\s+safe", r"12\.9", r"7\.65", r"0\.053", r"23\.5"):
        assert not re.search(pat, code), pat
