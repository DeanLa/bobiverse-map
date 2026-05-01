const DATA = await fetch('./data.json').then(r => r.json());
const CHAPTERS = DATA.chapters;
const ALL_STARS = DATA.stars;
const ALL_BOBS = DATA.bobs;
const ALL_TRAVELS = DATA.travels;
const ALL_EVENTS = DATA.events;

// ── New richer data fields ─────────────────────────────────────────────────────
const ALL_TECH = DATA.technologies || [];
const ALL_COMMS = DATA.communications || [];
const ALL_COMBAT = DATA.combat || [];
const ALL_FACTIONS = DATA.factions || [];
const ALL_FACTION_EVENTS = DATA.faction_events || [];
const ALL_SPECIES = DATA.alien_species || [];
const ALL_INFRA = DATA.infrastructure || [];
const ALL_THREADS = DATA.threads || [];
const ALL_QUOTES = DATA.quotes || [];
const ALL_PLOT_ARCS = DATA.plot_arcs || [];
const CHAR_ARCS = DATA.character_arcs || {};
const THEMES_BY_CH = DATA.themes_by_chapter || {};
const SCENES_BY_CH = DATA.scenes_by_chapter || {};
const ALL_THREATS = DATA.incoming_threats || [];

// ── Scope filtering ───────────────────────────────────────────────────────────
let scopeBook = 3;
let scopeMaxYear = 2263.9;
let scopeMaxChapter = 999;
let commsEnabled = true;

// Filtered working copies
let STARS, BOBS, TRAVELS, EVENTS;
let TECH, COMMS, COMBAT, SPECIES, QUOTES, ARCS;

function inScope(record) {
  // book + chapter (if chapter present) + year
  if (record.book > scopeBook) return false;
  if (record.chapter !== undefined && record.chapter !== null && record.chapter > scopeMaxChapter && record.book === scopeBook) return false;
  return true;
}

function applyScope() {
  // Filter events by book and maxYear; sort by year, breaking ties by chapter
  // so within-year-cluster ordering matches reading order.
  EVENTS = ALL_EVENTS.filter(function(e) { return inScope(e) && e.year <= scopeMaxYear; })
    .sort(function(a, b) {
      if (a.year !== b.year) return a.year - b.year;
      return (a.chapter || 0) - (b.chapter || 0);
    });

  // Filter bobs
  BOBS = {};
  for (var id in ALL_BOBS) {
    var b = ALL_BOBS[id];
    if (b.book <= scopeBook && b.created <= scopeMaxYear) BOBS[id] = b;
  }

  // Filter travels
  TRAVELS = ALL_TRAVELS.filter(function(t) { return t.book <= scopeBook && t.depart <= scopeMaxYear; });

  // Collect referenced star systems
  var usedStars = new Set(["Sol"]);
  for (var id in BOBS) usedStars.add(BOBS[id].at);
  TRAVELS.forEach(function(t) { usedStars.add(t.from); usedStars.add(t.to); });
  STARS = {};
  for (var id in ALL_STARS) { if (usedStars.has(id)) STARS[id] = ALL_STARS[id]; }

  // New collections
  TECH = ALL_TECH.filter(function(t) {
    return t.book <= scopeBook && (t.first_mentioned_chapter === null || t.first_mentioned_chapter === undefined || t.first_mentioned_chapter <= scopeMaxChapter || t.book < scopeBook);
  });
  COMMS = ALL_COMMS.filter(function(c) {
    return c.book <= scopeBook && (c.sent_chapter === null || c.sent_chapter === undefined || c.sent_chapter <= scopeMaxChapter || c.book < scopeBook);
  });
  COMBAT = ALL_COMBAT.filter(function(c) {
    return c.book <= scopeBook && (c.chapter <= scopeMaxChapter || c.book < scopeBook);
  });
  SPECIES = ALL_SPECIES.filter(function(s) {
    return s.book <= scopeBook && (s.first_chapter <= scopeMaxChapter || s.book < scopeBook);
  });
  QUOTES = ALL_QUOTES.filter(function(q) {
    return q.book <= scopeBook && (q.chapter <= scopeMaxChapter || q.book < scopeBook);
  });
  ARCS = ALL_PLOT_ARCS.filter(function(a) {
    return a.book <= scopeBook;
  });

  // Update slider
  var minEvt = 2133, maxEvt = scopeMaxYear;
  slider.min = minEvt;
  slider.max = maxEvt;
  if (parseFloat(slider.value) > maxEvt) slider.value = maxEvt;
  if (parseFloat(slider.value) < minEvt) slider.value = minEvt;
}

// ── Branch colors ─────────────────────────────────────────────────────────────
var BRANCH_HUES = {
  "Bob": [45,90,75], "Bill": [210,70,65], "Riker": [150,60,60], "Milo": [280,55,65],
  "Mario": [20,75,65], "Marvin": [320,50,60], "Luke": [60,60,55], "Bender": [190,50,55],
  "Khan": [35,65,55], "Pete": [340,45,60], "Victor": [100,45,55]
};

function getBranch(bobId) {
  var bob = ALL_BOBS[bobId];
  if (!bob || !bob.parent) return bobId;
  if (bob.parent === "Bob") return bobId;
  // Sub-branches that get their own color family
  if (BRANCH_HUES[bobId]) return bobId;
  return getBranch(bob.parent);
}

function getBobColor(bobId) {
  if (bobId === "Bob") return "hsl(45, 90%, 75%)";

  var branch = getBranch(bobId);
  var hue = BRANCH_HUES[branch] || [0, 50, 60];
  var bob = ALL_BOBS[bobId];
  var genOff = Math.min((bob.gen - 2) * 10, 40);
  return "hsl(" + (hue[0] + genOff) + ", " + hue[1] + "%, " + Math.min(hue[2] + genOff * 0.4, 85) + "%)";
}

var bobColors = {};
for (var id in ALL_BOBS) bobColors[id] = getBobColor(id);

// ── 3D projection ────────────────────────────────────────────────────────────
function starTo3D(star) {
  var ra = star.ra_h * (Math.PI / 12);
  var dec = star.dec_deg * (Math.PI / 180);
  var d = star.distance_ly;
  return { x: d * Math.cos(dec) * Math.cos(ra), y: d * Math.cos(dec) * Math.sin(ra), z: d * Math.sin(dec) };
}

var starPos3D = {};
for (var id in ALL_STARS) starPos3D[id] = starTo3D(ALL_STARS[id]);

// Custom layout: hand-tuned normalized positions (0-1) for better screen use
var customLayout = {
  "Sol":              { x: 0.50, y: 0.12 },
  "Epsilon Eridani":  { x: 0.42, y: 0.32 },
  "Delta Eridani":    { x: 0.58, y: 0.42 },
  "Omicron2 Eridani": { x: 0.30, y: 0.48 },
  "Alpha Centauri":   { x: 0.72, y: 0.20 },
  "82 Eridani":       { x: 0.22, y: 0.68 },
  "Beta Hydri":       { x: 0.12, y: 0.85 },
  "Epsilon Indi":     { x: 0.82, y: 0.35 },
  "Eta Cassiopeiae":  { x: 0.88, y: 0.08 },
  "Kappa Ceti":       { x: 0.62, y: 0.14 },
  "Gamma Leporis A":  { x: 0.35, y: 0.58 },
  "GL 877":           { x: 0.08, y: 0.55 },
  "Gliese 54":        { x: 0.15, y: 0.40 },
  "Delta Pavonis":    { x: 0.78, y: 0.72 },
  "Gamma Pavonis":    { x: 0.88, y: 0.60 },
  "HIP 14101":        { x: 0.48, y: 0.58 },
  "HIP 84051":        { x: 0.75, y: 0.88 },
  "Ragnarok":         { x: 0.38, y: 0.18 },
  "Odin":             { x: 0.25, y: 0.28 },
  "Zeta Tucanae":     { x: 0.05, y: 0.72 },
  "Pi3 Orionis":      { x: 0.52, y: 0.72 }
};

var layoutMode = 'spread'; // 'realistic' or 'spread'

// ── Canvas ────────────────────────────────────────────────────────────────────
var canvas = document.getElementById('canvas');
var ctx = canvas.getContext('2d');
var W, H, mapScale, offsetX, offsetY;

function resize() {
  var container = document.getElementById('map-container');
  W = container.clientWidth;
  H = container.clientHeight;
  canvas.width = W * devicePixelRatio;
  canvas.height = H * devicePixelRatio;
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  fitView();
}

function fitView() {
  if (layoutMode === 'spread') {
    mapScale = 1; offsetX = 0; offsetY = 0;
    return;
  }
  var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (var id in STARS) {
    var p = starPos3D[id];
    if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
  }
  var pad = 70;
  var rangeX = maxX - minX || 1, rangeY = maxY - minY || 1;
  mapScale = Math.min((W - pad * 2) / rangeX, (H - pad * 2) / rangeY);
  offsetX = W / 2 - (minX + maxX) / 2 * mapScale;
  offsetY = H / 2 + (minY + maxY) / 2 * mapScale;
}

function project(x3d, y3d) { return { x: x3d * mapScale + offsetX, y: -y3d * mapScale + offsetY }; }
function projectStar(starId) {
  if (layoutMode === 'spread') {
    var c = customLayout[starId];
    if (c) {
      var pad = 60;
      return { x: pad + c.x * (W - pad * 2), y: pad + c.y * (H - pad * 2) };
    }
  }
  var p = starPos3D[starId]; return project(p.x, p.y);
}

// ── Bob position ──────────────────────────────────────────────────────────────
function getBobPosition(bobId, year) {
  var bob = BOBS[bobId];
  if (!bob || year < bob.created) return null;
  if (bob.destroyed && year > bob.destroyed) return null;
  for (var i = 0; i < TRAVELS.length; i++) {
    var t = TRAVELS[i];
    if (t.bob !== bobId) continue;
    if (year >= t.depart && year <= t.arrive) {
      var frac = (year - t.depart) / (t.arrive - t.depart);
      var fromP = projectStar(t.from), toP = projectStar(t.to);
      if (!fromP || !toP) continue;
      return { x: fromP.x + (toP.x - fromP.x) * frac, y: fromP.y + (toP.y - fromP.y) * frac };
    }
  }
  var lastSys = bob.at, lastArr = bob.created;
  for (var i = 0; i < TRAVELS.length; i++) {
    var t = TRAVELS[i];
    if (t.bob !== bobId || t.arrive > year) continue;
    if (t.arrive > lastArr) { lastSys = t.to; lastArr = t.arrive; }
  }
  if (!STARS[lastSys]) return null;
  return projectStar(lastSys);
}

function isTraveling(bobId, year) {
  for (var i = 0; i < TRAVELS.length; i++) {
    var t = TRAVELS[i];
    if (t.bob === bobId && year >= t.depart && year <= t.arrive) return t;
  }
  return null;
}

// ── Background stars ──────────────────────────────────────────────────────────
var bgStars = [];
for (var i = 0; i < 150; i++) bgStars.push({
  xf: Math.sin(i * 127.1 + 0.5) * 0.5 + 0.5,
  yf: Math.sin(i * 311.7 + 0.3) * 0.5 + 0.5,
  br: 0.06 + (Math.sin(i * 73.3) * 0.5 + 0.5) * 0.14
});

// ── Draw ──────────────────────────────────────────────────────────────────────
function draw(year) {
  ctx.clearRect(0, 0, W, H);
  for (var i = 0; i < bgStars.length; i++) {
    var s = bgStars[i];
    ctx.fillStyle = "rgba(140,160,200," + s.br + ")";
    ctx.fillRect(s.xf * W, s.yf * H, 1, 1);
  }

  // Travel dashed lines
  ctx.save(); ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
  for (var i = 0; i < TRAVELS.length; i++) {
    var t = TRAVELS[i];
    if (year < t.depart || year > t.arrive) continue;
    var c = bobColors[t.bob]; if (!c) continue;
    var fromP = projectStar(t.from), toP = projectStar(t.to);
    if (!fromP || !toP) continue;
    ctx.strokeStyle = c.replace("hsl(", "hsla(").replace(")", ", 0.3)");
    ctx.beginPath(); ctx.moveTo(fromP.x, fromP.y); ctx.lineTo(toP.x, toP.y); ctx.stroke();
  }
  ctx.setLineDash([]); ctx.restore();

  // Light-speed communication dots (radio messages in flight)
  if (commsEnabled) {
    for (var ci = 0; ci < COMMS.length; ci++) {
      var co = COMMS[ci];
      if (co.sent_year === null || co.received_year === null) continue;
      if (co.lag_years === null || co.lag_years <= 0.05) continue;  // skip instant
      if (year < co.sent_year || year > co.received_year) continue;
      var fp = projectStar(co.from_system), tp = projectStar(co.to_system);
      if (!fp || !tp) continue;
      var frac = (year - co.sent_year) / (co.received_year - co.sent_year);
      var x = fp.x + (tp.x - fp.x) * frac;
      var y2 = fp.y + (tp.y - fp.y) * frac;
      // Faint tail
      ctx.strokeStyle = 'rgba(136, 200, 200, 0.18)';
      ctx.lineWidth = 0.5;
      ctx.beginPath(); ctx.moveTo(fp.x, fp.y); ctx.lineTo(tp.x, tp.y); ctx.stroke();
      // Glow + dot
      var grad = ctx.createRadialGradient(x, y2, 0, x, y2, 6);
      grad.addColorStop(0, 'rgba(136, 240, 240, 0.9)');
      grad.addColorStop(1, 'rgba(136, 240, 240, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(x, y2, 6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#aafffa';
      ctx.beginPath(); ctx.arc(x, y2, 1.6, 0, Math.PI * 2); ctx.fill();
    }
  }

  // Stars
  for (var id in STARS) {
    var p = projectStar(id);
    var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, 18);
    grad.addColorStop(0, 'rgba(100,140,220,0.12)'); grad.addColorStop(1, 'rgba(100,140,220,0)');
    ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(p.x, p.y, 18, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#5a7aaa'; ctx.beginPath(); ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#3a5070'; ctx.font = '9px Consolas, Monaco, monospace'; ctx.textAlign = 'center';
    ctx.fillText(STARS[id].name, p.x, p.y + 16);
  }

  // Bobs
  var bobs = [];
  for (var id in BOBS) {
    var pos = getBobPosition(id, year); if (!pos) continue;
    var grp = BOBS[id].group || 0;
    bobs.push({ id: id, x: pos.x, y: pos.y, traveling: isTraveling(id, year), color: bobColors[id], group: grp });
  }
  // Cluster
  var clusters = [], used = {};
  for (var i = 0; i < bobs.length; i++) {
    if (used[i]) continue;
    var cl = [bobs[i]]; used[i] = true;
    for (var j = i + 1; j < bobs.length; j++) {
      if (used[j]) continue;
      var dx = bobs[i].x - bobs[j].x, dy = bobs[i].y - bobs[j].y;
      if (Math.sqrt(dx * dx + dy * dy) < 20) { cl.push(bobs[j]); used[j] = true; }
    }
    clusters.push(cl);
  }
  for (var ci = 0; ci < clusters.length; ci++) {
    var cl = clusters[ci];
    for (var i = 0; i < cl.length; i++) {
      var b = cl[i];
      var r = b.group ? 7 : 5;
      ctx.fillStyle = b.color; ctx.beginPath(); ctx.arc(b.x, b.y, r, 0, Math.PI * 2); ctx.fill();
      if (b.group) {
        // Draw count inside the larger dot
        ctx.fillStyle = '#0a0e1a'; ctx.font = 'bold 8px Consolas, Monaco, monospace'; ctx.textAlign = 'center';
        ctx.fillText('+' + b.group, b.x, b.y + 3);
      }
      if (b.traveling) { ctx.strokeStyle = b.color; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(b.x, b.y, r + 2, 0, Math.PI * 2); ctx.stroke(); }
    }
    var cx = cl[0].x, cy = cl[0].y;
    ctx.font = '10px Consolas, Monaco, monospace'; ctx.textAlign = 'left';
    var startY = cy - (cl.length - 1) * 6;
    for (var i = 0; i < cl.length; i++) {
      ctx.fillStyle = cl[i].color;
      var label = cl[i].id + (cl[i].traveling ? ' >>' : '');
      ctx.fillText(label, cx + 10, startY + i * 13);
    }
  }
}

// ── Event log ─────────────────────────────────────────────────────────────────
var eventLog = document.getElementById('event-log');
var eventEls = [];

function buildEventLog() {
  eventLog.textContent = '';
  eventEls = [];
  _evScroll.current = -1;
  // Spread events that share the same year_precise (multiple chapters all
  // landing in the same month) so they fire sequentially as the slider sweeps
  // through. Spread scales with cluster size and is bounded by the distance
  // to neighboring distinct years so it never overlaps adjacent clusters.
  var effectiveYears = new Array(EVENTS.length);
  var i = 0;
  while (i < EVENTS.length) {
    var year = EVENTS[i].year;
    var j = i;
    while (j < EVENTS.length && EVENTS[j].year === year) j++;
    var size = j - i;
    if (size === 1) {
      effectiveYears[i] = year;
    } else {
      var prevYear = i > 0 ? EVENTS[i - 1].year : year - 1;
      var nextYear = j < EVENTS.length ? EVENTS[j].year : year + 1;
      // Spread up to 80% of the smaller gap to a neighbor; scale with cluster size.
      var maxSpread = Math.min(year - prevYear, nextYear - year) * 0.8;
      var desiredSpread = Math.min(0.5, 0.07 * size);  // 7% of a year per event, cap 0.5
      var spread = Math.min(desiredSpread, maxSpread);
      for (var k = 0; k < size; k++) {
        effectiveYears[i + k] = year + (k / (size - 1) - 0.5) * spread;
      }
    }
    i = j;
  }

  for (var i = 0; i < EVENTS.length; i++) {
    var ev = EVENTS[i];
    var el = document.createElement('div');
    el.className = 'event-item';
    var ys = document.createElement('span'); ys.className = 'event-year'; ys.textContent = Math.floor(ev.year); el.appendChild(ys);
    if (ev.destroyed) {
      var ds = document.createElement('span'); ds.className = 'event-destroyed'; ds.textContent = ev.text; el.appendChild(ds);
    } else if (ev.bob) {
      var bs = document.createElement('span'); bs.className = 'event-bob'; bs.textContent = ev.bob + ': '; el.appendChild(bs);
      el.appendChild(document.createTextNode(ev.text));
    } else {
      el.appendChild(document.createTextNode(ev.text));
    }
    eventLog.appendChild(el);
    eventEls.push({ el: el, year: effectiveYears[i] });
  }
}

// Smooth proximity-weighted intensity:
// - Events fade IN over the last 0.4 years before they fire (so they "approach")
// - Events fade OUT over ~6 years after firing (so the recent past stays warm)
// - Beyond those windows, items collapse to deep dim ("future")
// Inline styles are set per item; CSS holds only the future/default color.
//
var _evScroll = { current: -1, target: 0 };
function updateEventLog(year) {
  var FADE_IN = 0.4;
  var FADE_OUT = 6.0;
  for (var i = 0; i < eventEls.length; i++) {
    var item = eventEls[i];
    var delta = year - item.year;
    var intensity = 0;
    if (delta >= 0) {
      intensity = Math.max(0, 1 - delta / FADE_OUT);
    } else if (delta > -FADE_IN) {
      intensity = 1 + delta / FADE_IN;
    }
    intensity = intensity * intensity * (3 - 2 * intensity);  // smoothstep

    var el = item.el;
    if (delta < -FADE_IN) {
      el.style.color = '';
      el.style.backgroundColor = '';
      el.style.borderLeftColor = '';
    } else {
      var r = Math.round(74 + 158 * intensity);
      var g = Math.round(80 + 152 * intensity);
      var b = Math.round(104 + 128 * intensity);
      el.style.color = 'rgb(' + r + ',' + g + ',' + b + ')';
      el.style.backgroundColor = 'rgba(20, 26, 48, ' + (intensity * 0.7).toFixed(2) + ')';
      el.style.borderLeftColor = 'rgba(224, 200, 120, ' + intensity.toFixed(2) + ')';
    }
  }

  // Continuous scroll: find fractional event index for `year`, then lerp
  // scrollTop toward the target so jumps (slider drag, arrow keys) feel smooth.
  if (eventEls.length === 0) return;
  var idx;
  if (year <= eventEls[0].year) {
    idx = 0;
  } else if (year >= eventEls[eventEls.length - 1].year) {
    idx = eventEls.length - 1;
  } else {
    var lo = 0, hi = eventEls.length - 1;
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (eventEls[mid].year <= year) lo = mid; else hi = mid;
    }
    var span = eventEls[hi].year - eventEls[lo].year;
    var frac = span > 0 ? (year - eventEls[lo].year) / span : 0;
    idx = lo + frac;
  }
  var floor = Math.floor(idx);
  var ceil = Math.min(floor + 1, eventEls.length - 1);
  var f = idx - floor;
  var topFloor = eventEls[floor].el.offsetTop;
  var topCeil = eventEls[ceil].el.offsetTop;
  var pxTarget = topFloor + (topCeil - topFloor) * f;
  _evScroll.target = Math.max(0, pxTarget - eventLog.clientHeight * 0.5);
  if (_evScroll.current < 0) {
    _evScroll.current = _evScroll.target;
  } else {
    _evScroll.current += (_evScroll.target - _evScroll.current) * 0.13;
  }
  eventLog.scrollTop = _evScroll.current;
}

// ── Legend ─────────────────────────────────────────────────────────────────────
function buildLegend() {
  var legend = document.getElementById('legend');
  legend.textContent = '';
  var branches = ["Bob", "Bill", "Riker", "Khan", "Milo", "Mario"];
  for (var i = 0; i < branches.length; i++) {
    if (!BOBS[branches[i]]) continue;
    var item = document.createElement('div'); item.className = 'legend-item';
    var dot = document.createElement('span'); dot.className = 'legend-dot'; dot.style.background = bobColors[branches[i]];
    item.appendChild(dot); item.appendChild(document.createTextNode(branches[i]));
    legend.appendChild(item);
  }
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
var tooltip = document.getElementById('tooltip');
canvas.addEventListener('mousemove', function(e) {
  var rect = canvas.getBoundingClientRect();
  var mx = e.clientX - rect.left, my = e.clientY - rect.top;
  var year = parseFloat(slider.value);
  var found = null;
  for (var id in BOBS) {
    var pos = getBobPosition(id, year); if (!pos) continue;
    if ((mx - pos.x) * (mx - pos.x) + (my - pos.y) * (my - pos.y) < 144) { found = id; break; }
  }
  var foundStar = null;
  if (!found) for (var id in STARS) {
    var p = projectStar(id);
    if ((mx - p.x) * (mx - p.x) + (my - p.y) * (my - p.y) < 256) { foundStar = id; break; }
  }
  if (found) {
    var bob = BOBS[found], travel = isTraveling(found, year);
    tooltip.textContent = '';
    var nd = document.createElement('div'); nd.style.color = bobColors[found]; nd.style.fontWeight = 'bold'; nd.textContent = found; tooltip.appendChild(nd);
    var infoText = bob.group ? 'Unnamed group of ' + bob.group : 'Gen ' + bob.gen + ' | Parent: ' + (bob.parent || 'Original');
    var id2 = document.createElement('div'); id2.style.color = '#8090b0'; id2.textContent = infoText; tooltip.appendChild(id2);
    if (travel) { var td = document.createElement('div'); td.style.color = '#8090b0'; td.textContent = 'In transit: ' + travel.from + ' -> ' + travel.to; tooltip.appendChild(td); }
    if (bob.destroyed) { var dd = document.createElement('div'); dd.style.color = '#e07878'; dd.textContent = 'Destroyed: ' + Math.floor(bob.destroyed); tooltip.appendChild(dd); }
    tooltip.style.display = 'block'; tooltip.style.left = (mx + 14) + 'px'; tooltip.style.top = (my - 10) + 'px';
  } else if (foundStar) {
    var star = STARS[foundStar]; tooltip.textContent = '';
    var sn = document.createElement('div'); sn.style.color = '#e0c878'; sn.style.fontWeight = 'bold'; sn.textContent = star.name; tooltip.appendChild(sn);
    var sd = document.createElement('div'); sd.style.color = '#8090b0'; sd.textContent = star.distance_ly + ' ly from Sol'; tooltip.appendChild(sd);
    var bobsHere = [], sp = projectStar(foundStar);
    for (var id in BOBS) { var pos = getBobPosition(id, year); if (!pos) continue; if ((pos.x - sp.x) * (pos.x - sp.x) + (pos.y - sp.y) * (pos.y - sp.y) < 100 && !isTraveling(id, year)) bobsHere.push(id); }
    if (bobsHere.length) { var bd = document.createElement('div'); bd.style.color = '#8090b0'; bd.textContent = 'Bobs: ' + bobsHere.join(', '); tooltip.appendChild(bd); }
    tooltip.style.display = 'block'; tooltip.style.left = (mx + 14) + 'px'; tooltip.style.top = (my - 10) + 'px';
  } else tooltip.style.display = 'none';
});
canvas.addEventListener('mouseleave', function() { tooltip.style.display = 'none'; });

// ── Playback ──────────────────────────────────────────────────────────────────
var slider = document.getElementById('slider');
var yearDisplay = document.getElementById('year-display');
var playBtn = document.getElementById('play-btn');
var speedDisplay = document.getElementById('speed-display');
var playing = false, speed = 2, lastTime = null;

function update(year) {
  yearDisplay.textContent = Math.floor(year);
  draw(year);
  updateEventLog(year);
  if (typeof updateTechList === 'function') updateTechList(year);
  if (typeof updateSpeciesList === 'function') updateSpeciesList(year);
  if (typeof updateCombatList === 'function') updateCombatList(year);
  if (typeof updateQuotesList === 'function') updateQuotesList(year);
  if (typeof updateMoodStrip === 'function') updateMoodStrip(year);
}

slider.addEventListener('input', function() { update(parseFloat(slider.value)); });
playBtn.addEventListener('click', function() {
  playing = !playing; playBtn.textContent = playing ? 'Pause' : 'Play'; lastTime = null;
  if (playing) requestAnimationFrame(tick);
});
document.addEventListener('keydown', function(e) {
  if (e.key === '+' || e.key === '=') { speed = Math.min(speed * 1.5, 20); speedDisplay.textContent = speed.toFixed(1) + ' yr/s'; }
  if (e.key === '-') { speed = Math.max(speed / 1.5, 0.5); speedDisplay.textContent = speed.toFixed(1) + ' yr/s'; }
  if (e.key === ' ') { e.preventDefault(); playBtn.click(); }
  if (e.key === 'ArrowRight') { slider.value = Math.min(parseFloat(slider.value) + 1, parseFloat(slider.max)); update(parseFloat(slider.value)); }
  if (e.key === 'ArrowLeft') { slider.value = Math.max(parseFloat(slider.value) - 1, parseFloat(slider.min)); update(parseFloat(slider.value)); }
});
function tick(ts) {
  if (!playing) return;
  if (lastTime !== null) {
    var dt = (ts - lastTime) / 1000, val = parseFloat(slider.value) + dt * speed;
    if (val >= parseFloat(slider.max)) { val = parseFloat(slider.max); playing = false; playBtn.textContent = 'Play'; }
    slider.value = val; update(val);
  }
  lastTime = ts; if (playing) requestAnimationFrame(tick);
}

// ── Config screen ─────────────────────────────────────────────────────────────
var bookSelect = document.getElementById('book-select');
var chapterSelect = document.getElementById('chapter-select');
var startBtn = document.getElementById('start-btn');
var configOverlay = document.getElementById('config-overlay');
var scopeLabel = document.getElementById('scope-label');
var app = document.getElementById('app');

function populateChapters() {
  var book = parseInt(bookSelect.value);
  var chs = CHAPTERS[book];
  chapterSelect.textContent = '';
  for (var i = 0; i < chs.length; i++) {
    var opt = document.createElement('option');
    opt.value = i;
    opt.textContent = chs[i].label;
    chapterSelect.appendChild(opt);
  }
  chapterSelect.value = chs.length - 1; // default to last chapter
}

bookSelect.addEventListener('change', populateChapters);
populateChapters();

var layoutSelect = document.getElementById('layout-select');

function startApp() {
  var book = parseInt(bookSelect.value);
  var chIdx = parseInt(chapterSelect.value);
  var ch = CHAPTERS[book][chIdx];
  scopeBook = book;
  scopeMaxYear = ch.maxYear;
  scopeMaxChapter = ch.ch;
  layoutMode = layoutSelect.value;
  layoutBtn.textContent = 'Layout: ' + (layoutMode === 'realistic' ? 'Realistic' : 'Spread');

  var bookNames = { 1: "Book 1", 2: "Books 1-2", 3: "Books 1-3" };
  scopeLabel.textContent = bookNames[book] + " up to " + ch.label + " [change]";

  configOverlay.style.display = 'none';
  app.classList.add('visible');
  applyScope();
  resize();
  buildEventLog();
  buildLegend();
  buildTechList();
  buildSpeciesList();
  buildCombatList();
  buildQuotesList();
  buildArcsList();
  buildMoodStrip();
  update(parseFloat(slider.min));
}

startBtn.addEventListener('click', startApp);

scopeLabel.addEventListener('click', function() {
  playing = false; playBtn.textContent = 'Play';
  layoutSelect.value = layoutMode;
  app.classList.remove('visible');
  configOverlay.style.display = 'flex';
});

window.addEventListener('resize', function() {
  if (app.classList.contains('visible')) { resize(); update(parseFloat(slider.value)); }
});

// ── Layout toggle ────────────────────────────────────────────────────────────
var layoutBtn = document.getElementById('layout-btn');
layoutBtn.addEventListener('click', function() {
  layoutMode = layoutMode === 'realistic' ? 'spread' : 'realistic';
  layoutBtn.textContent = 'Layout: ' + (layoutMode === 'realistic' ? 'Realistic' : 'Spread');
  fitView();
  update(parseFloat(slider.value));
});

// ── Tab switching ───────────────────────────────────────────────────────────
var tabButtons = document.querySelectorAll('.panel-tab');
var tabContents = document.querySelectorAll('.panel-content');
tabButtons.forEach(function(btn) {
  btn.addEventListener('click', function() {
    var target = btn.getAttribute('data-tab');
    tabButtons.forEach(function(b) { b.classList.remove('active'); });
    tabContents.forEach(function(c) { c.classList.remove('active'); });
    btn.classList.add('active');
    document.querySelector('.panel-content[data-content="' + target + '"]').classList.add('active');
  });
});

// ── Comms toggle ────────────────────────────────────────────────────────────
var commsToggle = document.getElementById('comms-toggle');
commsToggle.addEventListener('click', function() {
  commsEnabled = !commsEnabled;
  commsToggle.textContent = 'Comms: ' + (commsEnabled ? 'ON' : 'OFF');
  commsToggle.classList.toggle('off', !commsEnabled);
  draw(parseFloat(slider.value));
});

// ── Tech list ───────────────────────────────────────────────────────────────
var techListEl = document.getElementById('tech-list');
function buildTechList() {
  techListEl.textContent = '';
  TECH.forEach(function(t) {
    var el = document.createElement('div'); el.className = 'tech-item future'; el.dataset.firstCh = t.first_mentioned_chapter || 999;
    var line1 = document.createElement('div');
    var ns = document.createElement('span'); ns.className = 'tech-name'; ns.textContent = t.name; line1.appendChild(ns);
    var ts = document.createElement('span'); ts.className = 'tech-tier'; ts.textContent = t.tier; line1.appendChild(ts);
    el.appendChild(line1);
    if (t.description) { var d = document.createElement('div'); d.className = 'tech-desc'; d.textContent = t.description; el.appendChild(d); }
    var when = 'mentioned ch ' + (t.first_mentioned_chapter || '?');
    if (t.first_deployed_chapter) when += ', deployed ch ' + t.first_deployed_chapter;
    var w = document.createElement('div'); w.className = 'tech-when'; w.textContent = when; el.appendChild(w);
    techListEl.appendChild(el);
  });
}
function updateTechList(year) {
  // Mark items recent if first_mentioned was in last few chapters before current year
  var children = techListEl.children;
  for (var i = 0; i < children.length; i++) {
    var el = children[i];
    var ch = parseInt(el.dataset.firstCh);
    var techRec = TECH[i];
    if (!techRec) continue;
    if (year < (techRec.history && techRec.history[0] ? techRec.history[0].year : 9999)) {
      el.className = 'tech-item future';
    } else {
      // Compare year vs latest history entry within bounds
      var recent = false;
      for (var j = 0; j < (techRec.history || []).length; j++) {
        var h = techRec.history[j];
        if (h.year <= year && (year - h.year) < 1.0) { recent = true; break; }
      }
      el.className = 'tech-item ' + (recent ? 'recent' : 'past');
    }
  }
}

// ── Species list ────────────────────────────────────────────────────────────
var speciesListEl = document.getElementById('species-list');
function buildSpeciesList() {
  speciesListEl.textContent = '';
  SPECIES.forEach(function(s) {
    var el = document.createElement('div'); el.className = 'species-item future';
    el.dataset.firstYear = s.first_year || 9999;
    if (s.hostile) el.classList.add('hostile');
    else if (s.hostile === false) el.classList.add('peaceful');
    var n = document.createElement('div'); n.className = 'species-name';
    n.textContent = s.name + (s.intelligent ? ' ◆' : '');
    if (s.hostile) n.classList.add('hostile');
    el.appendChild(n);
    var meta = 'first contact ch ' + s.first_chapter + ' · tech: ' + (s.tech_level || '?');
    var m = document.createElement('div'); m.className = 'species-meta'; m.textContent = meta; el.appendChild(m);
    speciesListEl.appendChild(el);
  });
  if (!SPECIES.length) {
    speciesListEl.innerHTML = '<div style="padding:12px;color:#5a6a8a;font-size:11px">No alien species yet.</div>';
  }
}
function updateSpeciesList(year) {
  var ch = speciesListEl.children;
  for (var i = 0; i < ch.length; i++) {
    var fy = parseFloat(ch[i].dataset.firstYear);
    if (year >= fy) ch[i].classList.remove('future'); else ch[i].classList.add('future');
  }
}

// ── Combat list ─────────────────────────────────────────────────────────────
var combatListEl = document.getElementById('combat-list');
function buildCombatList() {
  combatListEl.textContent = '';
  COMBAT.forEach(function(c) {
    var el = document.createElement('div'); el.className = 'combat-item future';
    el.dataset.year = c.year || 9999;
    var n = document.createElement('div'); n.className = 'combat-name'; n.textContent = c.name; el.appendChild(n);
    var w = document.createElement('div'); w.className = 'combat-where';
    w.textContent = (c.location || '?') + ' · ch ' + c.chapter;
    el.appendChild(w);
    if (c.outcome_summary) { var o = document.createElement('div'); o.className = 'combat-outcome'; o.textContent = c.outcome_summary; el.appendChild(o); }
    combatListEl.appendChild(el);
  });
  if (!COMBAT.length) combatListEl.innerHTML = '<div style="padding:12px;color:#5a6a8a;font-size:11px">No battles yet.</div>';
}
function updateCombatList(year) {
  var ch = combatListEl.children;
  for (var i = 0; i < ch.length; i++) {
    var y = parseFloat(ch[i].dataset.year);
    if (y > year) { ch[i].className = 'combat-item future'; }
    else if (year - y < 1.0) { ch[i].className = 'combat-item recent'; }
    else { ch[i].className = 'combat-item past'; }
  }
}

// ── Quotes list ─────────────────────────────────────────────────────────────
var quotesListEl = document.getElementById('quotes-list');
function buildQuotesList() {
  quotesListEl.textContent = '';
  QUOTES.forEach(function(q) {
    var el = document.createElement('div'); el.className = 'quote-item future';
    el.dataset.year = q.year || 9999;
    var t = document.createElement('div'); t.className = 'quote-text'; t.textContent = '"' + q.text + '"'; el.appendChild(t);
    var attr = document.createElement('div'); attr.className = 'quote-attr';
    attr.textContent = '— ' + q.speaker + ' (ch ' + q.chapter + ')';
    if (q.context) attr.textContent += ' · ' + q.context;
    el.appendChild(attr);
    quotesListEl.appendChild(el);
  });
}
function updateQuotesList(year) {
  var ch = quotesListEl.children;
  for (var i = 0; i < ch.length; i++) {
    var y = parseFloat(ch[i].dataset.year);
    if (y > year) ch[i].className = 'quote-item future'; else ch[i].className = 'quote-item past';
  }
}

// ── Arcs list ───────────────────────────────────────────────────────────────
var arcsListEl = document.getElementById('arcs-list');
function buildArcsList() {
  arcsListEl.textContent = '';
  ARCS.forEach(function(a) {
    var el = document.createElement('div'); el.className = 'arc-item';
    el.dataset.start = a.chapter_start;
    var n = document.createElement('div');
    var name = document.createElement('span'); name.className = 'arc-name'; name.textContent = a.name; n.appendChild(name);
    var range = document.createElement('span'); range.className = 'arc-range'; range.textContent = 'ch ' + a.chapter_start + '–' + a.chapter_end; n.appendChild(range);
    el.appendChild(n);
    var d = document.createElement('div'); d.className = 'arc-desc'; d.textContent = a.description; el.appendChild(d);
    if (a.key_characters && a.key_characters.length) {
      var c = document.createElement('div'); c.className = 'arc-chars'; c.textContent = a.key_characters.join(' · '); el.appendChild(c);
    }
    arcsListEl.appendChild(el);
  });
}

// ── Mood strip ──────────────────────────────────────────────────────────────
var moodStripEl = document.getElementById('mood-strip');
function buildMoodStrip() {
  moodStripEl.textContent = '';
  var book1Chapters = (CHAPTERS[scopeBook] || CHAPTERS[1] || []);
  // Also include book 2/3 if scope
  var allChapters = [];
  for (var bk = 1; bk <= scopeBook; bk++) {
    var list = CHAPTERS[bk] || [];
    for (var i = 0; i < list.length; i++) {
      allChapters.push({ book: bk, ch: list[i] });
    }
  }
  allChapters.forEach(function(entry) {
    var ch = entry.ch;
    var theme = THEMES_BY_CH[String(ch.ch)] || {};
    var mood = theme.mood || 'mundane';
    var cell = document.createElement('div');
    cell.className = 'mood-cell mood-' + mood;
    cell.title = (ch.label || ('ch ' + ch.ch)) + ' · ' + mood;
    cell.dataset.year = ch.maxYear;
    cell.dataset.chapter = ch.ch;
    cell.addEventListener('click', function() {
      slider.value = ch.maxYear;
      update(parseFloat(slider.value));
    });
    moodStripEl.appendChild(cell);
  });
}
function updateMoodStrip(year) {
  var cells = moodStripEl.children;
  for (var i = 0; i < cells.length; i++) {
    var y = parseFloat(cells[i].dataset.year);
    cells[i].classList.toggle('active', Math.abs(y - year) < 0.5);
  }
}

// ── Bob trading-card modal ──────────────────────────────────────────────────
var bobCard = document.getElementById('bob-card');
var bobCardBody = document.getElementById('bob-card-body');
var bobCardClose = document.getElementById('bob-card-close');
bobCardClose.addEventListener('click', function() { bobCard.classList.add('hidden'); });
bobCard.addEventListener('click', function(e) { if (e.target === bobCard) bobCard.classList.add('hidden'); });

function openBobCard(bobId) {
  var b = ALL_BOBS[bobId]; if (!b) return;
  var color = bobColors[bobId] || '#88a8c8';
  var p = b.personality || {};
  bobCardBody.textContent = '';

  var header = document.createElement('div'); header.className = 'bc-header';
  var nm = document.createElement('div'); nm.className = 'bc-name'; nm.textContent = bobId; nm.style.color = color;
  header.appendChild(nm);
  if (p.role && p.role !== 'unknown') {
    var rb = document.createElement('span'); rb.className = 'bc-role-badge'; rb.textContent = p.role; header.appendChild(rb);
  }
  bobCardBody.appendChild(header);

  var lineage = 'Gen ' + (b.gen || '?') + (b.parent ? ' · child of ' + b.parent : '') + ' · created ' + Math.floor(b.created || 0) + ' · book ' + b.book;
  var lin = document.createElement('div'); lin.className = 'bc-lineage'; lin.textContent = lineage; bobCardBody.appendChild(lin);

  if (p.traits && p.traits.length) {
    var traits = document.createElement('div'); traits.className = 'bc-traits';
    p.traits.forEach(function(t) {
      var c = document.createElement('span'); c.className = 'bc-trait'; c.textContent = t; traits.appendChild(c);
    });
    bobCardBody.appendChild(traits);
  }

  if (p.quirks) {
    var q = document.createElement('div'); q.className = 'bc-section';
    var ql = document.createElement('div'); ql.className = 'bc-label'; ql.textContent = 'Quirks'; q.appendChild(ql);
    var qt = document.createElement('div'); qt.className = 'bc-quirks'; qt.textContent = p.quirks; q.appendChild(qt);
    bobCardBody.appendChild(q);
  }

  if (p.nickname_origin) {
    var no = document.createElement('div'); no.className = 'bc-section';
    var nol = document.createElement('div'); nol.className = 'bc-label'; nol.textContent = 'Name origin'; no.appendChild(nol);
    var not = document.createElement('div'); not.className = 'bc-text'; not.textContent = p.nickname_origin; no.appendChild(not);
    bobCardBody.appendChild(no);
  }

  if (CHAR_ARCS[bobId]) {
    var arc = document.createElement('div'); arc.className = 'bc-section';
    var al = document.createElement('div'); al.className = 'bc-label'; al.textContent = 'Arc'; arc.appendChild(al);
    var at = document.createElement('div'); at.className = 'bc-text'; at.textContent = CHAR_ARCS[bobId]; arc.appendChild(at);
    bobCardBody.appendChild(arc);
  }

  // Stats: travels count, battles count
  var travelCount = 0, battleCount = 0;
  for (var i = 0; i < ALL_TRAVELS.length; i++) if (ALL_TRAVELS[i].bob === bobId) travelCount++;
  for (var i = 0; i < ALL_COMBAT.length; i++) {
    var c = ALL_COMBAT[i]; if (c.participants) {
      for (var j = 0; j < c.participants.length; j++) {
        if (c.participants[j].name === bobId) { battleCount++; break; }
      }
    }
  }
  var stats = document.createElement('div'); stats.className = 'bc-section bc-stats';
  function addStat(num, label) {
    var s = document.createElement('div');
    var n = document.createElement('div'); n.className = 'bc-stat-num'; n.textContent = num; s.appendChild(n);
    var l = document.createElement('div'); l.className = 'bc-stat-label'; l.textContent = label; s.appendChild(l);
    stats.appendChild(s);
  }
  addStat(travelCount, 'Travels');
  addStat(battleCount, 'Battles');
  if (b.destroyed) addStat(Math.floor(b.destroyed), 'Lost');
  bobCardBody.appendChild(stats);

  // Travels list
  var tt = ALL_TRAVELS.filter(function(t) { return t.bob === bobId; });
  if (tt.length) {
    var trv = document.createElement('div'); trv.className = 'bc-section';
    var tl = document.createElement('div'); tl.className = 'bc-label'; tl.textContent = 'Travels'; trv.appendChild(tl);
    tt.forEach(function(t) {
      var row = document.createElement('div'); row.className = 'bc-travel-row';
      row.innerHTML = Math.floor(t.depart) + ': ' + t.from + ' <span class="arrow">→</span> ' + t.to + ' (' + Math.floor(t.arrive) + ')';
      trv.appendChild(row);
    });
    bobCardBody.appendChild(trv);
  }

  bobCard.classList.remove('hidden');
}

// ── Canvas click-to-open card ───────────────────────────────────────────────
canvas.addEventListener('click', function(e) {
  var rect = canvas.getBoundingClientRect();
  var mx = e.clientX - rect.left, my = e.clientY - rect.top;
  var year = parseFloat(slider.value);
  for (var id in BOBS) {
    var pos = getBobPosition(id, year); if (!pos) continue;
    var dx = mx - pos.x, dy = my - pos.y;
    if (dx * dx + dy * dy < 144) { openBobCard(id); return; }
  }
});

// (update() already calls each panel updater conditionally)

// ── URL ?autostart=1 for headless verification ──────────────────────────────
if (typeof window !== 'undefined' && window.location && window.location.search.includes('autostart=1')) {
  setTimeout(function() {
    var btn = document.getElementById('start-btn'); if (btn) btn.click();
    var m = window.location.search.match(/year=(\d+(?:\.\d+)?)/);
    if (m) setTimeout(function() {
      slider.value = m[1]; update(parseFloat(slider.value));
    }, 200);
  }, 100);
}
