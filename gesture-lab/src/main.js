import {
  createFrameHold,
  detectPinch,
  extractDoubleHandFrame,
  smoothBounds,
  smoothPoint,
} from './gestureGeometry.js';

const MODE_LABELS = {
  particles: '粒子光感',
  write: '捏合写字',
  frame: '双手框选',
};

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [0, 9], [9, 10], [10, 11], [11, 12],
  [0, 13], [13, 14], [14, 15], [15, 16],
  [0, 17], [17, 18], [18, 19], [19, 20],
  [5, 9], [9, 13], [13, 17],
];

const video = document.querySelector('#camera');
const canvas = document.querySelector('#scene');
const ctx = canvas.getContext('2d', { alpha: true });
const permission = document.querySelector('#permission');
const startButton = document.querySelector('#startButton');
const statusEl = document.querySelector('#status');
const debugPanel = document.querySelector('#debugPanel');
const modeButtons = [...document.querySelectorAll('.mode-button')];
const videoToggle = document.querySelector('#videoToggle');
const skeletonToggle = document.querySelector('#skeletonToggle');
const clearButton = document.querySelector('#clearButton');
const resetButton = document.querySelector('#resetButton');

const state = {
  mode: 'particles',
  showVideo: true,
  showSkeleton: true,
  running: false,
  detector: null,
  detecting: false,
  lastDetectAt: 0,
  lastDebugAt: 0,
  hands: [],
  particles: [],
  strokes: [],
  currentStroke: null,
  previousPoint: null,
  smoothedFrame: null,
  frameHold: createFrameHold(320),
  lastVideoTime: -1,
};

const offscreen = document.createElement('canvas');
const offscreenCtx = offscreen.getContext('2d', { willReadFrequently: true });

resize();
initParticles();
drawIdle();

window.addEventListener('resize', () => {
  resize();
  initParticles();
});

window.addEventListener('keydown', (event) => {
  if (event.key.toLowerCase() === 'd') {
    debugPanel.hidden = !debugPanel.hidden;
  }
});

startButton.addEventListener('click', start);

modeButtons.forEach((button) => {
  button.addEventListener('click', () => {
    setMode(button.dataset.mode);
  });
});

videoToggle.addEventListener('click', () => {
  state.showVideo = !state.showVideo;
  video.classList.toggle('hidden', !state.showVideo);
  videoToggle.classList.toggle('active', state.showVideo);
});

skeletonToggle.addEventListener('click', () => {
  state.showSkeleton = !state.showSkeleton;
  skeletonToggle.classList.toggle('active', state.showSkeleton);
});

clearButton.addEventListener('click', () => {
  state.strokes = [];
  state.currentStroke = null;
});

resetButton.addEventListener('click', () => {
  state.strokes = [];
  state.currentStroke = null;
  state.previousPoint = null;
  state.smoothedFrame = null;
  initParticles();
});

async function start() {
  try {
    startButton.disabled = true;
    startButton.textContent = '启动中';
    setStatus('启动中');
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: 'user',
      },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    state.running = true;
    permission.classList.add('hidden');
    setStatus('加载中');
    requestAnimationFrame(loop);
    loadHandDetector();
  } catch (error) {
    console.error(error);
    startButton.disabled = false;
    startButton.textContent = '开启摄像头';
    setStatus('未授权');
  }
}

async function loadHandDetector() {
  try {
    state.detector = await createHandDetector();
    setStatus('等待手势');
  } catch (error) {
    console.error(error);
    setStatus('模型失败');
  }
}

async function createHandDetector() {
  await loadScript('/node_modules/@mediapipe/hands/hands.js');

  const hands = new window.Hands({
    locateFile: (file) => `/node_modules/@mediapipe/hands/${file}`,
  });

  hands.setOptions({
    maxNumHands: 2,
    modelComplexity: 0,
    minDetectionConfidence: 0.55,
    minTrackingConfidence: 0.5,
  });

  hands.onResults((results) => {
    const landmarks = results.multiHandLandmarks ?? [];
    const handednesses = results.multiHandedness ?? [];

    state.hands = landmarks.map((points, index) => ({
      landmarks: mirrorLandmarks(points),
      handedness: getHandedness(handednesses[index], index),
      score: getHandScore(handednesses[index]),
    }));
  });

  if (typeof hands.initialize === 'function') {
    await hands.initialize();
  }

  return hands;
}

function loop(now) {
  resize();
  const hands = detectHands(now);

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawBackdrop();

  if (state.mode === 'frame') {
    drawFrameMode(hands, now);
  } else if (state.mode === 'write') {
    drawWriteMode(hands);
  } else {
    drawParticleMode(hands);
  }

  if (state.showSkeleton) {
    drawSkeleton(hands);
  }

  debugHealth(now, hands);

  if (state.running) {
    requestAnimationFrame(loop);
  }
}

function detectHands(now) {
  if (!state.detector || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    return [];
  }

  scheduleHandDetection(now);
  updateStatus(state.hands);
  return state.hands;
}

async function scheduleHandDetection(now) {
  if (state.detecting || now - state.lastDetectAt < 66) return;
  if (video.currentTime === state.lastVideoTime) return;

  state.detecting = true;
  state.lastDetectAt = now;
  state.lastVideoTime = video.currentTime;

  try {
    await state.detector.send({ image: video });
  } catch (error) {
    console.error(error);
    setStatus('识别失败');
  } finally {
    state.detecting = false;
  }
}

function drawParticleMode(hands) {
  const driver = getIndexPoint(hands[0]) ?? { x: 0.5, y: 0.5 };
  state.previousPoint = smoothPoint(state.previousPoint, driver, 0.22);
  const target = toCanvas(state.previousPoint);

  ctx.globalCompositeOperation = 'lighter';
  for (const particle of state.particles) {
    const dx = target.x - particle.x;
    const dy = target.y - particle.y;
    const force = Math.max(0.2, 1 - Math.hypot(dx, dy) / Math.max(canvas.width, canvas.height));
    particle.vx += dx * 0.0007 * force;
    particle.vy += dy * 0.0007 * force;
    particle.vx *= 0.96;
    particle.vy *= 0.96;
    particle.x += particle.vx;
    particle.y += particle.vy;

    if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
    if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;

    const glow = 0.35 + force * 0.65;
    ctx.beginPath();
    ctx.fillStyle = `rgba(${particle.color},${glow})`;
    ctx.shadowColor = `rgba(${particle.color},0.95)`;
    ctx.shadowBlur = 18 * glow;
    ctx.arc(particle.x, particle.y, particle.size * (0.8 + force), 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalCompositeOperation = 'source-over';
  ctx.shadowBlur = 0;

  drawPulse(target.x, target.y, 88, 'rgba(56,232,255,0.28)');
}

function drawWriteMode(hands) {
  const hand = hands[0];
  const thumb = hand?.landmarks?.[4];
  const index = hand?.landmarks?.[8];
  const pinch = detectPinch(thumb, index, 0.055);
  const point = index ? toCanvas(index) : null;

  if (pinch.pinching && point) {
    setStatus('落笔');
    if (!state.currentStroke) {
      state.currentStroke = [];
      state.strokes.push(state.currentStroke);
    }
    state.currentStroke.push(point);
  } else {
    state.currentStroke = null;
  }

  drawStrokes();

  if (point) {
    drawPulse(point.x, point.y, pinch.pinching ? 42 : 24, pinch.pinching ? 'rgba(255,79,216,0.42)' : 'rgba(56,232,255,0.32)');
  }
}

function drawFrameMode(hands, now) {
  drawVideoProcessed();

  const rawFrame = extractDoubleHandFrame(hands);
  const heldFrame = state.frameHold.update(rawFrame, now);
  if (heldFrame.active && heldFrame.bounds) {
    state.smoothedFrame = smoothBounds(state.smoothedFrame, heldFrame.bounds, 0.28);
    drawColorWindow(state.smoothedFrame);
    drawFrameBorder(state.smoothedFrame, heldFrame.held);
  } else {
    state.smoothedFrame = null;
  }
}

function drawVideoProcessed() {
  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;

  ctx.save();
  ctx.globalAlpha = 0.86;
  ctx.filter = 'grayscale(1) brightness(0.72) contrast(1.08)';
  ctx.scale(-1, 1);
  ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
  ctx.restore();
  ctx.filter = 'none';
}

function drawColorWindow(bounds) {
  if (!bounds || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;
  const rect = boundsToCanvas(bounds);
  ctx.save();
  ctx.beginPath();
  ctx.rect(rect.x, rect.y, rect.width, rect.height);
  ctx.clip();
  ctx.scale(-1, 1);
  ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
  ctx.restore();
}

function drawFrameBorder(bounds, held) {
  const rect = boundsToCanvas(bounds);
  ctx.save();
  ctx.strokeStyle = held ? 'rgba(117,246,255,0.42)' : 'rgba(56,232,255,0.95)';
  ctx.lineWidth = 3;
  ctx.shadowColor = '#38e8ff';
  ctx.shadowBlur = 22;
  ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);

  ctx.strokeStyle = 'rgba(255,79,216,0.9)';
  ctx.shadowColor = '#ff4fd8';
  const len = Math.min(rect.width, rect.height) * 0.18;
  drawCorner(rect.x, rect.y, len, 1, 1);
  drawCorner(rect.x + rect.width, rect.y, len, -1, 1);
  drawCorner(rect.x, rect.y + rect.height, len, 1, -1);
  drawCorner(rect.x + rect.width, rect.y + rect.height, len, -1, -1);
  ctx.restore();
}

function drawCorner(x, y, len, sx, sy) {
  ctx.beginPath();
  ctx.moveTo(x, y + len * sy);
  ctx.lineTo(x, y);
  ctx.lineTo(x + len * sx, y);
  ctx.stroke();
}

function drawStrokes() {
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = 7;
  ctx.strokeStyle = '#ff4fd8';
  ctx.shadowColor = '#ff4fd8';
  ctx.shadowBlur = 18;

  for (const stroke of state.strokes) {
    if (stroke.length < 2) continue;
    ctx.beginPath();
    ctx.moveTo(stroke[0].x, stroke[0].y);
    for (const point of stroke.slice(1)) {
      ctx.lineTo(point.x, point.y);
    }
    ctx.stroke();
  }
  ctx.restore();
}

function drawSkeleton(hands) {
  ctx.save();
  ctx.lineWidth = 2;
  ctx.shadowBlur = 10;

  for (const hand of hands) {
    for (const [from, to] of HAND_CONNECTIONS) {
      const a = hand.landmarks[from];
      const b = hand.landmarks[to];
      if (!a || !b) continue;
      const pa = toCanvas(a);
      const pb = toCanvas(b);
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(117,246,255,0.72)';
      ctx.shadowColor = '#38e8ff';
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
    }

    for (const point of hand.landmarks) {
      const p = toCanvas(point);
      ctx.beginPath();
      ctx.fillStyle = 'rgba(234,254,255,0.88)';
      ctx.shadowColor = '#75f6ff';
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.restore();
}

function drawBackdrop() {
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  const gradient = ctx.createRadialGradient(
    canvas.width * 0.5,
    canvas.height * 0.45,
    0,
    canvas.width * 0.5,
    canvas.height * 0.45,
    Math.max(canvas.width, canvas.height) * 0.72,
  );
  gradient.addColorStop(0, 'rgba(56,232,255,0.08)');
  gradient.addColorStop(0.46, 'rgba(255,79,216,0.035)');
  gradient.addColorStop(1, 'rgba(3,5,13,0.42)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.restore();
}

function drawIdle() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawBackdrop();
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  for (const particle of state.particles) {
    ctx.beginPath();
    ctx.fillStyle = `rgba(${particle.color},0.45)`;
    ctx.shadowColor = `rgba(${particle.color},0.8)`;
    ctx.shadowBlur = 12;
    ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawPulse(x, y, radius, color) {
  ctx.save();
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.shadowColor = color;
  ctx.shadowBlur = 18;
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

function setMode(mode) {
  state.mode = mode;
  state.currentStroke = null;
  modeButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.mode === mode);
  });
  setStatus(MODE_LABELS[mode]);
}

function updateStatus(hands) {
  if (!state.detector) return;

  if (state.mode === 'frame') {
    setStatus(hands.length >= 2 ? '已识别双手' : '等待双手');
  } else if (hands.length > 0) {
    setStatus('已识别单手');
  } else if (hands.length === 0) {
    setStatus('等待手势');
  }
}

function setStatus(text) {
  statusEl.textContent = text;
}

function initParticles() {
  const count = Math.min(64, Math.max(36, Math.round((window.innerWidth * window.innerHeight) / 26000)));
  state.particles = Array.from({ length: count }, (_, index) => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    vx: (Math.random() - 0.5) * 0.9,
    vy: (Math.random() - 0.5) * 0.9,
    size: 1.3 + Math.random() * 2.6,
    color: index % 3 === 0 ? '255,79,216' : index % 3 === 1 ? '56,232,255' : '138,120,255',
  }));
}

function resize() {
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 1);
  const width = Math.floor(window.innerWidth * pixelRatio);
  const height = Math.floor(window.innerHeight * pixelRatio);
  if (canvas.width === width && canvas.height === height) return;
  canvas.width = width;
  canvas.height = height;
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

function getIndexPoint(hand) {
  return hand?.landmarks?.[8] ?? null;
}

function mirrorLandmarks(points) {
  return points.map((point) => ({
    x: 1 - point.x,
    y: point.y,
    z: point.z,
  }));
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      existing.addEventListener('load', resolve, { once: true });
      existing.addEventListener('error', reject, { once: true });
      if (window.Hands) resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.addEventListener('load', resolve, { once: true });
    script.addEventListener('error', reject, { once: true });
    document.head.append(script);
  });
}

function getHandedness(value, index) {
  return value?.label ?? value?.classification?.[0]?.label ?? `Hand-${index}`;
}

function getHandScore(value) {
  return value?.score ?? value?.classification?.[0]?.score ?? 1;
}

function debugHealth(now, hands) {
  debugPanel.textContent = [
    `模式 ${MODE_LABELS[state.mode]}`,
    `模型 ${state.detector ? '已加载' : '未加载'}`,
    `检测 ${state.detecting ? '运行中' : '空闲'}`,
    `手数 ${hands.length}`,
    `画布 ${canvas.width}x${canvas.height}`,
    `粒子 ${state.particles.length}`,
    `状态 ${statusEl.textContent}`,
  ].join('\n');

  if (now - state.lastDebugAt < 2000) return;
  state.lastDebugAt = now;
  console.info('[gesture-lab]', {
    mode: state.mode,
    detector: Boolean(state.detector),
    detecting: state.detecting,
    hands: hands.length,
    canvas: `${canvas.width}x${canvas.height}`,
    particles: state.particles.length,
    status: statusEl.textContent,
  });
}

function toCanvas(point) {
  return {
    x: point.x * canvas.width,
    y: point.y * canvas.height,
  };
}

function boundsToCanvas(bounds) {
  return {
    x: bounds.x * canvas.width,
    y: bounds.y * canvas.height,
    width: bounds.width * canvas.width,
    height: bounds.height * canvas.height,
  };
}
