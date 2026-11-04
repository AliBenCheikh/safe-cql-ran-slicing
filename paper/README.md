# Compiling the paper on Overleaf

1. Upload the whole `paper/` folder (a zip of the folder, or its contents at the project root): `main.tex`, `refs.bib`, `sections/`, `figures/`.
2. In the menu, set **Main document** to `main.tex` and the compiler to `pdfLaTeX` (the class `IEEEtran` is available on Overleaf).
3. Compile. The bibliography runs through BibTeX (`\bibliography{refs}`); Overleaf does it automatically.

## State of the draft

- `main.tex` includes sections 02 to 06 only. There is no abstract, introduction, related work or conclusion yet.
- `refs.bib` holds one placeholder entry per `\cite{TODO-...}` key of the sections; they have no author, title or year, so the references print empty.
- `figures/courbes_apprentissage.pdf` is produced by `python -m src.figures.courbes_apprentissage` (needs `results/` and `matplotlib`, not shipped with the paper); the PDF is committed.
- Every factual sentence of the sections carries a `% REG: <id>` comment pointing to `docs/registre_affirmations.md`; the comments do not show in the PDF.
- This has not been compiled locally (no LaTeX installation was available).
