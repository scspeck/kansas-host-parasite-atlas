# Kansas Host–Parasite Atlas — Version 2.1

Version 2.1 separates the website code from the specimen data.

## Why this version is easier to update

`index.html` no longer contains thousands of specimen records inside the page.
Instead, it loads:

- `data/specimens.geojson`
- `data/summary.json`

at runtime.

That means routine manual updates only require rebuilding the data files.

## Current dataset

- 7,775 mammal records
- 7,554 georeferenced records
- 221 records lacking decimal coordinates
- 163 host species
- 932 hosts with retained parasite material
- 1,101 retained parasite part records

## Manual update workflow

1. Download a new Arctos CSV export with the same relevant fields.
2. Run:

    python scripts/process_arctos_v2.py NEW_EXPORT.csv data

3. This refreshes:
   - `data/specimens.geojson`
   - `data/specimens_normalized.csv`
   - `data/parasite_parts.csv`
   - `data/summary.json`

4. Upload/commit those changed files to GitHub.
5. GitHub Pages will serve the updated map automatically.

You normally do NOT need to change or re-upload `index.html` for a routine data update.

## Important local-testing note

Because the page now uses `fetch()` to load data files, some browsers block it when
`index.html` is opened directly with a `file:///` URL.

For local testing, run this from the project folder:

    python3 -m http.server 8000

Then open:

    http://localhost:8000

GitHub Pages will work normally because it serves the site over HTTPS.

## GitHub Pages

Keep `index.html` at the repository root, with `data/` and `scripts/` beside it.

Repository structure:

    index.html
    README.md
    data/
      specimens.geojson
      specimens_normalized.csv
      parasite_parts.csv
      summary.json
    scripts/
      process_arctos_v2.py

## Future Version 3

When Arctos API access is available, the manual CSV-download step can be replaced
with an automated API request and scheduled GitHub Action.
