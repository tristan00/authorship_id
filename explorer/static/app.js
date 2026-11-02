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
  author: name => `#/author/${encodeURIComponent(name)}`,
  subreddit: name => `#/subreddit/${encodeURIComponent(name)}`,
  text: id => `#/text/${encodeURIComponent(id)}`,
};
const api = (...parts) => '/api/' + parts.map(encodeURIComponent).join('/');

const whole = new Intl.NumberFormat();
const compact = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });
const dateOnly = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
const dateTime = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'UTC', timeZoneName: 'short' });
const day = seconds => dateOnly.format(new Date(seconds * 1000));
const moment = seconds => dateTime.format(new Date(seconds * 1000));
const percent = share => `${Math.round(share * 100)}%`;
const UNITS = { age: ' years', height: ' cm', weight: ' kg', income: ' USD a year', birth_year: '' };
const amount = (attribute, value) => (attribute === 'birth_year' ? String(Math.round(value)) : whole.format(Math.round(value)));
const PREDICTED_SHOWN = 10;
const plural = (count, word) => (count === 1 ? word : `${word}s`);

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

async function getJson(url, signal) {
  const response = await fetch(url, { signal });
  const body = await response.json();
  if (!response.ok) throw new Failure(response.status, body.error);
  return body;
}

const describe = failure => (failure.status ? failure.message : 'The server could not be reached.');

function placeholder() {
  return h('div', { class: 'placeholder', 'aria-label': 'Loading' }, h('span'), h('span'), h('span'));
}

function inlinePlaceholder() {
  return h('span', { class: 'inline-placeholder', 'aria-label': 'Loading' });
}

function failed(page, failure, retry) {
  if (failure.name === 'AbortError') return null;
  if (failure.status === 404) {
    page.missing(failure.message);
    return null;
  }
  return h('p', { class: 'error', role: 'alert' }, describe(failure), h('button', { onclick: retry }, 'Try again'));
}

function fill(box, url, render, page, waiting = placeholder) {
  const start = () => fill(box, url, render, page, waiting);
  box.replaceChildren(waiting());
  getJson(url, page.signal)
    .then(data => box.replaceChildren(...[render(data)].flat()))
    .catch(failure => {
      const shown = failed(page, failure, start);
      if (shown) box.replaceChildren(shown);
    });
}

function section(title, note, content) {
  return h('section', { class: 'section' }, h('h2', {}, title), note && h('p', { class: 'note' }, note), h('div', { class: 'body' }, content));
}

function loaded(title, note, url, render, page) {
  const box = h('div');
  fill(box, url, render, page);
  return section(title, note, box);
}

const nameList = rows => h('ul', { class: 'names' }, rows);
const nameRow = (href, name, count) => h('li', {}, h('a', { href }, name), count && h('span', { class: 'count' }, count));

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
    getJson(`${api('search')}?q=${encodeURIComponent(query)}`, mine.signal)
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
  const note = 'Approximate counts from database statistics.';
  const startRows = (rows, link) => nameList(rows.map(row => nameRow(link(row.name), row.name, `about ${compact.format(row.texts)} texts`)));
  const starting = h('div');
  fill(starting, api('starts'), data => h('div', { class: 'columns' },
    section('Most active subreddits', note, startRows(data.subreddits, links.subreddit)),
    section('Most active authors', note, startRows(data.authors, links.author))), page);
  main.replaceChildren(
    starting,
    loaded('Data status', null, api('status'), data => [
      h('p', { class: 'muted small' }, `${data.months.length} ${plural(data.months.length, 'month')} loaded: ${data.months.join(', ')}`),
      h('ul', { class: 'status' }, data.checks.map(check => h('li', { class: check.current ? 'current' : 'stale' },
        h('span', { class: 'dot', 'aria-hidden': 'true' }), h('span', { class: 'name' }, check.name), h('span', { class: 'detail' }, check.detail)))),
    ], page),
  );
  document.getElementById('search').focus();
}

function authorLink(row) {
  return row.author_page ? h('a', { href: links.author(row.author) }, row.author) : h('span', {}, row.author || 'Unknown author');
}

function textRow(text, show) {
  const missingText = text.status === 'removed' ? 'Removed' : 'No text';
  const title = text.title || text.excerpt || missingText;
  const classes = ['item-title', text.title && 'post', title === missingText && 'state'].filter(Boolean).join(' ');
  return h('li', {},
    h('a', { class: classes, href: links.text(text.record_id) }, title),
    text.title && text.excerpt && h('p', { class: 'excerpt' }, text.excerpt),
    h('div', { class: 'meta' },
      show === 'subreddit' ? h('a', { href: links.subreddit(text.subreddit) }, text.subreddit) : authorLink(text),
      h('span', {}, day(text.created_utc)),
      show === 'subreddit' && h('span', {}, text.type)));
}

function feed(url, show, emptyMessage, page) {
  const list = h('ul', { class: 'texts' });
  const foot = h('div', { class: 'foot' });
  let cursor = null;
  const more = () => {
    foot.replaceChildren(placeholder());
    getJson(cursor ? `${url}?before=${encodeURIComponent(cursor)}` : url, page.signal).then(data => {
      data.texts.forEach(row => list.append(textRow(row, show)));
      cursor = data.next;
      foot.replaceChildren(...[
        !list.children.length && !cursor && h('p', { class: 'notice' }, emptyMessage),
        !data.texts.length && cursor && h('p', { class: 'notice small' }, 'No posts among these texts. Older ones may have some.'),
        cursor && h('button', { onclick: more }, 'Load more'),
      ].filter(Boolean));
    }).catch(failure => {
      const shown = failed(page, failure, more);
      if (shown) foot.replaceChildren(shown);
    });
  };
  more();
  return h('div', {}, list, foot);
}

function predictedCell(attribute, predicted) {
  if (predicted.kind === 'numeric') {
    return [
      h('span', {}, amount(attribute, predicted.value) + UNITS[attribute]),
      h('span', { class: 'extra' }, `range ${amount(attribute, predicted.lower)} to ${amount(attribute, predicted.upper)}`),
    ];
  }
  return [h('span', {}, predicted.value), h('span', { class: 'extra' }, percent(predicted.probability))];
}

function statedCell(attribute, value) {
  return attribute in UNITS && Number.isFinite(Number(value)) ? amount(attribute, Number(value)) + UNITS[attribute] : value;
}

function profileRow(item) {
  return h('tr', {},
    h('th', { scope: 'row' }, label(item.attribute)),
    item.stated === null ? h('td') : h('td', { 'data-label': 'Stated' }, statedCell(item.attribute, item.stated)),
    item.predicted ? h('td', { 'data-label': 'Predicted' }, predictedCell(item.attribute, item.predicted)) : h('td'));
}

function profile(data) {
  if (!data.stated.length && !data.has_prediction) {
    return h('p', { class: 'notice' }, 'This author has no stated attributes and the model has no prediction for them.');
  }
  const body = h('tbody', {}, data.stated.map(profileRow));
  if (data.stated.length && data.predicted_only.length) {
    body.append(h('tr', { class: 'group' }, h('th', { colspan: '3' }, 'Predicted only, most confident first')));
  }
  body.append(...data.predicted_only.slice(0, PREDICTED_SHOWN).map(profileRow));
  const rest = data.predicted_only.slice(PREDICTED_SHOWN);
  const expand = rest.length > 0 && h('button', {
    class: 'spaced',
    onclick: event => {
      body.append(...rest.map(profileRow));
      event.target.remove();
    },
  }, `Show ${rest.length} more ${plural(rest.length, 'prediction')}`);
  return [
    data.has_prediction && data.stale && h('p', { class: 'banner' }, 'Predictions predate the current claims.'),
    !data.stated.length && h('p', { class: 'notice spaced' }, 'This author has not stated any attributes.'),
    !data.has_prediction && h('p', { class: 'notice spaced' }, 'The model has no prediction for this author.'),
    h('table', { class: 'profile' }, h('thead', {}, h('tr', {}, h('th', {}, 'Attribute'), h('th', {}, 'Stated'), h('th', {}, 'Predicted'))), body),
    expand,
    data.has_prediction && h('p', { class: 'note spaced' }, `Ranges are ${percent(data.interval_mass)} intervals. Percentages are model probabilities.`),
  ].filter(Boolean);
}

function fact(word, count) {
  return h('span', {}, h('b', {}, whole.format(count)), ` ${plural(count, word)}`);
}

function authorPage(page, name) {
  document.title = `${name} - Explorer`;
  const facts = h('div', { class: 'facts' });
  fill(facts, api('author', name, 'activity'), data => [
    fact('text', data.texts),
    fact('post', data.posts),
    h('span', {}, `First seen ${day(data.first_seen)}`),
    h('span', {}, `Last seen ${day(data.last_seen)}`),
  ], page, inlinePlaceholder);
  main.replaceChildren(
    h('div', { class: 'page-title' }, h('h1', {}, name), facts),
    h('div', { class: 'split' },
      h('div', {},
        loaded('Profile', null, api('author', name), profile, page),
        section('Newest texts', null, feed(api('author', name, 'texts'), 'subreddit', 'This author has no texts.', page))),
      h('aside', {},
        loaded('Where they post', 'From their newest 1,000 texts.', api('author', name, 'subreddits'), data => (
          nameList(data.subreddits.map(row => nameRow(links.subreddit(row.subreddit), row.subreddit, `${whole.format(row.texts)} ${plural(row.texts, 'text')}`)))), page),
        loaded('Most similar writers', 'By writing style.', api('author', name, 'similar'), data => {
          if (data.similar === null) return h('p', { class: 'notice' }, 'This author has no writing style vector, so similar writers cannot be found.');
          return nameList(data.similar.map(row => nameRow(links.author(row.author), row.author, `${percent(row.similarity)} match`)));
        }, page))),
  );
}

function subredditPage(page, raw) {
  const name = raw.toLowerCase();
  document.title = `${name} - Explorer`;
  const facts = h('div', { class: 'facts' });
  fill(facts, api('subreddit', name, 'activity'), data => [
    fact('text', data.texts),
    h('span', {}, `First seen ${day(data.first_seen)}`),
    h('span', {}, `Last seen ${day(data.last_seen)}`),
  ], page, inlinePlaceholder);
  main.replaceChildren(
    h('div', { class: 'page-title' }, h('h1', {}, name), facts),
    h('div', { class: 'split' },
      h('div', {}, section('Newest posts', null, feed(api('subreddit', name, 'posts'), 'author', 'This subreddit has no posts.', page))),
      h('aside', {},
        loaded('Authors recently active', 'From the newest 1,000 texts here.', api('subreddit', name, 'authors'), data => (
          data.authors.length
            ? nameList(data.authors.map(row => nameRow(links.author(row.author), row.author, `${whole.format(row.texts)} ${plural(row.texts, 'text')}`)))
            : h('p', { class: 'notice' }, 'No named authors in the newest texts.')), page))),
  );
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
    h('span', {}, moment(text.created_utc)),
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
    ].filter(Boolean);
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
  const [kind, name] = parts;
  if (parts.length === 1 && kind === '') {
    home(page);
  } else if (parts.length === 2 && name && kind === 'author') {
    authorPage(page, name);
  } else if (parts.length === 2 && name && kind === 'subreddit') {
    subredditPage(page, name);
  } else if (parts.length === 2 && name && kind === 'text') {
    textPage(page, name);
  } else {
    showMissing(page, 'There is nothing at this address.');
  }
}

window.addEventListener('hashchange', route);
route();
