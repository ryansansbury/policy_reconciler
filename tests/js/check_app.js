/* The node check. It runs the built page's own script against a small DOM (dom.js), clicks every tab, runs the
   review, opens every finding, and changes a risk weight. It
   prints one JSON report, and tests/test_page.py fails on any check that doesn't pass.

       node tests/js/check_app.js <site folder>

   It can't see layout, color or real timing. Screenshots in Chrome cover those. */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const {Document} = require("./dom.js");

const SITE = path.resolve(process.argv[2]);
const report = {checks: [], errors: []};
function check(name, ok, detail) {
  report.checks.push({name: name, ok: !!ok, detail: detail === undefined ? "" : String(detail).slice(0, 400)});
}

const html = fs.readFileSync(path.join(SITE, "index.html"), "utf8");
const doc = new Document(html);
check("index.html parses with every tag closed", doc.errors.length === 0, doc.errors.slice(0, 5).join("; "));
check("nothing on the page loads from the network", !/src="(?:https?:)?\/\//.test(html) && !/<link(?![^>]*rel="canonical")[^>]*href="(?:https?:)?\/\//.test(html));
const timers = [];
const win = {document: doc, innerWidth: 1440, innerHeight: 900, addEventListener() {},
  setTimeout(fn) { timers.push(fn); return timers.length; }, clearTimeout(id) { timers[id - 1] = null; },
  location: {hash: ""}, history: {replaceState(s, t, url) { win.location.hash = url; }}, scrollTo() {}};
win.window = win;
const ctx = vm.createContext(win);
try {
  vm.runInContext(fs.readFileSync(path.join(SITE, "data.js"), "utf8"), ctx, {filename: "data.js"});
  vm.runInContext(fs.readFileSync(path.join(SITE, "app.js"), "utf8"), ctx, {filename: "app.js"});
} catch (e) {
  report.errors.push("the page's script threw: " + (e && e.stack || e));
}
const PR = win.PR, ADP = win.ADP;
function flush() {
  for (let guard = 0; guard < 200 && timers.some(Boolean); guard++) {
    const i = timers.findIndex(Boolean), fn = timers[i];
    timers[i] = null;
    fn();
  }
}
const click = (el) => doc.dispatch("click", el);
const active = () => (doc.querySelector(".tab.active") || {id: ""}).id;

function attempt(name, fn) {
  try { fn(); } catch (e) { report.errors.push(name + ": " + (e && e.stack || e)); }
}

if (PR && ADP) {
  attempt("tabs", () => {
    check("the page opens on the Library before the run", active() === "t-library" && !ADP.ran());
    for (const b of doc.querySelectorAll(".tabs [data-tab]")) {
      click(b);
      const name = b.getAttribute("data-tab");
      check("the " + name + " tab opens", active() === "t-" + name && b.getAttribute("aria-selected") === "true");
    }
  });
  attempt("run", () => {
    click(doc.getElementById("run"));
    check("the run starts with its first step active", doc.querySelectorAll(".step.active").length === 1);
    flush();
    check("the run ends with every step done", ADP.ran() && doc.querySelectorAll(".step.done").length === 6
      && doc.body.classList.contains("ran"));
  });
  attempt("findings", () => {
    const rows = doc.querySelectorAll("#f-list tbody tr");
    check("every finding is listed", rows.length === PR.findings.length && rows.length > 0, rows.length);
    let opened = 0;
    for (const f of PR.findings) {
      ADP.select(f.id);
      const box = doc.getElementById("f-detail");
      if (ADP.selected() === f.id && box.innerHTML.indexOf("sides") >= 0) { opened += 1; }
    }
    check("every finding opens side by side", opened === PR.findings.length, opened + " of " + PR.findings.length);
    const order = ADP.ranked();
    const risks = order.map((id) => ADP.riskOf(PR.findings.find((f) => f.id === id), PR.risk));
    check("findings are ranked by risk", risks.every((r, i) => i === 0 || risks[i - 1] >= r));
    ADP.setWeight("category.duplicate", 9);
    const top = PR.findings.find((f) => f.id === ADP.ranked()[0]);
    check("a weight change ranks the list again", top.type === "duplicate", top.type);
    ADP.setWeight("category.duplicate", PR.risk.category.duplicate);
    const sel = doc.querySelector("[data-filter=\"type\"]");
    sel._value = "superseded";
    doc.dispatch("change", sel);
    const shown = doc.querySelectorAll("#f-list tbody tr").length;
    check("a filter narrows the list", shown === PR.findings.filter((f) => f.type === "superseded").length, shown);
    sel._value = "";
    doc.dispatch("change", sel);
  });
  attempt("hours", () => {
    const r = ADP.hoursRecalc();
    check("the hours panel computes both sides", r && r.manualH > r.reviewH && r.reviewH > 0, JSON.stringify(r));
    const input = doc.querySelector("[data-hours=\"minutes_per_document\"]");
    input._value = "90";
    doc.dispatch("input", input);
    check("an edited assumption changes the estimate", ADP.hoursRecalc().manualH === r.manualH * 2);
    input._value = String(input.getAttribute("value"));
  });
  attempt("open demos", () => {
    if (doc.getElementById("change-result")) {
      check("any visitor can make the rule change and see what reran", ADP.reveal("change") === true
        && !doc.getElementById("change-result").hasAttribute("hidden"));
    }
    check("the approved-vendors control is open to every visitor",
          !doc.getElementById("vendors").hasAttribute("disabled"));
  });
  attempt("run label", () => {
    const btn = doc.getElementById("run");
    ADP.setRan(true);
    const label = btn.querySelector(".run-label").textContent;
    check("a run swaps the button's label and keeps its icon", label === PR.ui["strip.replay"]
      && btn.querySelector(".dot svg") !== null, label);
    ADP.setRan(false);
    check("a reset puts the first label back", btn.querySelector(".run-label").textContent === PR.ui["strip.run"]);
  });
  attempt("routing", () => {
    const views = doc.querySelectorAll(".route-view");
    if (!views.length) { return; }
    const sel = doc.getElementById("vendors");
    const shown = () => views.filter((v) => !v.hasAttribute("hidden"));
    check("one vendor view shows at a time", shown().length === 1, shown().length);
    const last = views[views.length - 1].getAttribute("data-vendors");
    sel._value = last;
    doc.dispatch("change", sel);
    check("choosing the approved vendors shows their view", shown().length === 1
      && shown()[0].getAttribute("data-vendors") === last);
    const pt = shown()[0].querySelector(".pt");
    const tip = doc.getElementById("viz-tip");
    doc.dispatch("focusin", pt);
    check("a focused dot shows its tooltip with the value first", !tip.hasAttribute("hidden")
      && tip.querySelector(".tip-row strong") !== null, tip.textContent);
    doc.dispatch("focusout", pt);
    check("leaving the dot hides its tooltip", tip.hasAttribute("hidden"));
    sel._value = views[0].getAttribute("data-vendors");
    doc.dispatch("change", sel);
  });
  attempt("code", () => {
    const links = Array.from(doc.querySelectorAll("#how-code a"));
    check("the code panel links six files to the repo on GitHub", links.length === 6 &&
          links.every((a) => /^https:\/\/github\.com\/[^/]+\/[^/]+\/blob\//.test(a.getAttribute("href"))),
          links.length);
    const boxes = Array.from(doc.querySelectorAll("svg.arch a.box"));
    check("every box on the diagram links its file in the repo", boxes.length > 0 &&
          boxes.every((a) => /\/blob\//.test(a.getAttribute("href"))), boxes.length);
    check("the page carries no source", win.PR_CODE === undefined && !doc.getElementById("code-body"));
  });
  attempt("reset", () => {
    ADP.reset();
    check("reset returns to the start", active() === "t-library" && !ADP.ran());
  });
} else {
  report.errors.push("window.PR or window.ADP is missing");
}
process.stdout.write(JSON.stringify(report) + "\n");
