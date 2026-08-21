# Mammal–Parasite Tracker — Authoritative Host Rebuild v2

This rebuild uses authoritative host records rather than inferring host traits/geography from parasite records.

## Inputs

- MSB:Mamm: 16,924 source records
- MSB:Para: 53,870 source records
- KSB:Mamm: 3,354 source records

## Browser dataset

The current tracker contains:

- **18,756 biological host individuals**
- **19,446 host catalog records**
- **690 biological hosts represented by both loaded MSB:Mamm and KSB:Mamm records**
- **29,878 parasite entities/positive observations**
- **29,901 association rows**
- **25,869 reciprocally documented MSB host–parasite relationships**

## Host reconciliation

Explicit Arctos `same individual as` relationships are used to collapse loaded MSB:Mamm and KSB:Mamm catalog records into one biological host for map display and counting. Both source GUIDs remain preserved.

## Parasite evidence

Two evidence models are intentionally distinguished:

- `cataloged_parasite_specimen`: independently cataloged MSB:Para voucher.
- `detection_observation`: positive parasite detection stored on the KSB:Mamm host record.

These can be searched together but should not be interpreted as equivalent sampling units.

## Interface

- **Host Mode** maps one point per reconciled biological mammal host.
- **Parasite Mode** maps parasite specimens/positive observations.
- Filters cover provenance, geography, host traits, parasite taxonomy, body weight, and time.
- **Download Filtered Associations** exports host traits, all loaded host GUIDs, parasite information, evidence, verification status, and geography together.

## Important next improvements

1. Link KSB positive detections to retained parasite parts without double-counting.
2. Add richer parasite traits from MSB:Para `ATTRIBUTEDETAIL`.
3. Normalize reproductive traits and measurement units.
4. Add arbitrary CSV import through the same schema.
5. Add remote collection/API adapters and an embeddable service.
