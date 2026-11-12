import { links } from "./api.js";
import { bar, columns, count, h, panel, table, tally } from "./ui.js";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function lines(title, row) {
  return [title, `${count(row.texts)} texts`, `${count(row.posts)} posts · ${count(row.texts - row.posts)} comments`];
}

function subreddits(type, name, rows) {
  const max = Math.max(1, ...rows.map((row) => row.texts));
  return table({
    columns: [
      { title: "Subreddit", kind: "mono", cell: (row) => h("a", { href: links.author(name, "records", { subreddit: row.subreddit }) }, `r/${row.subreddit}`) },
      { title: "Texts", kind: "num", cell: (row) => count(row.texts) },
      { title: "Posts", kind: "num", cell: (row) => count(row.posts) },
      { title: "", kind: "gauge", cell: (row) => bar(row.texts, max) },
      { title: "", kind: "num", cell: (row) => h("a", { href: links.subreddit(row.subreddit, "records"), title: `Open r/${row.subreddit}` }, "open") },
    ],
    rows,
    empty: "No records",
    tall: true,
  });
}

export function activity(type, name, data) {
  const link = links[type];
  const timeline = columns({
    rows: data.day,
    value: (row) => row.texts,
    lines: (row) => [...lines(row.day, row), "Click to read this day"],
    tick: (row) => (row.day.endsWith("-01") ? row.day.slice(0, 7) : null),
    href: (row) => link(name, "records", { from: row.day, to: row.day }),
    label: "Texts per day",
  });
  const hours = columns({
    rows: data.hour,
    value: (row) => row.texts,
    lines: (row) => lines(`${String(row.hour).padStart(2, "0")}:00–${String(row.hour).padStart(2, "0")}:59 UTC`, row),
    tick: (row) => (row.hour % 3 === 0 ? String(row.hour).padStart(2, "0") : null),
    height: 7,
    label: "Texts by hour of day",
  });
  const weekdays = columns({
    rows: data.weekday,
    value: (row) => row.texts,
    lines: (row) => lines(row.weekday, row),
    tick: (row, index) => DAYS[index],
    height: 7,
    label: "Texts by day of week",
  });
  const blocks = [panel("Texts per day", `${data.day.length} days · click a day to read it`, timeline)];
  blocks[0].classList.add("span-all");
  blocks.push(panel("Hour of day", "UTC", hours), panel("Day of week", "UTC", weekdays));
  if ("where" in data) {
    const where = panel("Subreddits", tally(data.where.length, "subreddit", "subreddits"), subreddits(type, name, data.where));
    where.classList.add("span-all");
    blocks.push(where);
  }
  return h("div", { class: "grid-2" }, blocks);
}
