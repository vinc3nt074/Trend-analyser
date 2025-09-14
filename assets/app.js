async function loadTrends() {
  const res = await fetch("trends.json?ts=" + Date.now());
  if (!res.ok) throw new Error("trends.json fehlt – warte auf GitHub Action.");
  return await res.json();
}
const esc = s => String(s ?? "").replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));

function badge(txt){ return `<span class="badge">${esc(txt)}</span>`; }
function pill(txt){ return `<span class="pill">${esc(txt)}</span>`; }

function render(data){
  const nicheSel = document.getElementById("niche");
  const qInput   = document.getElementById("q");
  const sortSel  = document.getElementById("sort");
  const list     = document.getElementById("list");

  const sources = [];
  if (data.source?.google) sources.push("Google");
  if (data.source?.tiktok_csv || data.source?.tiktok) sources.push("TikTok CSV");
  document.getElementById("srcs").innerHTML = sources.map(badge).join("");

  let items = (data.items||[]).slice();

  // Filter
  const niche = nicheSel.value;
  const q = (qInput.value||"").toLowerCase().trim();
  items = items.filter(it => niche==="alle" ? true : it.niche===niche);
  if (q){
    items = items.filter(it =>
      (it.title||"").toLowerCase().includes(q) ||
      JSON.stringify(it.sources||[]).toLowerCase().includes(q) ||
      JSON.stringify(it.articles||[]).toLowerCase().includes(q)
    );
  }

  // Sort
  const s = sortSel.value;
  items.sort((a,b)=>{
    if (s==="score") return (b.score||0)-(a.score||0);
    if (s==="title") return (a.title||"").localeCompare(b.title||"");
    if (s==="niche") return (a.niche||"").localeCompare(b.niche||"");
    return 0;
  });

  // Render
  list.innerHTML = items.map(it=>{
    const sigs = [
      it.formattedTraffic ? `Traffic: ${esc(it.formattedTraffic)}` : "",
      (it.tiktokViews ? `TT Views: ${esc(it.tiktokViews)}` : ""),
      (typeof it.tiktokGrowth!=="undefined" ? `TT Growth: ${esc(it.tiktokGrowth)}` : "")
    ].filter(Boolean).join(" • ");
    const links = (it.articles||[]).slice(0,3)
      .map(a=>`<a href="${esc(a.url)}" target="_blank">${esc(a.title||"Quelle")}</a>`).join("");
    const srcBadges = (it.sources||[]).map(s=>pill(s)).join("");
    const trendLink = it.shareUrl ? `<a href="${esc(it.shareUrl)}" target="_blank">Google Trends</a>` : "";

    return `
      <article class="item">
        <div class="row">
          ${pill(it.niche||"—")}
          <span class="pill score">Score: ${Math.round(it.score||0)}</span>
          <span class="row">${srcBadges}</span>
        </div>
        <h3>${esc(it.title||"—")}</h3>
        <div class="muted">${sigs || "—"}</div>
        <div class="links">
          ${links || trendLink || ""}
        </div>
      </article>
    `;
  }).join("");

  document.getElementById("meta").textContent =
    `${items.length} Trends • geladen: ${new Date(data.fetched_at||Date.now()).toLocaleString()}`;
}

async function boot(){
  try {
    const data = await loadTrends();
    render(data);
  } catch (e) {
    document.getElementById("meta").textContent = "trends.json noch nicht vorhanden – die GitHub Action erzeugt sie beim ersten Lauf.";
  }
}
document.getElementById("reload").addEventListener("click", boot);
document.getElementById("niche").addEventListener("change", boot);
document.getElementById("q").addEventListener("input", boot);
document.getElementById("sort").addEventListener("change", boot);
boot();
