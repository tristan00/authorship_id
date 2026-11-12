import { post } from "./api.js";
import { attributeName, attributeValue, count, failed, facts, h, loading, notice, panel, table } from "./ui.js";

const ARROW = " › ";
let threshold = 0;

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function chains(items) {
  const chance = new Map(items.map((item) => [item.value, item.confidence]));
  const paths = [...chance.keys()];
  const leaves = paths.filter((path) => !paths.some((other) => other.startsWith(path + ARROW)));
  return leaves
    .map((path) => {
      const parts = path.split(ARROW);
      return parts
        .map((part, depth) => {
          const prefix = parts.slice(0, depth + 1).join(ARROW);
          return chance.has(prefix) ? `${part} ${percent(chance.get(prefix))}` : part;
        })
        .join(ARROW);
    })
    .join("; ");
}

function shown(row) {
  const predicted = row.predicted;
  if (!Array.isArray(predicted)) return attributeValue(row.name, `${predicted.value.toFixed(0)} (${predicted.low.toFixed(0)}–${predicted.high.toFixed(0)})`, "no value");
  return attributeValue(row.name, predicted.length ? chains(predicted) : null, "no value");
}

function filtered(attributes) {
  return attributes.flatMap((row) => {
    if (!Array.isArray(row.predicted)) return [row];
    const kept = row.predicted.filter((item) => item.confidence >= threshold);
    return threshold === 0 || kept.length ? [{ name: row.name, predicted: kept }] : [];
  });
}

function result(data) {
  if (data.status === "empty") return notice("info", "The text is empty after cleaning.", null);
  const slot = h("div", {});
  const meta = h("span", {});
  const picker = h("input", { type: "range", min: "0", max: "100", step: "1", value: String(Math.round(threshold * 100)), "aria-label": "Minimum prediction confidence" });
  const readout = h("output", {});

  function render() {
    const rows = filtered(data.attributes);
    readout.textContent = percent(threshold);
    meta.textContent = `${count(rows.length)} of ${count(data.attributes.length)} attributes`;
    slot.replaceChildren(
      table({
        columns: [
          { title: "Attribute", kind: "mono", cell: (row) => attributeName(row.name) },
          { title: "Predicted", kind: "mono", cell: shown },
        ],
        rows,
        empty: `No predictions at ${percent(threshold)} confidence or above`,
        tall: true,
      }),
    );
  }

  picker.addEventListener("input", () => {
    threshold = Number(picker.value) / 100;
    render();
  });
  render();
  return [
    panel("Input", null, facts([["Tokens", count(data.tokens)], ["Truncated", data.truncated ? "yes" : "no"]])),
    panel("Prediction", meta, h("div", { class: "filter" }, h("label", {}, "Minimum confidence", picker, readout), h("span", { class: "filter-note" }, "Ages and years show an 80% range and are always listed")), slot),
  ];
}

export function predict(view) {
  document.title = "Predict text · explorer";
  const text = h("textarea", { "aria-label": "Text to predict from", spellcheck: "false" });
  const run = h("button", { type: "button", class: "run" }, "Predict");
  const output = h("div", { class: "predict-out", "aria-live": "polite" });

  async function go() {
    run.disabled = true;
    output.replaceChildren(loading("Predicting"));
    try {
      const data = await post("/api/predict", { text: text.value });
      if (output.isConnected) output.replaceChildren(...[result(data)].flat());
    } catch (error) {
      if (output.isConnected) output.replaceChildren(failed(error));
    } finally {
      run.disabled = false;
    }
  }

  run.addEventListener("click", go);
  text.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !run.disabled) go();
  });
  view.replaceChildren(
    h("h1", { class: "page-title" }, "Predict text"),
    h("div", { class: "predict" }, h("div", { class: "predict-in" }, text, h("div", { class: "actions" }, run, h("kbd", {}, "Ctrl+Enter"))), output));
  text.focus();
}
