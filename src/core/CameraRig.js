import * as THREE from 'three';

const DEG = Math.PI / 180;
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const smooth = (t) => t * t * (3 - 2 * t);

function wrapYaw(a) {
  // shortest-path yaw difference
  let d = ((a % 360) + 540) % 360 - 180;
  return d;
}

/**
 * Cinematic camera on top of OrbitControls. Poses are {target: Vector3, dist, yaw, pitch}
 * where yaw is the compass direction the camera looks toward (0 = north) and pitch is the
 * angle above the horizon.
 */
export class CameraRig {
  constructor(stage) {
    this.stage = stage;
    this.camera = stage.camera;
    this.controls = stage.controls;
    this.auto = true;
    this.proj = null;
    this.from = null;
    this.flyT = 1;
    this.flyDur = 2.4;
    this.pose = { target: new THREE.Vector3(), dist: 100, yaw: 0, pitch: 50 };
    this.listeners = new Set();
    this.controls.addEventListener('start', () => {
      if (this._programmatic) return;
      this.setAuto(false);
    });
  }

  onAutoChange(fn) {
    this.listeners.add(fn);
  }

  setAuto(v) {
    if (this.auto === v) return;
    this.auto = v;
    if (v) this.beginFly();
    for (const fn of this.listeners) fn(v);
  }

  setProjection(proj) {
    this.proj = proj;
  }

  /** Narrow (portrait) screens see less sideways, so scripted shots pull back. */
  get distScale() {
    const el = this.stage.container;
    const aspect = el.clientWidth / Math.max(1, el.clientHeight);
    return aspect >= 1.6 ? 1 : Math.min(2.2, Math.sqrt(1.6 / aspect));
  }

  /** Converts an episode camera spec into a pose on the current table. */
  poseFrom(spec) {
    const [x, z] = this.proj.geoToWorld(spec.target[0], spec.target[1]);
    const y = Math.max(this.proj.groundY(x, z), 0);
    return { target: new THREE.Vector3(x, y, z), dist: spec.dist * this.distScale, yaw: spec.yaw, pitch: spec.pitch };
  }

  currentPose() {
    const t = this.controls.target.clone();
    const off = this.camera.position.clone().sub(t);
    const dist = off.length();
    const pitch = Math.asin(THREE.MathUtils.clamp(off.y / dist, -1, 1)) / DEG;
    const yaw = Math.atan2(-off.x, off.z) / DEG; // looking direction = -off
    return { target: t, dist, yaw, pitch };
  }

  apply(pose) {
    const yaw = pose.yaw * DEG;
    const pitch = pose.pitch * DEG;
    const look = new THREE.Vector3(Math.sin(yaw), 0, -Math.cos(yaw));
    const pos = pose.target
      .clone()
      .addScaledVector(look, -pose.dist * Math.cos(pitch))
      .add(new THREE.Vector3(0, pose.dist * Math.sin(pitch), 0));
    this.camera.position.copy(pos);
    this.controls.target.copy(pose.target);
    this.camera.lookAt(pose.target);
  }

  lerpPose(a, b, t) {
    return {
      target: a.target.clone().lerp(b.target, t),
      dist: Math.exp(THREE.MathUtils.lerp(Math.log(a.dist), Math.log(b.dist), t)),
      yaw: a.yaw + wrapYaw(b.yaw - a.yaw) * t,
      pitch: THREE.MathUtils.lerp(a.pitch, b.pitch, t),
    };
  }

  /** Start a fly-in from wherever the camera is now toward the scripted pose. */
  beginFly(duration = 2.4) {
    this.from = this.currentPose();
    this.flyT = 0;
    this.flyDur = duration;
  }

  /** Jump without animation to the scripted pose of an episode at a given progress. */
  snapTo(episode, progress = 0) {
    const a = this.poseFrom(episode.camera);
    const b = episode.camera2 ? this.poseFrom(episode.camera2) : a;
    const p = this.lerpPose(a, b, smooth(THREE.MathUtils.clamp(progress, 0, 1)));
    this._programmatic = true;
    this.apply(p);
    this.controls.update();
    this._programmatic = false;
    this.from = null;
    this.flyT = 1;
  }

  /** Jump without animation (used on map switch). */
  snap(spec) {
    const p = this.poseFrom(spec);
    this._programmatic = true;
    this.apply(p);
    this.controls.update();
    this._programmatic = false;
    this.from = null;
    this.flyT = 1;
  }

  update(dt, episode, progress) {
    if (!this.proj) return;
    if (!this.auto || !episode) {
      this.controls.update();
      return;
    }
    const a = this.poseFrom(episode.camera);
    const b = episode.camera2 ? this.poseFrom(episode.camera2) : a;
    let desired = this.lerpPose(a, b, smooth(THREE.MathUtils.clamp(progress, 0, 1)));
    if (this.from && this.flyT < 1) {
      this.flyT = Math.min(1, this.flyT + dt / this.flyDur);
      desired = this.lerpPose(this.from, desired, easeInOut(this.flyT));
    }
    this._programmatic = true;
    this.apply(desired);
    this._programmatic = false;
  }
}
