# Mammal–Parasite Tracker — v1 Architecture Prototype

This version changes the project from a single-source atlas into a **collection-agnostic mammal–parasite discovery framework**.

## Core model

All inputs are normalized into three entities:

- **Hosts**
- **Parasites**
- **Associations**

The interface then provides two views of exactly the same association data:

- **Host Mode:** one mapped host with all matching parasites.
- **Parasite Mode:** one mapped parasite entity with its matching mammal host(s).

See `docs/CANONICAL_SCHEMA.md`.

## Sources included in this prototype

### MSB:Para adapter

Processes independently cataloged Arctos parasite records linked to hosts through explicit `parasite of` relationships.

- Hosts: 30,906
- Parasite records: 51,376
- Associations: 51,864
- Unresolved non-GUID host relationships: 129

Evidence type: `cataloged_parasite_specimen`.

### KSB:Mamm host-part adapter

Processes the earlier KSB prototype in which parasites remain parts of the host specimen. The adapter converts each documented parasite part/parsed parasite type into a searchable parasite entity linked to its mammal host while retaining evidence provenance.

- Hosts: 131
- Parasite entities: 151
- Associations: 151

Evidence type: `host_part`.

## Combined prototype

- Hosts: 31,037
- Parasite entities: 51,527
- Associations: 52,015

`data/tracker.json` is the compact browser dataset (~11.8 MB).  
`data/canonical.json.gz` is a compressed verbose representation for development/reference.

## Generic CSV support

`adapters/generic_csv.py` converts a collection-specific CSV using a JSON column mapping such as `examples/generic_mapping.json`.

`import.html` is an early browser-side column-mapping shell. It currently validates and previews mappings locally; the next step is to have it generate canonical entities and launch the map without any server upload.

## Why adapters matter

Collections do not have to organize parasites identically.

```text
MSB:Para                        KSB:Mamm
separate parasite GUID          parasite retained as host part
        │                                │
        └──────── adapters ──────────────┘
                         │
                         v
             Host / Parasite / Association
                         │
                 ┌───────┴───────┐
                 v               v
              Host Mode      Parasite Mode
                         │
                         v
                 combined download
```

Future adapters can target Arctos authoritative host records, ALA/GBIF occurrence services, other museum exports, or user-supplied CSV files.

## Current deployment

The prototype remains static and GitHub-Pages compatible. That is intentional for development. A future multi-user service with remote APIs and persistent uploads will likely move to a backend architecture such as FastAPI + PostgreSQL/PostGIS while retaining this canonical model as the API contract.
