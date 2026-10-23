/* Renders every chart from data/dashboard.json, which the Python pipeline writes. */
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const theme = new URLSearchParams(location.search).get("theme");
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
  const AGE_ORDER = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-90", "90-100"];
  const PRIOR_ORDER = ["0", "1", "2", "3", "4", "5+"];
  const MIN_CELL = 200;
  let data;
  let timelineDrawn = false;

  const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";
  const int = (x) => Math.round(x).toLocaleString("en-US");
  const days = (x) => x.toFixed(1);
  const ageLabel = (a) => a.replace("-", "–");

  function el(tag, attrs = {}, parent) {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) {
      node.setAttribute(k, (k === "width" || k === "height") && typeof v === "number" ? Math.max(0, v) : v);
    }
    if (parent) parent.appendChild(node);
    return node;
  }
  function text(parent, x, y, str, cls, attrs = {}) {
    const t = el("text", { x, y, class: cls, ...attrs }, parent);
    t.textContent = str;
    return t;
  }
  function svgFor(container, w, h, label) {
    container.innerHTML = "";
    return el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": label }, container);
  }
  /* Bars: rounded 4px at the data end, square at the baseline. */
  function barPath(x, y, w, h, horizontal) {
    const r = Math.min(4, (horizontal ? h : w) / 2, horizontal ? w : h);
    if (h <= 0 || w <= 0) return "";
    if (horizontal) {
      return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`;
    }
    return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
  }

  /* Tooltip */
  const tip = document.getElementById("tip");
  function showTip(evt, title, rows) {
    tip.innerHTML = `<b>${title}</b>` + rows.map((r) => `<span class="tip-row">${r}</span>`).join("<br>");
    tip.hidden = false;
    const pad = 14;
    const { innerWidth: vw } = window;
    const box = tip.getBoundingClientRect();
    let x = evt.clientX + pad;
    if (x + box.width > vw - 8) x = evt.clientX - box.width - pad;
    tip.style.left = Math.max(8, x) + "px";
    tip.style.top = Math.max(8, evt.clientY - box.height - pad) + "px";
  }
  const hideTip = () => { tip.hidden = true; };
  function hover(target, bar, title, rows) {
    target.addEventListener("pointermove", (e) => { bar.classList.add("is-hover"); showTip(e, title, rows); });
    target.addEventListener("pointerleave", () => { bar.classList.remove("is-hover"); hideTip(); });
  }

  /* An accessible table beneath each chart */
  function dataTable(figure, headers, rows) {
    figure.querySelector("details.data")?.remove();
    const d = document.createElement("details");
    d.className = "data";
    d.innerHTML = `<summary>Show the numbers</summary><table><thead><tr>${headers.map((h, i) =>
      `<th scope="col"${i ? ' class="num"' : ""}>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) =>
      `<tr>${r.map((c, i) => `<td${i ? ' class="num"' : ""}>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    figure.appendChild(d);
  }

  /* A round tick step that gives three or four gridlines, and the axis max it implies. */
  function niceScale(v) {
    const raw = v / 4;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
    return { step, max: Math.ceil(v / step) * step };
  }
  const niceMax = (v) => niceScale(v).max;

  /* ---------- Hero: a stay, the discharge, and the 30-day window ---------- */
  function timeline() {
    const box = document.getElementById("timeline");
    const W = box.clientWidth;
    const narrow = W < 600;
    const H = narrow ? 300 : 340;
    const m = { top: 30, bottom: 40 };
    const svg = svgFor(box, W, H, `Length of stay distribution and the 30-day readmission window: ${pct(data.kpi.lt30)} returned within 30 days`);
    const x = (d) => ((d + 14) / 44) * W;            // one scale for the whole timeline: day -14 to day +30
    const plotB = H - m.bottom;
    const los = data.los.slice().sort((a, b) => a.key - b.key);
    const maxN = Math.max(...los.map((r) => r.encounters));
    const barTop = m.top + 70;
    const y = (n) => plotB - (n / maxN) * (plotB - barTop);

    const win = el("rect", { x: x(0), y: m.top, width: x(30) - x(0), height: plotB - m.top, class: "tl-window" + (timelineDrawn ? "" : " tl-window-anim") }, svg);
    timelineDrawn = true;
    win.setAttribute("aria-hidden", "true");

    // Stays: a bar at -d counts stays that began d days before discharge
    for (const r of los) {
      const x0 = x(-r.key) + 1, x1 = x(-r.key + 1) - 1;
      const bar = el("path", { d: barPath(x0, y(r.encounters), x1 - x0, plotB - y(r.encounters)), class: "bar" }, svg);
      const hit = el("rect", { x: x(-r.key), y: m.top, width: x(-r.key + 1) - x(-r.key), height: plotB - m.top, class: "hit" }, svg);
      hover(hit, bar, `${r.key}-day stays`,
        [`${int(r.encounters)} encounters`, `${pct(r.lt30)} back within 30 days`]);
    }
    el("line", { x1: 0, x2: W, y1: plotB, y2: plotB, class: "baseline" }, svg);
    el("line", { x1: x(0), x2: x(0), y1: m.top - 14, y2: plotB + 6, class: "tl-discharge" }, svg);

    text(svg, x(-14), m.top + 4, "In hospital", "tl-zone", { "dominant-baseline": "hanging" });
    text(svg, x(0) + 8, m.top - 14, "Discharge", "tl-zone", { "dominant-baseline": "hanging", "font-weight": 650 });

    // Axis: days relative to discharge
    const ticks = narrow ? [-14, 0, 15, 30] : [-14, -7, 0, 7, 14, 21, 30];
    for (const t of ticks) {
      const label = t === 0 ? "0" : t < 0 ? `${-t} days before` : `day ${t}`;
      const anchor = t === -14 ? "start" : t === 30 ? "end" : "middle";
      text(svg, x(t), plotB + 22, label, "tick-label", { "text-anchor": anchor });
    }

    // The headline number lives in the window it describes
    const winW = x(30) - x(0);
    const big = Math.min(winW * 0.34, narrow ? 92 : 168);
    const bx = x(0) + (narrow ? 14 : 28);
    const by = m.top + 18 + big * 0.82;
    text(svg, bx, by, pct(data.kpi.lt30), "tl-big", { "font-size": big });
    const labelSize = narrow ? 14 : 16;
    const lines = narrow
      ? ["were back in hospital", "within 30 days"]
      : ["of patients sent home alive were back", "in hospital within 30 days"];
    lines.forEach((l, i) => text(svg, bx + 2, by + 12 + labelSize * 1.35 * (i + 1) - 6, l, "tl-big-label", { "font-size": labelSize }));
    text(svg, x(30) - 10, plotB - 12, `${pct(data.kpi.gt30)} more returned after day 30`, "tl-later", { "text-anchor": "end", "font-size": narrow ? 12 : 14 });
  }

  /* ---------- Vertical bars ---------- */
  function vbars(id, rows, { value, fmt, label, ref, refLabel, tipRows, height = 240, emphasize }) {
    const box = document.getElementById(id);
    const W = box.clientWidth;
    const m = { top: 34, right: 8, bottom: 30, left: 40 };
    const svg = svgFor(box, W, height, box.previousElementSibling?.textContent || id);
    const iw = W - m.left - m.right, ih = height - m.top - m.bottom;
    const vals = rows.map(value);
    const { step, max } = niceScale(Math.max(...vals, ref || 0));
    const y = (v) => m.top + ih - (v / max) * ih;
    const band = iw / rows.length;
    const gap = Math.max(2, Math.min(10, band * 0.22));

    const grid = el("g", { class: "grid axis" }, svg);
    for (let v = 0; v <= max + 1e-9; v += step) {
      el("line", { x1: m.left, x2: W - m.right, y1: y(v), y2: y(v) }, grid);
      text(grid, m.left - 6, y(v) + 4, fmt(v, step < 0.01 ? 1 : 0), "tick-label", { "text-anchor": "end" });
    }
    const iMax = vals.indexOf(Math.max(...vals));
    const iMin = vals.indexOf(Math.min(...vals));
    rows.forEach((r, i) => {
      const v = value(r);
      const bx = m.left + i * band + gap / 2;
      const cls = "bar" + (emphasize && emphasize(r) ? " is-return" : "");
      const bar = el("path", { d: barPath(bx, y(v), band - gap, m.top + ih - y(v)), class: cls }, svg);
      const hit = el("rect", { x: m.left + i * band, y: m.top, width: band, height: ih, class: "hit" }, svg);
      hover(hit, bar, label(r), tipRows(r));
      const showLabel = band > 26 ? true : i === iMax || i === iMin;
      text(svg, bx + (band - gap) / 2, height - m.bottom + 18, label(r), "tick-label", {
        "text-anchor": "middle", "font-size": band < 30 ? 11 : 12.5,
        ...(showLabel ? {} : { opacity: 0 }) });
      if (i === iMax || i === iMin) {
        text(svg, bx + (band - gap) / 2, y(v) - 6, fmt(v, 1), "value-label", { "text-anchor": "middle" });
      }
    });
    el("line", { x1: m.left, x2: W - m.right, y1: m.top + ih, y2: m.top + ih, class: "baseline" }, svg);
    if (ref != null) {
      el("line", { x1: m.left, x2: W - m.right, y1: y(ref), y2: y(ref), class: "ref-line" }, svg);
      // Key for the dashed line sits above the plot so it never collides with bars
      const key = text(svg, W - m.right, 12, refLabel, "ref-label", { "text-anchor": "end" });
      const kw = key.getComputedTextLength();
      el("line", { x1: W - m.right - kw - 30, x2: W - m.right - kw - 8, y1: 8, y2: 8, class: "ref-line" }, svg);
    }
  }

  /* ---------- Horizontal bars, sorted ---------- */
  function hbars(id, rows, { value, fmt, label, ref, refLabel, tipRows, emphasize }) {
    const box = document.getElementById(id);
    const W = box.clientWidth;
    const narrow = W < 480;
    const rowH = 34;
    const m = { top: 8, right: 56, bottom: 24, left: narrow ? 112 : 140 };
    const H = m.top + rows.length * rowH + m.bottom;
    const svg = svgFor(box, W, H, box.previousElementSibling?.textContent || id);
    const iw = W - m.left - m.right;
    const max = niceMax(Math.max(...rows.map(value), ref || 0));
    const x = (v) => m.left + (v / max) * iw;
    rows.forEach((r, i) => {
      const y0 = m.top + i * rowH;
      const v = value(r);
      const cls = "bar" + (emphasize && emphasize(r) ? " is-return" : "");
      const bar = el("path", { d: barPath(m.left, y0 + 7, x(v) - m.left, rowH - 14, true), class: cls }, svg);
      const hit = el("rect", { x: 0, y: y0, width: W, height: rowH, class: "hit" }, svg);
      hover(hit, bar, label(r), tipRows(r));
      text(svg, m.left - 10, y0 + rowH / 2 + 5, label(r), "cat-label", { "text-anchor": "end", "font-size": narrow ? 13 : 14 });
      text(svg, x(v) + 6, y0 + rowH / 2 + 4, fmt(v, 1), "value-label");
    });
    el("line", { x1: m.left, x2: m.left, y1: m.top, y2: H - m.bottom, class: "baseline" }, svg);
    if (ref != null) {
      el("line", { x1: x(ref), x2: x(ref), y1: m.top - 4, y2: H - m.bottom + 4, class: "ref-line" }, svg);
      text(svg, x(ref), H - 4, refLabel, "ref-label", { "text-anchor": "middle" });
    }
  }

  /* ---------- Heatmap: diagnosis rows by age columns ---------- */
  function heatColor(t) {
    const p = Math.round(12 + t * 88);
    return `color-mix(in oklab, var(--return) ${p}%, var(--paper))`;
  }
  function heatmap() {
    const box = document.getElementById("heat");
    const W = box.clientWidth;
    const narrow = W < 560;
    const diags = data.diag.filter((d) => d.key !== "Missing").sort((a, b) => b.encounters - a.encounters).map((d) => d.key);
    const ages = AGE_ORDER;
    const m = { top: 26, right: 4, bottom: 4, left: narrow ? 104 : 132 };
    const cw = (W - m.left - m.right) / ages.length;
    const ch = narrow ? 30 : 36;
    const H = m.top + diags.length * ch + m.bottom;
    const svg = svgFor(box, W, H, "Heatmap of 30-day readmission rate by age and diagnosis");
    const cells = data.heat.filter((c) => c.primary_diag_group !== "Missing");
    const valid = cells.filter((c) => c.eligible_encounters >= MIN_CELL);
    const lo = Math.min(...valid.map((c) => c.readmit_lt30_rate));
    const hi = Math.max(...valid.map((c) => c.readmit_lt30_rate));
    const step = (v) => Math.min(4, Math.floor(((v - lo) / (hi - lo)) * 5)) / 4;   // five classes

    ages.forEach((a, j) => text(svg, m.left + j * cw + cw / 2, m.top - 10, narrow ? a.split("-")[0] : ageLabel(a), "tick-label", { "text-anchor": "middle" }));
    diags.forEach((d, i) => {
      const y0 = m.top + i * ch;
      text(svg, m.left - 10, y0 + ch / 2 + 5, d, "cat-label", { "text-anchor": "end", "font-size": narrow ? 13 : 14 });
      ages.forEach((a, j) => {
        const c = cells.find((k) => k.age_band === a && k.primary_diag_group === d);
        const x0 = m.left + j * cw;
        const n = c ? c.eligible_encounters : 0;
        let mark;
        if (!c || n < MIN_CELL) {
          mark = el("rect", { x: x0 + 3, y: y0 + 3, width: cw - 6, height: ch - 6, rx: 3, class: "heat-empty" }, svg);
        } else {
          mark = el("rect", { x: x0, y: y0, width: cw, height: ch, rx: 4, class: "heat-cell", fill: heatColor(step(c.readmit_lt30_rate)) }, svg);
        }
        const hit = el("rect", { x: x0, y: y0, width: cw, height: ch, class: "hit" }, svg);
        hover(hit, mark, `${d}, age ${ageLabel(a)}`, n >= MIN_CELL
          ? [`${pct(c.readmit_lt30_rate)} back within 30 days`, `${int(n)} encounters`, `${days(c.avg_los_days)} days average stay`]
          : [`${int(n)} encounters, too few to rate`]);
      });
    });

    const ramp = document.getElementById("ramp");
    ramp.innerHTML = `${pct(lo, 0)} <span class="swatches">${[0, .25, .5, .75, 1].map((t) => `<i style="background:${heatColor(t)}"></i>`).join("")}</span> ${pct(hi, 0)}`;

    dataTable(box.parentElement, ["Diagnosis", ...ages.map(ageLabel)], diags.map((d) => [d, ...ages.map((a) => {
      const c = cells.find((k) => k.age_band === a && k.primary_diag_group === d);
      return c && c.eligible_encounters >= MIN_CELL ? pct(c.readmit_lt30_rate) : "–";
    })]));
  }

  /* ---------- Page ---------- */
  function byKey(list, order) { return order.map((k) => list.find((r) => String(r.key) === k)).filter(Boolean); }

  function renderText() {
    const k = data.kpi;
    document.getElementById("lede").textContent =
      `Readmissions and length of stay for ${int(k.encounters)} diabetic patient encounters across ${data.meta.hospitals} US hospitals, ${data.meta.years.replace("-", "–")}.`;
    document.getElementById("excluded").textContent = int(k.encounters - k.eligible);
    const stats = [
      [int(k.encounters), "hospital encounters"],
      [int(k.patients), "distinct patients"],
      [`${days(k.avg_los)} days`, "average length of stay"],
      [pct(k.lt30), "readmitted within 30 days", true],
      [pct(k.any), "readmitted at any point"],
    ];
    document.getElementById("stats").innerHTML = stats.map(([v, l, r]) =>
      `<div><dt>${l}</dt><dd${r ? ' class="is-return"' : ""}>${v}</dd></div>`).join("");

    const age = byKey(data.age, AGE_ORDER);
    const a8 = age.find((r) => r.key === "80-90"), a5 = age.find((r) => r.key === "50-60"), a0 = age[0];
    document.getElementById("age-note").innerHTML =
      `Average stay grows steadily with age, from <strong>${days(a0.avg_los)} days</strong> for children to <strong>${days(a8.avg_los)} days</strong> at 80–90. ` +
      `The 30-day rate rises from ${pct(a5.lt30)} at 50–60 to ${pct(a8.lt30)} at 80–90. Patients under 40 are few, so their bars move a lot on small numbers.`;

    const diag = data.diag.filter((d) => d.key !== "Missing");
    const dTop = diag.reduce((a, b) => (b.lt30 > a.lt30 ? b : a));
    const dLow = diag.reduce((a, b) => (b.lt30 < a.lt30 ? b : a));
    const dLos = diag.reduce((a, b) => (b.avg_los > a.avg_los ? b : a));
    document.getElementById("diag-note").innerHTML =
      `Patients admitted for diabetes itself come back within 30 days <strong>${pct(dTop.lt30)}</strong> of the time, against ${pct(dLow.lt30)} for ${dLow.key.toLowerCase()} admissions. ` +
      `${dLos.key} stays are the longest at ${days(dLos.avg_los)} days. Circulatory conditions are the most common reason for admission.`;

    const prior = byKey(data.prior, PRIOR_ORDER);
    const p0 = prior[0], p5 = prior[prior.length - 1];
    const home = data.discharge.find((d) => d.key === "Home"), snf = data.discharge.find((d) => d.key === "Nursing or rehab");
    document.getElementById("prior-note").innerHTML =
      `A patient with no inpatient stays in the prior year returns within 30 days ${pct(p0.lt30)} of the time. With five or more, it is <strong>${pct(p5.lt30)}</strong>, ${(p5.lt30 / p0.lt30).toFixed(1)} times as likely. ` +
      `Where patients go next matters too: ${pct(snf.lt30)} of those discharged to nursing or rehab facilities come back, against ${pct(home.lt30)} of those sent home.`;

    const los = data.los.slice().sort((a, b) => a.key - b.key);
    const l1 = los[0], l10 = los.find((r) => r.key === 10);
    document.getElementById("los-note").innerHTML =
      `One-day stays are followed by a return ${pct(l1.lt30)} of the time; ten-day stays by <strong>${pct(l10.lt30)}</strong>. Beyond ten days the groups are small and the rate levels off. ` +
      `Half of all stays are ${data.kpi.median_los} days or shorter.`;

    const a1c = data.a1c, notMeasured = a1c.find((r) => r.key === "Not measured");
    const measuredShare = 1 - notMeasured.encounters / data.kpi.encounters;
    const findings = [
      [true, `Start with the history, not the diagnosis`,
        `Prior-year inpatient stays separate low- and high-risk patients far better than diagnosis, age or length of stay. A patient with ${PRIOR_ORDER[5]} prior stays is ${(p5.lt30 / p0.lt30).toFixed(1)} times as likely to return within 30 days as one with none. It is a field every hospital already has at admission.`],
      [true, `Follow up hardest after discharges to facilities`,
        `Discharges to nursing or rehab (${pct(snf.lt30)}) and transfers (${pct(data.discharge.find((d) => d.key === "Transferred").lt30)}) return far more often than discharges home (${pct(home.lt30)}). Handover to the next care setting is where readmissions are made.`],
      [false, `Diabetes admissions are the riskiest group`,
        `When diabetes itself is the primary diagnosis, ${pct(dTop.lt30)} return within 30 days, the highest of any group with enough patients.`],
      [false, `HbA1c was measured in only ${pct(measuredShare, 0)} of encounters`,
        `When it was measured, 30-day readmission was lower (${pct(a1c.find((r) => r.key === "Norm").lt30)} for normal results, ${pct(a1c.find((r) => r.key === ">8").lt30)} for results above 8%) than when it wasn't (${pct(notMeasured.lt30)}). Testing may be a marker of more attentive diabetes care during the stay.`],
      [false, `Longer stays signal sicker patients, not safer discharges`,
        `The 30-day rate climbs from ${pct(l1.lt30)} after one-day stays to ${pct(l10.lt30)} after ten-day stays. Length of stay is a severity signal; shortening it is unlikely to raise readmissions on its own.`],
    ];
    document.getElementById("findings").innerHTML = findings.map(([r, h, p]) =>
      `<li${r ? ' class="is-return"' : ""}><b>${h}</b><p>${p}</p></li>`).join("");

    const rows = [
      ...data.validation.sql.map((c) => [c.check, "SQL", c.severity === "info" ? int(c.rows) : int(c.rows), c.severity === "info" ? "info" : c.passed ? "pass" : "fail", c.detail]),
      ...data.validation.pandas.map((c) => [c.check, "pandas", "", c.passed ? "pass" : "fail", c.detail]),
    ];
    const label = { pass: "Passed", fail: "Failed", info: "Reported" };
    document.querySelector("#checks tbody").innerHTML = rows.map(([c, s, n, r, d]) =>
      `<tr><td>${c}<br><small style="color:var(--ink-3)">${d}</small></td><td>${s}</td><td class="num">${n}</td><td class="result-${r}">${label[r]}</td></tr>`).join("");
  }

  let diagMetric = "lt30";
  function renderDiag() {
    const rows = data.diag.filter((d) => d.key !== "Missing").slice().sort((a, b) => b[diagMetric] - a[diagMetric]);
    const conf = {
      lt30: { fmt: (v, d) => pct(v, d === 0 ? 0 : 1), ref: data.kpi.lt30, refLabel: `All ${pct(data.kpi.lt30)}`, cap: "30-day readmission rate by primary diagnosis" },
      avg_los: { fmt: (v, d) => (d === 0 ? v.toFixed(0) : days(v)), ref: data.kpi.avg_los, refLabel: `All ${days(data.kpi.avg_los)}`, cap: "Average length of stay by primary diagnosis, days" },
      encounters: { fmt: (v) => int(v), ref: null, cap: "Encounters by primary diagnosis" },
    }[diagMetric];
    document.getElementById("diag-caption").textContent = conf.cap;
    hbars("diag", rows, {
      value: (r) => r[diagMetric], fmt: conf.fmt, label: (r) => r.key, ref: conf.ref, refLabel: conf.refLabel,
      emphasize: diagMetric === "lt30" ? (r) => r === rows[0] : null,
      tipRows: (r) => [`${pct(r.lt30)} back within 30 days`, `${days(r.avg_los)} days average stay`, `${int(r.encounters)} encounters`],
    });
    dataTable(document.getElementById("diag").parentElement, ["Diagnosis", "30-day rate", "Avg stay", "Encounters"],
      rows.map((r) => [r.key, pct(r.lt30), days(r.avg_los), int(r.encounters)]));
  }

  function renderCharts() {
    hideTip();
    timeline();
    const age = byKey(data.age, AGE_ORDER);
    const ref = data.kpi.lt30, refLabel = `All patients ${pct(ref)}`;
    const ageTip = (r) => [`${pct(r.lt30)} back within 30 days`, `${days(r.avg_los)} days average stay`, `${int(r.encounters)} encounters`];
    const ageShort = (r) => (r.key === "90-100" ? "90+" : r.key.split("-")[0]);
    vbars("age-rate", age, { value: (r) => r.lt30, fmt: (v, d) => pct(v, d === 0 ? 0 : 1), label: ageShort, ref, refLabel, tipRows: ageTip });
    vbars("age-los", age, { value: (r) => r.avg_los, fmt: (v, d) => (d === 0 ? v.toFixed(0) : days(v)), label: ageShort, tipRows: ageTip });
    dataTable(document.getElementById("age-los").parentElement.parentElement.lastElementChild,
      ["Age", "30-day rate", "Avg stay", "Encounters"], age.map((r) => [ageLabel(r.key), pct(r.lt30), days(r.avg_los), int(r.encounters)]));

    renderDiag();
    heatmap();

    const prior = byKey(data.prior, PRIOR_ORDER);
    vbars("prior", prior, {
      value: (r) => r.lt30, fmt: (v, d) => pct(v, d === 0 ? 0 : 1), label: (r) => r.key, ref, refLabel,
      emphasize: (r) => r.key === "5+",
      tipRows: (r) => [`${pct(r.lt30)} back within 30 days`, `${int(r.encounters)} encounters`],
    });
    const dis = data.discharge.filter((d) => d.lt30 != null && d.key !== "Unknown").sort((a, b) => b.lt30 - a.lt30);
    hbars("discharge", dis, {
      value: (r) => r.lt30, fmt: (v, d) => pct(v, d === 0 ? 0 : 1), label: (r) => r.key, ref, refLabel: `All ${pct(ref)}`,
      tipRows: (r) => [`${pct(r.lt30)} back within 30 days`, `${days(r.avg_los)} days average stay`, `${int(r.encounters)} encounters`],
    });
    dataTable(document.getElementById("discharge").parentElement, ["Discharged to", "30-day rate", "Encounters"],
      dis.map((r) => [r.key, pct(r.lt30), int(r.encounters)]));
    dataTable(document.getElementById("prior").parentElement, ["Prior-year stays", "30-day rate", "Encounters"],
      prior.map((r) => [r.key, pct(r.lt30), int(r.encounters)]));

    const los = data.los.slice().sort((a, b) => a.key - b.key);
    vbars("los", los, {
      value: (r) => r.lt30, fmt: (v, d) => pct(v, d === 0 ? 0 : 1), label: (r) => String(r.key), ref, refLabel, height: 260,
      tipRows: (r) => [`${pct(r.lt30)} back within 30 days`, `${int(r.encounters)} encounters`],
    });
    dataTable(document.getElementById("los").parentElement, ["Days in hospital", "30-day rate", "Encounters"],
      los.map((r) => [r.key, pct(r.lt30), int(r.encounters)]));
  }

  document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".seg button").forEach((o) => o.setAttribute("aria-checked", String(o === b)));
    diagMetric = b.dataset.metric;
    renderDiag();
  }));

  let lastW = 0, raf;
  window.addEventListener("resize", () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      if (Math.abs(window.innerWidth - lastW) < 4) return;
      lastW = window.innerWidth;
      renderCharts();
    });
  });

  fetch("data/dashboard.json")
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((json) => { data = json; lastW = window.innerWidth; renderText(); renderCharts(); })
    .catch(() => {
      document.getElementById("timeline").innerHTML =
        "<p>The chart data didn't load. Run <code>python run_pipeline.py</code> to create docs/data/dashboard.json, then serve the docs folder over HTTP.</p>";
    });
})();
