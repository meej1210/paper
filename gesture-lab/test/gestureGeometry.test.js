import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createFrameHold,
  detectPinch,
  extractDoubleHandFrame,
  smoothPoint,
} from '../src/gestureGeometry.js';

const hand = (handedness, thumb, index) => ({
  handedness,
  landmarks: Array.from({ length: 21 }, () => ({ x: 0, y: 0, z: 0 })),
  worldLandmarks: [],
  score: 0.95,
  thumb,
  index,
});

function withTips(handInput) {
  const copy = structuredClone(handInput);
  copy.landmarks[4] = handInput.thumb;
  copy.landmarks[8] = handInput.index;
  return copy;
}

test('detectPinch returns true when thumb and index tips are close', () => {
  const result = detectPinch(
    { x: 0.5, y: 0.5 },
    { x: 0.53, y: 0.52 },
    0.07,
  );

  assert.equal(result.pinching, true);
  assert.ok(result.distance < 0.07);
});

test('detectPinch returns false when thumb and index tips are far apart', () => {
  const result = detectPinch(
    { x: 0.2, y: 0.2 },
    { x: 0.6, y: 0.6 },
    0.07,
  );

  assert.equal(result.pinching, false);
});

test('extractDoubleHandFrame returns a normalized bounding frame from two hands', () => {
  const left = withTips(hand('Left', { x: 0.2, y: 0.25 }, { x: 0.25, y: 0.7 }));
  const right = withTips(hand('Right', { x: 0.8, y: 0.25 }, { x: 0.75, y: 0.7 }));

  const result = extractDoubleHandFrame([right, left]);

  assert.equal(result.active, true);
  assert.deepEqual(result.bounds, {
    x: 0.2,
    y: 0.25,
    width: 0.6,
    height: 0.45,
  });
  assert.equal(result.points.length, 4);
});

test('extractDoubleHandFrame is inactive unless both hands are present', () => {
  const left = withTips(hand('Left', { x: 0.2, y: 0.25 }, { x: 0.25, y: 0.7 }));

  const result = extractDoubleHandFrame([left]);

  assert.equal(result.active, false);
  assert.equal(result.bounds, null);
});

test('smoothPoint blends the previous point toward the next point', () => {
  const result = smoothPoint({ x: 0.2, y: 0.4 }, { x: 0.8, y: 0.6 }, 0.25);

  assert.deepEqual(result, { x: 0.35, y: 0.45 });
});

test('createFrameHold keeps the last valid frame briefly after tracking is lost', () => {
  const hold = createFrameHold(300);
  const frame = {
    active: true,
    bounds: { x: 0.2, y: 0.2, width: 0.5, height: 0.4 },
    points: [],
  };

  assert.equal(hold.update(frame, 1000).active, true);
  assert.equal(hold.update({ active: false, bounds: null, points: [] }, 1200).active, true);
  assert.equal(hold.update({ active: false, bounds: null, points: [] }, 1401).active, false);
});
