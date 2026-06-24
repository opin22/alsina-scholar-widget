import cloudscraper, re, json, os, sys, time
from datetime import date
from bs4 import BeautifulSoup

SCHOLAR_ID = "TxioLDYAAAAJ"
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.json")

def scrape():
    scraper = cloudscraper.create_scraper()
    resp = scraper.get(
        f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en",
        timeout=30,
    )
    soup = BeautifulSoup(resp.text, "html.parser")

    c = h = i10 = 0; cs = hs = i10s = 0
    tbl = soup.find("table", id="gsc_rsb_st")
    if tbl:
        for row in tbl.find_all("tr"):
            le = row.find("td", class_="gsc_rsb_sc1")
            if not le: continue
            lbl = le.get_text(strip=True)
            vc = row.find_all("td", class_="gsc_rsb_std")
            vs = []
            for td in vc:
                try: vs.append(int(td.get_text(strip=True)))
                except: vs.append(0)
            if len(vs) < 2: continue
            if lbl == "Citations": c, cs = vs[0], vs[1]
            elif lbl == "h-index": h, hs = vs[0], vs[1]
            elif lbl == "i10-index": i10, i10s = vs[0], vs[1]

    years = []
    hist = soup.find("div", class_="gsc_md_hist_b")
    if hist:
        bars = hist.find_all("a", class_=re.compile(r"gsc_g_a"))
        labels = hist.find_all("span", class_="gsc_g_t")
        for bar, lab in zip(bars, labels):
            years.append({"y": int(lab.get_text(strip=True)), "c": int(bar.get_text(strip=True))})
        years.sort(key=lambda x: x["y"])
    return {"citations": c, "citations_since": cs, "hindex": h, "i10index": i10, "years": years}

# Try up to 3 times
for attempt in range(3):
    try:
        out = scrape()
        if out["citations"] > 0:
            out["updated"] = date.today().isoformat()
            if not out["years"]:
                out["years"] = [{"y": y, "c": 0} for y in range(2020, 2027)]
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False)
            print(f"OK: {json.dumps(out)}")
            sys.exit(0)
        else:
            print(f"Attempt {attempt+1}: got zeros, retrying...", file=sys.stderr)
    except Exception as e:
        print(f"Attempt {attempt+1}: {e}", file=sys.stderr)
    time.sleep(5)

# Fallback: keep existing data
print("All attempts failed, keeping existing data", file=sys.stderr)
sys.exit(1)
