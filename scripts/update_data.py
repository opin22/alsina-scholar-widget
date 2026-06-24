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

# === Parse stats table ===
citations = hindex = i10index = 0
citations_since = hindex_since = i10index_since = 0

tbl = soup.find("table", id="gsc_rsb_st")
if tbl:
    cells = tbl.find_all("td", class_="gsc_rsb_sc")
    nums = {}
    for td in cells:
        label_el = td.find("span", class_="gsc_rsb_a1")
        val_el = td.find("span", class_="gsc_rsb_a2")
        if label_el and val_el:
            nums[label_el.get_text(strip=True)] = int(val_el.get_text(strip=True))
    citations = nums.get("Citations", 0)
    hindex = nums.get("h-index", 0)
    i10index = nums.get("i10-index", 0)

    rows = tbl.find_all("tr")
    if len(rows) >= 3:
        s = rows[2].find_all("td")
        if len(s) >= 3:
            citations_since = int(s[0].get_text(strip=True))
            hindex_since = int(s[1].get_text(strip=True))
            i10index_since = int(s[2].get_text(strip=True))

# === Parse citation histogram ===
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
