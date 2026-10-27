const head = document.getElementById('head');
const main = document.getElementById('main');
const state = { page: null, request: 0 };
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const fmt = (n) => Number(n).toLocaleString('en-US');
const enc = encodeURIComponent;
const plural = (n, word) => `${fmt(n)} ${word}${n === 1 ? '' : 's'}`;
const stamp = (utc) => new Date(utc * 1000).toISOString().slice(0, 16).replace('T', ' ');
const date = (utc) => stamp(utc).slice(0, 10);
const range = (rows) => rows.length ? `${date(Math.min(...rows.map((r) => r.first_utc)))} – ${date(Math.max(...rows.map((r) => r.last_utc)))}` : 'No activity';
const day = (utc) => { const d = new Date(utc * 1000); return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`; };
const userLink = (name) => name === '[deleted]' ? '<span>[deleted]</span>' : `<a href="#/u/${enc(name)}">u/${esc(name)}</a>`;
const subLink = (name) => `<a href="#/r/${enc(name)}">r/${esc(name)}</a>`;
const textLink = (id, label, cls = 'mono') => `<a class="${cls}" href="#/t/${enc(id)}">${esc(label ?? id)}</a>`;
const mono = (s) => `<span class="mono">${esc(s)}</span>`;
const quiet = (s) => `<span class="mono" style="font-size: 12px; color: var(--ink-3)">${s}</span>`;
const created = (utc) => quiet(stamp(utc));
const label = (attribute) => esc(attribute.replaceAll('_', ' '));
const suspectBox = (record, attribute, value, checked) => `<label class="flag"><input type="checkbox" data-record="${esc(record)}" data-attribute="${esc(attribute)}" data-value="${esc(value)}"${checked ? ' checked' : ''}>suspect</label>`;

async function get(path, init) {
  const response = await fetch(`/api/${path}`, init);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error);
  return body;
}

function tabs(list, active, base) {
  return `<div class="tabs" role="tablist">${list.map(([key, label, count]) => `<a class="tab" role="tab" aria-selected="${key === active}" href="${base}/${key}">${esc(label)}${count ? `<span class="count">${esc(count)}</span>` : ''}</a>`).join('')}</div>`;
}

function table(columns, rows, minWidth) {
  const grid = `grid-template-columns: ${columns.map((c) => c.w).join(' ')}`;
  const header = `<div class="tr th" style="${grid}">${columns.map((c) => `<div class="${c.num ? 'num' : ''}">${c.head ?? esc(c.label)}</div>`).join('')}</div>`;
  const filters = columns.some((c) => c.filter) ? `<div class="tr th filter-row" style="${grid}">${columns.map((c) => `<div>${c.filter ?? ''}</div>`).join('')}</div>` : '';
  const body = rows.map((r, i) => `<div class="tr" style="${grid}">${columns.map((c) => `<div class="${c.num ? 'num' : ''} ${c.cls ?? ''}">${c.cell(r, i)}</div>`).join('')}</div>`).join('');
  return `<div class="table-box"><div class="table" role="table" style="min-width: ${minWidth}px">${header}${filters}${body}</div></div>`;
}

function header(crumbs, body, tabList) {
  head.innerHTML = `<div class="wrap head"><nav class="crumbs" aria-label="Breadcrumb">${crumbs.join('<span aria-hidden="true">/</span>')}</nav>${body}${tabList}</div>`;
}

function more(id, shown, total, noun) {
  return shown < total ? `<button type="button" class="more" data-more="${id}">Show more ${noun} (${fmt(shown)} of ${fmt(total)})</button>` : '';
}

function pageTitle(name, summary) {
  return `<div class="page-title"><h1>${name}</h1><p class="note">${summary}</p></div>`;
}

async function usersPage(params, request) {
  const key = `users?${params}`;
  if (state.page?.key !== key) {
    main.innerHTML = '<p class="note">Loading…</p>';
    const data = await get(key);
    if (request !== state.request) return;
    state.page = { key, data, more: (which, offset) => `users/page?${params}&offset=${offset}` };
  }
  const { total, users, subreddits } = state.page.data;
  const sub = params.get('sub') ?? '';
  main.innerHTML = `${pageTitle('Users', `${mono(fmt(total))} users · ${range(subreddits)}`)}
    <form class="filters" data-page="users">
      <label class="field grow">Name contains<input name="q" type="search" value="${esc(params.get('q'))}" placeholder="Any part of a username" autocomplete="off"></label>
      <label class="field">Subreddit<select name="sub"><option value="">All subreddits</option>${subreddits.map((s) => `<option${s.subreddit === sub ? ' selected' : ''}>${esc(s.subreddit)}</option>`).join('')}</select></label>
    </form>
    <section class="panel" aria-label="Users">${table([
      { label: 'user', w: 'minmax(200px, 1fr)', cls: 'clip', cell: (u) => userLink(u.author) },
      { label: 'texts ↓', w: '110px', num: true, cell: (u) => fmt(u.texts) },
      { label: 'posts', w: '90px', num: true, cell: (u) => fmt(u.posts) },
      { label: 'comments', w: '110px', num: true, cell: (u) => fmt(u.texts - u.posts) },
      { label: 'subreddits', w: '110px', num: true, cell: (u) => fmt(u.subs) },
      { label: 'first text', w: '120px', cell: (u) => quiet(date(u.first_utc)) },
      { label: 'last text', w: '120px', cell: (u) => quiet(date(u.last_utc)) },
    ], users, 860)}${more('users', users.length, total, 'users')}</section>`;
}

function sortHead(params, page, defaults, column, text, title, numeric) {
  const [sort, dir] = [params.get('sort') ?? defaults[0], params.get('dir') ?? defaults[1]];
  const next = new URLSearchParams(params);
  next.set('sort', column);
  next.set('dir', sort === column ? (dir === 'desc' ? 'asc' : 'desc') : numeric ? 'desc' : 'asc');
  return `<a class="sort" href="#/${page}?${next}" title="${esc(title)}">${esc(text)}${sort === column ? (dir === 'desc' ? ' ↓' : ' ↑') : ''}</a>`;
}

const cellFilter = (params, name, hint) => `<input class="cell-filter" name="${name}" type="search" value="${esc(params.get(name) ?? '')}" placeholder="${esc(hint)}" aria-label="${esc(`${name} filter, ${hint}`)}" autocomplete="off">`;
const cellChoice = (params, name, choices) => `<select class="cell-filter" name="${name}" aria-label="${name} filter">${choices.map(([v, l]) => `<option value="${v}"${v === (params.get(name) ?? '') ? ' selected' : ''}>${l}</option>`).join('')}</select>`;

const TEXT_NOTE = `<p class="note">Counts are per text. <strong>Claims</strong>: self claims this text contributed to its author's profile.
  <strong>Incohesive</strong>: those about an attribute where the author's texts disagree with each other.
  <strong>Outvoted</strong>: those that lost, because the author's other texts settled on a different value.
  Number filters take <span class="mono">5</span>, <span class="mono">&gt;2</span>, <span class="mono">&lt;=3</span> or <span class="mono">2..8</span>; created takes dates the same way, such as <span class="mono">2026-02</span> or <span class="mono">&gt;2026-01-15</span>.</p>`;

async function textList(params, request, user) {
  const path = user ? `user/${enc(user)}/texts` : 'texts';
  const key = `${path}?${params}`;
  if (state.list?.key !== key) {
    main.innerHTML = '<p class="note">Loading…</p>';
    const data = await get(key).catch((error) => ({ error: error.message, total: 0, texts: [] }));
    if (request !== state.request) return null;
    state.list = { key, data, more: (which, offset) => `${path}/page?${params}&offset=${offset}` };
  }
  return state.list.data;
}

function textTable(params, { total, texts, error }, user) {
  const page = user ? `u/${enc(user)}/texts` : 'texts';
  const sorted = (column, text, title, numeric) => sortHead(params, page, user ? ['created_utc', 'desc'] : ['outvoted', 'desc'], column, text, title, numeric);
  const columns = [
    { head: 'text', w: '140px', cell: (t) => textLink(t.record_id) },
    { head: 'type', filter: cellChoice(params, 'type', [['', 'all'], ['post', 'posts'], ['comment', 'comments']]), w: '110px', cell: (t) => `<span class="badge ${t.record_type === 'post' ? 'post' : ''}">${t.record_type}</span>` },
    ...(user ? [] : [{ head: sorted('author', 'author', 'Sort by author'), filter: cellFilter(params, 'author', 'contains'), w: 'minmax(160px, 1fr)', cls: 'clip', cell: (t) => userLink(t.author) }]),
    { head: sorted('subreddit', 'subreddit', 'Sort by subreddit'), filter: cellFilter(params, 'sub', 'contains'), w: 'minmax(160px, 1fr)', cls: 'clip', cell: (t) => subLink(t.subreddit) },
    { head: sorted('created_utc', 'created', 'Sort by creation time', true), filter: cellFilter(params, 'created_utc', '2026-02'), w: '150px', cell: (t) => created(t.created_utc) },
    { head: sorted('words', 'words', 'Words in the text', true), filter: cellFilter(params, 'words', '<50'), w: '95px', num: true, cell: (t) => fmt(t.words) },
    { head: sorted('claims', 'claims', 'Self claims this text contributed', true), filter: cellFilter(params, 'claims', '>1'), w: '85px', num: true, cell: (t) => fmt(t.claims) },
    { head: sorted('incohesive', 'incohesive', 'Claims about an attribute where this author disagrees with themselves', true), filter: cellFilter(params, 'incohesive', '>0'), w: '100px', num: true, cell: (t) => fmt(t.incohesive) },
    { head: sorted('outvoted', 'outvoted', "Claims that lost to the author's other texts", true), filter: cellFilter(params, 'outvoted', '2..8'), w: '95px', num: true, cell: (t) => fmt(t.outvoted) },
    { head: 'suspect', filter: cellChoice(params, 'flagged', [['', 'any'], ['yes', 'flagged'], ['no', 'not flagged']]), w: '120px', cell: (t) => t.suspect.map(label).join(', ') },
  ];
  return `${TEXT_NOTE}<form data-page="${page}"><input type="hidden" name="sort" value="${esc(params.get('sort') ?? '')}"><input type="hidden" name="dir" value="${esc(params.get('dir') ?? '')}">
    <section class="panel" aria-label="Texts">${table(columns, texts, user ? 1000 : 1160)}${error ? `<p class="note error">${esc(error)}</p>` : texts.length ? '' : '<p class="note">No texts match these filters.</p>'}${more('texts', texts.length, total, 'texts')}</section></form>`;
}

async function textsPage(params, request) {
  const data = await textList(params, request);
  if (!data) return;
  main.innerHTML = `${pageTitle('Texts', `${mono(fmt(data.total))} texts with self claims`)}${textTable(params, data)}`;
}

async function subredditsPage(request) {
  const rows = await get('subreddits');
  if (request !== state.request) return;
  main.innerHTML = `${pageTitle('Subreddits', `${mono(fmt(rows.length))} subreddits · ${mono(fmt(rows.reduce((n, r) => n + r.texts, 0)))} texts · ${range(rows)}`)}
    <section class="panel" aria-label="Subreddits">${table([
      { label: 'subreddit', w: 'minmax(220px, 1fr)', cls: 'clip', cell: (s) => subLink(s.subreddit) },
      { label: 'texts ↓', w: '130px', num: true, cell: (s) => fmt(s.texts) },
      { label: 'posts', w: '110px', num: true, cell: (s) => fmt(s.posts) },
      { label: 'comments', w: '130px', num: true, cell: (s) => fmt(s.texts - s.posts) },
      { label: 'authors', w: '120px', num: true, cell: (s) => fmt(s.authors) },
    ], rows, 680)}</section>`;
}

async function searchPage(scope, query, request) {
  const data = await get(`search?q=${enc(query)}`);
  if (request !== state.request) return;
  const counts = { users: data.userTotal, subreddits: data.subs.length };
  head.innerHTML = `<div class="wrap head" style="padding-top: 20px"><h1 style="font-size: 26px">Search</h1>
    <form class="search" role="search" id="search"><label for="q" class="sr">Find a user or subreddit by name</label>
    <input id="q" name="q" type="search" value="${esc(query)}" placeholder="User or subreddit name" autocomplete="off"><button type="submit">Search</button></form>${tabs([['users', 'Users', fmt(counts.users)], ['subreddits', 'Subreddits', fmt(counts.subreddits)]], scope, `#/search/${enc(query)}`)}</div>`;
  let body = `<p class="note" style="color: var(--ink-3)"><strong style="color: var(--ink)">${fmt(counts[scope])}</strong> ${scope}${query ? ` with “${esc(query)}” in the name` : ''}${scope === 'users' && counts.users > data.users.length ? `, showing the ${data.users.length} with the most texts` : ''}</p>`;
  if (scope === 'users') {
    body += data.users.map((u) => `<article class="card"><a class="name" href="#/u/${enc(u.author)}">u/${esc(u.author)}</a>
      <div class="facts">${mono(fmt(u.texts))} texts · ${mono(fmt(u.posts))} posts · active ${day(u.first_utc)} – ${day(u.last_utc)}</div>
      <div class="chips">${u.subs.map((s) => `<a class="chip" href="#/r/${enc(s)}">r/${esc(s)}</a>`).join('')}</div></article>`).join('');
  } else {
    body += data.subs.map((s) => `<article class="card"><a class="name" href="#/r/${enc(s.subreddit)}">r/${esc(s.subreddit)}</a>
      <div class="facts">${mono(fmt(s.texts))} texts · ${mono(fmt(s.authors))} authors</div></article>`).join('');
  }
  main.innerHTML = body;
}

function highlighted(t) {
  const chars = [...t.text];
  let out = '', position = 0;
  for (const c of t.claims) {
    if (c.start_char < position) continue;
    out += `${esc(chars.slice(position, c.start_char).join(''))}<a class="claim-mark" href="#/t/${enc(t.record_id)}/claims" title="${esc(`${c.field.replaceAll('_', ' ')}: ${c.value}`)}">${esc(chars.slice(c.start_char, c.end_char).join(''))}</a>`;
    position = c.end_char;
  }
  return out + esc(chars.slice(position).join(''));
}

function textClaims(t) {
  const chars = [...t.text];
  return `<section class="panel" style="max-width: 900px; box-sizing: border-box" aria-label="Self claims"><h2>Self claims in this text</h2>${table([
      { label: 'attribute', w: '160px', cell: (c) => esc(c.field.replaceAll('_', ' ')) },
      { label: 'value', w: 'minmax(120px, 1fr)', cls: 'clip', cell: (c) => esc(c.value) },
      { label: 'span', w: 'minmax(140px, 1fr)', cls: 'clip', cell: (c) => `<mark>${esc(chars.slice(c.start_char, c.end_char).join(''))}</mark>` },
      { label: 'flag', w: '110px', cell: (c) => suspectBox(t.record_id, c.field, c.value, c.suspect) },
    ], t.claims, 520)}</section>`;
}

const textTabs = {
  text: (t) => `<section class="panel" style="max-width: 900px; box-sizing: border-box" aria-label="Text"><div class="text-body">${t.claims.length ? highlighted(t) : esc(t.text)}</div></section>`,
  claims: (t) => t.claims.length ? textClaims(t) : '<section class="panel"><p class="note">No self claims were extracted from this text.</p></section>',
  thread: (t) => {
    const limit = state.full ? t.thread.length : Math.max(50, t.thread.findIndex((c) => c.record_id === t.record_id) + 10);
    const missing = t.post.present ? '' : ` The post ${esc(t.post.record_id)} is not in the corpus.`;
    return `<section class="panel" aria-label="Thread" style="max-width: 980px; box-sizing: border-box; gap: 4px">
      <p class="note" style="margin-bottom: 8px">${plural(t.threadComments, 'comment')} on this post in the corpus.${missing}</p>
      ${t.thread.slice(0, limit).map((c) => `<div class="node ${c.record_id === t.record_id ? 'current' : ''}" style="margin-left: ${Math.min(c.depth, 12) * 28}px">
        <div class="node-meta">${userLink(c.author)}${textLink(c.record_id)}${created(c.created_utc)}</div>
        <p style="font-weight: ${c.record_type === 'post' ? 600 : 400}">${esc(c.record_type === 'post' ? c.text.split('\n\n')[0] : c.text)}</p></div>`).join('')}
      ${t.thread.length > limit ? '<button type="button" class="more" data-more="thread">Show full thread</button>' : ''}</section>`;
  },
};

function textHeader(t, tab) {
  const isPost = t.record_type === 'post';
  const postRef = t.post.present ? textLink(t.post.record_id, t.post.title ?? t.post.record_id, '') : mono(t.post.record_id);
  const context = isPost ? (t.title ? `<h1 class="title">${esc(t.title)}</h1>` : '')
    : `<p style="margin: 0; font-size: 14px; color: var(--ink-3)">${t.parent.record_id.startsWith('t1_') ? `Reply to ${t.parent.present ? `${textLink(t.parent.record_id)} by ${userLink(t.parent.author)}` : `${mono(t.parent.record_id)} (not in the corpus)`} in the post ${postRef}` : `Reply to the post ${postRef}`}${t.post.present ? '' : ' (not in the corpus)'}</p>`;
  header([subLink(t.subreddit), userLink(t.author), `<span class="mono" style="color: var(--ink)">${esc(t.record_id)}</span>`],
    `<div class="idline"><span class="badge ${isPost ? 'post' : ''}">${t.record_type}</span><span class="mono" style="font-size: 15px">${esc(t.record_id)}</span></div>
    ${context}
    <p class="summary"><span>in ${subLink(t.subreddit)}</span><span>by ${userLink(t.author)}</span><span class="mono">${stamp(t.created_utc)} UTC</span><span>status <span class="mono">${esc(t.text_status)}</span></span></p>`,
    tabs([['text', 'Text'], ['claims', 'Self claims', t.claims.length ? fmt(t.claims.length) : ''], ['thread', 'Thread', t.threadComments ? fmt(t.threadComments) : '']],
      tab, `#/t/${enc(t.record_id)}`));
}

function trendChart(rows, labels, title, allTicks = false) {
  const width = 960, height = 252, left = 52, right = 16, top = 28, bottom = 38;
  const ceiling = Math.max(1, ...rows.map((r) => r.texts));
  const step = (width - left - right) / rows.length;
  const x = (i) => left + step * (i + 0.5);
  const y = (v) => height - bottom - v / ceiling * (height - top - bottom);
  const grid = [...new Set([0, Math.ceil(ceiling / 2), ceiling])].map((v) => `<line x1="${left}" x2="${width - right}" y1="${y(v)}" y2="${y(v)}" class="chart-grid"/><text x="${left - 10}" y="${y(v) + 4}" text-anchor="end">${v}</text>`).join('');
  const ticks = allTicks ? rows.map((_, i) => i) : [...new Set([0, Math.floor((rows.length - 1) / 2), rows.length - 1])];
  const dates = ticks.map((i) => `<text x="${x(i)}" y="${height - 10}" text-anchor="${allTicks ? 'middle' : i === 0 ? 'start' : i === rows.length - 1 ? 'end' : 'middle'}">${esc(labels[i])}</text>`).join('');
  const anchor = (i) => x(i) < left + 200 ? 'start' : x(i) > width - right - 200 ? 'end' : 'middle';
  const marks = rows.map((r, i) => {
    const period = r.hour == null ? labels[i] : `${labels[i]}:00–${String((r.hour + 1) % 24).padStart(2, '0')}:00 UTC`;
    const description = `${period}: ${plural(r.posts, 'post')}, ${plural(r.texts - r.posts, 'comment')}`;
    const bars = `<rect class="comments" x="${x(i) - step * 0.35}" y="${y(r.texts - r.posts)}" width="${step * 0.7}" height="${y(0) - y(r.texts - r.posts)}"/><rect class="posts" x="${x(i) - step * 0.35}" y="${y(r.texts)}" width="${step * 0.7}" height="${y(r.texts - r.posts) - y(r.texts)}"/>`;
    return `<g class="day" tabindex="0" aria-label="${esc(description)}"><rect class="hit" x="${x(i) - step / 2}" y="${top}" width="${step}" height="${y(0) - top}"/>${bars}<text class="readout" x="${x(i)}" y="${top - 10}" text-anchor="${anchor(i)}">${esc(description)}</text></g>`;
  }).join('');
  return `<div class="chart-scroll"><svg class="trend-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>${grid}${dates}${marks}</svg></div>`;
}

function trendsPanel(data) {
  const { days, hours, weekdays } = data.trends;
  const legend = '<div class="chart-legend"><span class="comments">Comments</span><span class="posts">Posts</span></div>';
  return `<section class="panel"><h2>Posts and comments per day</h2><p class="note">Total posts and comments per UTC day.</p>${legend}${trendChart(days, days.map((r) => date(r.day)), 'Posts and comments by day in UTC')}</section>
    <section class="panel" aria-label="Time of day"><h2>Time of day</h2><p class="note">Total posts and comments by hour of day (UTC), across all recorded dates. Hover or focus a bar for counts.</p>${legend}${trendChart(hours, hours.map((r) => String(r.hour).padStart(2, '0')), 'Posts and comments by hour of day in UTC', true)}</section>
    <section class="panel" aria-label="Day of week"><h2>Day of week</h2><p class="note">Total posts and comments by weekday (UTC), across all recorded dates. Hover or focus a bar for counts.</p>${legend}${trendChart(weekdays, ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], 'Posts and comments by day of week in UTC', true)}</section>`;
}

const UNITS = { age: 'years', height: 'cm', weight: 'kg', income: 'USD per year' };

function claimValue(attribute, value) {
  if (typeof value !== 'number') return esc(value);
  return UNITS[attribute] ? `${fmt(Math.round(value * 10) / 10)} ${UNITS[attribute]}` : esc(String(value));
}

const claimSummary = (attribute, target) => claimValue(attribute, target.value);

const CLAIM_STATES = { accepted: 'agrees', outvoted: 'outvoted' };

const cohesion = (target) => target.outvoted ? 'incohesive' : 'cohesive';
const claimSources = (target) => Object.entries(target.stats.sources).map(([source, n]) => `${fmt(n)} ${source}`).join(' · ');
const published = (claims) => `consolidation published ${esc(stamp(Date.parse(claims.finished) / 1000))} UTC`;
const candidateList = (attribute, target) => target.candidates.length > 1
  ? `<div class="sub">${target.candidates.map((c) => `${claimValue(attribute, c.value)} (${fmt(c.support)})`).join(' · ')}</div>` : '';

const percent = (probability) => `${(100 * probability).toFixed(1)}%`;

function predictionFacet(facet) {
  const [top, ...others] = facet.candidates.filter((candidate) => candidate.kind !== 'unasserted');
  return `<div class="prediction-value"><span>${esc(top.label.replaceAll('_', ' '))}</span><span class="prediction-score" title="Uncalibrated model probability">${percent(top.probability)}</span></div>
    ${others.length ? `<details><summary>Other candidates</summary><ul class="prediction-options">${others.slice(0, 4).map((candidate) => `<li><span>${esc(candidate.label.replaceAll('_', ' '))}</span><span class="mono">${percent(candidate.probability)}</span></li>`).join('')}</ul></details>` : ''}`;
}

function numericPrediction(attribute, number) {
  const { lower, median, upper } = number.summary;
  const value = (n) => attribute === 'birth_year' ? String(Math.floor(n)) : claimValue(attribute, n);
  return `<div class="prediction-value"><span>${value(median)}</span><span class="sub">median</span></div>
    <div class="sub">80% model range: ${value(lower)}–${value(upper)}</div>`;
}

function predictionCell(attribute, prediction) {
  if (!prediction) throw new Error(`no ${attribute} prediction`);
  return UNITS[attribute] || attribute === 'birth_year' ? prediction.numeric.map((number) => numericPrediction(attribute, number)).join('')
    : prediction.facets.filter((facet) => facet.facet === 'value').map(predictionFacet).join('');
}

function claimsPanel(data) {
  const { targets, evidence, fields } = data.claims;
  const predictions = data.predictions;
  const ready = predictions.status === 'ready';
  const claimed = new Map(targets.map((item) => [item.attribute, item.target]));
  const tied = new Set(evidence.map((item) => item.attribute));
  const base = `#/u/${enc(data.summary.author)}/claims`;
  const predictionNote = ready ? `Out-of-fold model predictions, fold ${fmt(predictions.fold)} of ${fmt(predictions.folds)}, from ${fmt(predictions.sampled_texts)} sampled texts. Scores are uncalibrated.`
    : `No model prediction: the model covers users with at least ${fmt(predictions.minimum_texts)} texts.`;
  return `<section class="panel" aria-label="Demographics"><p class="note">${plural(targets.length, 'self-claimed attribute')} from ${plural(evidence.length, 'evidence row')}, ${published(data.claims)}.</p>
    <p class="note" role="status">${esc(predictionNote)}</p>
    <table class="demographics-table"><caption class="sr">Consolidated self claims and model predictions</caption>
    <thead><tr><th scope="col">Attribute</th><th scope="col">Consolidated value</th><th scope="col">Model prediction</th></tr></thead><tbody>${fields.map((attribute) => {
      const target = claimed.get(attribute);
      return `<tr data-attribute="${esc(attribute)}"><td><h3>${label(attribute)}</h3></td><td>${target ? `<div class="claim-value">${claimSummary(attribute, target)}</div>${candidateList(attribute, target)}
        <div class="claim-cell-meta"><span class="badge ${cohesion(target)}">${cohesion(target)}</span><a href="${base}/${enc(attribute)}">View evidence</a></div>
        <div class="sub">${plural(target.stats.observations, 'observation')} · ${claimSources(target)} · ${plural(target.stats.effective_units, 'distinct text')}</div>` : tied.has(attribute) ? `<p class="note">Claims tie, so there is no consolidated value. <a href="${base}/${enc(attribute)}">View evidence</a></p>` : '<p class="note">No self claim recorded.</p>'}</td>
        <td class="prediction">${ready ? predictionCell(attribute, predictions.attributes[attribute]) : ''}</td></tr>`;
    }).join('')}</tbody></table></section>`;
}

function claimEvidence(data, attribute) {
  const { targets, evidence } = data.claims;
  const found = targets.find((t) => t.attribute === attribute);
  const rows = evidence.filter((e) => e.attribute === attribute);
  if (!found && !rows.length) throw new Error(`no ${attribute} claims for this user`);
  const target = found && found.target;
  return `<p class="note"><a href="#/u/${enc(data.summary.author)}/claims">All demographics</a></p>
    <section class="panel" aria-label="${esc(attribute)} evidence">
      ${target ? `<div class="claim-head"><h2>${esc(attribute.replaceAll('_', ' '))}</h2><span class="badge ${cohesion(target)}">${cohesion(target)}</span><span class="claim-value">${claimSummary(attribute, target)}</span></div>
      ${candidateList(attribute, target)}
      <p class="note">${plural(target.stats.observations, 'observation')} (${claimSources(target)}) · ${plural(target.stats.effective_units, 'distinct text')} · ${published(data.claims)}</p>`
      : `<div class="claim-head"><h2>${esc(attribute.replaceAll('_', ' '))}</h2><span class="claim-value">Claims tie, so there is no consolidated value.</span></div>`}
      ${table([
        { label: 'state', w: '110px', cell: (e) => target ? `<span class="badge ${CLAIM_STATES[e.state]}">${CLAIM_STATES[e.state]}</span>` : `<span class="badge ${CLAIM_STATES[e.state]}">tied</span>` },
        { label: 'claimed', w: 'minmax(140px, 1fr)', cls: 'clip', cell: (e) => esc(e.value) },
        { label: 'source', w: 'minmax(180px, 1.2fr)', cls: 'clip', cell: (e) => e.source === 'text' ? textLink(e.source_key) : `flair <span title="${esc(e.source_key)}">“${esc(e.source_key)}”</span>` },
        { label: 'subreddit', w: '170px', cls: 'clip', cell: (e) => e.subreddit ? subLink(e.subreddit) : '' },
        { label: 'posted', w: '130px', cell: (e) => e.source === 'text' ? quiet(date(e.created_utc)) : '' },
        { label: 'flag', w: '110px', cell: (e) => e.source === 'text' ? suspectBox(e.source_key, attribute, e.value, e.suspect) : '' },
      ], rows, 970)}</section>`;
}

function similarPanel(data) {
  const similar = data.similar;
  if (similar.status === 'ineligible') {
    return '<section class="panel" aria-label="Most similar users"><h2>Most similar users</h2><p class="note">This user needs at least 64 available, nonempty texts to have a user vector.</p></section>';
  }
  if (similar.status !== 'ready') {
    return `<section class="panel" aria-label="Most similar users"><h2>Most similar users</h2><p class="note">The user index is being prepared. ${fmt(similar.indexed_users)} user vectors are ready. Reload this tab after the build finishes.</p></section>`;
  }
  return `<section class="panel" aria-label="Most similar users"><h2>Most similar users</h2><p class="note">The ${fmt(similar.users.length)} closest users among ${fmt(similar.indexed_users)} indexed users, based on 64 randomly sampled texts each. Higher cosine similarity means closer writing vectors.</p>${table([
    { label: '#', w: '55px', num: true, cell: (u, i) => fmt(i + 1) },
    { label: 'user', w: 'minmax(190px, 1fr)', cls: 'clip', cell: (u) => userLink(u.author) },
    { label: 'texts', w: '100px', num: true, cell: (u) => fmt(u.texts) },
    { label: 'top subreddits', w: 'minmax(260px, 1.5fr)', cell: (u) => `<div class="chips">${u.top_subreddits.map((s) => `<span class="chip">${subLink(s)}</span>`).join('')}</div>` },
    { label: 'similarity ↓', w: '120px', num: true, cell: (u) => u.similarity.toFixed(4) },
  ], similar.users, 725)}</section>`;
}

const userTabs = {
  similar: similarPanel,
  claims: claimsPanel,
  trends: trendsPanel,
};

const subTabs = {
  texts: (r) => `<section class="panel" aria-label="Posts">${table([
      { label: 'post', w: 'minmax(280px, 1fr)', cell: (t) => `${textLink(t.record_id, (t.text_status === 'removed' ? '[removed]' : t.text.split('\n\n')[0]) || t.record_id, '')}<div class="mono sub">${esc(t.record_id)}</div>` },
      { label: 'author', w: '180px', cls: 'clip', cell: (t) => userLink(t.author) },
      { label: 'created', w: '150px', cell: (t) => created(t.created_utc) },
      { label: 'comments', w: '100px', num: true, cell: (t) => fmt(t.comments) },
    ], r.posts, 720)}${more('posts', r.posts.length, r.summary.posts, 'posts')}</section>`,
  authors: (r) => `<section class="panel" aria-label="Authors">${table([
      { label: 'author', w: 'minmax(200px, 1fr)', cls: 'clip', cell: (a) => userLink(a.name) },
      { label: 'texts here', w: '120px', num: true, cell: (a) => fmt(a.texts) },
    ], r.authors, 320)}${more('authors', r.authors.length, r.summary.authors, 'authors')}</section>`,
};

async function entityPage(kind, name, tab, detail, params, request) {
  if (state.page?.key !== `${kind}/${name}`) {
    main.innerHTML = '<p class="note">Loading…</p>';
    const data = await get(`${kind}/${enc(name)}`);
    if (request !== state.request) return;
    state.page = { key: `${kind}/${name}`, data, more: (which, offset) => `${kind}/${enc(name)}/${which}?offset=${offset}` };
    state.full = false;
  }
  const data = state.page.data;
  if (kind === 'text') {
    textHeader(data, tab);
    main.innerHTML = textTabs[tab](data);
  } else if (kind === 'user') {
    const s = data.summary;
    header(['<a href="#/users">Users</a>', `<span style="color: var(--ink)">u/${esc(name)}</span>`],
      `<h1>u/${esc(name)}</h1><p class="summary">${plural(s.texts, 'text')} (${plural(s.posts, 'post')}, ${plural(s.texts - s.posts, 'comment')}) in ${plural(s.subs.length, 'subreddit')} · active ${day(s.first_utc)} – ${day(s.last_utc)}</p>`,
      tabs([['texts', 'Texts', fmt(s.texts)], ['trends', 'Trends'], ['claims', 'Demographics'], ['similar', 'Most similar users']], tab, `#/u/${enc(name)}`));
    if (tab === 'texts') {
      const list = await textList(params, request, name);
      if (list) main.innerHTML = textTable(params, list, name);
      return;
    }
    if (['trends', 'claims', 'similar'].includes(tab) && !data[tab]) {
      main.innerHTML = `<p class="note">Loading ${tab}…</p>`;
      data[tab] = await get(`user/${enc(name)}/${tab}`);
      if (request !== state.request) return;
    }
    if (tab === 'claims' && !data.predictions) {
      data.predictions = await get(`user/${enc(name)}/predictions`);
      if (request !== state.request) return;
    }
    main.innerHTML = tab === 'claims' && detail ? claimEvidence(data, detail) : userTabs[tab](data);
  } else {
    const s = data.summary;
    header(['<a href="#/subreddits">Subreddits</a>', `<span style="color: var(--ink)">r/${esc(name)}</span>`],
      `<h1>r/${esc(name)}</h1><p class="summary">${plural(s.texts, 'text')} (${plural(s.posts, 'post')}, ${plural(s.texts - s.posts, 'comment')}) · ${plural(s.authors, 'author')}</p>`,
      tabs([['texts', 'Texts', fmt(s.posts)], ['authors', 'Authors', fmt(s.authors)]], tab, `#/r/${enc(name)}`));
    main.innerHTML = subTabs[tab](data);
  }
}

const DEFAULT_TAB = { text: 'text', user: 'texts', subreddit: 'texts' };
const KINDS = { t: 'text', u: 'user', r: 'subreddit' };
const NAV = { t: 'texts', u: 'users', r: 'subreddits' };
const PAGES = {
  search: (parts, params, request) => searchPage(parts[2] === 'subreddits' ? 'subreddits' : 'users', parts[1] ?? '', request),
  users: (parts, params, request) => usersPage(params, request),
  subreddits: (parts, params, request) => subredditsPage(request),
  texts: (parts, params, request) => textsPage(params, request),
};

async function render() {
  const request = ++state.request;
  try {
    const [path, query] = location.hash.replace(/^#\/?/, '').split('?');
    const parts = path.split('/').map(decodeURIComponent);
    const page = parts[0] || 'users';
    document.querySelectorAll('.nav a').forEach((a) => (a.getAttribute('href') === `#/${NAV[page] ?? page}` ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current')));
    head.innerHTML = '';
    if (KINDS[page] && parts[1]) await entityPage(KINDS[page], parts[1], parts[2] || DEFAULT_TAB[KINDS[page]], parts[3], new URLSearchParams(query), request);
    else if (PAGES[page]) await PAGES[page](parts, new URLSearchParams(query), request);
    else throw new Error(`no such page: ${page}`);
  } catch (error) {
    if (request !== state.request) return;
    head.innerHTML = '';
    main.innerHTML = `<p class="note error">${esc(error.message)}</p>`;
  }
}

function remember(record, attribute, value, suspect) {
  const data = state.page.data;
  const rows = Array.isArray(data.claims) ? data.claims.filter((c) => data.record_id === record && c.field === attribute && c.value === value)
    : (data.claims?.evidence ?? []).filter((e) => e.source === 'text' && e.source_key === record && e.attribute === attribute && e.value === value);
  rows.forEach((r) => { r.suspect = suspect; });
  document.querySelectorAll('input[data-record]').forEach((box) => {
    if (box.dataset.record === record && box.dataset.attribute === attribute && box.dataset.value === value) box.checked = suspect;
  });
}

async function flag(box) {
  const { record, attribute, value } = box.dataset;
  box.disabled = true;
  box.parentElement.parentElement.querySelector('.error')?.remove();
  try {
    const body = JSON.stringify({ record_id: record, attribute, value, suspect: box.checked });
    const saved = await get('suspect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
    remember(saved.record_id, saved.attribute, saved.value, saved.suspect);
  } catch (error) {
    box.checked = !box.checked;
    const message = document.createElement('p');
    message.className = 'note error';
    message.textContent = error.message;
    box.parentElement.after(message);
  } finally {
    box.disabled = false;
  }
}

async function loadMore(button) {
  if (button.disabled) return;
  button.disabled = true;
  const which = button.dataset.more;
  const page = which === 'texts' ? state.list : state.page;
  const request = state.request;
  try {
    if (which === 'thread') state.full = true;
    else page.data[which].push(...await get(page.more(which, page.data[which].length)));
    if (request === state.request) await render();
  } catch (error) {
    if (request === state.request) {
      const message = document.createElement('p');
      message.className = 'note error';
      message.textContent = error.message;
      button.after(message);
    }
  } finally {
    button.disabled = false;
  }
}

document.addEventListener('submit', (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  if (event.target.id === 'search') location.hash = `#/search/${enc(form.get('q').trim())}`;
  else location.hash = `#/${event.target.dataset.page}?${new URLSearchParams([...form].map(([k, v]) => [k, v.trim()]).filter(([, v]) => v))}`;
});

document.addEventListener('change', (event) => {
  if (event.target.dataset.record) flag(event.target);
  else if (event.target.form?.dataset.page) event.target.form.requestSubmit();
});

document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-more]');
  if (button) loadMore(button);
});

window.addEventListener('hashchange', render);
render();
