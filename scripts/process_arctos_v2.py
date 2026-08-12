"""
Kansas Host–Parasite Atlas Version 2 processor.

Usage:
    python process_arctos_v2.py arctos_export.csv output_directory

Outputs:
    specimens_normalized.csv   all mammal records, including unmappable hosts
    parasite_parts.csv         one row per retained parasite part
    specimens.geojson          only records with valid DEC_LAT / DEC_LONG
    summary.json               dataset summary
"""
import pandas as pd
import json, re, sys
from pathlib import Path
from collections import Counter

PARASITE_PART_NAMES = {
    "ectoparasite","endoparasite","nematode","cestode","trematode",
    "acanthocephalan","flea","tick","mite","louse","lice","parasite"
}
GROUP_PATTERNS = {
    "flea": r"\b(\d+)\s+fleas?\b",
    "mite": r"\b(\d+)\s+mites?\b",
    "tick": r"\b(\d+)\s+ticks?\b",
    "louse": r"\b(\d+)\s+(?:lice|louse|louses)\b",
    "nematode": r"\b(\d+)\s+nematodes?\b",
    "cestode": r"\b(\d+)\s+cestodes?\b",
    "trematode": r"\b(\d+)\s+trematodes?\b",
}

def safe_json(v):
    if pd.isna(v) or not str(v).strip(): return []
    try:
        x=json.loads(v)
        return x if isinstance(x,list) else []
    except Exception: return []

def split_terms(v):
    if pd.isna(v): return []
    return [x.strip() for x in re.split(r"[;,|]",str(v)) if x.strip()]

def parse_counts(text):
    d={}
    if not text: return d
    s=str(text).lower()
    for k,p in GROUP_PATTERNS.items():
        m=re.search(p,s)
        if m: d[k]=int(m.group(1))
    return d

def preservation(part):
    vals=[]
    for a in part.get("part_attributes",[]) or []:
        if a.get("attribute_type")=="preservation" and a.get("attribute_value"):
            vals.append(str(a["attribute_value"]))
    return "; ".join(dict.fromkeys(vals))

def main(src,outdir):
    df=pd.read_csv(src)
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    features=[]; host_rows=[]; part_rows=[]
    status_counter=Counter(); part_counter=Counter()

    for _,r in df.iterrows():
        detected=split_terms(r.get("DETECTED"))
        not_detected=split_terms(r.get("NOT_DETECTED"))
        pparts=[]; agg=Counter()

        for p in safe_json(r.get("PARTDETAIL")):
            name=str(p.get("part_name") or "").strip()
            lname=name.lower()
            if lname not in PARASITE_PART_NAMES and "parasite" not in lname:
                continue
            parsed=parse_counts(p.get("part_remark")); agg.update(parsed)
            info={
                "part_name":name,"part_id":p.get("partID"),
                "remark":p.get("part_remark"),"preservation":preservation(p) or None,
                "condition":p.get("condition"),"count":p.get("part_count"),
                "parsed_counts":parsed
            }
            pparts.append(info); part_counter[lname]+=1
            part_rows.append({
                "host_guid":r.get("GUID"),"host_species":r.get("SPECIES"),
                "host_genus":r.get("GENUS"),"part_name":name,
                "part_id":p.get("partID"),"part_remark":p.get("part_remark"),
                "preservation":preservation(p),"condition":p.get("condition"),
                "part_count":p.get("part_count"),
                **{f"parsed_{k}_count":parsed.get(k) for k in GROUP_PATTERNS}
            })

        if detected and not_detected: status="mixed screening"
        elif detected: status="detected"
        elif not_detected: status="not detected"
        elif pparts: status="material present"
        else: status="not recorded"
        status_counter[status]+=1

        guid=str(r.get("GUID"))
        lat=pd.to_numeric(r.get("DEC_LAT"),errors="coerce")
        lon=pd.to_numeric(r.get("DEC_LONG"),errors="coerce")
        mappable=pd.notna(lat) and pd.notna(lon)

        props={
            "guid":guid,
            "species":None if pd.isna(r.get("SPECIES")) else str(r.get("SPECIES")),
            "genus":None if pd.isna(r.get("GENUS")) else str(r.get("GENUS")),
            "sex":None if pd.isna(r.get("SEX")) else str(r.get("SEX")),
            "life_stage":None if pd.isna(r.get("LIFE_STAGE")) else str(r.get("LIFE_STAGE")),
            "date":None if pd.isna(r.get("VERBATIM_DATE")) else str(r.get("VERBATIM_DATE")),
            "locality":None if pd.isna(r.get("VERBATIM_LOCALITY")) else str(r.get("VERBATIM_LOCALITY")),
            "detected":detected,"not_detected":not_detected,
            "parasite_status":status,"parasite_parts":pparts,
            "parasite_part_types":sorted(set(x["part_name"].lower() for x in pparts)),
            "parsed_counts":dict(agg),
            "arctos_url":f"https://arctos.database.museum/guid/{guid}"
        }

        if mappable:
            features.append({
                "type":"Feature",
                "geometry":{"type":"Point","coordinates":[float(lon),float(lat)]},
                "properties":props
            })

        host_rows.append({
            "guid":guid,"species":props["species"],"genus":props["genus"],
            "sex":props["sex"],"life_stage":props["life_stage"],"date":props["date"],
            "locality":props["locality"],
            "latitude":None if not mappable else float(lat),
            "longitude":None if not mappable else float(lon),
            "mappable":bool(mappable),
            "parasite_status":status,
            "detected":"; ".join(detected),"not_detected":"; ".join(not_detected),
            "parasite_parts_present":"; ".join(x["part_name"] for x in pparts),
            "parasite_summary":"; ".join(
                x["part_name"]+(f": {x['remark']}" if x.get("remark") else "")
                for x in pparts
            ),
            **{f"{k}_count":agg.get(k) for k in GROUP_PATTERNS},
            "arctos_url":props["arctos_url"]
        })

    pd.DataFrame(host_rows).to_csv(outdir/"specimens_normalized.csv",index=False)
    pd.DataFrame(part_rows).to_csv(outdir/"parasite_parts.csv",index=False)
    (outdir/"specimens.geojson").write_text(json.dumps(
        {"type":"FeatureCollection","features":features},separators=(",",":")
    ),encoding="utf-8")
    summary={
        "total_records":len(host_rows),
        "mapped_records":len(features),
        "unmapped_records":len(host_rows)-len(features),
        "host_species":len({x["species"] for x in host_rows if x["species"]}),
        "host_genera":len({x["genus"] for x in host_rows if x["genus"]}),
        "hosts_with_retained_parasite_material":sum(bool(x["parasite_parts_present"]) for x in host_rows),
        "parasite_part_records":len(part_rows),
        "status_counts":dict(status_counter),
        "part_type_counts":dict(part_counter)
    }
    (outdir/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("Usage: python process_arctos_v2.py input.csv output_directory")
    main(sys.argv[1],sys.argv[2])
