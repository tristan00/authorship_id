const SVG = "http://www.w3.org/2000/svg";
const UNITS = { age: "years" };
const grouped = new Intl.NumberFormat("en-US", { useGrouping: true, maximumFractionDigits: 0 });

export function h(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  node.append(...children.flat(Infinity).filter((child) => child !== null));
  return node;
}

export function count(value) {
  if (!Number.isInteger(value)) throw new Error(`Expected an integer count, received ${JSON.stringify(value)}`);
  return grouped.format(value);
}

export function tally(value, one, many) {
  return `${count(value)} ${value === 1 ? one : many}`;
}

export function absent(text) {
  return h("span", { class: "absent" }, text);
}

export function moment(seconds) {
  if (seconds === null) return absent("none");
  return new Date(seconds * 1000).toISOString().slice(0, 19).replace("T", " ") + " UTC";
}

export function attributeName(name) {
  return name.replaceAll("_", " ");
}

export function attributeValue(name, value, missing) {
  if (value === null) return absent(missing);
  return name in UNITS ? `${value} ${UNITS[name]}` : String(value);
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
