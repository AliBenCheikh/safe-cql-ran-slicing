"""Vérifie que les nombres de docs/registre_affirmations.md figurent dans la source citée sur la même ligne.

Lecture seule, aucun calcul nouveau, aucune évaluation. Fichiers lus : docs/*.md, quelques fichiers déjà produits de results/
(json, csv, log) cités dans le registre, et `git show` sur les commits cités. Ne lit ni data/ ni tests/.

Sortie : docs/verification_registre.md, un verdict par ligne du registre.

Règles (fixées avant la première exécution)
- Nombres extraits d'une ligne : valeur absolue, virgule ou point décimal, séparateurs de milliers (espace) acceptés.
  Ignorés : identifiants (E12-a, R1-W2), hachages, nombres collés à une lettre ou à « § », entiers de 0 à 10 sans décimale ni « % ».
  Les nombres en notation `6,0·10⁻⁵` sont cherchés comme texte.
- Un nombre x de d décimales est TROUVÉ dans une source s'il existe y avec au moins d décimales tel que round(y, d) == x
  (arrondi du registre), ou y == x exactement. Un registre plus précis que la source n'est pas accepté.
- Verdicts :
    OK     tous les nombres sont trouvés dans une source citée sur la ligne (ou via les identifiants de lignes citées).
    ABSENT au moins un nombre n'est trouvé dans aucune source citée sur la ligne.
    AMBIGU pas de source citée sur la ligne (section par défaut utilisée), ou nombre trouvé seulement par conversion
           %<->fraction, ou nombre absent mais ligne annonçant un « dérivé ».
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "docs" / "registre_affirmations.md"
OUT = ROOT / "docs" / "verification_registre.md"

ALIASES = {
    "audit": "audit_report", "phase1": "phase1_pipeline", "phase2": "phase2_baselines", "phase3": "phase3_learning_curves",
    "d6": "d6_shared_scripts", "d7": "d7_scheduler_order", "d8": "d8_chronology",
    "d1": "decision_memo", "d2": "decision_memo", "d3": "decision_memo", "d4": "decision_memo", "d5": "decision_memo",
    "e1": "e1_lp_diagnostic", "e2": "e2_safe_cql_diagnostic", "e11": "e11_alpha_grid",
    "e13a": "e13a_niveaux_charge", "e13b": "e13b_pas_echantillonnage", "e13d": "e13d_filtre_latence",
    "e13c": "dataset_notes", "e12": "e12_rapport_final",
}
PHRASES = [(r"Phase 1", "phase1_pipeline"), (r"Phase 2|phase 2", "phase2_baselines"), (r"mémo de décision", "decision_memo"),
           (r"Attente E12|attente E12|attentes", "e12_attente_pre_test")]
SECTION_DEFAULT = {
    "1": ["decision_memo", "d6_shared_scripts", "d7_scheduler_order", "d8_chronology", "audit_report", "phase1_pipeline"],
    "2": ["e12_rapport_final", "e12_attente_pre_test", "results/e12/test_results.json"],
    "3": ["e1_lp_diagnostic", "e2_safe_cql_diagnostic", "e11_alpha_grid"],
    "4": ["e1_lp_diagnostic", "e11_alpha_grid", "e2_safe_cql_diagnostic", "e13a2_resultats", "e12_rapport_final"],
    "5": ["e13a_niveaux_charge", "e13a2_resultats", "e13a2_protocole_entiers"],
    "6": ["e13b_pas_echantillonnage", "dataset_notes", "phase1_pipeline"],
    "7": ["e13d_filtre_latence", "e13d_protocole_filtre_latence", "dataset_notes"],
    "8": [], "9": [],
}
ID_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*-[A-Za-z0-9]+\b")
NUM_RE = re.compile(r"(?<![\w§.,])(\d{1,3}(?: \d{3})+|\d+)(?:[.,](\d+))?")
SCI_RE = re.compile(r"\d+(?:[,.]\d+)?·10⁻\d")
_cache: dict[str, str] = {}


def norm(s: str) -> str:
    return s.replace(" ", " ").replace(" ", " ").replace("−", "-")


def read_source(name: str) -> str | None:
    if name in _cache:
        return _cache[name]
    txt = None
    if re.fullmatch(r"[0-9a-f]{7,40}", name):
        r = subprocess.run(["git", "-C", str(ROOT), "show", "--no-color", name], capture_output=True, text=True)
        txt = r.stdout if r.returncode == 0 else None
    else:
        p = ROOT / (name if name.startswith("results/") else f"docs/{name}.md")
        if p.is_file() and p.suffix in (".md", ".json", ".csv", ".log") and p.resolve().is_relative_to(ROOT):
            txt = p.read_text(encoding="utf-8", errors="replace")
    if txt is not None:
        txt = norm(txt)
    _cache[name] = txt
    return txt


def split_num(tok_int: str, tok_dec: str | None):
    s = tok_int.replace(" ", "")
    return float(s + ("." + tok_dec if tok_dec else "")), (len(tok_dec) if tok_dec else 0)


def source_numbers(text: str):
    """Ensemble de (valeur, nb de décimales) de toutes les valeurs numériques du texte (formes groupée et non groupée)."""
    out = set()
    for m in re.finditer(r"(?<![\w.])(\d+(?: \d{3})*|\d+)(?:[.,](\d+))?", text):
        out.add(split_num(m.group(1), m.group(2)))
    for m in re.finditer(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?![\d])", text):        # 1,116 lu aussi comme 1116
        out.add((float(m.group(0).replace(",", "")), 0))
    for m in re.finditer(r"\d+(?:[.,]\d+)?(?:[eE]-?\d+)?", text):
        t = m.group(0).replace(",", ".")
        try:
            v = float(t)
        except ValueError:
            continue
        d = len(t.split(".")[1].split("e")[0].split("E")[0]) if "." in t else 0
        out.add((v, d))
    return out


def found(x: float, dx: int, pool) -> bool:
    for y, dy in pool:
        if dy >= dx and round(y, dx) == round(x, dx):
            return True
        if dy < dx and y == x:
            return True
    return False


def line_numbers(text: str):
    text = norm(text)
    text = re.sub(r"`[^`]*`", " ", text)          # code, chemins, hachages
    text = ID_RE.sub(" ", text)
    sci = SCI_RE.findall(text)
    text = SCI_RE.sub(" ", text)
    nums = []
    for m in NUM_RE.finditer(text):
        v, d = split_num(m.group(1), m.group(2))
        pct = bool(re.match(r"\s*(?:-\s*\d+(?:[.,]\d+)?\s*)?%", text[m.end():m.end() + 14]))
        if d == 0 and v <= 10 and not pct:
            continue
        nums.append((m.group(0).strip(), v, d, pct))
    return nums, sci


def resolve(text: str, rowsrc: dict[str, str]) -> list[str]:
    """Noms de sources citées dans `text` (cellule source ou ligne entière)."""
    names = []
    for m in re.finditer(r"results/[\w./]+", text):
        names.append(m.group(0))
    for m in re.finditer(r"\b[0-9a-f]{7}\b", text):
        if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-t", m.group(0)], capture_output=True).returncode == 0:
            names.append(m.group(0))
    stems = {p.stem for p in (ROOT / "docs").glob("*.md")}
    for tok in re.findall(r"[A-Za-z0-9_]+", text):
        if tok in stems:
            names.append(tok)
        elif tok.lower() in ALIASES and (tok.islower() or tok in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "E1", "E2", "E11")
                                         or tok.lower() in ("audit", "phase1", "phase2", "e13a", "e13b", "e13d", "e13c", "e12")):
            names.append(ALIASES[tok.lower()])
    for pat, nm in PHRASES:
        if re.search(pat, text):
            names.append(nm)
    for i in ID_RE.findall(text):
        if i in rowsrc:
            names.extend(resolve(rowsrc[i], {}))
    seen, out = set(), []
    for n in names:
        if n not in seen and read_source(n) is not None:
            seen.add(n); out.append(n)
    return out


def check(text: str, srcnames: list[str], bydefault: bool):
    nums, sci = line_numbers(text)
    if not nums and not sci:
        return "OK", "aucun nombre à vérifier", []
    pools, raw = {}, {}
    for n in srcnames:
        t = read_source(n)
        raw[n] = t
        pools[n] = source_numbers(t)
    missing, conv, hit = [], [], {}
    for lit, v, d, pct in nums:
        ok = False
        for n, pool in pools.items():
            if found(v, d, pool):
                ok = True; hit[lit] = n; break
        if not ok and pct:
            for n, pool in pools.items():
                if found(v / 100, d + 2, pool):
                    ok = True; conv.append(lit); break
            else:
                pass
        if not ok:
            missing.append(lit)
    for s in sci:
        if not any(s in raw[n] for n in raw):
            missing.append(s)
    if bydefault and not srcnames:
        return "AMBIGU", "aucune source résolvable", [lit for lit, *_ in nums]
    if missing:
        if "dérivé" in text or "dérivable" in text:
            return "AMBIGU", "nombre(s) absent(s) mais ligne annonçant un dérivé : " + ", ".join(missing), missing
        return "ABSENT", "non trouvé(s) : " + ", ".join(missing), missing
    if conv:
        return "AMBIGU", "trouvé(s) seulement par conversion % <-> fraction : " + ", ".join(conv), []
    if bydefault:
        return "AMBIGU", "pas de source citée sur la ligne ; trouvé dans la section par défaut : " + ", ".join(sorted(set(hit.values()))), []
    return "OK", "sources : " + ", ".join(sorted(set(hit.values()))), []


def main() -> int:
    lines = REG.read_text(encoding="utf-8").split("\n")
    # première passe : sources des lignes à identifiant (tables à 6 colonnes)
    rowsrc: dict[str, str] = {}
    for l in lines:
        if l.startswith("|"):
            c = [x.strip() for x in l.strip().strip("|").split("|")]
            if len(c) == 6 and ID_RE.fullmatch(c[0]):
                rowsrc[c[0]] = c[3]
    results = []
    sec = ""
    for n, l in enumerate(lines, 1):
        h = re.match(r"#{2,3} (\d+)", l)
        if h:
            sec = h.group(1)
            continue
        if not l.strip() or l.startswith("#") or l.startswith("|---") or sec in ("", "0"):
            continue
        label = l[:60]
        if l.startswith("|"):
            c = [x.strip() for x in l.strip().strip("|").split("|")]
            if len(c) == 6 and ID_RE.fullmatch(c[0]):
                label = c[0]
                text = " ".join([c[1], c[2], c[4]])
                names = resolve(c[3], rowsrc)
                v, why, miss = check(text, names, bydefault=not names)
            elif len(c) == 3 and sec == "8":
                label = c[0][:50]
                names = resolve(c[2], rowsrc)
                v, why, miss = check(c[0] + " " + c[1], names, bydefault=not names)
            elif len(c) == 3 and sec == "9":
                label = c[0][:50]
                names = resolve(c[1], rowsrc) + resolve(c[2], rowsrc)
                v, why, miss = check(c[0] + " " + c[1] + " " + c[2], list(dict.fromkeys(names)), bydefault=not names)
            else:
                continue
        else:
            names = resolve(l, rowsrc)
            bydefault = False
            if not names:
                names = [x for x in SECTION_DEFAULT.get(sec, []) if read_source(x) is not None]
                bydefault = True
            v, why, miss = check(l, names, bydefault=bydefault)
            if why == "aucun nombre à vérifier":
                continue
        results.append((n, label, v, why))
    cnt = {k: sum(1 for r in results if r[2] == k) for k in ("OK", "ABSENT", "AMBIGU")}
    with OUT.open("w", encoding="utf-8") as f:
        f.write("# Vérification du registre des affirmations\n\n")
        f.write("Produit par `src/checks/verifie_registre.py` (lecture seule ; aucun calcul nouveau ; ni `data/` ni `tests/` lus).\n")
        f.write("Règles de verdict : voir la docstring du script. Seules les lignes contenant au moins un nombre significatif sont listées.\n\n")
        f.write(f"Total : {len(results)} lignes — OK {cnt['OK']}, AMBIGU {cnt['AMBIGU']}, ABSENT {cnt['ABSENT']}.\n\n")
        f.write("| ligne | repère | verdict | détail |\n|---|---|---|---|\n")
        for n, label, v, why in results:
            f.write(f"| {n} | {label.replace('|', '/')} | {v} | {why.replace('|', '/')} |\n")
    print(cnt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
