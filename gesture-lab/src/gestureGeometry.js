const THUMB_TIP = 4;
const INDEX_TIP = 8;

export function distance(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

export function detectPinch(thumbTip, indexTip, threshold = 0.06) {
  if (!thumbTip || !indexTip) {
    return { pinching: false, distance: Infinity };
  }

  const value = distance(thumbTip, indexTip);
  return {
    pinching: value <= threshold,
    distance: value,
  };
}

export function smoothPoint(previous, next, alpha = 0.35) {
  if (!previous) return next;
  if (!next) return previous;

  return {
    x: round(previous.x + (next.x - previous.x) * alpha),
    y: round(previous.y + (next.y - previous.y) * alpha),
  };
}

export function smoothBounds(previous, next, alpha = 0.35) {
  if (!previous) return next;
  if (!next) return previous;

  return {
    x: round(previous.x + (next.x - previous.x) * alpha),
    y: round(previous.y + (next.y - previous.y) * alpha),
    width: round(previous.width + (next.width - previous.width) * alpha),
    height: round(previous.height + (next.height - previous.height) * alpha),
  };
}

export function extractDoubleHandFrame(hands) {
  if (!Array.isArray(hands) || hands.length < 2) {
    return inactiveFrame();
  }

  const usableHands = hands
    .map((hand) => ({
      handedness: hand.handedness,
      thumb: hand.landmarks?.[THUMB_TIP],
      index: hand.landmarks?.[INDEX_TIP],
      score: hand.score ?? 1,
    }))
    .filter((hand) => hand.thumb && hand.index && hand.score >= 0.4)
    .slice(0, 2);

  if (usableHands.length < 2) {
    return inactiveFrame();
  }

  const points = usableHands.flatMap((hand) => [hand.thumb, hand.index]);
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = clamp01(Math.min(...xs));
  const maxX = clamp01(Math.max(...xs));
  const minY = clamp01(Math.min(...ys));
  const maxY = clamp01(Math.max(...ys));
  const width = round(maxX - minX);
  const height = round(maxY - minY);

  if (width < 0.08 || height < 0.08) {
    return inactiveFrame();
  }

  return {
    active: true,
    bounds: {
      x: round(minX),
      y: round(minY),
      width,
      height,
    },
    points: points.map((point) => ({ x: round(point.x), y: round(point.y) })),
  };
}

export function createFrameHold(timeoutMs = 300) {
  let lastFrame = inactiveFrame();
  let lastSeenAt = 0;

  return {
    update(frame, now = performance.now()) {
      if (frame?.active) {
        lastFrame = frame;
        lastSeenAt = now;
        return frame;
      }

      if (lastFrame.active && now - lastSeenAt <= timeoutMs) {
        return { ...lastFrame, held: true };
      }

      lastFrame = inactiveFrame();
      return lastFrame;
    },
  };
}

function inactiveFrame() {
  return {
    active: false,
    bounds: null,
    points: [],
  };
}

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function round(value) {
  return Number(value.toFixed(4));
}
