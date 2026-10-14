import './styles/main.css';
import { App } from './app/App.js';

const app = new App(document.getElementById('app'));
window.__feishui = app;
app.start().catch((err) => {
  console.error(err);
  app.showFatal(err);
});
