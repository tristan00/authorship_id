import { enc, get, links } from "./api.js";
import { patterns } from "./patterns.js";
import { attributeName, attributeValue, count, failed, h, loading, notFound, notice, panel, table, tally } from "./ui.js";

function profile(data) {
  const name = { title: "Attribute", kind: "mono", cell: (row) => attributeName(row.name) };
  const stated = { title: "Stated", kind: "mono", cell: (row) => attributeValue(row.name, row.stated, "not stated") };
  if (!data.published) {
    return [
      notice("info", `${data.author} has no published prediction.`, null),
      panel("Stated attributes", tally(data.attributes.length, "attribute", "attributes"), table({ columns: [name, stated], rows: data.attributes, empty: "No stated attributes", tall: true })),
    ];
  }
  const predicted = { title: "Predicted", kind: "mono", cell: (row) => attributeValue(row.name, row.predicted, "no value") };
  const statedCount = data.attributes.filter((row) => row.stated !== null).length;
  return panel("Attributes", `${tally(data.attributes.length, "attribute", "attributes")}, ${count(statedCount)} stated`,
    table({ columns: [name, stated, predicted], rows: data.attributes, empty: "No attributes", tall: true, rowClass: (row) => (row.stated === null ? "" : "stated") }));
}

function similar(data) {
  if (!data.vector) return notice("info", `${data.author} has no author vector.`, null);
  return panel("Nearest authors", tally(data.similar.length, "author", "authors"), table({
    columns: [
      { title: "Author", kind: "mono", cell: (row) => h("a", { href: links.author(row.author, "profile") }, row.author) },
      { title: "Cosine similarity", kind: "num", cell: (row) => String(row.similarity) },
      { title: "Usable texts", kind: "num", cell: (row) => count(row.usable_texts) },
    ],
    rows: data.similar,
    empty: "No neighbours",
  }));
}

const PAGES = {
  author: {
    kind: "Author",
    tabs: [
      { id: "profile", title: "Profile", render: profile },
      { id: "patterns", title: "Posting patterns", render: (data) => patterns(data, [["Posts", "posts"], ["Subreddits", "subreddits"]], true) },
      { id: "similar", title: "Similar authors", render: similar },
    ],
  },
  subreddit: {
    kind: "Subreddit",
    tabs: [{ id: "patterns", title: "Posting patterns", render: (data) => patterns(data, [["Posts", "posts"]], false) }],
  },
};

export function firstTab(type) {
  return PAGES[type].tabs[0].id;
}

export function entity(view, type, name, tab) {
  const page = PAGES[type];
  const active = page.tabs.find((each) => each.id === tab);
  if (active === undefined) {
    view.replaceChildren(notFound(`${page.kind} pages have no ${tab} tab.`));
    return;
  }
  document.title = `${name} · ${active.title} · explorer`;
  const body = h("div", { class: "tab-body", role: "tabpanel", "aria-label": active.title }, loading());
  view.replaceChildren(h("article", { class: "entity" },
    h("header", { class: "entity-head" }, h("span", { class: "entity-kind" }, page.kind), h("h1", { class: "entity-name" }, name)),
    h("nav", { class: "rail", "aria-label": `${page.kind} tabs` },
      page.tabs.map((each) => h("a", each.id === tab ? { href: links[type](name, each.id), "aria-current": "page" } : { href: links[type](name, each.id) }, each.title))),
    body));
  get(`/api/${type}/${enc(name)}/${tab}`).then(
    (data) => body.isConnected && body.replaceChildren(...[active.render(data)].flat()),
    (error) => body.isConnected && (error.status === 404 ? view.replaceChildren(notFound(error.message)) : body.replaceChildren(failed(error))),
  );
}
