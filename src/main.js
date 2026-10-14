import './styles/main.css';
import { App } from './app/App.js';

const app = new App(document.getElementById('app'));
window.__feishui = app;

// When hosted in a viewer that hot-swaps new versions, keep the reader's place on the timeline.
const hot = window.claude?.hot;
hot?.snapshot?.(() => ({ T: app.T }));
const start = (data = {}) =>
  app.start(data || {}).catch((err) => {
    console.error(err);
    app.showFatal(err);
  });
if (hot?.ready) hot.ready(start);
else start(hot?.data ?? {});
