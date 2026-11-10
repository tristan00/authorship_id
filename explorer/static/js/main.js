import { links } from "./api.js";
import { entity, firstTab } from "./entity.js";
import { home } from "./home.js";
import { predict } from "./predict.js";
import { mountSearch } from "./search.js";
import { notFound } from "./ui.js";

const view = document.getElementById("view");

function parts() {
  return location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
}

function mark(section) {
  for (const link of document.querySelectorAll("[data-section]")) {
    if (link.dataset.section === section) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

function route() {
  window.scrollTo(0, 0);
  let path;
  try {
    path = parts();
  } catch {
    mark(null);
    view.replaceChildren(notFound(`Malformed address ${location.hash}`));
    return;
  }
  const [first, name, tab, ...rest] = path;
  if (path.length === 1 && first === "") {
    mark("home");
    home(view);
  } else if (path.length === 1 && first === "predict") {
    mark("predict");
    predict(view);
  } else if ((first === "author" || first === "subreddit") && name !== undefined && rest.length === 0) {
    mark(null);
    if (tab === undefined) location.replace(links[first](name, firstTab(first)));
    else entity(view, first, name, tab);
  } else {
    mark(null);
    document.title = "Not found · explorer";
    view.replaceChildren(notFound(`No page at ${location.hash}`));
  }
}

mountSearch(document.getElementById("finder"));
window.addEventListener("hashchange", route);
route();
