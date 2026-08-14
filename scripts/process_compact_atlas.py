"""Build compact relational atlas data from an Arctos parasite export.

Usage:
    python process_compact_atlas.py parasite_export.csv data

Expected columns:
GUID, SCIENTIFIC_NAME, VERBATIM_DATE, DEC_LAT, DEC_LONG, GENUS, SPECIES,
RELATEDCATALOGEDITEMS, ATTRIBUTEDETAIL
"""
import pandas as pd
import json, re, sys
from pathlib import Path
from collections import Counter

REL_PAT = re.compile(
    r'\(([^)]+)\)\s+Arctos record GUID\s+https://arctos\.database\.museum/guid/([^;\s]+)',
    re.I
)

def parse_relationships(text):
    if pd.isna(text): return []
    return [{"relationship":m.group(1).strip(),"guid":m.group(2).strip()}
            for m in REL_PAT.finditer(str(text))]

def safe_attrs(v):
    if pd.isna(v) or not str(v).strip(): return []
    try:
        x=json.loads(v)
        return x if isinstance(x,list) else []
    except Exception:
        return []

def first_attr(attrs,name):
    for a in attrs:
        if a.get("attribute_type")==name and a.get("attribute_value") not in (None,""):
            return str(a.get("attribute_value"))
    return None

def explicit_year(v):
    if pd.isna(v): return None
    m=re.search(r'(?<!\d)(18\d{2}|19\d{2}|20\d{2})(?!\d)',str(v))
    return int(m.group(1)) if m else None

def host_collection(guid):
    p=str(guid).split(":")
    return ":".join(p[:2]) if len(p)>=2 else str(guid)

def host_group(guid):
    suffix=host_collection(guid).split(":")[-1].lower()
    return {
        "mamm":"Mammal","bird":"Bird","fish":"Fish","herp":"Herpetofauna",
        "host":"Host collection","para":"Parasite record"
    }.get(suffix,"Other/unknown")

def main(src,outdir):
    df=pd.read_csv(src)
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    strings=[]; string_to_id={}
    def sid(value):
        if value is None or value=="": return -1
        value=str(value)
        if value not in string_to_id:
            string_to_id[value]=len(strings); strings.append(value)
        return string_to_id[value]

    parasite_meta=[]; parasite_guid_to_id={}
    host_temp={}
    relationships=[]

    for _,r in df.iterrows():
        rels=parse_relationships(r.get("RELATEDCATALOGEDITEMS"))
        host_rels=[x for x in rels if x["relationship"].lower()=="parasite of"]
        if not host_rels: continue

        pg=str(r.get("GUID"))
        if pg not in parasite_guid_to_id:
            pid=len(parasite_meta); parasite_guid_to_id[pg]=pid
            parasite_meta.append([
                sid(pg),
                sid(None if pd.isna(r.get("SCIENTIFIC_NAME")) else r.get("SCIENTIFIC_NAME")),
                sid(None if pd.isna(r.get("GENUS")) else r.get("GENUS")),
                sid(None if pd.isna(r.get("SPECIES")) else r.get("SPECIES"))
            ])
        else:
            pid=parasite_guid_to_id[pg]

        attrs=safe_attrs(r.get("ATTRIBUTEDETAIL"))
        host_taxon=first_attr(attrs,"verbatim host ID")
        loc=first_attr(attrs,"location in host")
        stage=first_attr(attrs,"life stage")
        psex=first_attr(attrs,"sex")
        count=first_attr(attrs,"individual count")
        year=explicit_year(r.get("VERBATIM_DATE"))

        lat=pd.to_numeric(r.get("DEC_LAT"),errors="coerce")
        lon=pd.to_numeric(r.get("DEC_LONG"),errors="coerce")
        if pd.isna(lat) or pd.isna(lon):
            lat_i=lon_i=None
        else:
            lat_i=round(float(lat),5); lon_i=round(float(lon),5)

        for hr in host_rels:
            hg=hr["guid"]
            if hg not in host_temp:
                host_temp[hg]={
                    "taxa":Counter(),"collection":host_collection(hg),
                    "group":host_group(hg),"coords":[],"years":[]
                }
            h=host_temp[hg]
            if host_taxon: h["taxa"][host_taxon]+=1
            if lat_i is not None: h["coords"].append((lon_i,lat_i))
            if year is not None: h["years"].append(year)

            relationships.append([
                pid,sid(hg),year if year is not None else -1,
                lat_i,lon_i,sid(loc),sid(stage),sid(psex),sid(count)
            ])

    host_meta=[]; guid_sid_to_hid={}
    for hg,h in host_temp.items():
        hg_sid=sid(hg); hid=len(host_meta); guid_sid_to_hid[hg_sid]=hid
        taxon=h["taxa"].most_common(1)[0][0] if h["taxa"] else None
        if h["coords"]:
            lon=round(sum(c[0] for c in h["coords"])/len(h["coords"]),5)
            lat=round(sum(c[1] for c in h["coords"])/len(h["coords"]),5)
        else:
            lon=lat=None
        years=h["years"]
        host_meta.append([
            hg_sid,sid(taxon),sid(h["collection"]),sid(h["group"]),lat,lon,
            min(years) if years else -1,max(years) if years else -1
        ])

    for row in relationships:
        row[1]=guid_sid_to_hid[row[1]]

    years=[r[2] for r in relationships if r[2]!=-1]
    summary={
        "source_records":len(df),
        "parasites":len(parasite_meta),
        "hosts":len(host_meta),
        "relationships":len(relationships),
        "mapped_relationships":sum(1 for r in relationships if r[3] is not None and r[4] is not None),
        "mapped_hosts":sum(1 for h in host_meta if h[4] is not None and h[5] is not None),
        "min_year":min(years) if years else None,
        "max_year":max(years) if years else None,
        "strings":len(strings)
    }
    data={"m":parasite_meta,"h":host_meta,"r":relationships,"s":strings,"summary":summary}
    (outdir/"atlas.json").write_text(json.dumps(data,separators=(",",":")),encoding="utf-8")
    (outdir/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("Usage: python process_compact_atlas.py parasite_export.csv data")
    main(sys.argv[1],sys.argv[2])
