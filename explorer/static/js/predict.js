import { post } from "./api.js";
import { attributeName, attributeValue, count, failed, facts, h, loading, notice, panel, table, tally } from "./ui.js";

function result(data) {
  if (data.status === "empty") return notice("info", "The text is empty after cleaning.", null);
  return [
    panel("Input", null, facts([["Tokens", count(data.tokens)], ["Truncated", data.truncated ? "yes" : "no"]])),
    panel("Prediction", tally(data.attributes.length, "attribute", "attributes"), table({
      columns: [
        { title: "Attribute", kind: "mono", cell: (row) => attributeName(row.name) },
        { title: "Predicted", kind: "mono", cell: (row) => attributeValue(row.name, row.predicted, "no value") },
      ],
      rows: data.attributes,
      empty: "No attributes",
      tall: true,
    })),
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
