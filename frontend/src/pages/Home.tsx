import { useCallback, useEffect, useRef, useState } from "react";
import Globe from "../components/Globe";

/* ─────────────────────────────────────────────
   HOOKS
   ───────────────────────────────────────────── */

/** Animated intersection observer hook for reveal-on-scroll. */
function useReveal(threshold = 0.12) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("revealed");
          obs.disconnect();
        }
      },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return ref;
}

/** Detect if user prefers reduced motion. */
function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return reduced;
}

/** Track mouse position in hero for parallax. */
function useMouseParallax(enabled: boolean) {
  const [mouse, setMouse] = useState({ x: 0.5, y: 0.5 });
  useEffect(() => {
    if (!enabled) return;
    const handler = (e: MouseEvent) => {
      setMouse({
        x: e.clientX / window.innerWidth,
        y: e.clientY / window.innerHeight,
      });
    };
    window.addEventListener("mousemove", handler, { passive: true });
    return () => window.removeEventListener("mousemove", handler);
  }, [enabled]);
  return mouse;
}

/* ─────────────────────────────────────────────
   COMPONENTS
   ───────────────────────────────────────────── */

function Reveal({
  children,
  className = "",
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useReveal();
  return (
    <div
      ref={ref}
      className={`reveal ${className}${delay ? ` reveal-delay-${delay}` : ""}`}
    >
      {children}
    </div>
  );
}

/** Canvas-based particle system for forest atmosphere. */
function ParticleCanvas({ reducedMotion }: { reducedMotion: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = window.innerWidth;
    let h = window.innerHeight;
    canvas.width = w;
    canvas.height = h;

    type Particle = {
      x: number; y: number; vx: number; vy: number;
      size: number; opacity: number; life: number; maxLife: number;
      type: "dust" | "firefly";
    };

    const particles: Particle[] = [];
    const count = reducedMotion ? 0 : 40;

    for (let i = 0; i < count; i++) {
      const isFirefly = Math.random() < 0.15;
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3,
        vy: isFirefly ? (Math.random() - 0.5) * 0.2 : -Math.random() * 0.4 - 0.1,
        size: isFirefly ? Math.random() * 2.5 + 1 : Math.random() * 1.5 + 0.5,
        opacity: Math.random() * 0.3 + 0.05,
        life: Math.random() * 600,
        maxLife: Math.random() * 400 + 300,
        type: isFirefly ? "firefly" : "dust",
      });
    }

    let raf: number;
    const animate = () => {
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        p.life++;
        if (p.life > p.maxLife) {
          p.x = Math.random() * w;
          p.y = h + 10;
          p.life = 0;
        }
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < -10) { p.y = h + 10; p.life = 0; }

        const fadeIn = Math.min(p.life / 60, 1);
        const fadeOut = Math.min((p.maxLife - p.life) / 60, 1);
        const alpha = p.opacity * fadeIn * fadeOut;

        if (p.type === "firefly") {
          const pulse = 0.5 + 0.5 * Math.sin(p.life * 0.05);
          ctx.fillStyle = `rgba(182, 243, 107, ${alpha * pulse * 0.7})`;
          ctx.shadowColor = "rgba(182, 243, 107, 0.3)";
          ctx.shadowBlur = 8;
        } else {
          ctx.fillStyle = `rgba(200, 220, 200, ${alpha * 0.5})`;
          ctx.shadowColor = "transparent";
          ctx.shadowBlur = 0;
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.shadowBlur = 0;
      raf = requestAnimationFrame(animate);
    };
    animate();

    const onResize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w;
      canvas.height = h;
    };
    window.addEventListener("resize", onResize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); };
  }, [reducedMotion]);

  return <canvas ref={canvasRef} className="particle-canvas" aria-hidden="true" />;
}

/* ─────────────────────────────────────────────
   DATA
   ───────────────────────────────────────────── */

const SEE_HUD_ITEMS = [
  { label: "DETECTION", value: "PERSON", color: "#FF8B70" },
  { label: "TRACK ID", value: "T-0042", color: "#B6F36B" },
  { label: "CONFIDENCE", value: "0.94", color: "#71E29B" },
  { label: "BOUNDING BOX", value: "[234, 118, 312, 287]", color: "#7FA991" },
];

const UNDERSTAND_HUD_ITEMS = [
  { label: "SCENE", value: "PROTECTED FOREST", color: "#71E29B" },
  { label: "ACTIVITY", value: "PERSISTENT TRACK", color: "#FFBD62" },
  { label: "CONTEXT", value: "HIGH-RISK ZONE", color: "#FF8B70" },
  { label: "CONFIDENCE", value: "0.87", color: "#B6F36B" },
];

const ACT_HUD_ITEMS = [
  { label: "POLICY", value: "WILDLIFE_ALERT", color: "#71E29B" },
  { label: "ACTION", value: "RANGER_DISPATCH", color: "#B6F36B" },
  { label: "STATUS", value: "ACKNOWLEDGED", color: "#71E29B" },
  { label: "PRIORITY", value: "HIGH", color: "#FF8B70" },
];

const BENCHMARK_ROWS = [
  { category: "VISION", model: "YOLO v8n", task: "Object Detection", accuracy: null, latency: null, status: "EVALUATION PENDING" },
  { category: "VISION", model: "YOLO v8s", task: "Object Detection", accuracy: null, latency: null, status: "EVALUATION PENDING" },
  { category: "SCENE", model: "VLM Adapter", task: "Scene Understanding", accuracy: null, latency: null, status: "EVALUATION PENDING" },
  { category: "SCENE", model: "VLM Adapter", task: "Activity Classification", accuracy: null, latency: null, status: "EVALUATION PENDING" },
  { category: "THREAT", model: "Rule Engine", task: "Threat Assessment", accuracy: null, latency: null, status: "CONNECTED" },
  { category: "MISSION", model: "Policy Eval", task: "Decision Routing", accuracy: null, latency: null, status: "CONNECTED" },
];

const SAFETY_PILLARS = [
  {
    icon: "👁",
    title: "HUMAN OVERSIGHT",
    desc: "Every decision is presented to a human operator. The system recommends — it does not act autonomously in the current demonstration.",
  },
  {
    icon: "📋",
    title: "EVIDENCE LOGGING",
    desc: "Every detection, scene interpretation, and decision is logged with evidence references and timestamps for full auditability.",
  },
  {
    icon: "⚖️",
    title: "RULE-BASED DECISIONS",
    desc: "Threat assessment uses a transparent, configurable rule engine — not a black-box model — for explainable decision-making.",
  },
  {
    icon: "🎛",
    title: "SIMULATED ACTUATORS",
    desc: "The current demonstration uses synthetic scenarios and simulated actuator actions. No real-world autonomous intervention is claimed.",
  },
];

/* ─────────────────────────────────────────────
   MAIN COMPONENT
   ───────────────────────────────────────────── */

export default function Home({ onNavigate }: { onNavigate: () => void }) {
  const [scrollY, setScrollY] = useState(0);
  const [heroLoaded, setHeroLoaded] = useState(false);
  const reducedMotion = useReducedMotion();
  const mouse = useMouseParallax(!reducedMotion);
  const globeSectionRef = useRef<HTMLElement>(null);
  const benchmarkSectionRef = useRef<HTMLElement>(null);
  const [benchmarkVisible, setBenchmarkVisible] = useState(false);
  const benchmarkLineRef = useRef<HTMLDivElement>(null);

  // Globe RAF-driven state (refs for zero-react-render performance)
  const globeContainerRef = useRef<HTMLDivElement>(null);
  const smoothScrollRef = useRef(0);
  const globeRafRef = useRef<number>(0);
  const benchmarksOffsetRef = useRef(0);
  const [globeScrollProgress, setGlobeScrollProgress] = useState(0);
  const [globeExitProgress, setGlobeExitProgress] = useState(0);
  const [globeMode, setGlobeMode] = useState<"geographic" | "intelligence">("geographic");

  // Hero entrance animation
  useEffect(() => {
    const timer = setTimeout(() => setHeroLoaded(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // Compute benchmarks section offset on mount and resize
  useEffect(() => {
    const update = () => {
      const el = benchmarkSectionRef.current;
      if (el) {
        benchmarksOffsetRef.current = el.getBoundingClientRect().top + window.scrollY;
      }
    };
    // Delay to ensure layout is complete
    const timer = setTimeout(update, 300);
    window.addEventListener("resize", update);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", update);
    };
  }, []);

  // RAF-driven globe animation loop (smooth scroll interpolation + exit transition)
  useEffect(() => {
    const tick = () => {
      const target = window.scrollY;
      const prev = smoothScrollRef.current;

      if (reducedMotion) {
        smoothScrollRef.current = target;
      } else {
        // Smooth interpolation toward target scroll position
        const ease = 0.08;
        smoothScrollRef.current += (target - prev) * ease;
        if (Math.abs(target - smoothScrollRef.current) < 0.5) {
          smoothScrollRef.current = target;
        }
      }

      const scroll = smoothScrollRef.current;

      // ── Scroll progress for globe rotation ──
      const maxScroll = 3000;
      const scrollProgress = Math.min(Math.max(scroll / maxScroll, 0), 1);

      // ── Exit progress: globe dissolves as user approaches benchmarks ──
      const benchmarksTop = benchmarksOffsetRef.current || 4000;
      const vh = window.innerHeight;
      const exitStart = benchmarksTop - vh * 0.9;
      const exitEnd = benchmarksTop + vh * 0.2;
      const exitRange = exitEnd - exitStart;
      const exitProgress = exitRange > 0
        ? Math.max(0, Math.min(1, (scroll - exitStart) / exitRange))
        : 0;

      // ── Base scale (gradual shrink as user scrolls down) ──
      let baseScale: number;
      if (scroll < 100) baseScale = 1;
      else if (scroll < 800) baseScale = 1 - (scroll - 100) * 0.0003;
      else baseScale = 0.8 - Math.min((scroll - 800) * 0.00005, 0.15);

      // ── Exit scale: globe expands outward during dissolve ──
      const exitScale = exitProgress * 0.35;
      const totalScale = baseScale + exitScale;

      // ── Opacity: base fade + exit fade ──
      let baseOpacity: number;
      if (scroll < 50) baseOpacity = 1;
      else baseOpacity = 1 - (scroll - 50) * 0.0002;
      baseOpacity = Math.max(0, Math.min(1, baseOpacity));
      const totalOpacity = baseOpacity * (1 - exitProgress);

      // ── Blur for cinematic dissolve ──
      const blur = reducedMotion ? 0 : exitProgress * 5;

      // ── Apply to globe container DOM (no React re-render) ──
      if (globeContainerRef.current) {
        const s = globeContainerRef.current.style;
        s.opacity = String(Math.max(0, totalOpacity));
        s.transform = `translate3d(-50%, -50%, 0) scale(${totalScale})`;
        s.filter = blur > 0.1 ? `blur(${blur}px)` : "";
      }

      // ── Throttled React state updates for Globe props ──
      // Only update when values change meaningfully (avoid ~60fps re-renders)
      const roundedSP = Math.round(scrollProgress * 200) / 200;
      const roundedEP = Math.round(exitProgress * 100) / 100;
      setGlobeScrollProgress((prev) => {
        if (Math.abs(prev - roundedSP) > 0.005) return roundedSP;
        return prev;
      });
      setGlobeExitProgress((prev) => {
        if (Math.abs(prev - roundedEP) > 0.005) return roundedEP;
        return prev;
      });

      // ── Globe mode: switches to "intelligence" as user approaches benchmarks ──
      const newMode: "geographic" | "intelligence" = scrollProgress > 0.7 ? "intelligence" : "geographic";
      setGlobeMode((prev) => (prev !== newMode ? newMode : prev));

      globeRafRef.current = requestAnimationFrame(tick);
    };

    globeRafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(globeRafRef.current);
  }, [reducedMotion]);

  // Also update scrollY for nav state (lightweight, separate from globe RAF)
  useEffect(() => {
    const onScroll = () => {
      setScrollY(window.scrollY);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Benchmark section observer
  useEffect(() => {
    const el = benchmarkSectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setBenchmarkVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.2 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Benchmark glow line animation
  useEffect(() => {
    if (!benchmarkVisible || !benchmarkLineRef.current) return;
    const el = benchmarkLineRef.current;
    el.style.transition = "none";
    el.style.transform = "translateX(-100%)";
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.transition = "transform 2s cubic-bezier(0.22, 1, 0.36, 1)";
        el.style.transform = "translateX(100%)";
      });
    });
  }, [benchmarkVisible]);

  function scrollToId(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  }

  // Parallax values for hero layers
  const px = (factor: number) => reducedMotion ? 0 : (mouse.x - 0.5) * factor;
  const py = (factor: number) => reducedMotion ? 0 : (mouse.y - 0.5) * factor;

  // Nav scroll state
  const navScrolled = scrollY > 60;

  return (
    <div className="home">
      {/* ── PARTICLE CANVAS ── */}
      <ParticleCanvas reducedMotion={reducedMotion} />

      {/* ── HERO ATMOSPHERIC LAYERS ── */}
      <div className="hero-atmosphere" aria-hidden="true">
        <div className="atmo-gradient" />
        <div className="atmo-layer atmo-forest-far" style={{ transform: `translate(${px(5)}px, ${py(3)}px)` }} />
        <div className="atmo-layer atmo-forest-mid" style={{ transform: `translate(${px(12)}px, ${py(6)}px)` }} />
        <div className="atmo-layer atmo-fog" style={{ transform: `translate(${px(8)}px, ${py(2)}px)` }} />
        <div className="atmo-layer atmo-light-rays" style={{ transform: `translate(${px(15)}px, ${py(4)}px)` }} />
        <div className="atmo-vignette" />
        <div className="atmo-noise" />
      </div>

      {/* ── FIXED GLOBE (centered, behind content, RAF-driven) ── */}
      <div
        ref={globeContainerRef}
        className="globe-fixed"
        aria-hidden="true"
        style={{
          opacity: 1,
          transform: "translate3d(-50%, -50%, 0) scale(1)",
        }}
      >
        <Globe
          scrollProgress={globeScrollProgress}
          exitProgress={globeExitProgress}
          mode={globeMode}
          size={Math.min(window.innerWidth * 0.7, 650)}
        />
      </div>

      {/* ── NAV ── */}
      <nav className={`home-nav ${navScrolled ? "nav-scrolled" : ""}`}>
        <div className="nav-inner">
          <span className="nav-logo">VANRAKSHAK</span>
          <div className="nav-links">
            <button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>Home</button>
            <button onClick={() => scrollToId("see")}>SEE</button>
            <button onClick={() => scrollToId("understand")}>UNDERSTAND</button>
            <button onClick={() => scrollToId("act")}>ACT</button>
            <button onClick={() => scrollToId("benchmarks")}>Benchmarks</button>
          </div>
          <button className="nav-cta" onClick={onNavigate}>
            ENTER MISSION →
          </button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className={`hero ${heroLoaded ? "hero-loaded" : ""}`}>
        <div
          className="hero-text"
          style={{ transform: reducedMotion ? undefined : `translate(${px(2)}px, ${py(1)}px)` }}
        >
          <p className="hero-eyebrow hero-anim hero-anim-1">AI-ASSISTED FOREST MONITORING</p>
          <h1 className="hero-headline hero-anim hero-anim-2">
            VANRAKSHAK
          </h1>
          <p className="hero-sub hero-anim hero-anim-2" style={{ fontSize: "clamp(18px, 2vw, 28px)", color: "var(--text-secondary)", letterSpacing: "0.12em", fontWeight: 300, textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>
            Intelligent Forest Protection, From Sky to Ground.
          </p>
          <p className="hero-sub hero-anim hero-anim-3">
            VanRakshak combines drone vision, scene understanding and
            safety-first autonomous response to help rangers detect,
            verify and respond to threats across protected forests.
          </p>
          <div className="hero-actions hero-anim hero-anim-4">
            <button className="btn-primary btn-cta-premium" onClick={onNavigate}>
              <span className="cta-text">ENTER MISSION CONTROL</span>
              <span className="cta-arrow">→</span>
            </button>
            <button className="btn-secondary" onClick={() => scrollToId("see")}>
              EXPLORE THE SYSTEM ↓
            </button>
          </div>
          <div className="hero-scroll-hint hero-anim hero-anim-5">
            <span className="line" />
            SCROLL TO EXPLORE
            <span className="line" />
          </div>
        </div>
      </section>

      {/* ── SEE SECTION ── */}
      <section className="section section-story" id="see">
        <div className="story-layout">
          <Reveal>
            <div className="story-text">
              <p className="section-eyebrow">01 — SEE</p>
              <h2 className="section-headline">
                See what is happening.
              </h2>
              <p className="section-body">
                Computer vision transforms drone footage into structured visual
                evidence — detecting people, objects and persistent tracks across
                protected environments.
              </p>
            </div>
          </Reveal>
          <Reveal delay={2}>
            <div className="story-visual">
              <div className="cinematic-image">
                <img
                  src="https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=900&q=80"
                  alt="Drone monitoring over forest canopy"
                  loading="lazy"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
                <div className="cinematic-overlay" />
                <div className="cinematic-grain" />
                <div className="cinematic-border" />
                {/* HUD Overlay */}
                <div className="hud-overlay">
                  {SEE_HUD_ITEMS.map((item) => (
                    <div className="hud-item" key={item.label}>
                      <span className="hud-label">{item.label}</span>
                      <span className="hud-value" style={{ color: item.color }}>{item.value}</span>
                    </div>
                  ))}
                  <div className="hud-corner hud-corner-tl" />
                  <div className="hud-corner hud-corner-tr" />
                  <div className="hud-corner hud-corner-bl" />
                  <div className="hud-corner hud-corner-br" />
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── UNDERSTAND SECTION ── */}
      <section className="section section-story section-story-reverse" id="understand">
        <div className="story-layout story-layout-reverse">
          <Reveal delay={2}>
            <div className="story-visual">
              <div className="cinematic-image">
                <img
                  src="https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=900&q=80"
                  alt="Forest surveillance perspective"
                  loading="lazy"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
                <div className="cinematic-overlay" />
                <div className="cinematic-grain" />
                <div className="cinematic-border" />
                <div className="hud-overlay hud-overlay-understand">
                  {UNDERSTAND_HUD_ITEMS.map((item) => (
                    <div className="hud-item" key={item.label}>
                      <span className="hud-label">{item.label}</span>
                      <span className="hud-value" style={{ color: item.color }}>{item.value}</span>
                    </div>
                  ))}
                  <div className="hud-corner hud-corner-tl" />
                  <div className="hud-corner hud-corner-tr" />
                  <div className="hud-corner hud-corner-bl" />
                  <div className="hud-corner hud-corner-br" />
                </div>
              </div>
            </div>
          </Reveal>
          <Reveal>
            <div className="story-text">
              <p className="section-eyebrow">02 — UNDERSTAND</p>
              <h2 className="section-headline">
                See beyond the frame.
              </h2>
              <p className="section-body">
                Object detection alone is not enough. VanRakshak adds semantic
                scene understanding to interpret what detected elements may mean
                in context — turning raw detections into meaningful environmental
                intelligence.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── ACT SECTION ── */}
      <section className="section section-story" id="act">
        <div className="story-layout">
          <Reveal>
            <div className="story-text">
              <p className="section-eyebrow">03 — ACT</p>
              <h2 className="section-headline">
                Turn intelligence into action.
              </h2>
              <p className="section-body">
                Safety-first mission policies transform verified observations into
                structured responses — from ranger dispatch to simulated autonomous
                actuators. Every decision is transparent, logged and human-approved.
              </p>
            </div>
          </Reveal>
          <Reveal delay={2}>
            <div className="story-visual">
              <div className="cinematic-image">
                <img
                  src="https://images.unsplash.com/photo-1446329813274-7c9036bd9a1f?w=900&q=80"
                  alt="Conservation team monitoring protected forest"
                  loading="lazy"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
                <div className="cinematic-overlay" />
                <div className="cinematic-grain" />
                <div className="cinematic-border" />
                <div className="hud-overlay hud-overlay-act">
                  {ACT_HUD_ITEMS.map((item) => (
                    <div className="hud-item" key={item.label}>
                      <span className="hud-label">{item.label}</span>
                      <span className="hud-value" style={{ color: item.color }}>{item.value}</span>
                    </div>
                  ))}
                  <div className="hud-corner hud-corner-tl" />
                  <div className="hud-corner hud-corner-tr" />
                  <div className="hud-corner hud-corner-bl" />
                  <div className="hud-corner hud-corner-br" />
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── MODEL BENCHMARKS ── */}
      <section className="section-benchmarks" id="benchmarks" ref={benchmarkSectionRef}>
        <div className="benchmarks-inner">
          <Reveal>
            <p className="section-eyebrow">MODEL BENCHMARKS</p>
            <h2 className="section-headline">
              Measured, not assumed.
            </h2>
            <p className="section-body" style={{ maxWidth: 680 }}>
              VanRakshak evaluates its perception and language components against
              repeatable benchmarks so model selection is based on measurable
              performance rather than assumptions.
            </p>
          </Reveal>

          <div className="benchmark-console">
            {/* Glow line */}
            <div className="benchmark-glow-line" ref={benchmarkLineRef} />

            <div className="benchmark-header">
              <span className="benchmark-header-dot" />
              <span className="benchmark-header-title">VANRAKSHAK // MODEL EVALUATION CONSOLE</span>
              <span className="benchmark-header-status">
                {benchmarkVisible ? "● CONNECTED" : "○ STANDBY"}
              </span>
            </div>

            <div className="benchmark-table">
              <div className="benchmark-table-header">
                <span className="bench-col bench-col-cat">CATEGORY</span>
                <span className="bench-col bench-col-model">MODEL</span>
                <span className="bench-col bench-col-task">TASK</span>
                <span className="bench-col bench-col-acc">ACCURACY</span>
                <span className="bench-col bench-col-lat">LATENCY</span>
                <span className="bench-col bench-col-status">STATUS</span>
              </div>
              {BENCHMARK_ROWS.map((row, i) => (
                <Reveal key={`${row.category}-${row.model}-${row.task}`} delay={Math.min(i + 1, 4)}>
                  <div className="benchmark-row">
                    <span className="bench-col bench-col-cat">{row.category}</span>
                    <span className="bench-col bench-col-model">{row.model}</span>
                    <span className="bench-col bench-col-task">{row.task}</span>
                    <span className="bench-col bench-col-acc bench-val-pending">
                      {row.accuracy ?? "—"}
                    </span>
                    <span className="bench-col bench-col-lat bench-val-pending">
                      {row.latency ?? "—"}
                    </span>
                    <span className={`bench-col bench-col-status ${row.status === "CONNECTED" ? "bench-status-connected" : "bench-status-pending"}`}>
                      {row.status}
                    </span>
                  </div>
                </Reveal>
              ))}
            </div>

            <div className="benchmark-footer">
              <p>ACCURACY &amp; LATENCY — CONNECTED DURING EVALUATION</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── SAFETY ── */}
      <section className="section-safety" id="safety">
        <div className="safety-inner">
          <Reveal>
            <p className="section-eyebrow">SAFETY BEFORE AUTONOMY</p>
            <h2 className="section-headline">
              Designed to assist.
              <br />
              Designed to stay accountable.
            </h2>
            <p className="section-body">
              VanRakshak separates observation, interpretation, decision logic and
              response. The current actuator layer is simulated, allowing the system
              architecture to be demonstrated without claiming real-world autonomous
              intervention.
            </p>
          </Reveal>
          <div className="safety-pillars">
            {SAFETY_PILLARS.map((pillar, i) => (
              <Reveal key={pillar.title} delay={i + 1}>
                <div className="safety-pillar">
                  <span className="safety-pillar-icon">{pillar.icon}</span>
                  <h4 className="safety-pillar-title">{pillar.title}</h4>
                  <p className="safety-pillar-desc">{pillar.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={4}>
            <div className="safety-note">
              The current demonstration uses synthetic scenarios and simulated
              actuator actions. No real-world autonomous intervention is claimed or
              implied. All responses are for demonstration purposes only.
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── FINAL CTA ── */}
      <section className="section-cta">
        <div className="cta-bg" />
        <div className="cta-content">
          <Reveal>
            <h2 className="cta-headline">
              Ready to enter
              <br />
              the forest?
            </h2>
            <p className="cta-sub">
              Move from the concept to the command layer.
            </p>
            <button className="btn-console btn-lg btn-cta-premium" onClick={onNavigate}>
              <span className="cta-text">ENTER MISSION CONTROL</span>
              <span className="cta-arrow">→</span>
            </button>
          </Reveal>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="home-footer">
        <div className="footer-inner">
          <div>
            <span className="footer-logo">VANRAKSHAK</span>
            <p className="footer-tagline">
              AI-assisted intelligence for forest monitoring and conservation.
            </p>
          </div>
          <div className="footer-links">
            <button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>Home</button>
            <button onClick={() => scrollToId("benchmarks")}>Benchmarks</button>
            <button onClick={onNavigate}>Mission Console</button>
            <button onClick={() => scrollToId("safety")}>About</button>
          </div>
        </div>
      </footer>
    </div>
  );
}
