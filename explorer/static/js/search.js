import { enc, get, links } from "./api.js";
import { count, failed, h, loading } from "./ui.js";

const PAUSE_MS = 160;

function group(title, rows, key, href, query) {
  return h("section", { class: "hit-group" },
    h("h3", {}, title),
    rows.length
      ? h("ol", {}, rows.map((row) => h("li", {}, h("a", { href: href(row[key]) }, h("span", {}, row[key]), h("span", { class: "num" }, count(row.texts))))))
      : h("span", { class: "absent" }, `None start with ${query}`));
}

export function mountSearch(root) {
  const input = h("input", { type: "search", placeholder: "Author or subreddit prefix", autocomplete: "off", spellcheck: "false", "aria-label": "Search authors and subreddits" });
  const hits = h("div", { class: "hits", hidden: "" });
  root.append(input, hits);
  let timer = 0;
  let sequence = 0;

  async function lookup() {
    const query = input.value.trim();
    const ticket = ++sequence;
    if (query === "") {
      hits.hidden = true;
      hits.replaceChildren();
      return;
    }
    hits.hidden = false;
    hits.replaceChildren(loading("Searching"));
    try {
      const data = await get(`/api/search?q=${enc(query)}`);
      if (ticket !== sequence) return;
      hits.replaceChildren(
        group("Subreddits", data.subreddits, "subreddit", (name) => links.subreddit(name, "records"), data.query.toLowerCase()),
        group("Authors", data.authors, "author", (name) => links.author(name, "records"), data.query));
    } catch (error) {
      if (ticket === sequence) hits.replaceChildren(failed(error));
    }
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(lookup, PAUSE_MS);
  });
  input.addEventListener("focus", () => {
    if (hits.childElementCount) hits.hidden = false;
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hits.hidden = true;
    if (event.key === "ArrowDown" && hits.querySelector("a")) {
      event.preventDefault();
      hits.querySelector("a").focus();
    }
    if (event.key === "Enter" && hits.querySelector("a")) location.hash = hits.querySelector("a").getAttribute("href");
  });
  hits.addEventListener("keydown", (event) => {
    const anchors = [...hits.querySelectorAll("a")];
    const at = anchors.indexOf(document.activeElement);
    if (event.key === "Escape") {
      hits.hidden = true;
      input.focus();
    }
    if (event.key === "ArrowDown" && at < anchors.length - 1) {
      event.preventDefault();
      anchors[at + 1].focus();
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      (at > 0 ? anchors[at - 1] : input).focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) hits.hidden = true;
  });
  window.addEventListener("hashchange", () => {
    hits.hidden = true;
  });
}
