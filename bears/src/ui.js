// DOM overlay: title, season switcher, tool buttons, place index, info card and map labels.
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { SEASONS } from './seasons.js';
import { PLACES } from './places.js';
import { CHARACTERS } from './characters.js';

const ACCENT = ['#e8628f', '#2b9a5f', '#d9692a', '#4f86c9'];
const ICON = { spring: '🌸', summer: '☀️', autumn: '🍁', winter: '❄️' };
const h = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
};

export class UI {
  constructor(app) {
    this.app = app;
    this.hidden = false;
    this.selected = null;
    const root = h('div', 'ui');
    app.el.appendChild(root);
    this.root = root;

    // title
    const title = h('header', 'title');
    title.innerHTML = `<h1>熊出没 · 四季狗熊岭</h1><p class="sub">三维地图模型 · <span class="series"></span></p>`;
    root.appendChild(title);
    this.seriesEl = title.querySelector('.series');

    // tools
    const tools = h('div', 'tools');
    const btn = (label, title, fn) => {
      const b = h('button', 'tool', label);
      b.title = title;
      b.addEventListener('click', fn);
      tools.appendChild(b);
      return b;
    };
    this.bAuto = btn('', '四季自动轮换（空格）', () => app.setAuto(!app.auto));
    this.bNight = btn('', '白天 / 夜晚（N）', () => app.setNight(app.nightTarget < 0.5));
    this.bLabels = btn('地名', '显示 / 隐藏地名', () => {
      root.parentElement.classList.toggle('no-labels');
      this.sync();
    });
    this.bIndex = btn('索引', '地点与角色索引', () => {
      this.index.classList.toggle('open');
      this.sync();
    });
    btn('复位', '回到全景视角（R）', () => app.resetView());
    root.appendChild(tools);

    // season bar
    const bar = h('nav', 'seasons');
    this.sBtns = SEASONS.map((s, i) => {
      const b = h('button', 'season', `<span class="big">${s.name}</span><span class="nm">${s.series}</span><i class="prog"></i>`);
      b.style.setProperty('--accent', ACCENT[i]);
      b.addEventListener('click', () => app.setSeason(i));
      bar.appendChild(b);
      return b;
    });
    root.appendChild(bar);

    // banner
    this.banner = h('div', 'banner');
    root.appendChild(this.banner);

    // index
    const idx = h('aside', 'index');
    idx.appendChild(h('h3', null, '地点'));
    const ul = h('ul');
    for (const p of PLACES) {
      const li = h('li', null, `<b>${p.name}</b><span>${p.brief}</span>`);
      li.addEventListener('click', () => this.select(p.id));
      ul.appendChild(li);
    }
    idx.appendChild(ul);
    idx.appendChild(h('h3', null, '角色'));
    const cl = h('ul', 'chars');
    for (const c of CHARACTERS) {
      const li = h('li', null, `<b>${c.name}</b><span>${c.desc}</span>`);
      li.addEventListener('click', () => {
        app.followChar(c.id);
        if (matchMedia('(max-width: 720px)').matches) idx.classList.remove('open');
      });
      cl.appendChild(li);
    }
    idx.appendChild(cl);
    idx.appendChild(
      h('p', 'note', '同人风格示意地图：地形与布局为创作演绎，角色以简单几何体塑造，并非官方模型。拖动旋转，滚轮缩放，右键平移；按 1–4 切换四季。')
    );
    root.appendChild(idx);
    this.index = idx;
    if (window.innerWidth > 1700) idx.classList.add('open');

    // info card
    const card = h('section', 'card');
    card.innerHTML = `<button class="x" aria-label="关闭">×</button><h2></h2><p class="brief"></p><div class="now"><em></em><p></p></div>`;
    card.querySelector('.x').addEventListener('click', () => this.select(null));
    root.appendChild(card);
    this.card = card;

    // follow chip
    this.followEl = h('div', 'follow');
    root.appendChild(this.followEl);

    // map labels
    this.pins = PLACES.map((p) => {
      const d = h('div', `pin k-${p.kind}`, `<span>${p.name}</span>`);
      d.addEventListener('pointerdown', (e) => e.stopPropagation());
      d.addEventListener('click', (e) => {
        e.stopPropagation();
        this.select(p.id);
      });
      const o = new CSS2DObject(d);
      o.position.set(p.x, app.hf.h(p.x, p.z) + (p.y ?? 3), p.z);
      app.scene.add(o);
      return { p, d, o };
    });
    for (const c of app.chars.list) {
      c.div.addEventListener('pointerdown', (e) => e.stopPropagation());
      c.div.addEventListener('click', (e) => {
        e.stopPropagation();
        app.followChar(c.id);
      });
    }

    window.addEventListener('keydown', (e) => {
      if (e.target.closest?.('input,textarea')) return;
      if (e.key >= '1' && e.key <= '4') app.setSeason(Number(e.key) - 1);
      else if (e.key === ' ') {
        e.preventDefault();
        app.setAuto(!app.auto);
      } else if (e.key === 'n' || e.key === 'N') app.setNight(app.nightTarget < 0.5);
      else if (e.key === 'r' || e.key === 'R') app.resetView();
      else if (e.key === 'Escape') this.select(null);
    });
    document.addEventListener('visibilitychange', () => (this.hidden = document.hidden));
    this.lastSeason = -1;
    this.sync();
  }

  select(id) {
    this.selected = id;
    for (const pin of this.pins) pin.d.classList.toggle('on', pin.p.id === id);
    this.card.classList.toggle('open', !!id);
    if (id) {
      this.app.focusPlace(id);
      if (matchMedia('(max-width: 720px)').matches) this.index.classList.remove('open');
    }
    this.fillCard();
    this.sync();
  }

  fillCard() {
    const p = PLACES.find((q) => q.id === this.selected);
    if (!p) return;
    const s = SEASONS[this.app.seasonIndex];
    this.card.querySelector('h2').textContent = p.name;
    this.card.querySelector('.brief').textContent = p.brief;
    this.card.querySelector('.now em').textContent = `${ICON[s.key]} ${s.name}季 · ${s.series}`;
    this.card.querySelector('.now p').textContent = p.text[s.key];
    this.card.style.setProperty('--accent', ACCENT[this.app.seasonIndex]);
  }

  setFollow(c) {
    this.followEl.classList.toggle('on', !!c);
    if (c) this.followEl.innerHTML = `正在跟随 <b>${c.name}</b> · 拖动画面即可退出`;
  }

  onSeasonProgress() {}

  sync() {
    const app = this.app, i = app.seasonIndex, s = SEASONS[i];
    this.sBtns.forEach((b, j) => b.classList.toggle('on', j === i));
    this.seriesEl.textContent = `${s.series} · ${s.tag}`;
    this.root.style.setProperty('--accent', ACCENT[i]);
    this.bAuto.innerHTML = app.auto ? '❚❚ 轮换' : '▶ 轮换';
    this.bAuto.classList.toggle('on', app.auto);
    this.bNight.innerHTML = app.nightTarget > 0.5 ? '☾ 夜晚' : '☀ 白天';
    this.bNight.classList.toggle('on', app.nightTarget > 0.5);
    this.bLabels.classList.toggle('on', !this.root.parentElement.classList.contains('no-labels'));
    this.bIndex.classList.toggle('on', this.index.classList.contains('open'));
    if (i !== this.lastSeason) {
      if (this.lastSeason >= 0) {
        this.banner.innerHTML = `<b>${s.series}</b><span>${s.tag}</span>`;
        this.banner.classList.remove('show');
        void this.banner.offsetWidth;
        this.banner.classList.add('show');
      }
      this.lastSeason = i;
      this.fillCard();
    }
  }

  frame() {
    const app = this.app;
    if (app.seasonIndex !== this.lastSeason) this.sync();
    const prog = app.auto ? Math.min(1, app.autoTimer / app.AUTO_PERIOD) : 0;
    this.sBtns.forEach((b, j) => b.style.setProperty('--p', j === app.seasonIndex ? prog : 0));
  }
}
