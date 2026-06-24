import cloudscraper, json, os
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

# Debug: print excerpts to find correct selectors
tbl = soup.find("table", id="gsc_rsb_st")
if tbl:
    print("=== TABLE FOUND ===")
    print(tbl.prettify()[:2000])
else:
    print("=== TABLE NOT FOUND ===")
    # Find any table
    for t in soup.find_all("table"):
        print("TABLE:", t.get("id", ""), t.get("class", ""))
    # search for citation numbers in the page
    text = resp.text
    import re
    nums = re.findall(r'Citations[^0-9]*(\d+)', text)
    print("Citations in text:", nums)
    # search for gsc_rsb_st
    if 'gsc_rsb_st' in text:
        idx = text.index('gsc_rsb_st')
        print("Context around gsc_rsb_st:", text[max(0,idx-200):idx+500])

hist = soup.find("div", class_="gsc_md_hist_b")
if hist:
    print("\n=== HISTOGRAM FOUND ===")
    print(hist.prettify()[:1000])
else:
    print("\n=== HISTOGRAM NOT FOUND ===")
    if 'gsc_md_hist_b' in resp.text:
        idx = resp.text.index('gsc_md_hist_b')
        print("Context:", resp.text[max(0,idx-200):idx+500])

# Write default data so deploy doesn't break
out = {
    "citations": 0, "citations_since": 0,
    "hindex": 0, "i10index": 0,
    "updated": date.today().isoformat(),
    "years": [{"y": y, "c": 0} for y in range(2020, 2027)],
}
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
