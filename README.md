# Kansas Host–Parasite Atlas — Version 2

Static GitHub Pages-ready prototype built from the full supplied KSB Arctos export.

## Dataset represented

- 7,775 mammal records
- 7,554 records with decimal coordinates
- 221 records retained in the normalized CSV but not mappable
- 163 host species
- 932 hosts with retained parasite material
- 1,101 retained parasite part records

## Website features

- Leaflet map with MarkerCluster for thousands of specimen points
- Genus and species filters
- Parasite screening-status filter
- Retained parasite-material filters
- Filters for explicit flea, mite, tick, and louse counts in part remarks
- Search by GUID, taxon, or locality
- Popups link to both the host GUID and individual retained Arctos parts
- Missing coordinates do not cause data loss
- Screening results and retained parasite material remain distinct concepts

## GitHub Pages

Upload the CONTENTS of this folder to the root of your GitHub repository so `index.html`
is visible at the repository root.

Then enable:

Settings → Pages → Deploy from a branch → main → / (root)

## Updating from another manual Arctos export

Run:

    python scripts/process_arctos_v2.py arctos_export.csv data

The processor recreates the normalized tables and GeoJSON. Note that this packaged
`index.html` currently embeds the generated GeoJSON so it can also open directly as
a local file. For fully automated API updates, Version 3 should load a generated
data file instead or use a build step to regenerate `index.html`.

## Interpretation

`DETECTED` / `NOT_DETECTED` are observations or screening information.
`PARTDETAIL` represents retained specimen material. Absence of a parasite part is
not interpreted as parasite absence.

Arctos GUID links are retained so Arctos remains the authoritative specimen source.
