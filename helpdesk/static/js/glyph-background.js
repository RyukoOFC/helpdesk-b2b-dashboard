/* Fundo animado de glifos em WebGL (port vanilla JS do componente GlyphBackground). */

const CHARACTERS =
  "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
const MAX_WAVES = 12;
const TRAIL = 12;
const TRAIL_LIFE = 700;
const WAVE_LIFE = 4;
const WAVE_GAP = 0.3;
const WAVE_SPEED = 560;
const WAVE_SLOWDOWN = 0.66;
const WAVE_EDGE = 10;
const WAVE_TAIL = 30;
const DRIFT = [-30, 12];
const ACTIVITY_DECAY = 900;
const MAX_DELTA = 64;

const VERTEX = `
attribute vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

const FRAGMENT = `
precision highp float;
uniform sampler2D atlas;
uniform vec2 size;
uniform vec2 cell;
uniform float dpr;
uniform float count;
uniform float time;
uniform float rest;
uniform float haze;
uniform float hoverInk;
uniform float activity;
uniform vec2 drift;
uniform vec3 color;
uniform vec3 accent;
uniform vec4 waves[${MAX_WAVES * 2}];
uniform vec4 trail[${TRAIL}];

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float smoothNoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
    mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
    u.y
  );
}

float clouds(vec2 p) {
  float v = 0.0;
  float a = 0.55;
  for (int i = 0; i < 4; i++) {
    v += a * smoothNoise(p);
    p = p * 2.02 + vec2(17.1, 9.4);
    a *= 0.5;
  }
  return v;
}

float outline(float kind, float angle, float phase) {
  if (kind < 0.5) return 1.0;
  if (kind < 1.5) {
    float s = sin(angle);
    float c = cos(angle);
    return (2.0 - 2.0 * s + s * sqrt(abs(c)) / (s + 1.4)) * 0.42;
  }
  return 1.0 + 0.14 * sin(3.0 * angle + phase) + 0.08 * sin(5.0 * angle - phase * 1.3);
}

void main() {
  vec2 pixel = vec2(gl_FragCoord.x, size.y - gl_FragCoord.y);
  vec2 index = floor(pixel / cell);
  vec2 point = (index + 0.5) * cell / dpr;

  float ring = 0.0;
  for (int i = 0; i < ${MAX_WAVES}; i++) {
    vec4 a = waves[i * 2];
    vec4 b = waves[i * 2 + 1];
    if (a.w <= 0.0) continue;
    vec2 v = point - a.xy;
    float angle = atan(-v.y, v.x);
    float shape = mix(1.0, outline(b.x, angle, b.z), b.y);
    shape *= 1.0 + 0.07 * sin(3.0 * angle + b.z + b.w) + 0.05 * sin(5.0 * angle - b.z * 1.7 - b.w * 1.3) + 0.03 * sin(9.0 * angle + b.w * 2.1);
    float d = length(v) - a.z * shape;
    float k = d > 0.0 ? d / ${WAVE_EDGE.toFixed(1)} : d / ${WAVE_TAIL.toFixed(1)};
    ring = max(ring, exp(-k * k) * a.w);
  }

  float hover = 0.0;
  for (int i = 0; i < ${TRAIL}; i++) {
    vec4 t = trail[i];
    if (t.w <= 0.0) continue;
    vec2 v = point - t.xy;
    hover += t.w * exp(-dot(v, v) / (2.0 * t.z * t.z));
  }
  hover = min(hover, 1.0);

  mat2 turn = mat2(0.82, 0.57, -0.57, 0.82);
  vec2 q = turn * (point - drift);
  float blob = smoothNoise(vec2(q.x / 140.0, q.y / 80.0) + vec2(time * 0.04, 0.0)) * 0.62
    + smoothNoise(vec2(q.x / 62.0, q.y / 36.0) + vec2(3.7, time * 0.06)) * 0.38;
  float grain = smoothNoise(vec2(q.x / 30.0, q.y / 14.0) + vec2(time * 0.2, 7.3));
  float cloud = blob * (0.82 + 0.24 * grain);
  float mask = pow(smoothstep(0.47 - 0.2 * activity, 0.84, cloud), 2.6);

  float seed = hash(index);
  float epoch = floor(time * 0.08 * (0.4 + seed) + seed * 97.0);
  float character = floor(hash(index + epoch * 0.137) * count);
  vec2 local = fract(pixel / cell);
  float ink = pow(texture2D(atlas, vec2((character + local.x) / count, local.y)).a, 1.7);

  float grey = ink * clamp(rest + haze * mask * (1.0 + 0.3 * activity) + hoverInk * hover * (0.6 + 0.4 * mask), 0.0, 1.0);
  float blue = ink * ring * 0.72;
  float alpha = grey + blue - grey * blue;
  vec3 tint = color * grey * (1.0 - blue) + accent * blue;
  gl_FragColor = vec4(tint, alpha);
}
`;

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
}

function toRgb(color) {
  const probe = document.createElement("canvas").getContext("2d");
  if (!probe) return [0.9, 0.9, 0.9];
  probe.fillStyle = color;
  probe.fillRect(0, 0, 1, 1);
  const [r, g, b] = probe.getImageData(0, 0, 1, 1).data;
  return [r / 255, g / 255, b / 255];
}

function drawAtlas(cellWidth, cellHeight, font) {
  const atlas = document.createElement("canvas");
  atlas.width = Math.ceil(cellWidth * CHARACTERS.length);
  atlas.height = Math.ceil(cellHeight);
  const context = atlas.getContext("2d");
  context.font = font;
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillStyle = "#fff";
  for (let i = 0; i < CHARACTERS.length; i++) {
    context.fillText(CHARACTERS[i], (i + 0.5) * cellWidth, cellHeight / 2);
  }
  return atlas;
}

function createRenderer(gl) {
  const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX);
  const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT);
  const program = gl.createProgram();
  if (!vertex || !fragment || !program) return null;
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
  gl.useProgram(program);

  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, "position");
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

  const at = (name) => gl.getUniformLocation(program, name);
  const uniforms = {
    size: at("size"),
    cell: at("cell"),
    dpr: at("dpr"),
    time: at("time"),
    activity: at("activity"),
    haze: at("haze"),
    drift: at("drift"),
    color: at("color"),
    accent: at("accent"),
    waves: at("waves"),
    trail: at("trail"),
  };
  gl.uniform1i(at("atlas"), 0);
  gl.uniform1f(at("count"), CHARACTERS.length);
  gl.uniform1f(at("rest"), 0);
  gl.uniform1f(at("hoverInk"), 0.3);

  return {
    atlas(image) {
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
    },
    draw(frame) {
      gl.viewport(0, 0, frame.width, frame.height);
      gl.uniform2f(uniforms.size, frame.width, frame.height);
      gl.uniform2f(uniforms.cell, ...frame.cell);
      gl.uniform1f(uniforms.dpr, frame.dpr);
      gl.uniform1f(uniforms.time, frame.time);
      gl.uniform1f(uniforms.activity, frame.activity);
      gl.uniform1f(uniforms.haze, frame.haze);
      gl.uniform2f(uniforms.drift, ...frame.drift);
      gl.uniform3f(uniforms.color, ...frame.color);
      gl.uniform3f(uniforms.accent, ...frame.accent);
      gl.uniform4fv(uniforms.waves, frame.waves);
      gl.uniform4fv(uniforms.trail, frame.trail);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    },
  };
}

export class GlyphBackground {
  constructor(container, options = {}) {
    this.container = container;
    this.glowColor = options.glowColor;
    this.shapeColor = options.shapeColor;
    this.fontSize = options.fontSize ?? 10;
    this.interactive = options.interactive ?? true;
    this.haze = options.haze ?? 0.1;

    this.canvas = document.createElement("canvas");
    this.canvas.setAttribute("aria-hidden", "true");
    this.canvas.className = "pointer-events-none absolute inset-0";
    container.prepend(this.canvas);

    const gl = this.canvas.getContext("webgl", {
      premultipliedAlpha: true,
      preserveDrawingBuffer: true,
      antialias: false,
    });
    this.renderer = gl ? createRenderer(gl) : null;
    if (!this.renderer) {
      this.canvas.remove();
      return;
    }

    this.width = 0;
    this.height = 0;
    this.dpr = 1;
    this.cell = [7, 13];
    this.frames = 0;
    this.colorKey = "";
    this.color = [0.9, 0.9, 0.9];
    this.accent = [0.9, 0.9, 0.9];
    this.waveBuffer = new Float32Array(MAX_WAVES * 8);
    this.trailBuffer = new Float32Array(TRAIL * 4);
    this.waves = [];
    this.trail = [];
    this.activity = { value: 0, at: 0 };
    this.time = 0;
    this.rafId = null;
    this.lastFrame = null;
    this.inView = true;
    this.pageVisible = document.visibilityState !== "hidden";
    this.motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    this.reduce = this.motionQuery.matches;

    this.handleVisibility = () => {
      this.pageVisible = document.visibilityState !== "hidden";
      this.updatePlaying();
    };
    this.handleMotionChange = (event) => {
      this.reduce = event.matches;
      this.updatePlaying();
    };
    this.handlePointerMove = (event) => this.onPointerMove(event);
    this.handlePointerDown = (event) => this.onPointerDown(event);

    document.addEventListener("visibilitychange", this.handleVisibility);
    this.motionQuery.addEventListener("change", this.handleMotionChange);
    window.addEventListener("pointermove", this.handlePointerMove);
    window.addEventListener("pointerdown", this.handlePointerDown);

    this.intersectionObserver = new IntersectionObserver(([entry]) => {
      this.inView = entry.isIntersecting;
      this.updatePlaying();
    });
    this.intersectionObserver.observe(container);

    this.resizeObserver = new ResizeObserver(() => {
      this.resize();
      this.draw(this.time);
    });
    this.resizeObserver.observe(container);

    this.resize();
    this.draw(this.time);
    this.updatePlaying();
  }

  resize() {
    const rect = this.container.getBoundingClientRect();
    this.width = rect.width;
    this.height = rect.height;
    this.dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
    this.canvas.width = Math.max(1, Math.round(this.width * this.dpr));
    this.canvas.height = Math.max(1, Math.round(this.height * this.dpr));
    this.canvas.style.width = `${this.width}px`;
    this.canvas.style.height = `${this.height}px`;

    const font = `${this.fontSize * this.dpr}px Menlo, ui-monospace, SFMono-Regular, Consolas, monospace`;
    const measure = document.createElement("canvas").getContext("2d");
    measure.font = font;
    this.cell = [
      Math.round(measure.measureText("0").width),
      Math.round(this.fontSize * 1.25 * this.dpr),
    ];
    this.renderer.atlas(drawAtlas(this.cell[0], this.cell[1], font));
  }

  updatePlaying() {
    const playing = this.inView && this.pageVisible && !this.reduce;
    if (playing && this.rafId === null) {
      this.lastFrame = null;
      this.rafId = requestAnimationFrame((now) => this.tick(now));
    } else if (!playing && this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
      this.draw(this.time);
    }
  }

  tick(now) {
    const delta = this.lastFrame === null ? 0 : Math.min(now - this.lastFrame, MAX_DELTA);
    this.lastFrame = now;
    this.time += delta;
    this.draw(this.time, true);
    this.rafId = requestAnimationFrame((next) => this.tick(next));
  }

  draw(time, looping = false) {
    if (this.width === 0 || this.height === 0) return;

    if (!looping || this.frames++ % 30 === 0) {
      const text = getComputedStyle(this.container).color || "#e5e5e5";
      const key = `${this.glowColor ?? text}|${this.shapeColor ?? text}`;
      if (key !== this.colorKey) {
        this.colorKey = key;
        this.color = toRgb(this.glowColor ?? text);
        this.accent = toRgb(this.shapeColor ?? text);
      }
    }

    this.waves = this.waves.filter((wave) => time - wave.start < WAVE_LIFE * 1000);
    this.waveBuffer.fill(0);
    this.waves.forEach((wave, i) => {
      const age = (time - wave.start) / 1000;
      if (age <= 0) return;
      const radius = (WAVE_SPEED * age) / (1 + WAVE_SLOWDOWN * age);
      const fade =
        Math.min(1, age / 0.05) *
        Math.exp(-Math.max(0, age - 0.4) / 1.3) *
        Math.min(1, (WAVE_LIFE - age) / 0.5);
      const b = this.waveBuffer;
      b[i * 8] = wave.x;
      b[i * 8 + 1] = wave.y;
      b[i * 8 + 2] = radius;
      b[i * 8 + 3] = fade * wave.strength;
      b[i * 8 + 4] = wave.kind;
      b[i * 8 + 5] = 0.12 + 0.5 * Math.min(1, age / 2.2);
      b[i * 8 + 6] = wave.phase;
      b[i * 8 + 7] = age * 3;
    });

    this.trailBuffer.fill(0);
    this.trail.forEach((point, i) => {
      const age = (time - point.t) / TRAIL_LIFE;
      if (age < 0 || age >= 1) return;
      const t = this.trailBuffer;
      t[i * 4] = point.x;
      t[i * 4 + 1] = point.y;
      t[i * 4 + 2] = 40 + 25 * age;
      t[i * 4 + 3] = 0.3 * (1 - age) * (1 - age);
    });

    const seconds = time / 1000;
    const activity =
      this.activity.value * Math.exp(-Math.max(0, time - this.activity.at) / ACTIVITY_DECAY);
    this.renderer.draw({
      activity,
      width: this.canvas.width,
      height: this.canvas.height,
      dpr: this.dpr,
      haze: this.haze,
      cell: this.cell,
      time: seconds,
      drift: [DRIFT[0] * seconds, DRIFT[1] * seconds],
      color: this.color,
      accent: this.accent,
      waves: this.waveBuffer,
      trail: this.trailBuffer,
    });
  }

  localPoint(event) {
    const rect = this.container.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  onPointerMove(event) {
    if (!this.interactive || this.reduce) return;
    const { x, y } = this.localPoint(event);
    const now = this.time;
    const last = this.trail[this.trail.length - 1];
    const current =
      this.activity.value * Math.exp(-Math.max(0, now - this.activity.at) / ACTIVITY_DECAY);
    this.activity = {
      value: Math.min(1, current + (last ? Math.hypot(x - last.x, y - last.y) : 0) / 600),
      at: now,
    };
    if (last && Math.hypot(x - last.x, y - last.y) < 18) return;
    this.trail = [
      ...this.trail.filter((p) => now - p.t < TRAIL_LIFE).slice(1 - TRAIL),
      { x, y, t: now },
    ];
  }

  onPointerDown(event) {
    if (!this.interactive || this.reduce) return;
    const { x, y } = this.localPoint(event);
    this.spawn(x, y);
    if (this.rafId === null) this.draw(this.time);
  }

  spawn(x, y) {
    const kind = 1 + Math.floor(Math.random() * 2);
    const phase = Math.random() * Math.PI * 2;
    for (const [delay, strength] of [
      [0, 1],
      [WAVE_GAP, 0.55],
    ]) {
      const wave = { x, y, kind, phase, strength, start: this.time + delay * 1000 };
      this.waves = [...this.waves.slice(1 - MAX_WAVES), wave];
    }
  }

  destroy() {
    if (this.rafId !== null) cancelAnimationFrame(this.rafId);
    this.rafId = null;
    document.removeEventListener("visibilitychange", this.handleVisibility);
    this.motionQuery.removeEventListener("change", this.handleMotionChange);
    window.removeEventListener("pointermove", this.handlePointerMove);
    window.removeEventListener("pointerdown", this.handlePointerDown);
    this.intersectionObserver.disconnect();
    this.resizeObserver.disconnect();
    this.canvas.remove();
  }
}

export function initGlyphBackgrounds(root = document) {
  return [...root.querySelectorAll("[data-glyph-background]")].map(
    (element) =>
      new GlyphBackground(element, {
        glowColor: element.dataset.glowColor,
        shapeColor: element.dataset.shapeColor,
        fontSize: element.dataset.fontSize ? Number(element.dataset.fontSize) : undefined,
        interactive: element.dataset.interactive !== "false",
        haze: element.dataset.haze ? Number(element.dataset.haze) : undefined,
      }),
  );
}

initGlyphBackgrounds();
