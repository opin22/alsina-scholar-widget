// ============================================
// Alsina Scholar Updater — Google Apps Script
// ============================================
// Tujuan: mengambil data sitasi Google Scholar dari IP Google (tidak diblokir),
// lalu push data.json ke repo GitHub (memicu deploy Pages otomatis).
//
// SETUP (sekali saja):
//  1. Buka https://script.google.com  -> New project
//  2. Paste seluruh file ini
//  3. Project Settings -> Script Properties -> tambahkan:
//       REPO       = opin22/alsina-scholar-widget
//       BRANCH     = master
//       DATA_PATH  = data.json
//       GS_USER_ID = TxioLDYAAAAJ
//       GITHUB_TOKEN = <Personal Access Token>
//     (Buat token di https://github.com/settings/tokens -> classic,
//      scope: "repo" cukup. Token disimpan aman di Script Properties.)
//  4. Jalankan fungsi setupTriggers() sekali untuk trigger harian.
//     (Izinkan otorisasi Akun Google saat diminta)
// ============================================

var DEFAULT_PROPS = {
  REPO: 'opin22/alsina-scholar-widget',
  BRANCH: 'master',
  DATA_PATH: 'data.json',
  GS_USER_ID: 'TxioLDYAAAAJ'
};

function setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  // Jalankan 2x sehari: 06:30 dan 18:30 (waktu zona script, biasanya UTC)
  ScriptApp.newTrigger('main').timeBased().atHour(6).everyDays(1).nearMinute(30).create();
  ScriptApp.newTrigger('main').timeBased().atHour(18).everyDays(1).nearMinute(30).create();
  Logger.log('Triggers dibuat: main @ 06:30 & 18:30');
}

function getProp(k) {
  var v = PropertiesService.getScriptProperties().getProperty(k);
  if (v === null) v = (DEFAULT_PROPS[k] !== undefined) ? DEFAULT_PROPS[k] : null;
  return v;
}

function main() {
  var token = getProp('GITHUB_TOKEN');
  if (!token) throw new Error('GITHUB_TOKEN belum di-set di Script Properties');

  var html = fetchGS();
  var gs = parseGS(html);
  if (!gs || gs.citations <= 0) throw new Error('Gagal parse Google Scholar: citations=0');

  var existing = fetchRepoData(token);
  var years = parseYears(html);
  if (years.length > 0) existing.years = years;

  var newData = {
    citations: gs.citations,
    citations_since: gs.citations_since,
    hindex: gs.hindex,
    i10index: gs.i10index,
    sinta_rank: existing.sinta_rank || 'Sinta 2',
    sinta_impact: existing.sinta_impact || 0,
    scopus_citedness: existing.scopus_citedness || 0,
    years: years.length > 0 ? years : (existing.years || []),
    updated: Utilities.formatDate(new Date(), 'UTC', 'yyyy-MM-dd')
  };

  var result = pushRepoData(token, newData);
  Logger.log('OK: citations=' + newData.citations + ' updated=' + newData.updated + ' sha=' + (result.sha || '?'));
  return 'citations=' + newData.citations;
}

// ---------- Google Scholar ----------

function fetchGS() {
  var user = getProp('GS_USER_ID');
  var url = 'https://scholar.google.com/citations?user=' + encodeURIComponent(user) + '&hl=en';
  var resp = UrlFetchApp.fetch(url, {
    muteHttpExceptions: true,
    headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36' }
  });
  var text = resp.getContentText();
  if (resp.getResponseCode() !== 200) throw new Error('HTTP ' + resp.getResponseCode());
  if (text.indexOf('gsc_rsb_st') === -1) throw new Error('Halaman bukan profil Scholar (kemungkinan captcha/redirect)');
  return text;
}

function parseGS(html) {
  // Baris: <td class="gsc_rsb_sc1"><a ...>Citations</a></td><td class="gsc_rsb_std">484</td><td class="gsc_rsb_std">473</td>
  var rows = html.match(/gsc_rsb_sc1[^>]*>.*?<\/td>\s*<td[^>]*>(\d+)<\/td>\s*<td[^>]*>(\d+)<\/td>/g);
  var out = { citations: 0, citations_since: 0, hindex: 0, i10index: 0 };
  if (!rows) return out;
  for (var i = 0; i < rows.length; i++) {
    var m = rows[i].match(/gsc_rsb_sc1[^>]*>.*?<a[^>]*>(.*?)<\/a><\/td>\s*<td[^>]*>(\d+)<\/td>\s*<td[^>]*>(\d+)<\/td>/s);
    if (!m) continue;
    var label = m[1].replace(/\s+/g, ' ').trim();
    var v1 = parseInt(m[2], 10), v2 = parseInt(m[3], 10);
    if (label.indexOf('Citations') === 0) { out.citations = v1; out.citations_since = v2; }
    else if (label.indexOf('h-index') === 0) { out.hindex = v1; }
    else if (label.indexOf('i10-index') === 0) { out.i10index = v1; }
  }
  return out;
}

function parseYears(html) {
  // Tahun: <span class="gsc_g_t" style="right:..">2020</span>
  // Nilai: <a class="gsc_g_a" style=".."><span class="gsc_g_al">7</span></a>
  // Urutan kemunculan di DOM sama untuk tahun & bar (kanan ke kiri), pasangkan berurutan.
  var years = [];
  var lblRe = /gsc_g_t[^>]*>(\d+)<\/span>/g;
  var barRe = /gsc_g_al[^>]*>(\d+)<\/span>/g;
  var lbls = [], bars = [], m;
  while ((m = lblRe.exec(html)) !== null) lbls.push(parseInt(m[1], 10));
  while ((m = barRe.exec(html)) !== null) bars.push(parseInt(m[1], 10));
  // DOM menampilkan tahun & bar dari kanan (terbaru) ke kiri; tahun baru dulu, bar baru dulu.
  lbls.reverse();
  bars.reverse();
  var n = Math.min(lbls.length, bars.length);
  for (var i = 0; i < n; i++) years.push({ y: lbls[i], c: bars[i] });
  years.sort(function (a, b) { return a.y - b.y; });
  return years;
}

// ---------- GitHub ----------

function githubHeaders(token) {
  return {
    'Authorization': 'Bearer ' + token,
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'alsina-updater',
    'X-GitHub-Api-Version': '2022-11-28'
  };
}

function fetchRepoData(token) {
  var repo = getProp('REPO'), branch = getProp('BRANCH'), path = getProp('DATA_PATH');
  var url = 'https://api.github.com/repos/' + repo + '/contents/' + path + '?ref=' + encodeURIComponent(branch);
  var resp = UrlFetchApp.fetch(url, { headers: githubHeaders(token), muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) return {};
  var body = JSON.parse(resp.getContentText());
  var raw = Utilities.newBlob(Utilities.base64Decode(body.content)).getDataAsString();
  try { return JSON.parse(raw); } catch (e) { return {}; }
}

function pushRepoData(token, data) {
  var repo = getProp('REPO'), branch = getProp('BRANCH'), path = getProp('DATA_PATH');
  var content = Utilities.base64Encode(JSON.stringify(data, null, 2));
  var url = 'https://api.github.com/repos/' + repo + '/contents/' + path;

  // Ambil SHA file saat ini (update, bukan overwrite-tanpa-history)
  var resp = UrlFetchApp.fetch(url + '?ref=' + encodeURIComponent(branch), { headers: githubHeaders(token), muteHttpExceptions: true });
  var sha = null;
  if (resp.getResponseCode() === 200) {
    sha = JSON.parse(resp.getContentText()).sha;
  }

  var payload = {
    message: 'update data: ' + data.updated + ' (GAS)',
    content: content,
    branch: branch
  };
  if (sha) payload.sha = sha;

  var put = UrlFetchApp.fetch(url, {
    method: 'put',
    headers: githubHeaders(token),
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  if (put.getResponseCode() !== 200 && put.getResponseCode() !== 201) {
    throw new Error('GitHub PUT failed: ' + put.getResponseCode() + ' ' + put.getContentText().slice(0, 300));
  }
  return JSON.parse(put.getContentText());
}
