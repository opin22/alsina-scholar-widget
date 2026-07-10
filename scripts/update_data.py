import cloudscraper, re, json, os, sys, time, requests
from datetime import date
from bs4 import BeautifulSoup

SCHOLAR_ID = "TxioLDYAAAAJ"
SINTA_JOURNAL_ID = "13830"
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.json")

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def parse_gs_page(html):
    soup = BeautifulSoup(html, "html.parser")
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

def scrape_gs():
    attempts = 0
    while attempts < 3:
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(
                f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en",
                timeout=30,
            )
            gs = parse_gs_page(resp.text)
            if gs["citations"] > 0:
                print(f"GS OK (cloudscraper): citations={gs['citations']}")
                return gs
        except Exception as e:
            print(f"GS cloudscraper attempt {attempts+1}: {e}", file=sys.stderr)
        try:
            resp = requests.get(
                f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"},
                timeout=30,
            )
            gs = parse_gs_page(resp.text)
            if gs["citations"] > 0:
                print(f"GS OK (requests): citations={gs['citations']}")
                return gs
        except Exception as e:
            print(f"GS requests attempt {attempts+1}: {e}", file=sys.stderr)
        attempts += 1
        time.sleep(5)
    return {"citations": 0, "citations_since": 0, "hindex": 0, "i10index": 0, "years": []}

def scrape_sinta():
    result = {}
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(
            f"https://sinta.kemdiktisaintek.go.id/journals/profile/{SINTA_JOURNAL_ID}",
            timeout=20,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        nums = soup.find_all("div", class_="stat-num")
        if len(nums) >= 3:
            result["sinta_impact"] = float(nums[0].get_text(strip=True))
            result["sinta_rank"] = nums[2].get_text(strip=True)
            print(f"SINTA OK: rank={result['sinta_rank']} impact={result['sinta_impact']}")
    except Exception as e:
        print(f"SINTA scrape failed: {e}", file=sys.stderr)
    return result

existing = load_existing()
out = dict(existing)

gs = scrape_gs()
if gs["citations"] > 0:
    out.update(gs)

sinta = scrape_sinta()
if sinta:
    out.update(sinta)

out["updated"] = date.today().isoformat()
if not out.get("years"):
    out["years"] = [{"y": y, "c": 0} for y in range(2020, 2027)]

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"Done: citations={out['citations']} sinta_rank={out.get('sinta_rank','?')}")
