import { SOUNDSCAPE } from '../data/effects.js';
import { AMBIENT_BEDS } from './Sound.js';

const FADE = 0.04; // of a time node: well under a second

/** Level (0..1) of every bed at timeline position T; only the ambient beds sound while paused. */
export function levelsAt(T, playing) {
  const out = {};
  for (const [key, windows] of Object.entries(SOUNDSCAPE.beds)) {
    let v = 0;
    if (playing || AMBIENT_BEDS.includes(key)) {
      for (const [a, b, level] of windows) {
        const e = Math.min(1, (T - a + FADE) / FADE, (b + FADE - T) / FADE);
        if (e > 0) v = Math.max(v, level * e);
      }
    }
    out[key] = v;
  }
  return out;
}

/** Names of the cues whose moment falls in (from, to]. */
export function cuesBetween(from, to) {
  return SOUNDSCAPE.cues.filter(([t]) => t > from && t <= to).map(([, name]) => name);
}
