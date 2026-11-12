import { enc, get, links } from "./api.js";
import { activity } from "./activity.js";
import { records } from "./records.js";
import { attributeName, attributeValue, bar, compact, count, day, failed, h, loading, notFound, notice, paths, stats, table } from "./ui.js";

function attributes(data) {
  const name = { title: "Attribute", kind: "mono", cell: (row) => attributeName(row.name) };
  const stated = { title: "Stated", kind: "mono", cell: (row) => attributeValue(row.name, row.stated, "—") };
  const predicted = { title: "Predicted", kind: "mono", cell: (row) => (row.predicted ? paths(row.predicted.split("; ").map((chain) => chain.split(" › "))) : attributeValue(row.name, null, "—")) };
  return h("section", { class: "panel" }, table({
    columns: data.published ? [name, stated, predicted] : [name, stated],
    rows: data.attributes,
    empty: "No attributes",
    rowClass: (row) => (row.stated === null ? "" : "stated"),
  }));
}

function similar(data) {
  if (!data.vector) return notice("info", "No author vector", null);
  return h("section", { class: "panel" }, table({
    columns: [
      { title: "#", kind: "num rank", cell: (row, index) => count(index + 1) },
      { title: "Author", kind: "mono", cell: (row) => h("a", { href: links.author(row.author, "records") }, row.author) },
      { title: "Similarity", kind: "num", cell: (row) => row.similarity.toFixed(3) },
      { title: "", kind: "gauge", cell: (row) => bar(Math.max(0, row.similarity), 1) },
      { title: "Texts used", kind: "num", cell: (row) => count(row.usable_texts) },
    ],
    rows: data.similar,
    empty: "No neighbours",
  }));
}

function authors(name, data) {
  const max = Math.max(1, ...data.authors.map((row) => row.texts));
  return h("section", { class: "panel" }, table({
    columns: [
      { title: "#", kind: "num rank", cell: (row, index) => count(index + 1) },
      { title: "Author", kind: "mono", cell: (row) => h("a", { href: links.author(row.author, "records") }, row.author) },
      { title: "Texts", kind: "num", cell: (row) => count(row.texts) },
      { title: "Posts", kind: "num", cell: (row) => count(row.posts) },
      { title: "", kind: "gauge", cell: (row) => bar(row.texts, max) },
      { title: "", kind: "num", cell: (row) => h("a", { href: links.subreddit(name, "records", { author: row.author }) }, "records here") },
    ],
    rows: data.authors,
    empty: "No authors",
  }));
}

const PAGES = {
  author: {
    kind: "u/",
    external: (name) => `https://www.reddit.com/user/${enc(name)}`,
    numbers: (data) => [["Texts", compact(data.texts)], ["Posts", compact(data.posts)], ["Comments", compact(data.texts - data.posts)], ["Subreddits", compact(data.subreddits)],
      ["First seen", day(data.first_seen)], ["Last seen", day(data.last_seen)]],
    tabs: [
      { id: "records", title: "Records" },
      { id: "profile", title: "Attributes", render: (name, data) => attributes(data) },
      { id: "patterns", title: "Activity", render: (name, data) => activity("author", name, data) },
      { id: "similar", title: "Similar authors", render: (name, data) => similar(data) },
    ],
  },
  subreddit: {
    kind: "r/",
    external: (name) => `https://www.reddit.com/r/${enc(name)}`,
    numbers: (data) => [["Texts", compact(data.texts)], ["Posts", compact(data.posts)], ["Comments", compact(data.texts - data.posts)],
      ["First seen", day(data.first_seen)], ["Last seen", day(data.last_seen)]],
    tabs: [
      { id: "records", title: "Records" },
      { id: "patterns", title: "Activity", render: (name, data) => activity("subreddit", name, data) },
      { id: "authors", title: "Top authors", render: authors },
    ],
  },
};

export function firstTab(type) {
  return PAGES[type].tabs[0].id;
}

async function body(slot, type, name, tab, params, summary) {
  if (tab.id === "records") {
    const choices = type === "author" ? get(`/api/author/${enc(name)}/patterns`).then((data) => data.where) : null;
    const known = await summary;
    if (slot.isConnected) slot.replaceChildren(...records(type, name, params, known, choices));
    return;
  }
  const data = await get(links.api(`/api/${type}/${enc(name)}/${tab.id}`, Object.fromEntries(params)));
  if (slot.isConnected) slot.replaceChildren(...[tab.render(name, data)].flat());
}

export function entity(view, type, name, tab, params) {
  const page = PAGES[type];
  const active = page.tabs.find((each) => each.id === tab);
  if (active === undefined) {
    view.replaceChildren(notFound(`No ${tab} tab here`));
    return;
  }
  document.title = `${page.kind}${name} · ${active.title}`;
  const numbers = h("div", { class: "entity-stats" });
  const slot = h("div", { class: "tab-body", role: "tabpanel", "aria-label": active.title }, loading());
  view.replaceChildren(h("article", { class: "entity" },
    h("header", { class: "entity-head" },
      h("h1", { class: "entity-name" }, h("span", { class: "entity-kind" }, page.kind), name),
      h("a", { class: "out", href: page.external(name), target: "_blank", rel: "noopener noreferrer" }, "reddit ↗"),
      numbers),
    h("nav", { class: "tabs", "aria-label": "Sections" },
      page.tabs.map((each) => h("a", { href: links[type](name, each.id), "aria-current": each.id === tab ? "page" : null }, each.title))),
    slot));
  const summary = get(`/api/${type}/${enc(name)}/summary`);
  summary.then((data) => numbers.isConnected && numbers.replaceChildren(stats(page.numbers(data))), () => {});
  body(slot, type, name, active, params, summary).catch((error) => {
    if (!slot.isConnected) return;
    if (error.status === 404) view.replaceChildren(notFound(error.message));
    else slot.replaceChildren(failed(error));
  });
}
