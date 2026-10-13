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
4. A same-repository PR automatically runs the **Publication preview** workflow, validates the candidate, then commits generated static HTML and sitemap to the **draft branch**, never to main. It attaches screenshots and the HTML bundle as a GitHub Actions artifact. It is a downloadable preview, **not** a hosted public preview URL. In ChatGPT, provide the preview directly as artifacts whenever possible. Fork-origin PRs are deliberately excluded from this write-capable workflow.
5. Show any unresolved validation or layout issues and obtain explicit approval before merging or deploying. Changing the reviewed content requires a fresh preview.
6. Merge **source plus all generated static HTML and sitemap changes** so branch-based GitHub Pages publishing sees the final page from the actual merge commit. The main-branch check asserts generated outputs are in sync instead of committing post-merge. Verify the live page, sitemap and navigation afterwards.

For articles and cases, inspect the existing design language and ensure that a new page is discoverable from the home page. Check captions, figures, tables, mobile overflow and any external links. Long articles must be scrolled in the HTML preview; screenshots alone are insufficient.

## Why generated files must travel with the approved merge

GitHub documents that commits made by a workflow with its default `GITHUB_TOKEN` do **not** trigger a GitHub Pages build. The previous Notes generator wrote to `main` after a user's commit, creating a risk of generated content not reaching the live site. The new publication-preview workflow instead builds and commits generated output **on the PR branch**. That way the reviewed merge commit contains the final static files and can trigger the normal Pages build. The main-branch generator workflow now checks that those files match their sources; it never makes a follow-on bot commit.

**Privacy warning:** This is a *public repository*. A draft branch or PR is not private: unpublished manuscript text placed on GitHub may be visible before the homepage changes. For confidential drafts, prepare and inspect a local ChatGPT HTML preview first and commit only with informed approval.

