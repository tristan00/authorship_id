export class RequestError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function call(path, init) {
  const response = await fetch(path, init);
  const payload = await response.json();
  if (!response.ok) throw new RequestError(response.status, payload.error);
  return payload;
}

export const enc = encodeURIComponent;

export function get(path) {
  return call(path, { headers: { Accept: "application/json" } });
}

export function post(path, body) {
  return call(path, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(body) });
}

function query(params) {
  const found = new URLSearchParams(Object.entries(params ?? {}).filter(([, value]) => value !== null && value !== undefined && value !== ""));
  return found.size ? `?${found}` : "";
}

export const links = {
  author: (name, tab, params) => `#/author/${enc(name)}/${tab}${query(params)}`,
  subreddit: (name, tab, params) => `#/subreddit/${enc(name)}/${tab}${query(params)}`,
  api: (path, params) => `${path}${query(params)}`,
};
