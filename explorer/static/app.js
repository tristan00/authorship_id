'use strict';

const main = document.getElementById('main');
let current = null;

function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (key.startsWith('on')) el.addEventListener(key.slice(2), value);
    else el.setAttribute(key, value);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid !== null && kid !== undefined && kid !== false) el.append(kid);
  }
  return el;
}

const links = {
  author: (name, tab) => `#/author/${encodeURIComponent(name)}${tab ? `/${tab}` : ''}`,
  subreddit: (name, tab) => `#/subreddit/${encodeURIComponent(name)}${tab ? `/${tab}` : ''}`,
  text: id => `#/text/${encodeURIComponent(id)}`,
};
const api = (...parts) => '/api/' + parts.map(encodeURIComponent).join('/');

const whole = new Intl.NumberFormat();
const timestamp = seconds => new Date(seconds * 1000).toISOString().replace('T', ' ').replace('.000Z', ' UTC');
const UNITS = { age: ' years', height: ' cm', weight: ' kg', income: ' USD a year' };
const plural = (count, word) => (count === 1 ? word : `${word}s`);
const raw = value => (value === null || value === undefined ? '' : String(value));
const shown = (attribute, value) => (value === null || value === undefined ? '' : `${value}${UNITS[attribute] || ''}`);

function label(name) {
  const words = name.replace(/_/g, ' ').trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

class Failure extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(url, signal, options) {
  const response = await fetch(url, { ...options, signal });
  const body = await response.json();
  if (!response.ok) throw new Failure(response.status, body.error);
  return body;
}

const describe = failure => (failure.status ? failure.message : 'The server could not be reached.');

function placeholder() {
  return h('div', { class: 'placeholder', 'aria-label': 'Loading' }, h('span'), h('span'), h('span'));
}

function failed(page, failure, retry) {
  if (failure.name === 'AbortError') return null;
  if (failure.status === 404) {
    page.missing(failure.message);
    return null;
  }
  return h('p', { class: 'error', role: 'alert' }, describe(failure), h('button', { onclick: retry }, 'Try again'));
}

function fill(box, url, render, page, options) {
  const start = () => fill(box, url, render, page, options);
  box.replaceChildren(placeholder());
  request(url, page.signal, options)
    .then(data => box.replaceChildren(...[render(data)].flat().filter(Boolean)))
    .catch(failure => {
      const shown = failed(page, failure, start);
      if (shown) box.replaceChildren(shown);
    });
  return box;
}

function section(title, note, content) {
  return h('section', { class: 'section' }, h('h2', {}, title), note && h('p', { class: 'note' }, note), h('div', { class: 'body' }, content));
}

function table(headings, rows) {
  return h('div', { class: 'table-wrap' }, h('table', { class: 'grid' },
    h('thead', {}, h('tr', {}, headings.map(heading => h('th', { scope: 'col' }, heading)))),
    h('tbody', {}, rows)));
}

const head = text => h('th', { scope: 'row' }, text);
const cell = content => h('td', {}, content);
const count = value => h('td', { class: 'num' }, whole.format(value));
const exact = value => h('td', { class: 'num' }, raw(value));
const pair = (name, value) => h('tr', {}, head(name), cell(value));

const nameList = rows => h('ul', { class: 'names' }, rows);
const nameRow = (href, name, note) => h('li', {}, h('a', { href }, name), note && h('span', { class: 'count' }, note));
const texts = number => `${whole.format(number)} ${plural(number, 'text')}`;

function startSearch() {
  const input = document.getElementById('search');
  const results = document.getElementById('results');
  let timer = null;
  let searching = null;

  const close = () => {
    clearTimeout(timer);
    if (searching) searching.abort();
    results.replaceChildren();
  };

  const show = (query, data) => {
    if (!data.authors.length && !data.subreddits.length) {
      results.replaceChildren(h('p', { class: 'search-state notice' }, `No author or subreddit starts with ${query}.`));
      return;
    }
    results.replaceChildren(
      h('div', {}, h('h2', {}, 'Authors'), data.authors.length
        ? nameList(data.authors.map(name => nameRow(links.author(name), name)))
        : h('p', { class: 'notice small' }, 'No matching authors.')),
      h('div', {}, h('h2', {}, 'Subreddits'), data.subreddits.length
        ? nameList(data.subreddits.map(name => nameRow(links.subreddit(name), name)))
        : h('p', { class: 'notice small' }, 'No matching subreddits.')),
    );
  };

  const run = (query, open) => {
    close();
    const mine = searching = new AbortController();
    request(`${api('search')}?q=${encodeURIComponent(query)}`, mine.signal)
      .then(data => {
        show(query, data);
        const hits = [...results.querySelectorAll('a')];
        const chosen = hits.find(hit => hit.textContent.toLowerCase() === query.toLowerCase()) || hits[0];
        if (open && chosen) location.hash = chosen.getAttribute('href');
      })
      .catch(failure => {
        if (failure.name === 'AbortError') return;
        results.replaceChildren(h('p', { class: 'search-state error', role: 'alert' }, describe(failure), h('button', { onclick: () => run(query, open) }, 'Try again')));
      });
  };

  input.addEventListener('input', () => {
    const query = input.value.trim();
    close();
    if (query) timer = setTimeout(() => run(query, false), 150);
  });
  input.addEventListener('keydown', event => {
    const query = input.value.trim();
    if (event.key === 'Enter' && query) run(query, true);
    if (event.key === 'Escape') close();
  });
  document.addEventListener('click', event => {
    if (event.target.closest('a') || !event.target.closest('.finder')) close();
  });
  return () => {
    close();
    input.value = '';
  };
}

const clearSearch = startSearch();

function home(page) {
  document.title = 'Explorer';
  const startRows = (rows, link) => nameList(rows.map(row => nameRow(link(row.name), row.name, texts(row.texts))));
  main.replaceChildren(
    fill(h('div'), api('starts'), data => h('div', { class: 'columns' },
      section('Most active subreddits', null, startRows(data.subreddits, links.subreddit)),
      section('Most active authors', null, startRows(data.authors, links.author))), page),
    fill(h('div'), api('status'), data => section('Data status', null, [
      h('p', { class: 'muted small' }, `${data.months.length} ${plural(data.months.length, 'month')} loaded: ${data.months.join(', ')}`),
      h('ul', { class: 'status' }, data.checks.map(check => h('li', { class: check.current ? 'current' : 'stale' },
        h('span', { class: 'dot', 'aria-hidden': 'true' }), h('span', { class: 'name' }, check.name), h('span', { class: 'detail' }, check.detail)))),
    ]), page),
  );
  document.getElementById('search').focus();
}

function authorLink(row) {
  return row.author_page ? h('a', { href: links.author(row.author) }, row.author) : h('span', {}, row.author || 'Unknown author');
}

function profileRow(item) {
  const stated = item.stated || {};
  const predicted = item.predicted || {};
  return h('tr', {},
    head(label(item.attribute)),
    cell(shown(item.attribute, stated.value)),
    exact(stated.support),
    exact(stated.share),
    cell(shown(item.attribute, predicted.value)),
    exact(predicted.probability),
    cell(shown(item.attribute, predicted.lower)),
    cell(shown(item.attribute, predicted.upper)));
}

function profile(data) {
  if (!data.attributes.length) {
    return h('p', { class: 'notice' }, 'This author has no stated attributes and the model has no prediction for them.');
  }
  return [
    data.attributes.every(item => item.stated === null) && h('p', { class: 'notice spaced' }, 'This author has not stated any attributes.'),
    !data.has_prediction && h('p', { class: 'notice spaced' }, 'The model has no prediction for this author.'),
    h('p', { class: 'note spaced' }, `Lower and upper bound an interval with mass ${data.interval_mass}.`),
    table(['Attribute', 'Stated', 'Stated support', 'Stated share', 'Predicted', 'Probability', 'Lower', 'Upper'], data.attributes.map(profileRow)),
  ];
}

const windowNote = data => (data.counted === data.texts
  ? `Counted over all ${texts(data.texts)}.`
  : `Counted over the newest ${whole.format(data.counted)} of ${texts(data.texts)}.`);

function timing(data) {
  return [
    section('Hour of day (UTC)', null, table(['Hour', 'Texts'], data.hours.map(row => {
      const hour = String(row.hour).padStart(2, '0');
      return h('tr', {}, head(`${hour}:00 to ${hour}:59`), count(row.texts));
    }))),
    section('Day of week (UTC)', null, table(['Day', 'Texts'], data.weekdays.map(row => h('tr', {}, head(row.day), count(row.texts))))),
    section('Month (UTC)', null, table(['Month', 'Texts'], data.months.map(row => h('tr', {}, head(row.month), count(row.texts))))),
  ];
}

function activity(page, url, totals, where) {
  const when = h('div');
  return [
    fill(h('div'), url, data => {
      when.replaceChildren(...timing(data));
      return section('Totals', null, table(['Measure', 'Value'], totals(data)));
    }, page),
    when,
    where,
  ];
}

function authorActivity(page, name) {
  const where = fill(h('div'), api('author', name, 'subreddits'), data => section('Subreddits', windowNote(data), table(['Subreddit', 'Texts'],
    data.subreddits.map(row => h('tr', {}, head(h('a', { href: links.subreddit(row.subreddit) }, row.subreddit)), count(row.texts))))), page);
  return activity(page, api('author', name, 'activity'), data => [
    pair('Texts', whole.format(data.texts)),
    pair('Posts', whole.format(data.posts)),
    pair('First seen', timestamp(data.first_seen)),
    pair('Last seen', timestamp(data.last_seen)),
  ], where);
}

function authorSimilar(page, name) {
  return fill(h('div'), api('author', name, 'similar'), data => {
    if (data.similar === null) return h('p', { class: 'notice' }, 'This author has no writing style vector, so similar authors cannot be found.');
    return section('Similar authors', `The ${data.similar.length} nearest authors by writing style vector.`, table(['Author', 'Cosine similarity', 'Usable texts'],
      data.similar.map(row => h('tr', {}, head(h('a', { href: links.author(row.author) }, row.author)), exact(row.similarity), count(row.usable_texts)))));
  }, page);
}

function authorProfile(page, name) {
  return fill(h('div'), api('author', name), profile, page);
}

function subredditActivity(page, name) {
  return activity(page, api('subreddit', name, 'activity'), data => [
    pair('Texts', whole.format(data.texts)),
    pair('First seen', timestamp(data.first_seen)),
    pair('Last seen', timestamp(data.last_seen)),
  ], null);
}

function subredditAuthors(page, name) {
  return fill(h('div'), api('subreddit', name, 'authors'), data => section('Authors', windowNote(data), table(['Author', 'Texts'],
    data.authors.map(row => h('tr', {}, head(authorLink(row)), count(row.texts))))), page);
}

const TABS = {
  author: [['profile', 'Profile', authorProfile], ['activity', 'Activity', authorActivity], ['similar', 'Similar authors', authorSimilar]],
  subreddit: [['activity', 'Activity', subredditActivity], ['authors', 'Authors', subredditAuthors]],
};

function entityPage(page, kind, name, tab) {
  const tabs = TABS[kind];
  const chosen = tab === undefined ? tabs[0] : tabs.find(([key]) => key === tab);
  if (!chosen) {
    showMissing(page, 'This page has no such tab.');
    return;
  }
  const [key, title, render] = chosen;
  document.title = `${name} - ${title} - Explorer`;
  main.replaceChildren(
    h('div', { class: 'page-title' }, h('h1', {}, name)),
    h('nav', { class: 'tabs', 'aria-label': 'Sections' }, tabs.map(([other, heading]) => h('a', other === key ? { href: links[kind](name, other), 'aria-current': 'page' } : { href: links[kind](name, other) }, heading))),
    h('div', { class: 'panel' }, render(page, name)),
  );
}

function candidates(item) {
  return item.candidates ? h('ul', { class: 'candidates' }, item.candidates.map(option => h('li', {}, h('span', {}, option.value), h('span', { class: 'num' }, raw(option.probability))))) : '';
}

function textPrediction(data) {
  if (data.status === 'empty') return h('p', { class: 'notice' }, 'The text is empty after cleaning, so there is nothing to predict.');
  return [
    section('Input', null, table(['Measure', 'Value'], [
      pair('Tokens', whole.format(data.tokens)),
      pair('Truncated', data.truncated ? 'Yes' : 'No'),
      pair('Model months', data.months.join(', ')),
    ])),
    section('Attributes', null, table(['Attribute', 'Predicted', 'Probability', 'Lower', 'Upper', 'Interval mass', 'Candidates'],
      Object.entries(data.attributes).map(([attribute, item]) => h('tr', {},
        head(label(attribute)),
        cell(shown(attribute, item.value)),
        exact(item.probability),
        cell(shown(attribute, item.lower)),
        cell(shown(attribute, item.upper)),
        exact(item.interval_mass),
        cell(candidates(item)))))),
  ];
}

function predictPage(page) {
  document.title = 'Predict text - Explorer';
  const input = h('textarea', { class: 'predict-input', rows: '10', 'aria-label': 'Text to predict from', spellcheck: 'false' });
  const output = h('div', { class: 'panel' });
  const run = event => {
    event.preventDefault();
    fill(output, api('predict'), textPrediction, page, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: input.value }) });
  };
  main.replaceChildren(
    h('div', { class: 'page-title' }, h('h1', {}, 'Predict text')),
    h('form', { class: 'predict', onsubmit: run }, input, h('div', {}, h('button', { type: 'submit' }, 'Predict'))),
    output,
  );
  input.focus();
}

function bodyOf(text) {
  if (text.body.trim()) return h('div', { class: 'body-text' }, text.body);
  const states = {
    removed: 'This text was removed or deleted before it was collected.',
    title_only: 'This post has a title but no body text.',
  };
  return h('p', { class: 'state body-text' }, states[text.status] || 'This text has no content.');
}

function textMeta(text) {
  return h('div', { class: 'meta' },
    authorLink(text),
    h('a', { href: links.subreddit(text.subreddit) }, text.subreddit),
    h('span', {}, timestamp(text.created_utc)),
    h('span', {}, text.type));
}

function parentItem(parent) {
  return h('li', {},
    parent.title && h('p', { class: 'thread-title' }, parent.title),
    textMeta(parent),
    bodyOf(parent),
    h('p', { class: 'small spaced' }, h('a', { href: links.text(parent.record_id) }, 'Open this text')));
}

function postLine(text) {
  if (text.type !== 'comment') return null;
  if (!text.post) return h('p', { class: 'muted small spaced' }, 'Its post is outside the loaded months.');
  return h('p', { class: 'small spaced' }, 'In post: ', h('a', { href: links.text(text.post.record_id) }, text.post.title || 'Untitled post'));
}

function textPage(page, id) {
  document.title = 'Text - Explorer';
  const box = h('div', { class: 'text-page' });
  main.replaceChildren(box);
  fill(box, api('text', id), text => {
    const heading = text.title || `Comment by ${text.author}`;
    document.title = `${heading} - Explorer`;
    const reading = h('article', { class: 'reading' }, h('h1', {}, heading), textMeta(text), postLine(text), bodyOf(text));
    const end = {
      outside: 'Earlier messages in this thread are outside the loaded months.',
      capped: `Only the nearest ${text.parents.length} levels above this text are shown.`,
    }[text.chain_end];
    if (text.parents.length) requestAnimationFrame(() => reading.scrollIntoView({ block: 'start' }));
    return [
      end && h('p', { class: 'notice small page-title' }, end),
      text.parents.length > 0 && h('ol', { class: 'thread' }, text.parents.map(parentItem)),
      reading,
    ];
  }, page);
}

function showMissing(page, message) {
  page.controller.abort();
  document.title = 'Not found - Explorer';
  main.replaceChildren(h('div', { class: 'page-title' },
    h('h1', {}, 'Not found'),
    h('p', { class: 'spaced' }, message),
    h('p', { class: 'spaced' }, h('a', { href: '#/' }, 'Back to start'))));
}

function route() {
  if (current) current.abort();
  const controller = current = new AbortController();
  const page = { signal: controller.signal, controller, missing: message => showMissing(page, message) };
  const path = location.hash.replace(/^#\/?/, '');
  clearSearch();
  window.scrollTo(0, 0);
  let parts;
  try {
    parts = path.split('/').map(decodeURIComponent);
  } catch {
    showMissing(page, 'This address is not valid.');
    return;
  }
  const [kind, name, tab] = parts;
  for (const link of document.querySelectorAll('.nav a')) {
    if (link.getAttribute('href') === `#/${kind}`) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  if (parts.length === 1 && kind === '') {
    home(page);
  } else if (parts.length === 1 && kind === 'predict') {
    predictPage(page);
  } else if (parts.length <= 3 && name && Object.hasOwn(TABS, kind)) {
    entityPage(page, kind, kind === 'subreddit' ? name.toLowerCase() : name, tab);
  } else if (parts.length === 2 && name && kind === 'text') {
    textPage(page, name);
  } else {
    showMissing(page, 'There is nothing at this address.');
  }
}

window.addEventListener('hashchange', route);
route();
