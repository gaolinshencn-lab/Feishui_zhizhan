import { EPISODES } from '../data/episodes.js';

const SVG = {
  play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/></svg>',
  pause: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h3.6v14H7zM13.4 5H17v14h-3.6z" fill="currentColor"/></svg>',
  prev: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h2v14H6zM19 5.5v13L9.5 12z" fill="currentColor"/></svg>',
  next: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 5h2v14h-2zM5 5.5v13L14.5 12z" fill="currentColor"/></svg>',
  turnCcw:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.94 9.5A7 7 0 1 1 8.5 19.06" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M9.11 8.02L5.94 9.5 5.64 6.01" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  turnCw:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.06 9.5A7 7 0 1 0 15.5 19.06" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M14.89 8.02L18.06 9.5 18.36 6.01" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  flip:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 11.4A7 7 0 0 1 18.6 9.6M19 12.6A7 7 0 0 1 5.4 14.4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M15.8 9.4l2.9.5.6-2.9M8.2 14.6l-2.9-.5-.6 2.9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  camera: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h3l1.6-2.4h6.8L17 8h3v11H4z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><circle cx="12" cy="13.2" r="3.4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
  layers: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4l9 5-9 5-9-5z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M3 13.5l9 5 9-5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
  full: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
  info: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M12 10.5v6M12 7.3v.4" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
  legend: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h3M5 12h3M5 17h3M11 7h8M11 12h8M11 17h8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
  close: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  sound: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9.5h3.5L12 6v12l-4.5-3.5H4z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path class="wave" d="M15.5 9.2a4 4 0 010 5.6M18 7a7.2 7.2 0 010 10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  pin: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-6.5-6.2-6.5-11.2a6.5 6.5 0 0113 0C18.5 14.8 12 21 12 21z" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="9.8" r="2.3" fill="currentColor"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};

const GROUPS = [
  { label: '战略态势', from: 0, to: 2 },
  { label: '淝水战场', from: 3, to: 10 },
  { label: '战后', from: 11, to: 12 },
];

function fmtNum(v) {
  if (typeof v !== 'number') return v;
  if (v >= 10000) {
    const w = v / 10000;
    return `${Number.isInteger(w) ? w : w.toFixed(1)}万`;
  }
  return `${v.toLocaleString('zh-CN')}`;
}

export class UI {
  constructor(app, root) {
    this.app = app;
    this.root = root;
    this.build();
  }

  build() {
    const r = this.root;
    r.insertAdjacentHTML(
      'beforeend',
      `
<div class="topshade" aria-hidden="true"></div>
<header class="masthead">
  <div class="seal-mark" aria-hidden="true"><span>淝</span><span>水</span></div>
  <div class="masthead__text">
    <h1 class="masthead__title">淝水之战</h1>
    <p class="masthead__sub">三维战场态势沙盘 · 东晋太元八年 · 前秦建元十九年 · 公元三八三年</p>
  </div>
</header>

<nav class="toolbar" aria-label="视图">
  <div class="scale-switch" role="tablist" aria-label="沙盘">
    <button class="scale-switch__btn" data-map="strategic" role="tab" id="tab-strategic">战略全局</button>
    <button class="scale-switch__btn" data-map="tactical" role="tab" id="tab-tactical">淝水战场</button>
  </div>
  <button class="icon-btn" id="btn-camera" aria-pressed="true" title="自动镜头：跟随剧情推移视角">${SVG.camera}<span>自动镜头</span></button>
  <button class="icon-btn" id="btn-places" aria-expanded="false" title="地名索引：古今对照，点击飞往">${SVG.pin}<span>地名</span></button>
  <button class="icon-btn" id="btn-sound" aria-pressed="false" title="声音：琴声、战鼓与风声">${SVG.sound}<span>声音</span></button>
  <button class="icon-btn" id="btn-layers" aria-expanded="false" title="图层与显示">${SVG.layers}<span>图层</span></button>
  <button class="icon-btn" id="btn-full" title="全屏">${SVG.full}<span>全屏</span></button>
  <button class="icon-btn" id="btn-about" title="史料与说明">${SVG.info}<span>说明</span></button>
</nav>

<section class="layers-pop" id="layers-pop" hidden aria-label="图层">
  <h2 class="pop-title">图层与显示</h2>
  <label class="toggle"><input type="checkbox" id="lay-places" checked /><span>地名标注</span></label>
  <label class="toggle"><input type="checkbox" id="lay-modern" checked /><span>古今地名对照</span></label>
  <label class="toggle"><input type="checkbox" id="lay-arrows" checked /><span>行军路线</span></label>
  <label class="toggle"><input type="checkbox" id="lay-markers" checked /><span>事件与人物言语</span></label>
  <label class="toggle"><input type="checkbox" id="lay-units" checked /><span>部队番号</span></label>
  <label class="toggle"><input type="checkbox" id="lay-contours" checked /><span>等高线</span></label>
  <label class="toggle"><input type="checkbox" id="lay-grid" /><span>方格网（战场 5 公里 / 全局 100 公里）</span></label>
  <label class="range"><span>地形垂直夸张 <output id="exag-out">×5</output></span><input type="range" id="lay-exag" min="1" max="12" step="1" value="5" /></label>
  <label class="range"><span>画质</span>
    <select id="lay-quality"><option value="high">高</option><option value="medium" selected>标准</option><option value="low">省电</option></select>
  </label>
</section>

<section class="places-pop" id="places-pop" hidden aria-label="地名索引">
  <h2 class="pop-title">地名索引</h2>
  <p class="pop-note">古名 · 今地，点击即飞往该处</p>
  <div class="places-list" id="places-list"></div>
</section>

<div class="caption" id="caption" aria-hidden="true"><div class="caption__no" id="cap-no"></div><div class="caption__title" id="cap-title"></div><div class="caption__date" id="cap-date"></div></div>

<aside class="episode" id="episode" aria-live="polite">
  <button class="episode__toggle" id="episode-toggle" aria-expanded="true" aria-controls="episode-body">${SVG.chevron}<span class="sr">展开或收起</span></button>
  <div class="episode__head">
    <div class="episode__no" id="ep-no"></div>
    <div class="episode__dates"><div class="episode__date" id="ep-date"></div><div class="episode__western" id="ep-western"></div></div>
  </div>
  <h2 class="episode__title" id="ep-title"></h2>
  <p class="episode__subtitle" id="ep-subtitle"></p>
  <div class="episode__body" id="episode-body">
    <p class="episode__text" id="ep-text"></p>
    <figure class="quote" id="ep-quote"><blockquote id="ep-quote-text"></blockquote><figcaption id="ep-quote-src"></figcaption></figure>
    <div class="forces" id="ep-forces"></div>
    <details class="datenote" id="ep-datenote"><summary>日期考</summary><p id="ep-datenote-text"></p></details>
    <div class="people" id="ep-people"></div>
  </div>
</aside>

<section class="legend" id="legend" aria-label="图例">
  <button class="legend__toggle" id="legend-toggle" aria-expanded="true">${SVG.legend}<span>图例</span></button>
  <div class="legend__body" id="legend-body">
    <div class="legend__row"><span class="sw sw--jin"></span>东晋军<span class="sw sw--qin"></span>前秦军</div>
    <div class="legend__row"><span class="ar ar--advance"></span>进军<span class="ar ar--retreat"></span>撤退 / 溃逃</div>
    <div class="legend__row"><span class="ar ar--naval"></span>舟师<span class="ar ar--envoy"></span>使者 / 信使</div>
    <div class="legend__row"><span class="ar ar--plan"></span>计划 / 意图<span class="lg-flag"></span>主将牙旗</div>
    <div class="legend__row"><span class="mk mk--battle"></span>交战<span class="mk mk--death"></span>阵亡<span class="mk mk--seal">成</span>成语典故</div>
    <p class="legend__note">兵俑与舟船为示意，大小经放大；地形垂直比例经夸张。</p>
    <p class="legend__note legend__keys">拖动平移 · 右键或 Ctrl 拖动旋转 · 滚轮缩放</p>
  </div>
</section>

<div class="hud" id="hud">
  <div class="viewctl" role="group" aria-label="视角">
    <button class="viewctl__btn" id="turn-ccw" type="button" title="沙盘逆时针转 45°（Q）" aria-label="沙盘逆时针转 45 度">${SVG.turnCcw}</button>
    <button class="compass" id="compass" type="button" title="回到正北" aria-label="指北针：点击回到正北"><span class="compass__rose" id="compass-rose"><span>北</span></span></button>
    <button class="viewctl__btn" id="turn-cw" type="button" title="沙盘顺时针转 45°（E）" aria-label="沙盘顺时针转 45 度">${SVG.turnCw}</button>
    <button class="viewctl__flip" id="flip-view" type="button" title="翻转视角 180°（R）" aria-label="翻转视角 180 度">${SVG.flip}<span>翻转</span></button>
  </div>
  <div class="scalebar" id="scalebar"><div class="scalebar__bar" id="scalebar-bar"></div><div class="scalebar__label" id="scalebar-label"></div></div>
</div>

<footer class="timeline" id="timeline" aria-label="时间轴">
  <div class="timeline__controls">
    <button class="tl-btn" id="tl-prev" title="上一节点（←）">${SVG.prev}</button>
    <button class="tl-btn tl-btn--play" id="tl-play" title="播放 / 暂停（空格）">${SVG.play}</button>
    <button class="tl-btn" id="tl-next" title="下一节点（→）">${SVG.next}</button>
    <select class="tl-speed" id="tl-speed" aria-label="播放速度"><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option></select>
  </div>
  <div class="timeline__track" id="tl-track">
    <div class="timeline__groups" id="tl-groups"></div>
    <div class="timeline__rail" id="tl-rail"><div class="timeline__fill" id="tl-fill"></div><div class="timeline__head" id="tl-head"></div></div>
    <ol class="timeline__nodes" id="tl-nodes"></ol>
  </div>
</footer>

<div class="tooltip" id="tooltip" hidden></div>

<dialog class="about" id="about">
  <button class="about__close" id="about-close" aria-label="关闭">${SVG.close}</button>
  <h2>关于这座沙盘</h2>
  <div class="about__cols">
    <section>
      <h3>史料</h3>
      <p>战事经过、兵力与言语均据《资治通鉴》卷一〇四至一〇五（晋纪二十六至二十七）、《晋书》卷九《孝武帝纪》、卷七十九《谢安传》《谢玄传》、卷一一四《苻坚载记》；地名考证参用郦道元《水经注》卷三十二及胡三省《通鉴》注。</p>
      <p>日期以东晋太元八年历日为准（十月丙辰朔、十一月丙戌朔），公历为儒略历，依寿星万年历换算。淝水决战之日史有异说：《通鉴》系于十一月，《晋书·孝武帝纪》作“十月乙亥”（383年11月30日）。</p>
    </section>
    <section>
      <h3>地形与水系</h3>
      <p>地形取自 AWS Terrain Tiles（SRTM 等数据）的真实高程，战场沙盘约 82×49 公里，全局沙盘约 1260×770 公里。战场水系据 OpenStreetMap；全局水系据 Natural Earth，并按古地理改绘：黄河取东汉王景以来故道，淮河取宋以前独流入海之道，海岸线西移至约当时位置，删去丹江口水库、洪泽湖等后世水体。寿县周边的瓦埠湖、城西湖等在东晋时尚未成湖，图中作低洼湿地处理。</p>
    </section>
    <section>
      <h3>示意与推定</h3>
      <p>史书只记大势，各部的具体营址、队形与行军道路多为据史文与地形所作的推定，例如晋军大营按“去洛涧二十五里”（一晋里约435米）定位，青冈仅知“去寿春三十里”，方位为示意。兵俑、舟船与旗帜均经放大，数量不代表实际人数。</p>
      <p>操作：拖动平移沙盘，右键拖动（或按住 Ctrl / Shift 拖动）旋转与俯仰，滚轮向指针处缩放；触屏单指平移、双指缩放旋转。指北针两旁的按钮把沙盘逆时针或顺时针转 45°，「翻转」转 180° 看向对面（快捷键 Q、E、R），点击指北针回到正北。空格播放或暂停，左右方向键切换时间节点。</p>
    </section>
  </div>
</dialog>

<div class="map-fade" id="map-fade"></div>
`
    );

    this.$ = (id) => r.querySelector(`#${id}`);
    if (window.innerWidth <= 900) {
      // phones start with the story card folded so the battlefield stays visible
      this.$('episode').classList.add('is-collapsed');
      this.$('episode-toggle').setAttribute('aria-expanded', 'false');
      this.$('legend').classList.add('is-collapsed');
    }
    if (window.matchMedia?.('(pointer: coarse)').matches) {
      this.root.querySelector('.legend__keys').textContent = '单指平移 · 双指缩放与旋转';
    }
    this.buildTimeline();
    this.bind();
  }

  buildTimeline() {
    const nodes = this.$('tl-nodes');
    const groups = this.$('tl-groups');
    const N = EPISODES.length;
    EPISODES.forEach((ep, i) => {
      const li = document.createElement('li');
      li.className = `tl-node map-${ep.map}`;
      li.style.left = `${((i + 0.5) / N) * 100}%`;
      li.innerHTML = `<button class="tl-node__btn" data-i="${i}" title="${ep.title}（${ep.date}）"><span class="tl-node__dot"></span><span class="tl-node__label"><span class="tl-node__title">${ep.title}</span><span class="tl-node__date">${ep.date.replace('太元八年', '').trim() || ep.date}</span></span></button>`;
      nodes.appendChild(li);
    });
    for (const g of GROUPS) {
      const el = document.createElement('div');
      el.className = 'tl-group';
      el.style.left = `${(g.from / N) * 100}%`;
      el.style.width = `${((g.to - g.from + 1) / N) * 100}%`;
      el.innerHTML = `<span>${g.label}</span>`;
      groups.appendChild(el);
    }
  }

  bind() {
    const app = this.app;
    this.$('tl-play').addEventListener('click', () => app.togglePlay());
    this.$('tl-prev').addEventListener('click', () => app.stepEpisode(-1));
    this.$('tl-next').addEventListener('click', () => app.stepEpisode(1));
    this.$('tl-speed').addEventListener('change', (e) => (app.speed = Number(e.target.value)));
    this.$('compass').addEventListener('click', () => app.rig.faceNorth());
    this.$('turn-ccw').addEventListener('click', () => app.rig.turn(45));
    this.$('turn-cw').addEventListener('click', () => app.rig.turn(-45));
    this.$('flip-view').addEventListener('click', () => app.rig.turn(180));
    this.$('tl-nodes').addEventListener('click', (e) => {
      const b = e.target.closest('.tl-node__btn');
      if (b) app.jumpTo(Number(b.dataset.i));
    });
    // scrubbing on the rail
    const rail = this.$('tl-track');
    let dragging = false;
    const scrub = (ev) => {
      const rect = this.$('tl-rail').getBoundingClientRect();
      const f = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
      app.scrubTo(f * EPISODES.length);
    };
    rail.addEventListener('pointerdown', (ev) => {
      if (ev.target.closest('.tl-node__btn')) return;
      dragging = true;
      rail.setPointerCapture(ev.pointerId);
      app.pause();
      scrub(ev);
    });
    rail.addEventListener('pointermove', (ev) => dragging && scrub(ev));
    rail.addEventListener('pointerup', () => (dragging = false));
    rail.addEventListener('pointercancel', () => (dragging = false));

    for (const b of this.root.querySelectorAll('.scale-switch__btn')) {
      b.addEventListener('click', () => app.showMap(b.dataset.map));
    }
    this.$('btn-camera').addEventListener('click', () => app.rig.setAuto(!app.rig.auto));
    app.rig.onAutoChange((v) => this.$('btn-camera').setAttribute('aria-pressed', String(v)));
    this.$('btn-full').addEventListener('click', () => {
      const el = document.documentElement;
      if (!document.fullscreenElement) el.requestFullscreen?.().catch(() => {});
      else document.exitFullscreen?.().catch(() => {});
    });
    const pop = this.$('layers-pop');
    this.$('btn-layers').addEventListener('click', (e) => {
      e.stopPropagation();
      pop.hidden = !pop.hidden;
      this.$('btn-layers').setAttribute('aria-expanded', String(!pop.hidden));
    });
    document.addEventListener('pointerdown', (e) => {
      if (!pop.hidden && !pop.contains(e.target) && !e.target.closest('#btn-layers')) {
        pop.hidden = true;
        this.$('btn-layers').setAttribute('aria-expanded', 'false');
      }
    });
    const places = this.$('places-pop');
    this.$('btn-places').addEventListener('click', (e) => {
      e.stopPropagation();
      places.hidden = !places.hidden;
      this.$('btn-places').setAttribute('aria-expanded', String(!places.hidden));
      if (!places.hidden) {
        pop.hidden = true;
        this.$('btn-layers').setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('pointerdown', (e) => {
      if (!places.hidden && !places.contains(e.target) && !e.target.closest('#btn-places')) {
        places.hidden = true;
        this.$('btn-places').setAttribute('aria-expanded', 'false');
      }
    });
    this.$('places-list').addEventListener('click', (e) => {
      const b = e.target.closest('[data-place]');
      if (b) app.flyToPlace(b.dataset.place);
    });
    this.$('btn-sound').addEventListener('click', async () => {
      const on = this.$('btn-sound').getAttribute('aria-pressed') !== 'true';
      const ok = await app.sound.setEnabled(on);
      this.$('btn-sound').setAttribute('aria-pressed', String(on && ok));
      if (on && ok) app.sound.phrase(app.episodeIndex);
    });
    const about = this.$('about');
    this.$('btn-about').addEventListener('click', () => (about.showModal ? about.showModal() : about.setAttribute('open', '')));
    this.$('about-close').addEventListener('click', () => (about.close ? about.close() : about.removeAttribute('open')));
    about.addEventListener('click', (e) => {
      if (e.target === about) about.close?.();
    });
    const toggles = {
      'lay-places': (v) => app.setLayer('places', v),
      'lay-modern': (v) => app.setLayer('modern', v),
      'lay-arrows': (v) => app.setLayer('arrows', v),
      'lay-markers': (v) => app.setLayer('markers', v),
      'lay-units': (v) => app.setLayer('unitLabels', v),
      'lay-contours': (v) => app.setLayer('contours', v),
      'lay-grid': (v) => app.setLayer('grid', v),
    };
    for (const [id, fn] of Object.entries(toggles)) this.$(id).addEventListener('change', (e) => fn(e.target.checked));
    this.$('lay-exag').addEventListener('change', (e) => app.setExaggeration(Number(e.target.value)));
    this.$('lay-exag').addEventListener('input', (e) => (this.$('exag-out').textContent = `×${e.target.value}`));
    this.$('lay-quality').addEventListener('change', (e) => {
      app.qualityLocked = true;
      app.setQuality(e.target.value);
    });

    this.$('episode-toggle').addEventListener('click', () => {
      const ep = this.$('episode');
      const collapsed = ep.classList.toggle('is-collapsed');
      this.$('episode-toggle').setAttribute('aria-expanded', String(!collapsed));
      this.updateInsets();
    });
    window.addEventListener('resize', () => this.updateInsets());
    if (window.ResizeObserver) {
      const ro = new ResizeObserver(() => this.updateInsets());
      for (const el of this.root.querySelectorAll('.masthead, .toolbar, #episode, #legend, #timeline')) ro.observe(el);
    }
    this.updateInsets();
    this.$('legend-toggle').addEventListener('click', () => {
      const lg = this.$('legend');
      const collapsed = lg.classList.toggle('is-collapsed');
      this.$('legend-toggle').setAttribute('aria-expanded', String(!collapsed));
    });

    window.addEventListener('keydown', (e) => {
      if (e.target.closest?.('input, select, textarea, dialog[open]')) return;
      if (e.code === 'Space') {
        e.preventDefault();
        app.togglePlay();
      } else if (e.code === 'ArrowRight') app.stepEpisode(1);
      else if (e.code === 'ArrowLeft') app.stepEpisode(-1);
      else if (e.ctrlKey || e.metaKey || e.altKey) return;
      else if (e.code === 'KeyQ') app.rig.turn(45);
      else if (e.code === 'KeyE') app.rig.turn(-45);
      else if (e.code === 'KeyR') app.rig.turn(180);
    });
  }

  /** Tell the stage how much of the screen the episode panel covers. */
  updateInsets() {
    const panel = this.$('episode');
    if (!panel) return;
    this.measureChrome();
    const r = panel.getBoundingClientRect();
    const W = window.innerWidth;
    const H = window.innerHeight;
    if (W > 900) {
      this.app.stage.setInsets({ right: Math.min(r.width + 24, W * 0.4), bottom: 0 });
    } else {
      const covered = Math.max(0, H - r.top - 0) - 0;
      this.app.stage.setInsets({ right: 0, bottom: Math.min(covered * 0.75, H * 0.45) });
    }
  }

  /** Screen boxes of the overlay panels; map labels give way to them instead of showing through. */
  measureChrome() {
    const boxes = [];
    for (const el of this.root.querySelectorAll('.masthead, .toolbar, #episode, #legend, #timeline, .viewctl')) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) boxes.push([r.left, r.top, r.right, r.bottom]);
    }
    this.chrome = boxes;
  }

  setPlaying(p) {
    const b = this.$('tl-play');
    b.innerHTML = p ? SVG.pause : SVG.play;
    b.classList.toggle('is-playing', p);
    b.setAttribute('aria-label', p ? '暂停' : '播放');
  }

  renderPlaces(places) {
    const groups = [
      { label: '城邑营垒', kinds: ['capital', 'city', 'fort', 'camp'] },
      { label: '津渡关隘', kinds: ['ford', 'site', 'pass'] },
      { label: '山川', kinds: ['mountain'] },
    ];
    this.$('places-list').innerHTML = groups
      .map((g) => {
        const items = places.filter((p) => g.kinds.includes(p.kind));
        if (!items.length) return '';
        return `<div class="places-group"><div class="places-group__label">${g.label}</div>${items
          .map(
            (p) =>
              `<button class="place-item" data-place="${p.id}"><span class="place-item__name">${p.name}${p.approx ? '<i>（约）</i>' : ''}</span><span class="place-item__modern">${p.modern || ''}</span></button>`
          )
          .join('')}</div>`;
      })
      .join('');
  }

  showCaption(i) {
    const ep = EPISODES[i];
    const el = this.$('caption');
    this.$('cap-no').textContent = `第${ep.no}节`;
    this.$('cap-title').textContent = ep.title;
    this.$('cap-date').textContent = ep.date;
    el.classList.remove('is-on');
    void el.offsetWidth;
    el.classList.add('is-on');
  }

  setMap(name) {
    for (const b of this.root.querySelectorAll('.scale-switch__btn')) {
      const on = b.dataset.map === name;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-selected', String(on));
    }
    document.body.dataset.map = name;
  }

  setTime(T) {
    const N = EPISODES.length;
    const f = Math.min(1, T / N);
    this.$('tl-fill').style.width = `${f * 100}%`;
    this.$('tl-head').style.left = `${f * 100}%`;
  }

  setEpisode(i) {
    const ep = EPISODES[i];
    for (const li of this.root.querySelectorAll('.tl-node')) li.classList.remove('is-current', 'is-past');
    this.root.querySelectorAll('.tl-node').forEach((li, k) => {
      if (k < i) li.classList.add('is-past');
      if (k === i) li.classList.add('is-current');
    });
    this.$('ep-no').innerHTML = `<span>第</span>${ep.no}<span>节</span>`;
    this.$('ep-date').textContent = ep.date;
    this.$('ep-western').textContent = ep.western;
    this.$('ep-title').textContent = ep.title;
    this.$('ep-subtitle').textContent = ep.subtitle;
    this.$('ep-text').textContent = ep.narrative;
    this.$('ep-quote-text').textContent = ep.quote.text;
    this.$('ep-quote-src').textContent = `—— ${ep.quote.source}`;
    const dn = this.$('ep-datenote');
    dn.hidden = !ep.dateNote;
    if (ep.dateNote) this.$('ep-datenote-text').textContent = ep.dateNote;
    this.$('ep-people').innerHTML = ep.people.map((p) => `<span class="chip">${p}</span>`).join('');
    this.renderForces(ep);
    const box = this.$('episode');
    box.classList.remove('is-swap');
    void box.offsetWidth;
    box.classList.add('is-swap');
  }

  renderForces(ep) {
    const f = ep.forces;
    const el = this.$('ep-forces');
    if (!f) {
      el.innerHTML = '';
      return;
    }
    const q = f.qin;
    const j = f.jin;
    let html = '<div class="forces__title">兵力</div>';
    if (ep.tally && typeof q.value === 'number' && typeof j.value === 'number') {
      const per = 10000;
      const nq = Math.round(q.value / per);
      const nj = Math.round(j.value / per);
      const fig = (cls) => `<i class="tally__fig ${cls}"></i>`;
      html += `<div class="tally" role="img" aria-label="前秦约${fmtNum(q.value)}，东晋约${fmtNum(j.value)}；每个小人代表一万人">
        <div class="tally__row"><span class="tally__side side-qin">${q.label}<b>${fmtNum(q.value)}</b></span><span class="tally__figs">${fig('qin').repeat(nq)}</span></div>
        <div class="tally__row"><span class="tally__side side-jin">${j.label}<b>${fmtNum(j.value)}</b></span><span class="tally__figs">${fig('jin').repeat(nj)}</span></div>
        <div class="tally__key">每个小人代表一万人</div>
      </div>`;
    } else {
      html += `<div class="versus">
        <div class="versus__side side-qin"><span class="versus__label">${q.label}</span><span class="versus__value">${fmtNum(q.value)}</span></div>
        <div class="versus__side side-jin"><span class="versus__label">${j.label}</span><span class="versus__value">${fmtNum(j.value)}</span></div>
      </div>`;
    }
    html += `<ul class="forces__detail"><li class="side-qin">${q.detail}</li><li class="side-jin">${j.detail}</li></ul>`;
    el.innerHTML = html;
  }

  showTooltip(p, anchorEl) {
    const tip = this.$('tooltip');
    if (!p) {
      tip.hidden = true;
      return;
    }
    tip.innerHTML = `<div class="tooltip__name">${p.name}${p.alt ? `<span>（又称${p.alt}）</span>` : ''}</div>${p.modern ? `<div class="tooltip__modern">${p.modern}</div>` : ''}${p.note ? `<p>${p.note}</p>` : ''}`;
    tip.hidden = false;
    const r = anchorEl.getBoundingClientRect();
    const w = Math.min(300, window.innerWidth - 32);
    tip.style.width = `${w}px`;
    let x = r.left + r.width / 2 - w / 2;
    x = Math.max(16, Math.min(window.innerWidth - w - 16, x));
    let y = r.top - 12;
    tip.style.left = `${x}px`;
    tip.style.top = `${y}px`;
    tip.classList.toggle('below', y < 160);
    if (y < 160) tip.style.top = `${r.bottom + 12}px`;
  }

  updateHud(camera, controls, proj) {
    // compass: camera yaw relative to north
    const dx = controls.target.x - camera.position.x;
    const dz = controls.target.z - camera.position.z;
    const yaw = Math.atan2(dx, -dz); // 0 when looking north
    this.$('compass-rose').style.transform = `rotate(${-yaw}rad)`;
    // scale bar: world units per pixel at the target distance
    const dist = camera.position.distanceTo(controls.target);
    const h = 2 * dist * Math.tan((camera.fov * Math.PI) / 360);
    const unitsPerPx = h / window.innerHeight;
    const kmPerPx = unitsPerPx / proj.kmToWorld;
    const target = kmPerPx * 110;
    const steps = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500];
    const km = steps.find((s) => s >= target * 0.6) || 500;
    const px = km / kmPerPx;
    this.$('scalebar-bar').style.width = `${Math.round(px)}px`;
    const li = Math.round(km / 0.4356);
    this.$('scalebar-label').textContent = km >= 1 ? `${km} 公里 ≈ ${li} 晋里` : `${km * 1000} 米`;
  }

  fadeMap(on) {
    this.$('map-fade').classList.toggle('is-on', on);
  }
}
