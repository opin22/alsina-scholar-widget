export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname !== "/") {
      return new Response("Not found", { status: 404 });
    }

    const token = url.searchParams.get("token");
    if (!env.SECRET_TOKEN || token !== env.SECRET_TOKEN) {
      return new Response(JSON.stringify({ error: "forbidden" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (!env.SCRAPINGBEE_KEY) {
      return new Response(JSON.stringify({ error: "no_scrapingbee_key" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    const id = url.searchParams.get("id") || "TxioLDYAAAAJ";
    const gsUrl = "https://scholar.google.com/citations?user=" + id + "&hl=en";
    const sbUrl =
      "https://app.scrapingbee.com/api/v1/?api_key=" +
      env.SCRAPINGBEE_KEY +
      "&url=" +
      encodeURIComponent(gsUrl) +
      "&render_js=false&custom_google=True";

    try {
      const resp = await fetch(sbUrl);
      const html = await resp.text();

      if (!html || html.indexOf("gsc_rsb_st") === -1) {
        return new Response(
          JSON.stringify({ error: "blocked", http: resp.status }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        );
      }

      let citations = 0,
        cSince = 0,
        h = 0,
        hSince = 0,
        i10 = 0,
        i10Since = 0;

      const tableMatch = html.match(
        /<table[^>]*id=["']gsc_rsb_st["'][^>]*>([\s\S]*?)<\/table>/i
      );
      if (tableMatch) {
        const rows = tableMatch[1].split(/<tr[^>]*>/i);
        for (const row of rows) {
          const labelM = row.match(/gsc_rsb_sc1[^>]*>[\s\S]*?>([^<]*)</i);
          if (!labelM) continue;
          const vals = [];
          for (const m of row.matchAll(/gsc_rsb_std[^>]*>(\d+)</gi)) {
            vals.push(parseInt(m[1], 10));
          }
          if (vals.length < 2) continue;
          const label = labelM[1].trim();
          if (label === "Citations") {
            citations = vals[0];
            cSince = vals[1];
          } else if (label === "h-index") {
            h = vals[0];
            hSince = vals[1];
          } else if (label === "i10-index") {
            i10 = vals[0];
            i10Since = vals[1];
          }
        }
      }

      const years = [];
      const yearSpans = [
        ...html.matchAll(/<span class="gsc_g_t"[^>]*>(\d{4})<\/span>/gi),
      ];
      const barVals = [
        ...html.matchAll(/gsc_g_a[^>]*>[\s\S]*?gsc_g_al[^>]*>(\d+)</gi),
      ];
      for (let i = 0; i < yearSpans.length; i++) {
        const y = parseInt(yearSpans[i][1], 10);
        const c = barVals[i] ? parseInt(barVals[i][1], 10) : 0;
        years.push({ y, c });
      }
      years.sort((a, b) => a.y - b.y);

      const data = {
        citations,
        citations_since: cSince,
        hindex: h,
        i10index: i10,
        years,
      };
      return new Response(JSON.stringify(data), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-store",
        },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: String(e) }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
