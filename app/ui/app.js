/* Policy Reconciler. The page script: tabs, the "Run the review" replay, the ranked findings with editable risk
   weights, and the side-by-side view. Everything it shows comes from window.PR, which the build
   wrote, so no click waits on anything and nothing reaches the network. Pure helpers sit on window.ADP for the
   node check. */
(function () {
  "use strict";
  var win = window, doc = document;
  var D = win.PR || {}, U = D.ui || {}, F = D.findings || [], H = D.detail_html || {};
  var ADP = win.ADP = {};
  var state = {tab: null, ran: false, timer: null, selected: null, weights: copy(D.risk || {})};

  function copy(o) { return JSON.parse(JSON.stringify(o || {})); }
  function $(sel, root) { return (root || doc).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || doc).querySelectorAll(sel)); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function word(key, fill) {
    var t = U[key] || "";
    Object.keys(fill || {}).forEach(function (k) { t = t.split("{" + k + "}").join(String(fill[k])); });
    return t;
  }
  ADP.word = word;

  /* ------------------------------------------------------------------ tabs */
  function showTab(name) {
    state.tab = name;
    $$(".tab").forEach(function (s) { s.classList.toggle("active", s.id === "t-" + name); });
    $$(".tabs [data-tab]").forEach(function (b) { b.setAttribute("aria-selected", String(b.getAttribute("data-tab") === name)); });
    var on = $(".tabs [data-tab=\"" + name + "\"]");
    if (on && on.scrollIntoView) { on.scrollIntoView({block: "nearest", inline: "nearest"}); }
  }
  ADP.showTab = showTab;
  ADP.tab = function () { return state.tab; };

  /* ------------------------------------------------------------------ the run */
  function stopReplay() { if (state.timer) { win.clearTimeout(state.timer); state.timer = null; } }
  function setRan(on) {
    stopReplay();
    state.ran = on;
    doc.body.classList.toggle("ran", on);
    $$(".steps .step").forEach(function (s) { s.classList.remove("active"); s.classList.toggle("done", on); });
    var run = $("#run .run-label");
    if (run) { run.textContent = on ? (U["strip.replay"] || "") : (U["strip.run"] || ""); }
  }
  function replay() {
    setRan(false);
    var steps = $$(".steps .step"), i = 0;
    function next() {
      if (i > 0) { steps[i - 1].classList.remove("active"); steps[i - 1].classList.add("done"); }
      if (i >= steps.length) { setRan(true); return; }
      steps[i].classList.add("active");
      i += 1;
      state.timer = win.setTimeout(next, 420);
    }
    next();
  }
  ADP.setRan = setRan;
  ADP.ran = function () { return state.ran; };

  /* ------------------------------------------------------------------ findings */
  function riskOf(f, w) {
    var t = (w.topics || {})[f.topic] || {severity: 1, customer: false};
    var cat = f.live ? "conflict" : f.type;
    var n = (w.category[cat] || 0) * (t.severity + (t.customer ? w.customer_weight : 0) + w.breadth_weight * f.breadth);
    return Math.round(n * 100) / 100;
  }
  ADP.riskOf = riskOf;
  function filters() {
    var out = {};
    $$("[data-filter]").forEach(function (s) { out[s.getAttribute("data-filter")] = s.value; });
    return out;
  }
  function ranked() {
    var fl = filters(), w = state.weights;
    return F.filter(function (f) {
      return Object.keys(fl).every(function (k) { return !fl[k] || String(f[k]) === fl[k]; });
    }).map(function (f) { return {f: f, risk: riskOf(f, w)}; }).sort(function (a, b) {
      return b.risk - a.risk || (a.f.id < b.f.id ? -1 : 1);
    });
  }
  ADP.ranked = function () { return ranked().map(function (r) { return r.f.id; }); };
  function row(r, n) {
    var f = r.f, t = D.titles || {};
    var where = word("findings.where", {keep: t[f.keep] || f.keep, change: t[f.change] || f.change});
    return "<tr data-id=\"" + esc(f.id) + "\" tabindex=\"0\" class=\"" + (f.id === state.selected ? "sel" : "") + "\">" +
      "<td class=\"n\">" + n + "</td><td><span class=\"pill c-" + esc(f.type) + "\">" + esc(word("cat." + f.type)) +
      "</span></td><td>" + esc(f.label || word("cat." + f.type)) + "<span class=\"muted\"> " + esc(f.topic_name) +
      "</span></td><td>" + esc(where) + "</td><td><span class=\"pill d-" + esc(f.decided_by) + "\">" +
      esc(word("decider." + f.decided_by)) + "</span></td><td class=\"n\">" + r.risk.toFixed(1) + "</td></tr>";
  }
  function renderList() {
    var body = $("#f-list tbody");
    if (!body) { return; }
    var rows = ranked();
    body.innerHTML = rows.map(function (r, i) { return row(r, i + 1); }).join("");
    var count = $("#f-count");
    if (count) { count.textContent = word("findings.count", {n: rows.length, total: F.length}); }
  }
  function select(id) {
    if (!H[id]) { return; }
    state.selected = id;
    var box = $("#f-detail");
    if (box) { box.innerHTML = H[id]; }
    $$("#f-list tr[data-id]").forEach(function (tr) { tr.classList.toggle("sel", tr.getAttribute("data-id") === id); });
  }
  ADP.select = select;
  ADP.selected = function () { return state.selected; };
  function setWeight(path, value) {
    var parts = path.split("."), o = state.weights;
    for (var i = 0; i < parts.length - 1; i++) { o = o[parts[i]]; }
    o[parts[parts.length - 1]] = Math.max(0, Math.min(9, parseFloat(value) || 0));
  }
  ADP.setWeight = function (path, value) { setWeight(path, value); renderList(); };

  /* ------------------------------------------------------------------ hours and cost
     A manual review reads every document against the rest. The review leaves a specialist only the findings to
     confirm, and its own time and AI cost are measured. Every assumption is an input on the page. */
  function hoursRecalc() {
    var box = $("#hours");
    if (!box) { return null; }
    var v = {};
    $$("[data-hours]", box).forEach(function (i) { v[i.getAttribute("data-hours")] = Math.max(0, parseFloat(i.value) || 0); });
    var docs = +box.getAttribute("data-documents"), finds = +box.getAttribute("data-findings");
    var manualH = docs * v.minutes_per_document / 60, reviewH = finds * v.minutes_per_finding / 60 +
      (+box.getAttribute("data-seconds")) / 3600;
    var manualC = manualH * v.hourly_rate, reviewC = reviewH * v.hourly_rate + (+box.getAttribute("data-ai"));
    var r = {manualH: Math.round(manualH), reviewH: Math.round(reviewH * 10) / 10,
             manualC: Math.round(manualC), reviewC: Math.round(reviewC)};
    var fmt = function (n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); };
    $("#hours-manual").textContent = word("hours.manual", {hours: fmt(r.manualH), cost: fmt(r.manualC)});
    $("#hours-review").textContent = word("hours.review", {hours: r.reviewH, cost: fmt(r.reviewC)});
    $("#hours-saved").textContent = word("hours.saved", {hours: fmt(Math.round(manualH - reviewH)),
                                                          cost: fmt(Math.round(manualC - reviewC))});
    return r;
  }
  ADP.hoursRecalc = hoursRecalc;

  function approveDemo(group) {
    var btn = $("[data-approve=\"" + group + "\"]");
    if (btn) { btn.outerHTML = "<span class=\"pill s-ok\">" + esc(U["drafts.approved_demo"] || "") + "</span>"; }
    return true;
  }
  ADP.approveDemo = approveDemo;
  function reveal(name) {
    var btn = $("[data-reveal=\"" + name + "\"]");
    if (!btn || btn.hasAttribute("disabled")) { return false; }
    var box = doc.getElementById(name + "-result");
    if (box) { box.hidden = false; }
    return true;
  }
  ADP.reveal = reveal;

  /* ------------------------------------------------------------------ events, delegated from the document */
  function near(e, sel) { return e.target && e.target.closest ? e.target.closest(sel) : null; }
  doc.addEventListener("click", function (e) {
    var el = near(e, "[data-tab]");
    if (el) { showTab(el.getAttribute("data-tab")); return; }
    if (near(e, "#run")) { replay(); return; }
    var ap = near(e, "[data-approve]");
    if (ap) { approveDemo(ap.getAttribute("data-approve")); return; }
    var rv = near(e, "[data-reveal]");
    if (rv) { reveal(rv.getAttribute("data-reveal")); return; }
    el = near(e, "#f-list tr[data-id]");
    if (el) { select(el.getAttribute("data-id")); }
  });
  doc.addEventListener("change", function (e) {
    if (near(e, "[data-filter]")) { renderList(); return; }
    if (near(e, "#vendors")) {
      var combo = e.target.value;
      hideTip();
      $$(".route-view").forEach(function (t) { t.hidden = t.getAttribute("data-vendors") !== combo; });
      return;
    }
    if (near(e, "#audit-step")) {
      var v = e.target.value;
      $$("#audit tbody tr").forEach(function (tr) { tr.hidden = !!v && tr.getAttribute("data-step") !== v; });
    }
  });
  /* ------------------------------------------------------------------ the routing chart's tooltip
     Each dot carries its rows in data-tip, with every model within a few pixels of it, and the tooltip shows the value
     first. Every value is in the table view too, so the tooltip never gates one. Rows go in with textContent. */
  function showTip(pt) {
    var tip = doc.getElementById("viz-tip");
    if (!tip || !pt) { return false; }
    var rows = [];
    try { rows = JSON.parse(pt.getAttribute("data-tip") || "[]"); } catch (err) { rows = []; }
    tip.textContent = "";
    rows.forEach(function (r) {
      var row = doc.createElement("div"), key = doc.createElement("span"), v = doc.createElement("strong");
      var n = doc.createElement("span"), s = doc.createElement("span");
      row.setAttribute("class", "tip-row");
      key.setAttribute("class", "key k-" + (r.k || "clears"));
      s.setAttribute("class", "muted");
      v.textContent = r.v; n.textContent = r.n; s.textContent = r.s;
      row.appendChild(key); row.appendChild(v); row.appendChild(n); row.appendChild(s);
      tip.appendChild(row);
    });
    var box = tip.parentNode.getBoundingClientRect(), at = pt.getBoundingClientRect();
    tip.style.left = Math.round(at.left - box.left + at.width / 2) + "px";
    tip.style.top = Math.round(at.top - box.top) + "px";
    tip.hidden = false;
    return true;
  }
  function hideTip() { var tip = doc.getElementById("viz-tip"); if (tip) { tip.hidden = true; } }
  ADP.showTip = showTip;
  ADP.hideTip = hideTip;
  function leaving(e) {
    var pt = near(e, ".pt"), to = e.relatedTarget;
    return pt && !(to && to.closest && to.closest(".pt") === pt);
  }
  doc.addEventListener("pointerover", function (e) { var pt = near(e, ".pt"); if (pt) { showTip(pt); } });
  doc.addEventListener("pointerout", function (e) { if (leaving(e)) { hideTip(); } });
  doc.addEventListener("focusin", function (e) { var pt = near(e, ".pt"); if (pt) { showTip(pt); } });
  doc.addEventListener("focusout", function (e) { if (leaving(e)) { hideTip(); } });
  doc.addEventListener("input", function (e) {
    var el = near(e, "[data-weight]");
    if (el) { setWeight(el.getAttribute("data-weight"), el.value); renderList(); return; }
    if (near(e, "[data-hours]")) { hoursRecalc(); }
  });


  /* ------------------------------------------------------------------ scrolling and starting over */
  function into(el) { if (el && el.scrollIntoView) { el.scrollIntoView({behavior: "smooth", block: "start"}); } }
  function toTop() { if (win.scrollTo) { win.scrollTo(0, 0); } }
  function resetAll() {
    setRan(false);
    state.weights = copy(D.risk);
    $$("[data-weight]").forEach(function (inp) {
      var parts = inp.getAttribute("data-weight").split("."), o = D.risk;
      parts.forEach(function (p) { o = o[p]; });
      inp.value = o;
    });
    $$("[data-filter]").forEach(function (s) { s.value = ""; });
    $$("details[open]").forEach(function (d) { d.removeAttribute("open"); });
    renderList();
    if (F.length) { select(ranked()[0].f.id); }
    showTab("library");
    toTop();
  }
  ADP.reset = resetAll;
  doc.addEventListener("keydown", function (e) {
    var row = near(e, "#f-list tr[data-id]");
    if (row && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); select(row.getAttribute("data-id")); }
  });

  /* ------------------------------------------------------------------ the line rule
     No paragraph ends on a line under 80% full. spillReport() measures every visible block of text and lists the
     ones whose last line falls short, so the copy can be rephrased. The browser check calls it at 1440 pixels. */
  var NOT_TEXT = /^(SCRIPT|STYLE|PRE|CODE|TEXTAREA|INPUT|SELECT|OPTION|BR|IMG|TABLE|THEAD|TBODY|TR|BUTTON|SVG)$/i;
  function shown(el) {
    for (var p = el; p && p.parentElement; p = p.parentElement) {
      var up = p.parentElement;
      if (up.tagName === "DETAILS" && !up.open && p.tagName !== "SUMMARY") { return false; }
    }
    return el.checkVisibility ? el.checkVisibility({visibilityProperty: true}) : el.getClientRects().length > 0;
  }
  var DATA = "blockquote, q, td, th, code, .side, .ex, .ans, .dr-text, .decoys, .sources, .cites, .list-wrap, " +
    "details.nf summary, svg";
  function textBlock(el) {
    if (NOT_TEXT.test(el.tagName) || !shown(el) || (el.closest && el.closest(DATA))) { return false; }
    var cs = win.getComputedStyle(el);
    if (/^(inline|contents|none)$/.test(cs.display) || /^(nowrap|pre)$/.test(cs.whiteSpace)) { return false; }
    var text = false;
    for (var n = el.firstChild; n; n = n.nextSibling) {
      if (n.nodeType === 3) { text = text || /\S/.test(n.data); continue; }
      if (n.nodeType !== 1) { continue; }
      if (!/^inline/.test(win.getComputedStyle(n).display)) { return false; }
      text = text || /\S/.test(n.textContent);
    }
    return text;
  }
  function lineBoxes(el) {
    var lines = [], range = doc.createRange(), walker = doc.createTreeWalker(el, 4), node, re = /\S+/g, m;
    while ((node = walker.nextNode())) {
      re.lastIndex = 0;
      while ((m = re.exec(node.data))) {
        range.setStart(node, m.index);
        range.setEnd(node, m.index + m[0].length);
        var rects = range.getClientRects(), r = rects[rects.length - 1];
        if (!r || r.width < 0.5) { continue; }
        var mid = (r.top + r.bottom) / 2, line = null;
        for (var j = 0; j < lines.length && !line; j++) { if (Math.abs(lines[j].mid - mid) < r.height / 2) { line = lines[j]; } }
        if (line) { line.l = Math.min(line.l, r.left); line.r = Math.max(line.r, r.right); line.words += 1; }
        else { lines.push({mid: mid, l: r.left, r: r.right, words: 1}); }
      }
    }
    return lines.sort(function (a, b) { return a.mid - b.mid; });
  }
  function spillReport(root) {
    if (!root || !doc.createRange || !doc.createTreeWalker || !win.getComputedStyle) { return []; }
    return Array.prototype.filter.call(root.querySelectorAll("*"), textBlock).map(function (el) {
      var lines = lineBoxes(el), cs = win.getComputedStyle(el);
      var inner = el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      if (lines.length < 2 || !inner) { return null; }
      var last = lines[lines.length - 1], fill = (last.r - lines[0].l) / inner;
      return fill < 0.8 ? {text: el.textContent.replace(/\s+/g, " ").trim().slice(0, 160), tag: el.tagName.toLowerCase(),
        cls: String(el.className || ""), lines: lines.length, fill: Math.round(fill * 100), words: last.words} : null;
    }).filter(Boolean);
  }
  ADP.spillReport = spillReport;
  /* A block of text that wraps should run the full width of its box first. narrowReport() lists every wrapping
     block narrower than its parent's content box, which a width cap causes. A parent that lays its children side by
     side, as a flex row or a grid of columns, is left out, since a narrow column there is the layout. */
  function narrowReport(root) {
    if (!root || !doc.createRange || !doc.createTreeWalker || !win.getComputedStyle) { return []; }
    return Array.prototype.filter.call(root.querySelectorAll("*"), textBlock).map(function (el) {
      var up = el.parentElement, cs = up && win.getComputedStyle(up);
      if (!up || lineBoxes(el).length < 2) { return null; }
      if (/flex/.test(cs.display) && !/column/.test(cs.flexDirection)) { return null; }
      if (/grid/.test(cs.display) && cs.gridTemplateColumns.trim().split(/\s+/).length > 1) { return null; }
      var room = up.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      var used = el.getBoundingClientRect().width;
      return room && used < room * 0.92 ? {text: el.textContent.replace(/\s+/g, " ").trim().slice(0, 120),
        tag: el.tagName.toLowerCase(), cls: String(el.className || ""), width: Math.round(used),
        room: Math.round(room)} : null;
    }).filter(Boolean);
  }
  ADP.narrowReport = narrowReport;

  /* ------------------------------------------------------------------ start */
  renderList();
  if (F.length) { select(ranked()[0].f.id); }
  hoursRecalc();
  showTab("library");
})();

/* Phones and touch screens. The page names its open tab for the phone rules in app.css, the tab row fades at an edge
   with more to swipe to, each cell of a wide table carries its column's name so a phone can show each row as a card,
   and on a phone a tapped finding scrolls into view below the list. Every rule these feed sits under a phone-sized or
   touch-only media query, so a desktop with a mouse sees none of it. */
(function () {
  "use strict";
  var win = window, doc = document, ADP = win.ADP || {};
  if (!doc || !doc.body || !doc.querySelectorAll) { return; }
  function $(sel, root) { return (root || doc).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || doc).querySelectorAll(sel)); }
  function phone() { return !!(win.matchMedia && win.matchMedia("(max-width: 640px)").matches); }
  /* Not data-tab, which the page's click handler reads on any element a click lands inside. */
  function markTab() { if (ADP.tab) { doc.body.setAttribute("data-shown-tab", ADP.tab() || ""); } }
  var nav = $("nav.tabs"), row = $("nav.tabs ul"), list = $("#f-list");
  function edges() {
    if (!nav || !row || !nav.classList) { return; }
    var max = (row.scrollWidth || 0) - (row.clientWidth || 0), at = row.scrollLeft || 0;
    nav.classList.toggle("more-left", max > 1 && at > 1);
    nav.classList.toggle("more-right", max > 1 && at < max - 1);
  }
  function label(table) {
    var heads = $$("thead th", table).map(function (th) { return (th.textContent || "").trim(); });
    $$("tbody tr", table).forEach(function (tr) {
      $$("td", tr).forEach(function (td, i) {
        if (heads[i] && !td.getAttribute("data-label")) { td.setAttribute("data-label", heads[i]); }
      });
    });
    return heads.length;
  }
  $$("main table").forEach(function (t) {
    if (t.id !== "f-list" && t.id !== "audit" && label(t) > 3) { t.classList.add("cards"); }
  });
  if (list) { label(list); }
  markTab();
  edges();
  if (win.MutationObserver) {
    if (nav) {
      new win.MutationObserver(function () { markTab(); edges(); })
        .observe(nav, {subtree: true, attributes: true, attributeFilter: ["aria-selected"]});
    }
    var body = $("#f-list tbody");
    if (body) { new win.MutationObserver(function () { label(list); }).observe(body, {childList: true}); }
  }
  if (row && row.addEventListener) { row.addEventListener("scroll", edges, {passive: true}); }
  if (win.addEventListener) { win.addEventListener("resize", edges); }
  doc.addEventListener("click", function (e) {
    var tr = e.target && e.target.closest ? e.target.closest("#f-list tr[data-id]") : null, box = $("#f-detail");
    if (tr && box && phone() && box.scrollIntoView) { box.scrollIntoView({behavior: "smooth", block: "start"}); }
  });
})();
