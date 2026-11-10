import { links } from "./api.js";
import { bar, count, facts, h, moment, panel, table, tally } from "./ui.js";

function spread(rows, label, title, posts) {
  const max = Math.max(...rows.map((row) => row.texts));
  return table({
    columns: [
      { title, kind: "mono", cell: label },
      { title: "Texts", kind: "num", cell: (row) => count(row.texts) },
      ...(posts ? [{ title: "Posts", kind: "num", cell: (row) => count(row.posts) }] : []),
      { title: "", kind: "gauge", cell: (row) => bar(row.texts, max) },
    ],
    rows,
    empty: "No records",
  });
}

export function patterns(data, extra, posts) {
  const totals = data.totals;
  const blocks = [
    panel("Totals", null, facts([
      ["Texts", count(totals.texts)],
      ...extra.map(([title, key]) => [title, count(totals[key])]),
      ["First seen", moment(totals.first_seen)],
      ["Last seen", moment(totals.last_seen)],
    ])),
  ];
  if ("where" in data) {
    const where = panel("Where", tally(data.where.length, "subreddit", "subreddits"),
      spread(data.where, (row) => h("a", { href: links.subreddit(row.subreddit, "patterns") }, row.subreddit), "Subreddit", posts));
    where.classList.add("wide");
    blocks.push(where);
  }
  blocks.push(
    panel("Hour of day", "UTC", spread(data.hour, (row) => `${String(row.hour).padStart(2, "0")}:00`, "Hour", posts)),
    panel("Day of week", "UTC", spread(data.weekday, (row) => row.weekday, "Day", posts)),
    panel("Month", "UTC", spread(data.month, (row) => row.month, "Month", posts)),
  );
  return h("div", { class: "sheet" }, blocks);
}
