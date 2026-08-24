import { useCallback, useEffect, useRef, useMemo } from "react";

/* ─────────────────────────────────────────────
   CONSTANTS
   ───────────────────────────────────────────── */

const TAU = Math.PI * 2;

/** Simple continent outlines (lon/lat arrays, approximate). */
const CONTINENTS: [number, number][][] = [
  // Africa-ish
  [[-18, 37], [10, 37], [12, 30], [32, 30], [42, 12], [50, 10], [42, -3], [40, -12], [35, -25], [28, -34], [18, -35], [12, -18], [15, -5], [10, 5], [-5, 5], [-18, 15]],
  // Asia
  [[28, 42], [40, 42], [50, 38], [60, 36], [70, 28], [80, 10], [98, 8], [108, 15], [120, 22], [130, 30], [140, 38], [142, 45], [135, 55], [120, 55], [100, 50], [80, 50], [60, 50], [40, 45]],
  // South America
  [[-80, 12], [-75, 5], [-70, -5], [-65, -15], [-55, -22], [-48, -25], [-42, -22], [-38, -10], [-35, -2], [-50, 5], [-60, 10], [-75, 12]],
  // North America
  [[-125, 50], [-120, 60], [-100, 68], [-80, 65], [-60, 50], [-65, 45], [-80, 30], [-100, 28], [-105, 22], [-115, 30], [-122, 40]],
  // Europe
  [[-10, 38], [0, 43], [10, 48], [20, 55], [30, 60], [35, 68], [25, 72], [10, 65], [5, 55], [-5, 48], [-10, 40]],
];

/* ─────────────────────────────────────────────
   MATH HELPERS
   ───────────────────────────────────────────── */

function lonLatTo3D(lonDeg: number, latDeg: number): [number, number, number] {
  const lon = (lonDeg * Math.PI) / 180;
  const lat = (latDeg * Math.PI) / 180;
  return [
    Math.cos(lat) * Math.cos(lon),
    Math.cos(lat) * Math.sin(lon),
    Math.sin(lat),
  ];
}

function rotateY(p: [number, number, number], angle: number): [number, number, number] {
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  return [
    p[0] * cos - p[2] * sin,
    p[1],
    p[0] * sin + p[2] * cos,
  ];
}

function rotateX(p: [number, number, number], angle: number): [number, number, number] {
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  return [
    p[0],
    p[1] * cos - p[2] * sin,
    p[1] * sin + p[2] * cos,
  ];
}

/* ─────────────────────────────────────────────
   GLOBE COMPONENT — Cursor Globe
   ───────────────────────────────────────────── */

export interface GlobeProps {
  /** Width/height of the canvas in logical pixels. */
  size?: number;
  /** Time seed for rotation (updated by parent RAF loop). */
  time: number;
}

export default function Globe({ size = 60, time }: GlobeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const globeRadius = useMemo(() => size * 0.38, [size]);

  const draw = useCallback(
    (ctx: CanvasRenderingContext2D, w: number, h: number, t: number) => {
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;
      const radius = globeRadius;

      // Continuous rotation: ~10 seconds per full revolution
      // TAU / (10 * 1000) ≈ 0.000628 per ms
      const baseRotation = t * 0.000628;
      const tiltAngle = -0.15;
      const opacity = 0.9;

      // ── OUTER GLOW — #27A567 family ──
      const glowRadius = radius * 1.4;
      const glowGrad = ctx.createRadialGradient(cx, cy, radius * 0.5, cx, cy, glowRadius);
      glowGrad.addColorStop(0, `rgba(39, 165, 103, ${0.15 * opacity})`);
      glowGrad.addColorStop(0.5, `rgba(18, 70, 48, ${0.08 * opacity})`);
      glowGrad.addColorStop(1, "rgba(11, 42, 29, 0)");
      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, glowRadius, 0, TAU);
      ctx.fill();

      // ── GLOBE BODY — translucent dark glass ──
      const bodyGrad = ctx.createRadialGradient(cx - radius * 0.3, cy - radius * 0.3, 0, cx, cy, radius);
      bodyGrad.addColorStop(0, `rgba(40, 80, 60, ${0.25 * opacity})`);
      bodyGrad.addColorStop(0.5, `rgba(25, 55, 40, ${0.35 * opacity})`);
      bodyGrad.addColorStop(1, `rgba(39, 165, 103, ${0.25 * opacity})`);
      ctx.fillStyle = bodyGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.fill();

      // ── GLASS HIGHLIGHT ──
      const specGrad = ctx.createRadialGradient(
        cx - radius * 0.25, cy - radius * 0.3, 0,
        cx - radius * 0.1, cy - radius * 0.1, radius * 0.7
      );
      specGrad.addColorStop(0, `rgba(255, 255, 255, ${0.12 * opacity})`);
      specGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = specGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.fill();

      // ── GRID LINES ──
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.clip();

      const lineAlpha = 0.18 * opacity;

      // Latitude lines
      for (let lat = -60; lat <= 60; lat += 30) {
        ctx.beginPath();
        ctx.strokeStyle = `rgba(39, 165, 103, ${lineAlpha * (lat === 0 ? 2.5 : 1)})`;
        ctx.lineWidth = lat === 0 ? 0.8 : 0.4;
        for (let lon = -180; lon <= 180; lon += 3) {
          const p = lonLatTo3D(lon, lat);
          const rp = rotateY(p, baseRotation);
          const rp2 = rotateX(rp, tiltAngle);
          const px = cx + rp2[0] * radius;
          const py = cy - rp2[2] * radius;
          if (rp2[1] < 0) continue;
          if (lon === -180) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.stroke();
      }

      // Longitude lines
      for (let lon = 0; lon < 360; lon += 30) {
        ctx.beginPath();
        ctx.strokeStyle = `rgba(39, 165, 103, ${lineAlpha * (lon === 0 ? 2 : 1)})`;
        ctx.lineWidth = 0.3;
        let started = false;
        for (let lat = -90; lat <= 90; lat += 3) {
          const p = lonLatTo3D(lon, lat);
          const rp = rotateY(p, baseRotation);
          const rp2 = rotateX(rp, tiltAngle);
          const px = cx + rp2[0] * radius;
          const py = cy - rp2[2] * radius;
          if (rp2[1] < 0) { started = false; continue; }
          if (!started) { ctx.moveTo(px, py); started = true; }
          else ctx.lineTo(px, py);
        }
        ctx.stroke();
      }

      // ── CONTINENT SILHOUETTES ──
      ctx.strokeStyle = `rgba(39, 165, 103, ${0.35 * opacity})`;
      ctx.fillStyle = `rgba(18, 70, 48, ${0.18 * opacity})`;
      ctx.lineWidth = 0.5;

      for (const continent of CONTINENTS) {
        ctx.beginPath();
        let started = false;
        let visible = false;
        for (const [lon, lat] of continent) {
          const p = lonLatTo3D(lon, lat);
          const rp = rotateY(p, baseRotation);
          const rp2 = rotateX(rp, tiltAngle);
          const px = cx + rp2[0] * radius;
          const py = cy - rp2[2] * radius;
          if (rp2[1] < 0.05) { started = false; continue; }
          visible = true;
          if (!started) { ctx.moveTo(px, py); started = true; }
          else ctx.lineTo(px, py);
        }
        if (visible) { ctx.closePath(); ctx.fill(); ctx.stroke(); }
      }

      ctx.restore(); // unclip

      // ── EDGE GLOW — #27A567 ──
      const edgeGrad = ctx.createRadialGradient(cx, cy, radius * 0.92, cx, cy, radius * 1.02);
      edgeGrad.addColorStop(0, "rgba(39, 165, 103, 0)");
      edgeGrad.addColorStop(0.7, `rgba(39, 165, 103, ${0.10 * opacity})`);
      edgeGrad.addColorStop(1, `rgba(39, 165, 103, ${0.18 * opacity})`);
      ctx.fillStyle = edgeGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.02, 0, TAU);
      ctx.fill();

      // ── OUTER RING ──
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.strokeStyle = `rgba(39, 165, 103, ${0.40 * opacity})`;
      ctx.lineWidth = 0.8;
      ctx.stroke();
    },
    [globeRadius]
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);

    draw(ctx, size, size, time);
  }, [size, draw, time]);

  return (
    <canvas
      ref={canvasRef}
      className="globe-canvas"
      aria-hidden="true"
      style={{ width: size, height: size }}
    />
  );
}
