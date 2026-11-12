import { enc, get, links } from "./api.js";
import { count, day, failed, h, loading, moment, notice, segmented } from "./ui.js";

const STATUS = { removed: "removed", empty: "empty" };

function permalink(record) {
  const post = record.link_id.replace(/^t3_/, "");
  return record.record_type === "post" ? `https://www.reddit.com/comments/${post}` : `https://www.reddit.com/comments/${post}/_/${record.record_id.replace(/^t1_/, "")}`;
}

function item(record, type) {
  const split = record.record_type === "post" && record.text ? record.text.indexOf("\n") : -1;
  const text = h("div", { class: "record-text" }, split > 0 ? [h("strong", { class: "record-title" }, record.text.slice(0, split)), record.text.slice(split).replace(/^\n+/, "")] : record.text ?? "");
  const more = h("button", { type: "button", class: "more", hidden: true }, "Show more");
  more.addEventListener("click", () => {
    const open = text.classList.toggle("open");
    more.textContent = open ? "Show less" : "Show more";
  });
  requestAnimationFrame(() => {
    if (text.scrollHeight > text.clientHeight + 2 || record.cut) more.hidden = false;
  });
  const where = type === "author"
    ? h("a", { class: "where", href: links.subreddit(record.subreddit, "records") }, `r/${record.subreddit}`)
    : record.author.startsWith("[") ? h("span", { class: "where" }, record.author) : h("a", { class: "where", href: links.author(record.author, "records") }, `u/${record.author}`);
  return h("article", { class: "record" },
    h("header", { class: "record-meta" },
      h("time", { datetime: new Date(record.at * 1000).toISOString() }, moment(record.at)),
      h("span", { class: `kind ${record.record_type}` }, record.record_type),
      where,
      record.link_flair ? h("span", { class: "flair" }, record.link_flair) : null,
      record.author_flair ? h("span", { class: "flair user" }, record.author_flair) : null,
      record.over_18 ? h("span", { class: "tag" }, "nsfw") : null,
      record.text_status in STATUS ? h("span", { class: "tag" }, STATUS[record.text_status]) : null,
      record.cut ? h("span", { class: "tag" }, "truncated") : null,
      h("a", { class: "out", href: permalink(record), target: "_blank", rel: "noopener noreferrer" }, "reddit ↗")),
    record.text ? text : null,
    record.text ? more : null);
}

function field(label, control) {
  return h("label", { class: "field" }, h("span", {}, label), control);
}

export function records(type, name, params, summary, choices) {
  const state = Object.fromEntries(["type", "subreddit", "author", "from", "to"].map((key) => [key, params.get(key) ?? ""]));
  const go = (changes) => {
    location.hash = links[type](name, "records", { ...state, ...changes });
  };
  const first = summary.first_seen === null ? null : day(summary.first_seen);
  const last = summary.last_seen === null ? null : day(summary.last_seen);
  const dates = ["from", "to"].map((key) => {
    const input = h("input", { type: "date", value: state[key], min: first, max: last });
    input.addEventListener("change", () => go({ [key]: input.value }));
    return field(key === "from" ? "From" : "To", input);
  });
  let scope;
  if (type === "author") {
    const select = h("select", {}, h("option", { value: "" }, "All subreddits"), state.subreddit ? h("option", { value: state.subreddit, selected: true }, `r/${state.subreddit}`) : null);
    choices.then((rows) => select.replaceChildren(h("option", { value: "" }, "All subreddits"),
      rows.map((row) => h("option", { value: row.subreddit, selected: row.subreddit === state.subreddit }, `r/${row.subreddit} (${count(row.texts)})`))), () => {});
    select.addEventListener("change", () => go({ subreddit: select.value }));
    scope = field("Subreddit", select);
  } else {
    const input = h("input", { type: "search", value: state.author, placeholder: "any author", spellcheck: "false" });
    input.addEventListener("change", () => go({ author: input.value.trim() }));
    scope = field("Author", input);
  }
  const active = Object.values(state).some(Boolean);
  const bar = h("div", { class: "toolbar" },
    segmented("Record type", [["", "All"], ["post", "Posts"], ["comment", "Comments"]], state.type, (value) => go({ type: value })),
    scope, dates,
    active ? h("a", { class: "clear", href: links[type](name, "records") }, "Clear filters") : null);
  const list = h("div", { class: "feed" }, loading("Loading records"));
  const footer = h("div", { class: "feed-foot" });

  async function load(before, replace) {
    try {
      const data = await get(links.api(`/api/${type}/${enc(name)}/records`, { ...state, before }));
      if (!list.isConnected) return;
      const items = data.records.map((record) => item(record, type));
      if (replace) list.replaceChildren(...(items.length ? items : [notice("info", "No records match these filters", null)]));
      else list.append(...items);
      footer.replaceChildren(data.next ? h("button", { type: "button", class: "load", onclick: (event) => {
        event.currentTarget.disabled = true;
        event.currentTarget.textContent = "Loading";
        load(data.next, false);
      } }, "Load more") : null);
    } catch (error) {
      if (list.isConnected) (replace ? list : footer).replaceChildren(failed(error));
    }
  }

  load(null, true);
  return [bar, list, footer];
}
