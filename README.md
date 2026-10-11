# PSLL – Public Space as Living Lab (html-test branch)

This branch hosts a single, self-contained HTML visualization. All data, styles and scripts are inlined in
`public/index.html`, so there is no data pipeline or framework here. The original Vite + notebook dashboard
is unchanged on `main`.

| Path | What |
|---|---|
| `public/index.html` | The visualization (one file, ~18 MB, no external requests) |
| `scripts/build.mjs` | Copies `public/` to `dist/` |
| `package.json` | `npm run build` (what Cloudflare Pages runs), `npm run preview` (local server on :8000) |

## Deploy (Cloudflare Pages)

The Cloudflare Pages project `psll-dataviz` builds with `npm run build` and serves `dist/`. Those settings
apply to every branch, so this branch builds without any dashboard changes.

- Every push to `html-test` produces a preview deployment at `https://html-test.psll-dataviz.pages.dev`.
- To serve this branch on the production domain, set **Workers & Pages → psll-dataviz → Settings →
  Builds & deployments → Production branch** to `html-test`. Switch it back to `main` to restore the old
  dashboard.
- Cloudflare Pages allows files up to 25 MiB; `public/index.html` must stay under that.

## Updating the visualization

Replace `public/index.html` with the new export (keep the file name), commit, and push to `html-test`.

## Preview locally

```bash
npm run preview   # then open http://localhost:8000
```
