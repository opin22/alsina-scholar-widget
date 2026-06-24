import cloudscraper, re, json, os
from datetime import date
from bs4 import BeautifulSoup

SCHOLAR_ID = "TxioLDYAAAAJ"
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.json")

scraper = cloudscraper.create_scraper()
resp = scraper.get(
    f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en",
    timeout=30,
)
soup = BeautifulSoup(resp.text, "html.parser")

citations = hindex = i10index = 0
citations_since = hindex_since = i10index_since = 0

tbl = soup.find("table", id="gsc_rsb_st")
if tbl:
    for row in tbl.find_all("tr"):
        label_el = row.find("td", class_="gsc_rsb_sc1")
        if not label_el:
            continue
        label = label_el.get_text(strip=True)
        val_cells = row.find_all("td", class_="gsc_rsb_std")
        vals = []
        for td in val_cells:
            try:
                vals.append(int(td.get_text(strip=True)))
            except ValueError:
                vals.append(0)
        if len(vals) < 2:
            continue
        if label == "Citations":
            citations, citations_since = vals[0], vals[1]
        elif label == "h-index":
            hindex, hindex_since = vals[0], vals[1]
        elif label == "i10-index":
            i10index, i10index_since = vals[0], vals[1]

years = []
hist = soup.find("div", class_="gsc_md_hist_b")
if hist:
    bars = hist.find_all("a", class_=re.compile(r"gsc_g_a"))
    labels = hist.find_all("span", class_="gsc_g_t")
    for bar, lab in zip(bars, labels):
        yr = int(lab.get_text(strip=True))
        cnt = int(bar.get_text(strip=True))
        years.append({"y": yr, "c": cnt})
    years.sort(key=lambda x: x["y"])

out = {
    "citations": citations,
    "citations_since": citations_since,
    "hindex": hindex,
    "i10index": i10index,
    "updated": date.today().isoformat(),
    "years": years or [{"y": y, "c": 0} for y in range(2020, 2027)],
}

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)

print(f"OK: {json.dumps(out, ensure_ascii=False)}")
