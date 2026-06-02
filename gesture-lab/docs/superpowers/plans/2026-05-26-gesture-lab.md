# Gesture Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent full-screen Chinese gesture interaction webpage with particle light, pinch writing, and double-hand frame color modes.

**Architecture:** A static Vite-style browser app served from `gesture-lab`, with shared camera and hand tracking feeding three Canvas renderers. Pure gesture geometry is isolated in `src/gestureGeometry.js` and covered by Node tests.

**Tech Stack:** HTML, CSS, JavaScript modules, Canvas 2D, MediaPipe Tasks Vision Hand Landmarker, browser `getUserMedia`, Node test runner.

---

### Task 1: Gesture Geometry

**Files:**
- Create: `gesture-lab/src/gestureGeometry.js`
- Create: `gesture-lab/test/gestureGeometry.test.js`

- [ ] Write tests for pinch detection, double-hand frame extraction, point smoothing, and frame hold behavior.
- [ ] Run `npm test` and verify the tests fail because the module does not exist yet.
- [ ] Implement the geometry module with named exports.
- [ ] Run `npm test` and verify all geometry tests pass.

### Task 2: Static App Shell

**Files:**
- Create: `gesture-lab/package.json`
- Create: `gesture-lab/index.html`
- Create: `gesture-lab/src/styles.css`
- Create: `gesture-lab/src/main.js`

- [ ] Add scripts for `npm test`, `npm run dev`, and `npm run build`.
- [ ] Build the full-screen Chinese UI with three mode buttons and short status labels.
- [ ] Implement camera permission flow and video visibility toggle.
- [ ] Keep the interface compact with no long instructional text.

### Task 3: Rendering Modes

**Files:**
- Modify: `gesture-lab/src/main.js`

- [ ] Add MediaPipe Hand Landmarker loading.
- [ ] Add shared frame loop that reads video, hand landmarks, and mode state.
- [ ] Implement `粒子光感` particle renderer driven by index fingertip / palm center.
- [ ] Implement `捏合写字` renderer using thumb-index pinch as pen down.
- [ ] Implement `双手框选` renderer using both hands' thumb and index tips as a frame.

### Task 4: Verification

**Files:**
- Verify: `gesture-lab`

- [ ] Run `npm test`.
- [ ] Run `npm run build`.
- [ ] Start `npm run dev -- --host 127.0.0.1`.
- [ ] Open the local URL in the in-app browser.
- [ ] Verify the page loads full-screen, Chinese labels are visible, and controls switch state.
