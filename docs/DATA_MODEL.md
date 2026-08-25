# Data Model Notes

## Biological host
The map's host unit is a biological mammal individual. When loaded MSB:Mamm and KSB:Mamm catalog records are explicitly connected by `same individual as`, both records are assigned to one biological host.

## Host catalog record
Catalog records remain separate objects beneath the biological host. This preserves source-specific identifiers and metadata.

## Parasite entity
An MSB:Para record is an independently cataloged parasite specimen. A KSB `detected` assertion is represented as a positive parasite observation rather than being promoted to a voucher specimen.

## Association
An association links a biological host to a parasite entity/observation. MSB relationships are assigned `reciprocal`, `mammal_side_only`, or `parasite_side_only` verification status when possible.

## Current KSB limitation
KSB retained parasite parts are not yet reconciled with KSB `detected` assertions. This release therefore uses positive detections for searchability and does not yet count retained parts as additional parasite entities.
