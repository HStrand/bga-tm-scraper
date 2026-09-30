#!/usr/bin/env python3
"""Build the interactive card timing matrix page from card_timing_*.csv.

Run card_timing.py first. Writes card_timing_matrix.html next to this script
(self-contained: inline SVG + JSON, no external libraries).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).parent
M = pd.read_csv(here / "card_timing_matrix.csv")
G = pd.read_csv(here / "card_timing_gen.csv")
A = pd.read_csv(here / "card_timing_allgen.csv")
out = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "card_timing_matrix.html"

ok = M[M.quadrant != "insufficient"]
d = np.r_[ok.rel_delta_early, ok.rel_delta_late]
l = np.r_[ok.log_rr_early, ok.log_rr_late]
K = float(d.std() / l.std())
EARLY, LATE = "1-4", "9-12"

def r(x, n=3):
    return None if (pd.isna(x) or not np.isfinite(x)) else round(float(x), n)

gens = {c: g for c, g in G.groupby("Card")}
data = []
for _, m in M.iterrows():
    g = gens.get(m.Card)
    rows = []
    for _, x in g.sort_values("Gen").iterrows():
        rows.append([int(x.Gen), r(x.rel_delta), r(x.se), r(x.log_rr), int(x.n_played), int(x.n_held)])
    data.append({
        "c": m.Card,
        "e": [r(m.rel_delta_early), r(m.se_early), r(m.log_rr_early), int(m.n_played_early) if not pd.isna(m.n_played_early) else 0, int(m.n_held_early) if not pd.isna(m.n_held_early) else 0],
        "l": [r(m.rel_delta_late), r(m.se_late), r(m.log_rr_late), int(m.n_played_late) if not pd.isna(m.n_played_late) else 0, int(m.n_held_late) if not pd.isna(m.n_held_late) else 0],
        "g": rows,
    })
allg = [[int(x.g), r(x.played_all), r(x.rate_all)] for _, x in A.iterrows()]
n_cards = len(M)
n_plays = int(G.n_played.sum())

html = r"""<title>Card Timing Matrix</title>
<style>
:root{
  --surface:#fcfcfb; --page:#f6f6f2; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,.10); --tip:#ffffff;
  --q1:#2a78d6; --q2:#eb6834; --q3:#2a9d5c; --q4:#8b5cf6; --sel:#0b0b0b;
  --tint:.045;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --surface:#1a1a19; --page:#0d0d0d; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10); --tip:#242423;
    --q1:#3987e5; --q2:#d95926; --q3:#2f9a5c; --q4:#9b7cf3; --sel:#ffffff; --tint:.08;
  }
}
:root[data-theme="dark"]{
  --surface:#1a1a19; --page:#0d0d0d; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10); --tip:#242423;
  --q1:#3987e5; --q2:#d95926; --q3:#2f9a5c; --q4:#9b7cf3; --sel:#ffffff; --tint:.08;
}
*{box-sizing:border-box}
body{background:var(--page);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;padding-block:28px;padding-inline:16px;margin:0}
.wrap{max-width:1000px;margin:0 auto;display:grid;gap:18px}
h1{font-size:21px;font-weight:600;margin:0;letter-spacing:-.01em;text-wrap:balance}
h2{font-size:15px;font-weight:600;margin:0 0 8px}
.sub{color:var(--ink2);font-size:14px;line-height:1.5;max-width:70ch;margin:6px 0 0}
.card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:16px 18px 12px;position:relative}
.controls{display:flex;flex-wrap:wrap;gap:14px 22px;align-items:flex-end;font-size:13px;color:var(--ink2)}
.ctl{display:flex;flex-direction:column;gap:5px}
.ctl label{font-size:11.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.ctl input[type=range]{width:190px;accent-color:var(--q1)}
.ctl select,.ctl input[type=search]{font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--axis);border-radius:4px;padding:5px 8px}
.ctl input[type=search]{width:220px}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{font:inherit;font-size:12.5px;padding:4px 9px;border-radius:999px;border:1px solid var(--axis);background:transparent;color:var(--ink2);cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.chip i{width:9px;height:9px;border-radius:50%;display:inline-block}
.chip[aria-pressed="true"]{background:color-mix(in srgb,var(--ink) 9%,transparent);border-color:var(--ink2);color:var(--ink)}
.chip:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--q1);outline-offset:2px}
.kval{font-variant-numeric:tabular-nums;color:var(--ink)}
svg{width:100%;height:auto;display:block;overflow:visible}
.gridline{stroke:var(--grid);stroke-width:1}
.zero{stroke:var(--axis);stroke-width:1;stroke-dasharray:4 4}
.tick{fill:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.axlabel{fill:var(--ink2);font-size:12.5px}
.qlabel{fill:var(--ink2);font-size:12px;font-weight:600;letter-spacing:.03em;text-transform:uppercase}
.qsub{fill:var(--muted);font-size:11px}
.dot{stroke:var(--surface);stroke-width:1.5;cursor:pointer}
.dot.dim{opacity:.14;pointer-events:none}
.dot.thin{fill:var(--surface);stroke:var(--dc);stroke-width:2}
.dot.thin.sel{stroke:var(--sel)}
.dot.sel{stroke:var(--sel);stroke-width:2.5}
.lbl{fill:var(--ink);font-size:11.5px;pointer-events:none;paint-order:stroke;stroke:var(--surface);stroke-width:3px;stroke-linejoin:round}
.line{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.mdot{stroke:var(--surface);stroke-width:2}
.tooltip{position:absolute;pointer-events:none;background:var(--tip);border:1px solid var(--border);border-radius:4px;padding:8px 10px;font-size:12px;line-height:1.45;color:var(--ink);box-shadow:0 2px 8px rgba(0,0,0,.14);min-width:190px;display:none;z-index:2}
.tooltip b{font-weight:600}
.tooltip .r{display:flex;justify-content:space-between;gap:14px;font-variant-numeric:tabular-nums}
.tooltip .r span:first-child{color:var(--muted)}
.detail{display:grid;grid-template-columns:minmax(220px,1fr) 2fr;gap:18px}
@media (max-width:720px){.detail{grid-template-columns:1fr}}
.stats{display:grid;grid-template-columns:auto 1fr 1fr;gap:4px 12px;font-size:13px;font-variant-numeric:tabular-nums;align-content:start}
.stats .h{color:var(--muted);font-size:11.5px;letter-spacing:.04em;text-transform:uppercase}
.stats .v{text-align:right}
.qtag{display:inline-flex;align-items:center;gap:7px;font-size:13px;color:var(--ink2);margin:4px 0 12px}
.qtag i{width:10px;height:10px;border-radius:50%;display:inline-block}
.mini{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media (max-width:560px){.mini{grid-template-columns:1fr}}
.mini h3{font-size:12.5px;font-weight:500;color:var(--ink2);margin:0 0 4px}
.tblwrap{overflow-x:auto;margin-top:6px}
table{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums;min-width:760px;width:100%}
th,td{padding:5px 9px;text-align:right;border-bottom:1px solid var(--grid);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:500;cursor:pointer;user-select:none;position:sticky;top:0;background:var(--surface)}
th.on{color:var(--ink)}
td.name{color:var(--ink);cursor:pointer}
td.name i{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:7px}
.foot{font-size:12.5px;color:var(--muted);line-height:1.55;max-width:78ch}
.foot code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;color:var(--ink2)}
details summary{cursor:pointer;color:var(--ink2);font-size:13px}
</style>

<div class="wrap">
  <div>
    <h1>Card timing matrix: early value against late value</h1>
    <p class="sub">Every project card scored for play in generations __EARLY__ and generations __LATE__. Each score adds how the card performs when played, relative to the average card played in the same generation, to how often holders play it, relative to the average card. 2-player standard filters, __NCARDS__ cards, __NPLAYS__ plays.</p>
  </div>

  <div class="card">
    <div class="controls">
      <div class="ctl"><label for="k">Play-rate weight k <span class="kval" id="kv"></span></label><input type="range" id="k" min="0" max="1.5" step="0.01"></div>
      <div class="ctl"><label for="minp">Min plays per window</label>
        <select id="minp"><option value="200">200</option><option value="500">500</option><option value="1000">1,000</option><option value="3000">3,000</option><option value="10000">10,000</option></select></div>
      <div class="ctl"><label>Highlight quadrants</label><div class="chips" id="chips"></div></div>
      <div class="ctl"><label for="q">Find a card</label><input type="search" id="q" list="cardlist" placeholder="Immigrant City"><datalist id="cardlist"></datalist></div>
    </div>
  </div>

  <div class="card">
    <div id="scatter"></div>
    <div class="tooltip" id="tip"></div>
  </div>

  <div class="card" id="detailcard">
    <h2 id="dname"></h2>
    <div class="qtag" id="dq"></div>
    <div class="detail">
      <div class="stats" id="dstats"></div>
      <div class="mini">
        <div><h3>Performance when played, relative to the average card that generation (Elo, ±1 SE)</h3><div id="m1"></div></div>
        <div><h3>Play rate among holders, relative to the average card (log ratio)</h3><div id="m2"></div></div>
      </div>
    </div>
  </div>

  <details>
    <summary>Table of highlighted cards</summary>
    <div class="tblwrap"><table id="tbl"></table></div>
  </details>

  <p class="foot">
    <b>Score</b> = <code>rel_delta + k × log(rate / rate_all)</code>, per window (plays pooled across the window's generations).
    <code>rel_delta</code> is the mean Elo change of players who played the card in the window, after removing corporation and starting-hand strength, minus the same for all card plays in the window.
    <code>rate</code> is the share of players holding the card unplayed who play it that generation; <code>rate_all</code> the same across all cards.
    The default k of __K__ gives the two terms equal spread across cards; the slider re-scores on the fly. A window counts when its plays reach the minimum, or when at least 20 times that many holder-generations exist, since the play rate is measured from holders. A card with too few plays in a window is drawn hollow, and its played delta is shrunk toward zero by <code>n / (n + 200)</code> so a noisy estimate cannot swing the score. Axes use an asinh scale, linear near zero and compressed beyond about ±1 Elo, so the four quadrants are equal in size.
    A strongly negative play-rate term early usually means the card's requirement is not met yet rather than that players decline it.
  </p>
</div>

<script>
const DATA = __DATA__;
const ALLG = __ALLG__;
const K0 = __K__;
const Q = [
  {id:"ge_gl", name:"Good early, good late", col:"var(--q3)", test:(e,l)=>e>0&&l>0},
  {id:"ge_bl", name:"Good early, bad late",  col:"var(--q1)", test:(e,l)=>e>0&&l<=0},
  {id:"be_gl", name:"Bad early, good late",  col:"var(--q2)", test:(e,l)=>e<=0&&l>0},
  {id:"be_bl", name:"Bad early, bad late",   col:"var(--q4)", test:(e,l)=>e<=0&&l<=0},
];
const state = {k:K0, minp:200, on:new Set(), sel:"Immigrant City", hover:null};
// axis transform: symmetric, compressed beyond ~1 Elo so quadrants are equal and the tails still fit
const C=0.6, T=v=>Math.asinh(v/C);
const f2 = v => (v>0?"+":"")+v.toFixed(2);
const fn = v => v.toLocaleString();
const quadOf = c => Q.find(q=>q.test(c.se,c.sl));
// fixed axis extents: scores are linear in k, so the widest values sit at the slider's ends (k=0 and k=1.5)
const EXT=(()=>{const base=DATA.filter(c=>c.e[0]!=null&&c.l[0]!=null&&c.e[2]!=null&&c.l[2]!=null&&(c.e[3]>=200||c.e[4]>=4000)&&(c.l[3]>=200||c.l[4]>=4000));
  const ex=[],ey=[]; [0,1.5].forEach(k=>base.forEach(c=>{ex.push(Math.abs(c.e[0]*c.e[3]/(c.e[3]+200)+k*c.e[2])); ey.push(Math.abs(c.l[0]*c.l[3]/(c.l[3]+200)+k*c.l[2]));}));
  return {x:Math.max(1.5,...ex)*1.08, y:Math.max(1.5,...ey)*1.08};})();

// a window counts when its plays OR its holder-generations clear the floor (the play-rate term
// is well measured from holders alone); a played delta from few plays is shrunk toward zero
const N0=200, HOLD=20;
const shrink=w=>w[0]==null?null:w[0]*w[3]/(w[3]+N0);
const winOK=w=>w[0]!=null&&w[2]!=null&&(w[3]>=state.minp||w[4]>=HOLD*state.minp);
function score(){
  DATA.forEach(c=>{
    c.de=shrink(c.e); c.dl=shrink(c.l);
    c.se = c.de==null?null:c.de+state.k*c.e[2];
    c.sl = c.dl==null?null:c.dl+state.k*c.l[2];
    c.thin = c.e[3]<state.minp || c.l[3]<state.minp;
    c.ok = c.se!=null && c.sl!=null && winOK(c.e) && winOK(c.l);
    c.q = c.ok?quadOf(c):null;
    c.vis = c.ok && (state.on.size===0 || state.on.has(c.q.id));
  });
}

// ---------- scatter ----------
const W=940,H=640,m={t:36,r:26,b:52,l:58};
const SX=v=>m.l+(T(v)-T(-EXT.x))/(T(EXT.x)-T(-EXT.x))*(W-m.l-m.r);
const SY=v=>m.t+(T(EXT.y)-T(v))/(T(EXT.y)-T(-EXT.y))*(H-m.t-m.b);
const maxN=Math.max(1,...DATA.map(c=>c.e[3]+c.l[3]));
const rad=c=>3.2+5.5*Math.sqrt((c.e[3]+c.l[3])/maxN);
const dotEl=new Map(); let svgEl,labelsEl,countEls={};
// static parts (axes, tints, labels) are built once; updates only move the dots
function buildScatter(){
  const x=SX,y=SY,xmin=-EXT.x,xmax=EXT.x,ymin=-EXT.y,ymax=EXT.y;
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Scatter of early score against late score for every card">`;
  const tint=(x0,x1,y0,y1,col)=>`<rect x="${x(x0)}" y="${y(y1)}" width="${x(x1)-x(x0)}" height="${y(y0)-y(y1)}" fill="${col}" opacity="var(--tint)"/>`;
  s+=tint(0,xmax,0,ymax,"var(--q3)")+tint(0,xmax,ymin,0,"var(--q1)")+tint(xmin,0,0,ymax,"var(--q2)")+tint(xmin,0,ymin,0,"var(--q4)");
  const TK=[-4,-2,-1,-0.5,0,0.5,1,2,4];
  TK.filter(v=>Math.abs(v)<EXT.x).forEach(v=>{
    s+=`<line class="${v===0?'zero':'gridline'}" x1="${x(v)}" x2="${x(v)}" y1="${m.t}" y2="${H-m.b}"/>`;
    s+=`<text class="tick" x="${x(v)}" y="${H-m.b+18}" text-anchor="middle">${v>0?'+':''}${v}</text>`;});
  TK.filter(v=>Math.abs(v)<EXT.y).forEach(v=>{
    s+=`<line class="${v===0?'zero':'gridline'}" x1="${m.l}" x2="${W-m.r}" y1="${y(v)}" y2="${y(v)}"/>`;
    s+=`<text class="tick" x="${m.l-10}" y="${y(v)+4}" text-anchor="end">${v>0?'+':''}${v}</text>`;});
  s+=`<text class="axlabel" x="${(m.l+W-m.r)/2}" y="${H-8}" text-anchor="middle">Early score, generations __EARLY__ (Elo, compressed beyond ±1)</text>`;
  s+=`<text class="axlabel" transform="translate(16 ${(m.t+H-m.b)/2}) rotate(-90)" text-anchor="middle">Late score, generations __LATE__ (Elo, compressed beyond ±1)</text>`;
  const ql=(tx,ty,anchor,name,id)=>`<text class="qlabel" x="${tx}" y="${ty}" text-anchor="${anchor}">${name}</text><text class="qsub" id="cnt_${id}" x="${tx}" y="${ty+15}" text-anchor="${anchor}"></text>`;
  s+=ql(W-m.r-8,m.t+16,"end","Good early, good late","ge_gl");
  s+=ql(W-m.r-8,H-m.b-22,"end","Good early, bad late","ge_bl");
  s+=ql(m.l+8,m.t+16,"start","Bad early, good late","be_gl");
  s+=ql(m.l+8,H-m.b-22,"start","Bad early, bad late","be_bl");
  s+=`<g id="dots"></g><g id="labels"></g></svg>`;
  const el=document.getElementById('scatter'); el.innerHTML=s;
  svgEl=el.firstElementChild; labelsEl=svgEl.querySelector('#labels');
  Q.forEach(q=>countEls[q.id]=svgEl.querySelector('#cnt_'+q.id));
  const g=svgEl.querySelector('#dots'), NS='http://www.w3.org/2000/svg';
  DATA.forEach(c=>{
    const d=document.createElementNS(NS,'circle'); d.setAttribute('r',rad(c)); d.dataset.c=c.c;
    const t=document.createElementNS(NS,'title'); t.textContent=c.c; d.appendChild(t);
    d.addEventListener('mousemove',e=>showTip(e,c.c)); d.addEventListener('mouseleave',hideTip);
    d.addEventListener('click',()=>select(c.c));
    dotEl.set(c.c,d); g.appendChild(d);
  });
}
const dotClass=c=>`dot${c.vis?'':' dim'}${c.c===state.sel?' sel':''}${c.thin?' thin':''}`;
function updateDots(){
  const g=svgEl.querySelector('#dots');
  // order: dimmed first, then highlighted, selected last, so the selected dot sits on top
  const order=DATA.filter(c=>c.ok).sort((a,b)=>(a.vis-b.vis)||((a.c===state.sel)-(b.c===state.sel)));
  const frag=document.createDocumentFragment();
  DATA.forEach(c=>{if(!c.ok) dotEl.get(c.c).style.display='none';});
  order.forEach(c=>{
    const d=dotEl.get(c.c);
    d.style.display=''; d.setAttribute('cx',SX(c.se)); d.setAttribute('cy',SY(c.sl)); d.setAttribute('fill',c.q.col);
    d.setAttribute('class',dotClass(c));
    if(c.thin) d.style.setProperty('--dc',c.q.col); else d.style.removeProperty('--dc');
    frag.appendChild(d);
  });
  g.appendChild(frag);
  Q.forEach(q=>countEls[q.id].textContent=`${order.filter(c=>c.q.id===q.id).length} cards`);
  updateLabels();
}
function updateLabels(){
  const vis=DATA.filter(c=>c.vis);
  const lab=[...vis].sort((a,b)=>(Math.abs(b.se)+Math.abs(b.sl))-(Math.abs(a.se)+Math.abs(a.sl))).slice(0,14);
  if(state.sel && !lab.some(c=>c.c===state.sel)){const sc=vis.find(c=>c.c===state.sel); if(sc) lab.push(sc);}
  // greedy collision pass: labels on the same side that overlap vertically get pushed down
  const L=lab.map(c=>({c,side:c.se>0?1:0,px:SX(c.se),py:SY(c.sl)+4,r:rad(c)})).sort((a,b)=>a.py-b.py);
  L.forEach(l=>l.py0=l.py);
  [0,1].forEach(side=>{let last=-1e9;L.filter(l=>l.side===side).forEach(l=>{if(l.py-last<13) l.py=last+13; last=l.py;});});
  // a label that would drift far from its dot is dropped rather than misplaced (the selected card always keeps its label)
  labelsEl.innerHTML=L.filter(l=>l.py-l.py0<=20||l.c.c===state.sel).map(l=>{const anchor=l.side?"end":"start", dx=l.side?-l.r-4:l.r+4;
    return `<text class="lbl" x="${l.px+dx}" y="${l.py}" text-anchor="${anchor}">${esc(l.c.c)}</text>`;}).join('');
}
function drawScatter(){ if(!svgEl) buildScatter(); updateDots(); }
const enc=s=>s.replace(/"/g,'&quot;'); const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
const tip=document.getElementById('tip');
function showTip(e,name){
  const c=DATA.find(d=>d.c===name); if(!c) return;
  const card=e.currentTarget.closest('.card')||document.getElementById('scatter').parentElement;
  tip.innerHTML=`<b>${esc(c.c)}</b><div style="color:${c.q.col};font-size:11.5px;margin-bottom:4px">${c.q.name}</div>`+
    `<div class="r"><span>Early score</span><span>${f2(c.se)}</span></div>`+
    `<div class="r"><span>&nbsp;&nbsp;when played</span><span>${f2(c.e[0])} ± ${c.e[1].toFixed(2)}</span></div>`+
    `<div class="r"><span>&nbsp;&nbsp;play rate ×</span><span>${Math.exp(c.e[2]).toFixed(2)} (n ${fn(c.e[3])})</span></div>`+
    `<div class="r"><span>Late score</span><span>${f2(c.sl)}</span></div>`+
    `<div class="r"><span>&nbsp;&nbsp;when played</span><span>${f2(c.l[0])} ± ${c.l[1].toFixed(2)}</span></div>`+
    `<div class="r"><span>&nbsp;&nbsp;play rate ×</span><span>${Math.exp(c.l[2]).toFixed(2)} (n ${fn(c.l[3])})</span></div>`+
    (c.thin?`<div style="color:var(--muted);margin-top:3px">Few plays in one window: delta shrunk toward 0</div>`:'');
  tip.style.display='block';
  const cr=card.getBoundingClientRect();
  let left=e.clientX-cr.left+14, top=e.clientY-cr.top-10;
  if(left+tip.offsetWidth>cr.width-8) left=e.clientX-cr.left-tip.offsetWidth-14;
  tip.style.left=left+'px'; tip.style.top=top+'px';
}
function hideTip(){tip.style.display='none';}

// ---------- detail ----------
function drawDetail(){
  const c=DATA.find(d=>d.c===state.sel);
  const dc=document.getElementById('detailcard');
  if(!c){dc.hidden=true;return;} dc.hidden=false;
  document.getElementById('dname').textContent=c.c;
  const q=c.se!=null&&c.sl!=null?quadOf(c):null;
  document.getElementById('dq').innerHTML=q?`<i style="background:${q.col}"></i>${q.name}${c.ok?(c.thin?' (hollow dot: few plays in one window, delta shrunk)':''):' (too few plays and holders, not plotted)'}`:'Not enough plays in one window';
  const st=document.getElementById('dstats');
  const row=(h,a,b)=>`<div class="h">${h}</div><div class="v">${a}</div><div class="v">${b}</div>`;
  st.innerHTML=row('', 'Early __EARLY__', 'Late __LATE__')+
    row('Score', c.se==null?'–':f2(c.se), c.sl==null?'–':f2(c.sl))+
    row('When played', c.e[0]==null?'–':`${f2(c.e[0])} ± ${c.e[1].toFixed(2)}`, c.l[0]==null?'–':`${f2(c.l[0])} ± ${c.l[1].toFixed(2)}`)+
    (c.thin?row('Shrunk (used)', c.de==null?'–':f2(c.de), c.dl==null?'–':f2(c.dl)):'')+
    row('Play rate vs avg', c.e[2]==null?'–':`×${Math.exp(c.e[2]).toFixed(2)}`, c.l[2]==null?'–':`×${Math.exp(c.l[2]).toFixed(2)}`)+
    row('Plays', fn(c.e[3]), fn(c.l[3]))+
    row('Holder-gens', fn(c.e[4]), fn(c.l[4]));
  // mini charts
  const pts=c.g.filter(p=>p[1]!=null&&p[4]>=30);
  document.getElementById('m1').innerHTML=miniLine(pts.map(p=>({g:p[0],v:p[1],se:p[2]})),true);
  document.getElementById('m2').innerHTML=miniLine(c.g.filter(p=>p[3]!=null&&p[5]>=100).map(p=>({g:p[0],v:p[3],se:0})),false);
}
function miniLine(pts,band){
  const W=440,H=200,m={t:12,r:12,b:30,l:40};
  if(!pts.length) return `<div class="foot">Not enough plays</div>`;
  const vals=pts.flatMap(p=>[p.v+p.se,p.v-p.se]);
  let lo=Math.min(0,...vals), hi=Math.max(0,...vals); const pad=(hi-lo)*0.12||0.5; lo-=pad; hi+=pad;
  const x=g=>m.l+(g-1)/11*(W-m.l-m.r), y=v=>m.t+(hi-v)/(hi-lo)*(H-m.t-m.b);
  let s=`<svg viewBox="0 0 ${W} ${H}">`;
  const span=hi-lo, step=span>4?1:span>2?0.5:span>1?0.25:0.1;
  for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step){const vv=Math.round(v*1000)/1000;
    s+=`<line class="${Math.abs(vv)<1e-9?'zero':'gridline'}" x1="${m.l}" x2="${W-m.r}" y1="${y(vv)}" y2="${y(vv)}"/><text class="tick" x="${m.l-6}" y="${y(vv)+4}" text-anchor="end">${vv>0?'+':''}${vv.toFixed(step<0.5?2:1)}</text>`;}
  for(let g=1;g<=12;g++) s+=`<text class="tick" x="${x(g)}" y="${H-m.b+16}" text-anchor="middle">${g}</text>`;
  s+=`<text class="axlabel" x="${(m.l+W-m.r)/2}" y="${H-2}" text-anchor="middle">Generation played</text>`;
  // window shading
  s+=`<rect x="${x(1)-8}" y="${m.t}" width="${x(4)-x(1)+16}" height="${H-m.t-m.b}" fill="var(--ink)" opacity="0.035"/>`;
  s+=`<rect x="${x(9)-8}" y="${m.t}" width="${x(12)-x(9)+16}" height="${H-m.t-m.b}" fill="var(--ink)" opacity="0.035"/>`;
  const col=band?'var(--q1)':'var(--q2)';
  if(band){const up=pts.map(p=>`${x(p.g)},${y(p.v+p.se)}`).join(' '), dn=[...pts].reverse().map(p=>`${x(p.g)},${y(p.v-p.se)}`).join(' ');
    s+=`<polygon points="${up} ${dn}" fill="${col}" opacity="0.13"/>`;}
  s+=`<polyline class="line" stroke="${col}" points="${pts.map(p=>`${x(p.g)},${y(p.v)}`).join(' ')}"/>`;
  pts.forEach(p=>{s+=`<circle class="mdot" cx="${x(p.g)}" cy="${y(p.v)}" r="3.5" fill="${col}"><title>Gen ${p.g}: ${f2(p.v)}</title></circle>`;});
  return s+`</svg>`;
}

// ---------- table ----------
let sortKey='se', sortDir=-1;
const COLS=[["c","Card",c=>c.c],["q","Quadrant",c=>c.q.name],["se","Early score",c=>c.se],["e0","Early when played",c=>c.de],["e2","Early play rate ×",c=>Math.exp(c.e[2])],["e3","Early plays",c=>c.e[3]],
            ["sl","Late score",c=>c.sl],["l0","Late when played",c=>c.dl],["l2","Late play rate ×",c=>Math.exp(c.l[2])],["l3","Late plays",c=>c.l[3]]];
function drawTable(){
  const vis=DATA.filter(c=>c.vis);
  const get=Object.fromEntries(COLS.map(([k,,f])=>[k,f]));
  vis.sort((a,b)=>{const va=get[sortKey](a),vb=get[sortKey](b);return (typeof va==='string'?va.localeCompare(vb):va-vb)*sortDir;});
  const t=document.getElementById('tbl');
  t.innerHTML=`<tr>${COLS.map(([k,h])=>`<th data-k="${k}" class="${k===sortKey?'on':''}">${h}${k===sortKey?(sortDir<0?' ↓':' ↑'):''}</th>`).join('')}</tr>`+
    vis.map(c=>`<tr><td class="name" data-c="${enc(c.c)}"><i style="background:${c.q.col}"></i>${esc(c.c)}</td><td>${c.q.name}</td><td>${f2(c.se)}</td><td>${f2(c.de)}</td><td>${Math.exp(c.e[2]).toFixed(2)}</td><td>${fn(c.e[3])}</td><td>${f2(c.sl)}</td><td>${f2(c.dl)}</td><td>${Math.exp(c.l[2]).toFixed(2)}</td><td>${fn(c.l[3])}</td></tr>`).join('');
  t.querySelectorAll('th').forEach(th=>th.addEventListener('click',()=>{const k=th.dataset.k; if(sortKey===k) sortDir*=-1; else {sortKey=k; sortDir=(k==='c'||k==='q')?1:-1;} drawTable();}));
  t.querySelectorAll('td.name').forEach(td=>td.addEventListener('click',()=>{select(td.dataset.c); document.getElementById('scatter').scrollIntoView({behavior:'smooth',block:'nearest'});}));
}

// ---------- wiring ----------
function select(name){
  const prev=state.sel; state.sel=name;
  [prev,name].forEach(n=>{const c=DATA.find(d=>d.c===n), d=dotEl.get(n); if(d&&c&&c.ok) d.setAttribute('class',dotClass(c));});
  const d=dotEl.get(name); if(d) d.parentNode.appendChild(d);
  updateLabels(); drawDetail();
}
let tableTimer=null;
function render(){score(); drawScatter(); drawDetail(); clearTimeout(tableTimer); tableTimer=setTimeout(drawTable,250);}
let raf=null;
function renderSoon(){ if(raf) return; raf=requestAnimationFrame(()=>{raf=null; render();}); }
const kin=document.getElementById('k'), kv=document.getElementById('kv');
kin.value=K0.toFixed(2); kv.textContent='= '+K0.toFixed(2);
kin.addEventListener('input',()=>{state.k=+kin.value; kv.textContent='= '+state.k.toFixed(2); renderSoon();});
document.getElementById('minp').addEventListener('change',e=>{state.minp=+e.target.value; render();});
const chips=document.getElementById('chips');
Q.forEach(q=>{const b=document.createElement('button'); b.className='chip'; b.type='button'; b.dataset.id=q.id; b.setAttribute('aria-pressed','false'); b.innerHTML=`<i style="background:${q.col}"></i>${q.name}`;
  b.addEventListener('click',()=>{if(state.on.has(q.id)) state.on.delete(q.id); else state.on.add(q.id); b.setAttribute('aria-pressed',String(state.on.has(q.id))); render();}); chips.appendChild(b);});
const dl=document.getElementById('cardlist'); [...DATA].sort((a,b)=>a.c.localeCompare(b.c)).forEach(c=>{const o=document.createElement('option'); o.value=c.c; dl.appendChild(o);});
document.getElementById('q').addEventListener('change',e=>{const c=DATA.find(d=>d.c.toLowerCase()===e.target.value.trim().toLowerCase()); if(c) select(c.c);});
try{const k=localStorage.getItem('ctm_k'); if(k) {state.k=+k; kin.value=state.k.toFixed(2); kv.textContent='= '+state.k.toFixed(2);} }catch(e){}
kin.addEventListener('change',()=>{try{localStorage.setItem('ctm_k',kin.value);}catch(e){}});
render();
</script>
"""
html = (html.replace("__DATA__", json.dumps(data, separators=(",", ":")))
            .replace("__ALLG__", json.dumps(allg))
            .replace("__K__", f"{K:.2f}")
            .replace("__EARLY__", EARLY).replace("__LATE__", LATE)
            .replace("__NCARDS__", f"{n_cards:,}").replace("__NPLAYS__", f"{n_plays:,}"))
out.write_text(html, encoding="utf-8")
print(f"Wrote {out} ({out.stat().st_size/1024:.0f} KB), k = {K:.3f}")
