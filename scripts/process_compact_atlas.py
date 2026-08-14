"""
Build compact host-centered relational atlas data from an Arctos parasite export.

Usage:
    python process_compact_atlas.py parasite_export.csv data

Expected CSV columns:
GUID
SCIENTIFIC_NAME
VERBATIM_DATE
DEC_LAT
DEC_LONG
KINGDOM
PHYLUM
PHYLCLASS
PHYLORDER
FAMILY
GENUS
SPECIES
RELATEDCATALOGEDITEMS
ATTRIBUTEDETAIL

The script produces:
    data/atlas.json
    data/summary.json

The website reads atlas.json directly.
"""

# -----------------------------
# IMPORTS
# -----------------------------

import pandas as pd
import json
import re
import sys

from pathlib import Path
from collections import Counter


# -----------------------------
# REGULAR EXPRESSION FOR
# PARSING ARCTOS RELATIONSHIPS
# -----------------------------

# Arctos stores related records in text that looks something like:
#
# (parasite of) Arctos record GUID
# https://arctos.database.museum/guid/UAM:Mamm:78325
#
# This regular expression extracts:
#
# relationship = "parasite of"
# guid         = "UAM:Mamm:78325"

REL_PAT = re.compile(
    r'\(([^)]+)\)\s+Arctos record GUID\s+'
    r'https://arctos\.database\.museum/guid/([^;\s]+)',
    re.I
)


# -----------------------------
# PARSE RELATED ARCTOS RECORDS
# -----------------------------

def parse_relationships(text):
    """
    Parse the RELATEDCATALOGEDITEMS field.

    Returns a list such as:

    [
        {
            "relationship": "parasite of",
            "guid": "UAM:Mamm:78325"
        },
        {
            "relationship": "same lot as",
            "guid": "MSB:Para:2"
        }
    ]

    If there are no relationships, return an empty list.
    """

    if pd.isna(text):
        return []

    return [
        {
            "relationship": m.group(1).strip(),
            "guid": m.group(2).strip()
        }
        for m in REL_PAT.finditer(str(text))
    ]


# -----------------------------
# PARSE ATTRIBUTEDETAIL JSON
# -----------------------------

def safe_attrs(v):
    """
    ATTRIBUTEDETAIL is stored in the CSV as a JSON string.

    Example:

    [
      {
        "attribute_type": "verbatim host ID",
        "attribute_value": "Myodes rutilus"
      }
    ]

    This converts that string back into a Python list.

    If the field is blank or malformed, return [] instead
    of causing the script to crash.
    """

    if pd.isna(v) or not str(v).strip():
        return []

    try:
        x = json.loads(v)

        return x if isinstance(x, list) else []

    except Exception:
        return []


# -----------------------------
# GET ONE ATTRIBUTE VALUE
# -----------------------------

def first_attr(attrs, name):
    """
    Search the parsed ATTRIBUTEDETAIL list for a particular
    attribute type.

    Example:

        first_attr(attrs, "verbatim host ID")

    might return:

        "Myodes rutilus"

    We only use the first matching value.
    """

    for a in attrs:

        if (
            a.get("attribute_type") == name
            and a.get("attribute_value") not in (None, "")
        ):
            return str(a.get("attribute_value"))

    return None


# -----------------------------
# EXTRACT A FOUR-DIGIT YEAR
# -----------------------------

def explicit_year(v):
    """
    Extract an explicit four-digit year from VERBATIM_DATE.

    Examples:

        "23 Jul 2002"  -> 2002
        "15 June 2023" -> 2023
        "1897-02-12"   -> 1897

    We intentionally DO NOT guess dates such as:

        "6-13-85"

    because 85 could theoretically mean 1885 or 1985.

    If no four-digit year exists, return None.
    """

    if pd.isna(v):
        return None

    m = re.search(
        r'(?<!\d)(18\d{2}|19\d{2}|20\d{2})(?!\d)',
        str(v)
    )

    return int(m.group(1)) if m else None


# -----------------------------
# GET COLLECTION PREFIX
# -----------------------------

def host_collection(guid):
    """
    Convert a full Arctos GUID:

        UAM:Mamm:78325

    into its collection prefix:

        UAM:Mamm

    This allows the website to filter by host collection.
    """

    p = str(guid).split(":")

    return ":".join(p[:2]) if len(p) >= 2 else str(guid)


# -----------------------------
# CLASSIFY HOST TYPE
# -----------------------------

def host_group(guid):
    """
    Infer a broad host group from the Arctos collection prefix.

    Examples:

        MSB:Mamm -> Mammal
        MSB:Bird -> Bird
        MSB:Fish -> Fish
        MSB:Herp -> Herpetofauna

    MSB:Host is a special host collection and gets its own label.
    """

    suffix = host_collection(guid).split(":")[-1].lower()

    return {
        "mamm": "Mammal",
        "bird": "Bird",
        "fish": "Fish",
        "herp": "Herpetofauna",
        "host": "Host collection",
        "para": "Parasite record"
    }.get(
        suffix,
        "Other/unknown"
    )


# -----------------------------
# MAIN PROCESSING FUNCTION
# -----------------------------

def main(src, outdir):

    # Read the raw Arctos CSV into a pandas DataFrame.
    df = pd.read_csv(src)

    # Convert the output path to a Path object.
    outdir = Path(outdir)

    # Create the output directory if it does not exist.
    outdir.mkdir(
        parents=True,
        exist_ok=True
    )


    # =========================================================
    # STRING DICTIONARY
    # =========================================================

    # Repeated strings are one of the major reasons GeoJSON
    # becomes huge.
    #
    # Instead of storing:
    #
    # "Paranoplocephala nearctica"
    #
    # thousands of times, we store it ONCE in:
    #
    # strings = [...]
    #
    # and refer to it with an integer ID.

    strings = []

    string_to_id = {}


    def sid(value):
        """
        Convert a string into a compact integer ID.

        Example:

            "Myodes rutilus" -> 143

        If we encounter the same string again, we reuse 143.

        -1 represents missing data.
        """

        if value is None or value == "":
            return -1

        value = str(value)

        if value not in string_to_id:

            string_to_id[value] = len(strings)

            strings.append(value)

        return string_to_id[value]


    # =========================================================
    # TEMPORARY DATA STRUCTURES
    # =========================================================

    # One entry per unique parasite GUID.
    parasite_meta = []

    # Lets us quickly find the integer ID belonging to a
    # parasite GUID.
    parasite_guid_to_id = {}

    # Temporary host information keyed by host GUID.
    #
    # We use this while reading parasite records because
    # multiple parasites may belong to the same host.
    host_temp = {}

    # Every parasite <-> host link is stored here.
    relationships = []


    # =========================================================
    # LOOP THROUGH EVERY PARASITE RECORD
    # =========================================================

    for _, r in df.iterrows():

        # ---------------------------------------------
        # Find all related Arctos records
        # ---------------------------------------------

        rels = parse_relationships(
            r.get("RELATEDCATALOGEDITEMS")
        )


        # ---------------------------------------------
        # Keep only "parasite of" relationships
        # ---------------------------------------------

        # A parasite may have relationships such as:
        #
        # same lot as
        # collected with
        # parasite of
        #
        # For the atlas we specifically want host links.

        host_rels = [
            x
            for x in rels
            if x["relationship"].lower() == "parasite of"
        ]


        # If this parasite is not linked to a host,
        # skip it for the relational map.
        if not host_rels:
            continue


        # ---------------------------------------------
        # Process parasite GUID
        # ---------------------------------------------

        pg = str(
            r.get("GUID")
        )


        # If we have not seen this parasite before,
        # create a parasite metadata record.
        if pg not in parasite_guid_to_id:

            pid = len(
                parasite_meta
            )

            parasite_guid_to_id[pg] = pid


            # Each parasite record is stored as a compact ARRAY
            # rather than a verbose JSON object.
            #
            # Positions:
            #
            # 0 = GUID
            # 1 = scientific name
            # 2 = kingdom
            # 3 = phylum
            # 4 = class
            # 5 = order
            # 6 = family
            # 7 = genus
            # 8 = species
            #
            # Each text field is actually stored as a STRING ID.

            parasite_meta.append([
                sid(pg),

                sid(
                    None
                    if pd.isna(r.get("SCIENTIFIC_NAME"))
                    else r.get("SCIENTIFIC_NAME")
                ),

                sid(
                    None
                    if pd.isna(r.get("KINGDOM"))
                    else r.get("KINGDOM")
                ),

                sid(
                    None
                    if pd.isna(r.get("PHYLUM"))
                    else r.get("PHYLUM")
                ),

                sid(
                    None
                    if pd.isna(r.get("PHYLCLASS"))
                    else r.get("PHYLCLASS")
                ),

                sid(
                    None
                    if pd.isna(r.get("PHYLORDER"))
                    else r.get("PHYLORDER")
                ),

                sid(
                    None
                    if pd.isna(r.get("FAMILY"))
                    else r.get("FAMILY")
                ),

                sid(
                    None
                    if pd.isna(r.get("GENUS"))
                    else r.get("GENUS")
                ),

                sid(
                    None
                    if pd.isna(r.get("SPECIES"))
                    else r.get("SPECIES")
                )
            ])

        else:

            # If we have already seen this parasite,
            # retrieve its existing integer ID.
            pid = parasite_guid_to_id[pg]


        # =====================================================
        # EXTRACT PARASITE ATTRIBUTES
        # =====================================================

        attrs = safe_attrs(
            r.get("ATTRIBUTEDETAIL")
        )


        # Host species / identification.
        host_taxon = first_attr(
            attrs,
            "verbatim host ID"
        )


        # Where the parasite was found within the host.
        #
        # Examples might include:
        #
        # stomach
        # intestine
        # liver
        # body surface
        loc = first_attr(
            attrs,
            "location in host"
        )


        # Parasite life stage.
        stage = first_attr(
            attrs,
            "life stage"
        )


        # Parasite sex.
        psex = first_attr(
            attrs,
            "sex"
        )


        # Number of individuals represented by the record.
        count = first_attr(
            attrs,
            "individual count"
        )


        # Get a numerical collection year.
        year = explicit_year(
            r.get("VERBATIM_DATE")
        )


        # =====================================================
        # COORDINATES
        # =====================================================

        lat = pd.to_numeric(
            r.get("DEC_LAT"),
            errors="coerce"
        )

        lon = pd.to_numeric(
            r.get("DEC_LONG"),
            errors="coerce"
        )


        # If either coordinate is missing,
        # mark the location as unavailable.
        if pd.isna(lat) or pd.isna(lon):

            lat_i = None
            lon_i = None

        else:

            # Round to five decimal places.
            #
            # This is approximately meter-level precision,
            # which is more than enough for this map,
            # while reducing file size.
            lat_i = round(
                float(lat),
                5
            )

            lon_i = round(
                float(lon),
                5
            )


        # =====================================================
        # PROCESS EACH HOST LINK
        # =====================================================

        # Most parasite records will have one host, but this
        # allows the data model to support multiple links.

        for hr in host_rels:

            hg = hr["guid"]


            # ---------------------------------------------
            # Create host accumulator if necessary
            # ---------------------------------------------

            if hg not in host_temp:

                host_temp[hg] = {

                    # We may encounter several slightly different
                    # host identifications associated with parasites.
                    # Counter lets us choose the most common one.
                    "taxa": Counter(),

                    "collection": host_collection(hg),

                    "group": host_group(hg),

                    # All parasite coordinates associated with host.
                    "coords": [],

                    # All collection years associated with host.
                    "years": []
                }


            h = host_temp[hg]


            # ---------------------------------------------
            # Count host taxon observations
            # ---------------------------------------------

            if host_taxon:

                h["taxa"][host_taxon] += 1


            # ---------------------------------------------
            # Save associated coordinates
            # ---------------------------------------------

            if lat_i is not None:

                h["coords"].append(
                    (
                        lon_i,
                        lat_i
                    )
                )


            # ---------------------------------------------
            # Save associated years
            # ---------------------------------------------

            if year is not None:

                h["years"].append(
                    year
                )


            # =================================================
            # BUILD RELATIONSHIP RECORD
            # =================================================

            # Each relationship array contains:
            #
            # 0 = parasite integer ID
            # 1 = host GUID string ID (temporary)
            # 2 = year
            # 3 = latitude
            # 4 = longitude
            # 5 = location in host
            # 6 = parasite life stage
            # 7 = parasite sex
            # 8 = individual count
            #
            # Missing year uses -1.

            relationships.append([
                pid,

                sid(hg),

                year
                if year is not None
                else -1,

                lat_i,

                lon_i,

                sid(loc),

                sid(stage),

                sid(psex),

                sid(count)
            ])


    # =========================================================
    # BUILD FINAL HOST TABLE
    # =========================================================

    host_meta = []

    # Maps the host GUID string ID to its smaller host integer ID.
    guid_sid_to_hid = {}


    for hg, h in host_temp.items():

        hg_sid = sid(hg)

        hid = len(
            host_meta
        )

        guid_sid_to_hid[hg_sid] = hid


        # -----------------------------------------------------
        # Choose most commonly reported host taxon
        # -----------------------------------------------------

        if h["taxa"]:

            taxon = h["taxa"].most_common(
                1
            )[0][0]

        else:

            taxon = None


        # -----------------------------------------------------
        # Estimate host coordinates
        # -----------------------------------------------------

        # Because this dataset came from the parasite
        # export rather than the host export, we infer the host
        # location from coordinates of parasites associated with it.
        #
        # In the production KSB atlas, we should use the host
        # record's actual coordinates instead.

        if h["coords"]:

            lon = round(
                sum(
                    c[0]
                    for c in h["coords"]
                )
                / len(h["coords"]),
                5
            )

            lat = round(
                sum(
                    c[1]
                    for c in h["coords"]
                )
                / len(h["coords"]),
                5
            )

        else:

            lon = None
            lat = None


        years = h["years"]


        # -----------------------------------------------------
        # Store compact host metadata
        # -----------------------------------------------------

        # Host array:
        #
        # 0 = host GUID string ID
        # 1 = host taxon string ID
        # 2 = collection string ID
        # 3 = broad host group string ID
        # 4 = latitude
        # 5 = longitude
        # 6 = earliest associated year
        # 7 = latest associated year

        host_meta.append([
            hg_sid,

            sid(taxon),

            sid(
                h["collection"]
            ),

            sid(
                h["group"]
            ),

            lat,

            lon,

            min(years)
            if years
            else -1,

            max(years)
            if years
            else -1
        ])


    # =========================================================
    # REPLACE HOST GUID STRING IDS WITH HOST INTEGER IDS
    # =========================================================

    # Earlier, relationship rows referenced the host GUID through
    # the string dictionary.
    #
    # Now that hosts have compact integer IDs, replace them.

    for row in relationships:

        row[1] = guid_sid_to_hid[
            row[1]
        ]


    # =========================================================
    # SUMMARY INFORMATION
    # =========================================================

    years = [
        r[2]
        for r in relationships
        if r[2] != -1
    ]


    summary = {

        "source_records": len(df),

        "parasites": len(
            parasite_meta
        ),

        "hosts": len(
            host_meta
        ),

        "relationships": len(
            relationships
        ),

        "mapped_relationships": sum(
            1
            for r in relationships
            if r[3] is not None
            and r[4] is not None
        ),

        "mapped_hosts": sum(
            1
            for h in host_meta
            if h[4] is not None
            and h[5] is not None
        ),

        "min_year": (
            min(years)
            if years
            else None
        ),

        "max_year": (
            max(years)
            if years
            else None
        ),

        "strings": len(
            strings
        )
    }


    # =========================================================
    # FINAL COMPACT DATA OBJECT
    # =========================================================

    # Short property names reduce file size further:
    #
    # m = parasite metadata
    # h = host metadata
    # r = relationships
    # s = shared string dictionary

    data = {

        "m": parasite_meta,

        "h": host_meta,

        "r": relationships,

        "s": strings,

        "summary": summary
    }


    # =========================================================
    # WRITE atlas.json
    # =========================================================

    # separators removes unnecessary whitespace:
    #
    # default:
    # { "m": [...] }
    #
    # compact:
    # {"m":[...]}
    #
    # This saves a surprising amount of space in large JSON files.

    (
        outdir
        / "atlas.json"
    ).write_text(

        json.dumps(
            data,
            separators=(
                ",",
                ":"
            )
        ),

        encoding="utf-8"
    )


    # =========================================================
    # WRITE HUMAN-READABLE SUMMARY
    # =========================================================

    (
        outdir
        / "summary.json"
    ).write_text(

        json.dumps(
            summary,
            indent=2
        ),

        encoding="utf-8"
    )


# -----------------------------
# COMMAND-LINE ENTRY POINT
# -----------------------------

if __name__ == "__main__":

    # Script requires:
    #
    # argument 1 = CSV
    # argument 2 = output folder

    if len(sys.argv) != 3:

        raise SystemExit(
            "Usage: python process_compact_atlas.py "
            "parasite_export.csv data"
        )


    main(
        sys.argv[1],
        sys.argv[2]
    )
