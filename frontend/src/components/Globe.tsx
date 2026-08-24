import { useCallback, useEffect, useRef, useMemo } from "react";

/* ─────────────────────────────────────────────
   CONSTANTS
   ───────────────────────────────────────────── */

const TAU = Math.PI * 2;

/** Simple continent outlines (lon/lat arrays, very approximate for atmosphere). */
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

/** Label data points that float around the globe. */
interface DataPoint {
  lon: number;
  lat: number;
  label: string;
  color: string;
  size: number;
}

const DATA_POINTS: DataPoint[] = [
  { lon: 78.0, lat: 26.9, label: "MONITORING NODE", color: "#B6F36B", size: 3 },
  { lon: 76.5, lat: 25.5, label: "DRONE PATROL", color: "#71E29B", size: 2.5 },
  { lon: 79.0, lat: 27.5, label: "WILDLIFE CORRIDOR", color: "#FFBD62", size: 2.5 },
  { lon: 77.0, lat: 24.8, label: "RANGER STATION", color: "#71E29B", size: 2 },
  { lon: 80.0, lat: 28.0, label: "FOREST ZONE", color: "#B6F36B", size: 3 },
  { lon: 74.0, lat: 22.0, label: "MONITORING NODE", color: "#71E29B", size: 2 },
  { lon: 82.0, lat: 30.0, label: "DRONE PATROL", color: "#FFBD62", size: 2 },
  { lon: 30.0, lat: -1.0, label: "FOREST ZONE", color: "#71E29B", size: 2.5 },
  { lon: -60.0, lat: -10.0, label: "WILDLIFE CORRIDOR", color: "#FFBD62", size: 2 },
  { lon: -50.0, lat: 2.0, label: "FOREST ZONE", color: "#B6F36B", size: 2.5 },
];

/* ─────────────────────────────────────────────
   MATH HELPERS
   ───────────────────────────────────────────── */

/** Convert lon/lat (degrees) to 3D point on unit sphere. */
function lonLatTo3D(lonDeg: number, latDeg: number): [number, number, number] {
  const lon = (lonDeg * Math.PI) / 180;
  const lat = (latDeg * Math.PI) / 180;
  return [
    Math.cos(lat) * Math.cos(lon),
    Math.cos(lat) * Math.sin(lon),
    Math.sin(lat),
  ];
}

/** Rotate a 3D point around the Y axis. */
function rotateY(p: [number, number, number], angle: number): [number, number, number] {
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  return [
    p[0] * cos - p[2] * sin,
    p[1],
    p[0] * sin + p[2] * cos,
  ];
}

/** Rotate around X axis. */
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
   GLOBE COMPONENT
   ───────────────────────────────────────────── */

export interface GlobeProps {
  /** Scroll progress 0–1 controlling rotation. */
  scrollProgress: number;
  /** Visual mode changes as user scrolls to benchmarks. */
  mode?: "geographic" | "intelligence" | "expanding";
  /** Expansion progress 0–1 for the enter-mission transition. */
  expandProgress?: number;
  /** Exit dissolve progress 0–1 for the benchmarks section transition. */
  exitProgress?: number;
  /** Width of the canvas. */
  size?: number;
}

export default function Globe({
  scrollProgress,
  mode = "geographic",
  expandProgress = 0,
  exitProgress = 0,
  size = 600,
}: GlobeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const timeRef = useRef<number>(0);

  // Store dynamic props in refs so draw callback is stable (no RAF restarts).
  const scrollProgressRef = useRef(scrollProgress);
  scrollProgressRef.current = scrollProgress;
  const exitProgressRef = useRef(exitProgress);
  exitProgressRef.current = exitProgress;
  const modeRef = useRef(mode);
  modeRef.current = mode;

  // Memoize static data
  const globeRadius = useMemo(() => size * 0.38, [size]);

  const draw = useCallback(
    (ctx: CanvasRenderingContext2D, w: number, h: number, time: number) => {
      const sp = scrollProgressRef.current;
      const ep = exitProgressRef.current;
      const currentMode = modeRef.current;

      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;

      // Exit expansion: globe grows as it dissolves
      const exitExpand = 1 + ep * 0.5;
      const radius = globeRadius * (1 + expandProgress * 2.5) * exitExpand;
      const opacity = Math.max(0, 1 - expandProgress * 0.3) * (1 - ep);

      // Scroll-driven rotation
      const baseRotation = sp * TAU * 0.8;
      const tiltAngle = -0.15; // slight axial tilt

      // ── OUTER ATMOSPHERIC GLOW ──
      const glowRadius = radius * 1.35;
      const glowGrad = ctx.createRadialGradient(cx, cy, radius * 0.6, cx, cy, glowRadius);
      glowGrad.addColorStop(0, `rgba(113, 226, 155, ${0.04 * opacity})`);
      glowGrad.addColorStop(0.5, `rgba(182, 243, 107, ${0.02 * opacity})`);
      glowGrad.addColorStop(1, "rgba(18, 40, 31, 0)");
      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, glowRadius, 0, TAU);
      ctx.fill();

      // ── EXIT GLOW: expanding halo that intensifies then fades ──
      if (ep > 0 && ep < 1) {
        const exitGlowRadius = radius * (1.5 + ep * 1.2);
        const exitGlowGrad = ctx.createRadialGradient(cx, cy, radius * 0.4, cx, cy, exitGlowRadius);
        exitGlowGrad.addColorStop(0, `rgba(182, 243, 107, ${0.1 * (1 - ep)})`);
        exitGlowGrad.addColorStop(0.4, `rgba(113, 226, 155, ${0.05 * (1 - ep)})`);
        exitGlowGrad.addColorStop(1, "rgba(182, 243, 107, 0)");
        ctx.fillStyle = exitGlowGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, exitGlowRadius, 0, TAU);
        ctx.fill();
      }

      // ── GLOBE BODY — translucent dark green ──
      const bodyGrad = ctx.createRadialGradient(cx - radius * 0.3, cy - radius * 0.3, 0, cx, cy, radius);
      bodyGrad.addColorStop(0, `rgba(16, 35, 26, ${0.35 * opacity})`);
      bodyGrad.addColorStop(0.5, `rgba(13, 27, 22, ${0.55 * opacity})`);
      bodyGrad.addColorStop(1, `rgba(8, 17, 14, ${0.75 * opacity})`);
      ctx.fillStyle = bodyGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.fill();

      // ── GLASS HIGHLIGHT (specular) ──
      const specGrad = ctx.createRadialGradient(
        cx - radius * 0.25, cy - radius * 0.3, 0,
        cx - radius * 0.1, cy - radius * 0.1, radius * 0.7
      );
      specGrad.addColorStop(0, `rgba(182, 243, 107, ${0.06 * opacity})`);
      specGrad.addColorStop(1, "rgba(182, 243, 107, 0)");
      ctx.fillStyle = specGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.fill();

      // ── EQUATOR & MERIDIAN LINES ──
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.clip();

      const lineAlpha = 0.08 * opacity;

      // Latitude lines
      for (let lat = -60; lat <= 60; lat += 30) {
        ctx.beginPath();
        ctx.strokeStyle = `rgba(113, 226, 155, ${lineAlpha * (lat === 0 ? 2.5 : 1)})`;
        ctx.lineWidth = lat === 0 ? 1.2 : 0.6;
        for (let lon = -180; lon <= 180; lon += 3) {
          const p = lonLatTo3D(lon, lat);
          const rp = rotateY(p, baseRotation);
          const rp2 = rotateX(rp, tiltAngle);
          const px = cx + rp2[0] * radius;
          const py = cy - rp2[2] * radius;
          if (rp2[1] < 0) continue; // behind globe
          if (lon === -180) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.stroke();
      }

      // Longitude lines
      for (let lon = 0; lon < 360; lon += 30) {
        ctx.beginPath();
        ctx.strokeStyle = `rgba(113, 226, 155, ${lineAlpha * (lon === 0 ? 2 : 1)})`;
        ctx.lineWidth = 0.5;
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
      ctx.strokeStyle = `rgba(45, 80, 64, ${0.25 * opacity})`;
      ctx.fillStyle = `rgba(27, 57, 44, ${0.12 * opacity})`;
      ctx.lineWidth = 0.8;

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

      // ── SCANNING ARC ──
      const scanAngle = (time * 0.0008 + baseRotation) % TAU;
      const scanGrad = ctx.createConicGradient(scanAngle - Math.PI / 6, cx, cy);
      scanGrad.addColorStop(0, "rgba(182, 243, 107, 0)");
      scanGrad.addColorStop(0.05, `rgba(182, 243, 107, ${0.06 * opacity})`);
      scanGrad.addColorStop(0.1, "rgba(182, 243, 107, 0)");
      ctx.fillStyle = scanGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.fill();

      ctx.restore(); // unclip

      // ── ORBITAL RINGS ──
      const ringAlpha = currentMode === "intelligence" ? 0.18 : 0.1;
      const ringCount = currentMode === "intelligence" ? 3 : 2;

      for (let i = 0; i < ringCount; i++) {
        const orbitRadius = radius * (1.18 + i * 0.12);
        const orbitSpeed = (i % 2 === 0 ? 1 : -1) * 0.3;
        const orbitTilt = 0.3 + i * 0.15;
        const dashPhase = time * 0.0003 * orbitSpeed;

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(orbitTilt);

        ctx.beginPath();
        ctx.ellipse(0, 0, orbitRadius, orbitRadius * 0.3, 0, 0, TAU);
        ctx.strokeStyle = `rgba(113, 226, 155, ${ringAlpha * opacity})`;
        ctx.lineWidth = 0.8;
        ctx.setLineDash([4, 8]);
        ctx.lineDashOffset = dashPhase * 40;
        ctx.stroke();
        ctx.setLineDash([]);

        // Small dot on orbital ring
        const dotAngle = time * 0.001 * orbitSpeed + i * 2.1;
        const dotX = Math.cos(dotAngle) * orbitRadius;
        const dotY = Math.sin(dotAngle) * orbitRadius * 0.3;
        ctx.beginPath();
        ctx.arc(dotX, dotY, 2, 0, TAU);
        ctx.fillStyle = `rgba(182, 243, 107, ${0.5 * opacity})`;
        ctx.fill();

        ctx.restore();
      }

      // ── DATA POINTS ──
      const dpAlpha = currentMode === "intelligence" ? 0.9 : 0.7;
      const showLabels = currentMode !== "expanding";

      for (const dp of DATA_POINTS) {
        const p = lonLatTo3D(dp.lon, dp.lat);
        const rp = rotateY(p, baseRotation);
        const rp2 = rotateX(rp, tiltAngle);

        if (rp2[1] < 0.15) continue; // behind globe

        const px = cx + rp2[0] * radius;
        const py = cy - rp2[2] * radius;
        const depth = (rp2[1] + 1) / 2; // 0..1

        // Point
        const sz = dp.size * (0.6 + depth * 0.4);
        ctx.beginPath();
        ctx.arc(px, py, sz, 0, TAU);
        ctx.fillStyle = dp.color.replace(")", `, ${dpAlpha * depth * opacity})`).replace("rgb", "rgba");
        // Quick hex-to-rgba workaround: draw with global alpha
        ctx.globalAlpha = dpAlpha * depth * opacity;
        ctx.fillStyle = dp.color;
        ctx.fill();
        ctx.globalAlpha = 1;

        // Pulsing ring
        const pulseSize = sz + 2 + Math.sin(time * 0.003 + dp.lon) * 1.5;
        ctx.beginPath();
        ctx.arc(px, py, pulseSize, 0, TAU);
        ctx.strokeStyle = dp.color;
        ctx.globalAlpha = 0.15 * depth * opacity;
        ctx.lineWidth = 0.5;
        ctx.stroke();
        ctx.globalAlpha = 1;

        // Label
        if (showLabels && depth > 0.4 && radius > 120) {
          ctx.font = `${Math.max(8, 9 * (radius / 230))}px 'JetBrains Mono', monospace`;
          ctx.fillStyle = `rgba(232, 237, 233, ${0.5 * depth * opacity})`;
          ctx.textAlign = "left";
          ctx.fillText(dp.label, px + sz + 6, py + 3);

          // Connector line
          ctx.beginPath();
          ctx.moveTo(px + sz + 1, py);
          ctx.lineTo(px + sz + 5, py);
          ctx.strokeStyle = `rgba(113, 226, 155, ${0.2 * depth * opacity})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }

      // ── EDGE GLOW ──
      const edgeGrad = ctx.createRadialGradient(cx, cy, radius * 0.92, cx, cy, radius * 1.02);
      edgeGrad.addColorStop(0, "rgba(113, 226, 155, 0)");
      edgeGrad.addColorStop(0.7, `rgba(113, 226, 155, ${0.04 * opacity})`);
      edgeGrad.addColorStop(1, `rgba(113, 226, 155, ${0.08 * opacity})`);
      ctx.fillStyle = edgeGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.02, 0, TAU);
      ctx.fill();

      // ── OUTER RING ──
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, TAU);
      ctx.strokeStyle = `rgba(45, 80, 64, ${0.3 * opacity})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    },
    [globeRadius, expandProgress]
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

    const animate = (ts: number) => {
      timeRef.current = ts;
      draw(ctx, size, size, ts);
      animFrameRef.current = requestAnimationFrame(animate);
    };
    animFrameRef.current = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(animFrameRef.current);
  }, [size, draw]);

  return (
    <canvas
      ref={canvasRef}
      className="globe-canvas"
      aria-hidden="true"
      style={{ width: size, height: size }}
    />
  );
}
