import json, os
from datetime import date
from scholarly import scholarly, ProxyGenerator

SCHOLAR_ID = "TxioLDYAAAAJ"
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.json")

pg = ProxyGenerator()
pg.FreeProxies()
scholar.use_proxy(pg)

try:
    author = scholarly.search_author_id(SCHOLAR_ID)
    author = scholarly.fill(author, sections=["basics", "indices", "publications"])

    # Gather citations per year from the author object
    years_data = []
    if "cites_per_year" in author:
        for yr, cnt in sorted(author["cites_per_year"].items()):
            if isinstance(yr, int) and yr >= 2019:
                years_data.append({"y": yr, "c": cnt})
    else:
        years_data = [{"y": y, "c": 0} for y in range(2020, 2027)]

    out = {
        "citations": author.get("citedby", 0),
        "citations_since": author.get("citedby5y", 0),
        "hindex": author.get("hindex", 0),
        "i10index": author.get("i10index", 0),
        "updated": date.today().isoformat(),
        "years": years_data,
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    print(f"OK: {json.dumps(out, ensure_ascii=False)}")

except Exception as e:
    print(f"ERROR: {e}")
    raise
