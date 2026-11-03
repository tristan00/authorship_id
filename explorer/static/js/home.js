import { get, links } from "./api.js";
import { count, fill, h, panel, table } from "./ui.js";

function ranking(rows, key, title, href) {
  return table({
    columns: [
      { title: "#", kind: "num rank", cell: (row, index) => count(index + 1) },
      { title, kind: "mono", cell: (row) => h("a", { href: href(row[key]) }, row[key]) },
      { title: "Texts", kind: "num", cell: (row) => count(row.texts) },
    ],
    rows,
    empty: "No rows",
  });
}

function checks(data) {
  return table({
    columns: [
      { title: "Check", kind: "", cell: (row) => h("strong", {}, row.name) },
      { title: "State", kind: "", cell: (row) => h("span", { class: row.current ? "flag ok" : "flag stale" }, row.current ? "current" : "not current") },
      { title: "Detail", kind: "", cell: (row) => row.detail },
    ],
    rows: data.checks,
    empty: "No checks",
  });
}

export function home(view) {
  document.title = "Index · explorer";
  const status = h("div", {});
  const subreddits = h("div", {});
  const authors = h("div", {});
  const statusPanel = panel("Data status", null, status);
  statusPanel.classList.add("status-panel");
  view.replaceChildren(h("div", { class: "home" },
    statusPanel,
    panel("Most active subreddits", "by texts", subreddits),
    panel("Most active authors", "by texts", authors)));
  const lists = get("/api/home");
  fill(status, get("/api/status"), checks);
  fill(subreddits, lists, (data) => ranking(data.subreddits, "subreddit", "Subreddit", (name) => links.subreddit(name, "patterns")));
  fill(authors, lists, (data) => ranking(data.authors, "author", "Author", (name) => links.author(name, "profile")));
}
