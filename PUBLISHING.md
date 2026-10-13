# Preview-first publishing

**The author supplies content; the assistant applies site conventions, renders the actual HTML, and asks for approval before publishing.** No admin login or CMS is required.

## Content types

| Contribution | Where authored | Associated output |
| --- | --- | --- |
| Note | `notes/direct-notes.json` | `notes/index.html`, `notes/n/*/index.html`, `sitemap.xml` |
| Article | `articles/<slug>/index.html` | Home-page Writing links, `sitemap.xml` |
| Case study | Standalone directory such as `nyshex/` | Home-page cases, navigation and sitemap |
| Other page / tool | Appropriate standalone HTML folder | Links, sitemap and relevant assets |

For a Note, use the existing JSON object format: `id`, `date` (`YYYY-MM-DD`), `title`, `body`, `category`. Infer the metadata from the submitted writing and existing Notes. Valid categories: AI & future work; Products & systems; Judgment & knowledge; Writing & craft; Life & learning; Society & institutions. Other optional fields in existing entries may be preserved. The generator derives display text where possible. **Do not manually edit the large embedded legacy Notes dataset.**

## Draft → preview → approval → live

1. Work in a draft branch. No direct writing to `main` merely because an author supplies new content.
2. Generate and verify the candidate:
   ```sh
   python scripts/validate_notes.py
   python scripts/generate_note_pages.py
   python scripts/check_site.py
   ```
3. Preview the same candidate that will be merged, both in the browser and on mobile. Locally:
   ```sh
   python -m pip install playwright
   python -m playwright install chromium
   python scripts/preview_content.py --base origin/main
   ```
   Open `publication-preview/index.html` to view screenshots. Unzip `publication-preview/site-preview.zip`, change into the extracted site folder, run `python -m http.server 8000`, then open `http://localhost:8000/` for a navigable actual HTML site. Root-relative assets do not work reliably when opening an HTML file via `file://`. Remote fonts and external images still depend on network access.
4. A PR automatically runs the **Publication preview** workflow and attaches the same screenshots and HTML bundle as a GitHub Actions artifact. It is a downloadable preview, **not** a hosted public preview URL. In ChatGPT, provide the preview directly as artifacts whenever possible.
5. Show any unresolved validation or layout issues and obtain explicit approval before merging or deploying. Changing the reviewed content requires a fresh preview.
6. Merge **source plus all generated static HTML and sitemap changes** so the branch-based GitHub Pages deployment sees the final page from the actual merge commit. Verify the live page, sitemap and navigation afterwards.

For articles and cases, inspect the existing design language and ensure that a new page is discoverable from the home page. Check captions, figures, tables, mobile overflow and any external links. Long articles must be scrolled in the HTML preview; screenshots alone are insufficient.

## Why generated files must travel with the approved merge

The current `.github/workflows/generate-note-pages.yml` generates static pages and commits them using the default `GITHUB_TOKEN`. GitHub documents that commits made with that token do **not** trigger a GitHub Pages build. Therefore an automated post-merge generator commit alone does not guarantee the live site updated. Generate and include static output in the reviewed PR before merging. Do not switch Pages publishing mode without checking its current configuration. An eventual explicit generate-and-deploy Pages workflow is a separate infrastructure improvement.

## Final publication checks

Check that the words are preserved, category and title are accurate, links work, metadata and sitemap exist, desktop and mobile pages display correctly, author approval covers this exact candidate, and the live site actually updates.
