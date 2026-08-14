# Host–Parasite Relational Atlas - Host-Centered GitHub Version

This practice atlas uses a compact relational JSON architecture designed to fit comfortably within GitHub's browser-upload limits.

## Size reduction

The earlier practice version used roughly 45 MB of GeoJSON. This version stores the same core relational information in:

- `data/atlas.json` — about 6.3 MB
- `data/summary.json` — tiny summary file

The reduction comes from:

- storing repeated strings once in a string dictionary,
- using integer IDs for hosts and parasites,
- storing coordinates once as numeric arrays,
- generating Arctos URLs in the browser rather than storing them repeatedly,
- avoiding verbose GeoJSON property names on every record.

## Current dataset

- 51,316 parasite records
- 30,849 unique host GUIDs
- 51,790 parasite-to-host relationships
- 40,733 mapped relationships
- 24,379 mapped hosts

## GitHub Pages

Upload the contents of this folder to a repository:

    index.html
    README.md
    data/
      atlas.json
      summary.json
    scripts/
      process_compact_atlas.py

Every individual file is comfortably under GitHub's 25 MiB browser-upload limit.

Then enable:

Settings → Pages → Deploy from a branch → main → / (root)

## Compact data structure

`atlas.json` contains:

- `s` — unique strings
- `m` — parasite metadata
- `h` — host metadata
- `r` — parasite↔host relationship/map rows

The website reconstructs display labels from those integer references in the browser.

## Future scaling

This architecture is appropriate for tens of thousands of records on GitHub Pages.
When the atlas reaches hundreds of thousands or millions of relationships, the next step should be a database/API rather than continually enlarging `atlas.json`.


## Host-centered map change

The map now displays only one point per host GUID.

Parasite records are not shown as separate map points. Instead:

- each host popup lists linked parasite GUIDs,
- parasite genus/species filters show only hosts containing matching parasite records,
- the year slider filters hosts based on linked parasite records within the selected year range,
- searches can still match host GUIDs, host taxa, parasite GUIDs, or parasite taxa.

This is simpler for interpretation and reduces geographic clutter while preserving the host–parasite relationship structure.


## Higher parasite taxonomy

This version adds cascading filters for:

- Kingdom
- Phylum
- Class
- Order
- Family
- Genus
- Species

Selecting a higher rank restricts the available choices at all lower ranks. The map remains host-centered: a host is shown only if at least one linked parasite record matches the full selected taxonomy and year filters.
