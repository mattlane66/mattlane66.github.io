# Site architecture

This repository is the deployable source for [mattlane66.github.io](https://mattlane66.github.io).

The site intentionally avoids a framework and build pipeline. Most pages are self-contained HTML/CSS/JS so a case study or tool can remain portable, inspectable, and publishable directly through GitHub Pages.

## What is hand-authored vs. generated

- `index.html` — portfolio home and navigation.
- `about/index.html` — About page.
- `nyshex/index.html`, `codeai/index.html`, `splice/index.html` — self-contained product cases.
- `fit-check/index.html` — self-contained interactive method/workbench.
- `planning-tools/index.html` — **generated standalone deployment artifact** from the Planning Skills Lab. It bundles its runtime and is intentionally large; do not treat the minified bundle as hand-authored source.
- `notes/index.html` — generated static notes archive.
- `assets/` — local visual assets used by the portfolio.
- `favicon.svg` / `favicon.ico` — explicit and fallback site icons.
- `scripts/check_site.py` — dependency-free release checks.

## Page contract

Every public HTML page should have:

1. HTML5 doctype and `lang`.
2. UTF-8 charset and responsive viewport.
3. A useful title and meta description.
4. Exactly one semantic `h1` (it may be visually hidden when the design does not call for a visible page title).
5. A favicon, either explicitly linked or via the root fallback.
6. No broken internal links or asset references.
7. `rel="noopener"` on links that open a new tab.
8. Responsive behavior at phone widths.
9. Meaningful `alt` text for informative images.
10. No credentials, API keys, or secrets in the public source.

The `Site health` GitHub Action enforces the structural checks that can be verified statically.

## Security model

This is a static GitHub Pages site: there is no application server, database, login, payment flow, or server-side user data in this repository. The meaningful security boundary is therefore **repository write access**.

Changes to the public site come from commits to `main`, followed by GitHub Pages deployment. Protecting the GitHub account, installed GitHub Apps, collaborators, and the `main` branch matters more than application-server hardening here.

## Maintenance rule

Prefer the simplest implementation that preserves the experience. Avoid adding a framework, runtime dependency, tracker, or remote script unless it solves a concrete problem that the current static approach cannot.
