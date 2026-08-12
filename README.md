# Kansas Host–Parasite Atlas — Prototype

This prototype was generated from the supplied manual Arctos export.

## Open the map

Open `index.html` in a web browser while connected to the internet. The specimen
data are embedded directly in the HTML, so no local web server is required.
Internet access is only needed for Leaflet/OpenStreetMap assets.

## Current prototype features

- Maps all specimens with decimal coordinates.
- Filters by host species and screening status.
- Searches by GUID, species, or locality.
- Keeps `DETECTED` and `NOT_DETECTED` separate.
- Parses retained parasite parts from `PARTDETAIL`.
- Conservatively extracts flea, mite, tick, and louse/lice counts when those
  counts are explicitly stated in part remarks.
- Links every popup to the authoritative Arctos GUID.
- Does not interpret a missing parasite record as a negative observation.

## Files

- `index.html`: interactive website prototype.
- `data/specimens.geojson`: map-ready specimen data.
- `data/specimens_normalized.csv`: one row per mammal host.
- `data/parasite_parts.csv`: one row per retained parasite part.
- `scripts/process_arctos.py`: reusable parser for future manual exports.

## Future API version

When Arctos API access is available, the data acquisition step can be replaced
with a scheduled API request. The normalization logic and website data model can
remain substantially the same.

## Important interpretation note

Screening status and retained material are distinct. A value in `DETECTED`
records an observation, while a parasite part in `PARTDETAIL` represents retained
material. The prototype intentionally preserves that distinction.
