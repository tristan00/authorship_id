const SVG = "http://www.w3.org/2000/svg";
const UNITS = { age: "years" };
const grouped = new Intl.NumberFormat("en-US", { useGrouping: true, maximumFractionDigits: 0 });
const compacted = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

export function h(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== null && value !== undefined && value !== false) node.setAttribute(key, value === true ? "" : value);
  }
  node.append(...children.flat(Infinity).filter((child) => child !== null && child !== undefined && child !== false));
  return node;
}

export function count(value) {
  if (!Number.isInteger(value)) throw new Error(`Expected an integer count, received ${JSON.stringify(value)}`);
  return grouped.format(value);
}

export function compact(value) {
  return value < 10000 ? count(value) : compacted.format(value);
}

export function tally(value, one, many) {
  return `${count(value)} ${value === 1 ? one : many}`;
}

export function absent(text) {
  return h("span", { class: "absent" }, text);
}

export function moment(seconds) {
  if (seconds === null) return absent("none");
  return new Date(seconds * 1000).toISOString().slice(0, 16).replace("T", " ");
}

export function day(seconds) {
  return new Date(seconds * 1000).toISOString().slice(0, 10);
}

export function attributeName(name) {
  return name.replaceAll("_", " ");
}

export function attributeValue(name, value, missing) {
  if (value === null) return absent(missing);
  return name in UNITS ? `${value} ${UNITS[name]}` : String(value);
}

export function paths(chains) {
  const same = (row, depth) => row > 0 && chains[row].slice(0, depth + 1).every((part, index) => chains[row - 1][index] === part);
  return h("div", { class: "paths" }, chains.map((parts, row) => h("div", { class: "path" },
    parts.map((part, depth) => [depth ? h("span", { class: "sep" }, " › ") : null, h("span", { class: same(row, depth) ? "repeat" : null }, part)]))));
}

export function bar(value, max) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("class", "bar");
  svg.setAttribute("viewBox", "0 0 100 1");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("aria-hidden", "true");
  const rect = document.createElementNS(SVG, "rect");
  rect.setAttribute("width", max === 0 ? "0" : String((100 * value) / max));
  rect.setAttribute("height", "1");
  svg.append(rect);
  return svg;
}

export function table({ columns, rows, empty, tall = false, rowClass = () => "" }) {
  const head = h("thead", {}, h("tr", {}, columns.map((column) => h("th", { scope: "col", class: column.kind }, column.title))));
  const body = rows.length
    ? rows.map((row, index) => h("tr", { class: rowClass(row) }, columns.map((column) => h("td", { class: column.kind }, column.cell(row, index)))))
    : h("tr", {}, h("td", { class: "empty", colspan: String(columns.length) }, empty));
  return h("div", { class: tall ? "scroll tall" : "scroll" }, h("table", { class: "data" }, head, h("tbody", {}, body)));
}

export function facts(pairs) {
  return h("table", { class: "data facts" }, h("tbody", {}, pairs.map(([label, value]) => h("tr", {}, h("th", { scope: "row" }, label), h("td", {}, value)))));
}

export function stats(pairs) {
  return h("dl", { class: "stats" }, pairs.map(([label, value]) => h("div", { class: "stat" }, h("dt", {}, label), h("dd", {}, value))));
}

export function panel(title, meta, ...content) {
  return h("section", { class: "panel" }, h("header", { class: "panel-head" }, h("h2", {}, title), meta === null ? null : h("span", { class: "panel-meta" }, meta)), content);
}

export function notice(kind, title, detail) {
  return h("div", { class: `notice ${kind}`, role: kind === "error" ? "alert" : "status" }, h("strong", {}, title), detail === null ? null : h("span", { class: "detail" }, detail));
}

export function loading(text = "Loading") {
  return h("div", { class: "loading", role: "status" }, text);
}

export function failed(error) {
  return notice("error", error.status === undefined ? "Error" : `Error ${error.status}`, error.message);
}

export function notFound(detail) {
  return notice("missing", "Not found", detail);
}

export async function fill(slot, request, render) {
  slot.replaceChildren(loading());
  try {
    const data = await request;
    if (slot.isConnected) slot.replaceChildren(...[render(data)].flat());
  } catch (error) {
    if (slot.isConnected) slot.replaceChildren(failed(error));
  }
}

export function segmented(label, options, current, choose) {
  return h("div", { class: "segmented", role: "group", "aria-label": label },
    options.map(([value, text]) => h("button", { type: "button", "aria-pressed": String(value === current), onclick: () => choose(value) }, text)));
}

const tip = h("div", { class: "tip", role: "tooltip", hidden: true });
document.body.append(tip);

function showTip(target, lines) {
  tip.replaceChildren(...lines.map((line, index) => h(index ? "span" : "strong", {}, line)));
  tip.hidden = false;
  const box = target.getBoundingClientRect();
  const width = tip.offsetWidth;
  tip.style.left = `${Math.min(Math.max(8, box.left + box.width / 2 - width / 2), window.innerWidth - width - 8)}px`;
  tip.style.top = `${box.top - tip.offsetHeight - 8 + window.scrollY}px`;
}

function hideTip() {
  tip.hidden = true;
}

window.addEventListener("hashchange", hideTip);

export function columns({ rows, value, label, tick, lines, href, height = 9 }) {
  const max = Math.max(1, ...rows.map(value));
  const plot = h("div", { class: "columns", role: "img", "aria-label": `${rows.length} columns, peak ${count(max)}` },
    rows.map((row) => {
      const size = value(row);
      const inner = h("span", { class: "column-bar" });
      inner.style.height = `${size ? Math.max(1, (100 * size) / max) : 0}%`;
      const props = { class: "column", onmouseenter: (event) => showTip(event.currentTarget, lines(row)), onmouseleave: hideTip, onfocus: (event) => showTip(event.currentTarget, lines(row)), onblur: hideTip };
      return href ? h("a", { ...props, href: href(row), "aria-label": lines(row).join(", ") }, inner) : h("span", { ...props, tabindex: "0", "aria-label": lines(row).join(", ") }, inner);
    }));
  plot.style.height = `${height}rem`;
  const axis = h("div", { class: "columns-axis" }, rows.map((row, index) => h("span", {}, tick(row, index) ?? "")));
  return h("figure", { class: "chart" }, h("div", { class: "chart-scale" }, h("span", {}, compact(max)), h("span", {}, "0")), h("div", { class: "chart-body" }, plot, axis),
    label ? h("figcaption", { class: "sr-only" }, label) : null);
}
