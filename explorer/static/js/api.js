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

export const links = {
  author: (name, tab) => `#/author/${enc(name)}/${tab}`,
  subreddit: (name, tab) => `#/subreddit/${enc(name)}/${tab}`,
};
