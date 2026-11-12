import { get, links } from "./api.js";
import { bar, columns, compact, count, failed, h, loading, panel, stats, table } from "./ui.js";

const MONTHS = new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone: "UTC" });

function month(text) {
  return MONTHS.format(new Date(`${text}-01T00:00:00Z`));
}

function ranking(rows, key, href, prefix) {
  const max = Math.max(1, ...rows.map((row) => row.texts));
  return table({
    columns: [
      { title: "#", kind: "num rank", cell: (row, index) => count(index + 1) },
      { title: "Name", kind: "mono", cell: (row) => h("a", { href: href(row[key]) }, `${prefix}${row[key]}`) },
      { title: "Texts", kind: "num", cell: (row) => compact(row.texts) },
      { title: "", kind: "gauge", cell: (row) => bar(row.texts, max) },
    ],
    rows,
    empty: "No rows",
  });
}

function status(data) {
  return h("ul", { class: "pills" }, data.checks.map((check) => h("li", { class: check.current ? "pill ok" : "pill stale", title: check.detail ?? "Current" },
    h("span", { class: "dot", "aria-hidden": "true" }), check.name, check.current ? null : h("span", { class: "pill-detail" }, check.detail))));
}

function overview(data) {
  const records = data.months.reduce((sum, row) => sum + row.records, 0);
  const span = data.months.length ? `${month(data.months[0].month)} – ${month(data.months.at(-1).month)}` : "none";
  return [
    stats([["Records", compact(records)], ["Authors", compact(data.author_total)], ["Subreddits", compact(data.subreddit_total)], ["Months", `${data.months.length} · ${span}`]]),
    columns({
      rows: data.months,
      value: (row) => row.records,
      lines: (row) => [month(row.month), `${count(row.records)} records`],
      tick: (row) => month(row.month),
      height: 6,
      label: "Records per month",
    }),
  ];
}

export function home(view) {
  document.title = "Overview · explorer";
  const head = h("div", { class: "overview" }, loading());
  const checks = h("div", {}, loading());
  const subreddits = h("div", {}, loading());
  const authors = h("div", {}, loading());
  const summary = panel("Data", null, head);
  const state = panel("Pipeline", null, checks);
  view.replaceChildren(h("div", { class: "home" }, summary, state,
    panel("Top subreddits", "by texts", subreddits), panel("Top authors", "by texts", authors)));
  get("/api/home").then((data) => {
    if (!view.isConnected) return;
    head.replaceChildren(...overview(data));
    subreddits.replaceChildren(ranking(data.subreddits, "subreddit", (name) => links.subreddit(name, "records"), "r/"));
    authors.replaceChildren(ranking(data.authors, "author", (name) => links.author(name, "records"), "u/"));
  }, (error) => head.replaceChildren(failed(error)));
  get("/api/status").then((data) => checks.replaceChildren(status(data)), (error) => checks.replaceChildren(failed(error)));
}
