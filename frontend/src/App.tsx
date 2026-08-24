import { useCallback, useEffect, useRef, useState } from "react";
import Home from "./pages/Home";
import MissionConsole from "./pages/MissionConsole";

/** Lightweight same-tab router using History API so browser back works. */
export default function App() {
  const [view, setView] = useState<"home" | "console">(() =>
    window.location.hash === "#console" ? "console" : "home"
  );
  const [transitioning, setTransitioning] = useState(false);
  const [transitionTarget, setTransitionTarget] = useState<"home" | "console" | null>(null);

  // Cursor-positioned transition state
  const [cursorTransition, setCursorTransition] = useState(false);
  const [expandProgress, setExpandProgress] = useState(0);
  const [expandOrigin, setExpandOrigin] = useState({ x: 0.5, y: 0.5 }); // normalized 0-1
  const expandRafRef = useRef<number>(0);
  const expandStartRef = useRef<number>(0);

  // Reduced motion check
  const prefersReducedMotion = useRef(
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  const navigateTo = useCallback((target: "home" | "console", cursorX?: number, cursorY?: number) => {
    if (target === view || transitioning || cursorTransition) return;

    if (target === "console") {
      // Check reduced motion — skip animation, navigate directly
      if (prefersReducedMotion.current) {
        window.history.pushState({}, "", "#console");
        setView("console");
        window.scrollTo({ top: 0 });
        return;
      }

      // Cursor-positioned transition
      const originX = cursorX != null ? cursorX / window.innerWidth : 0.5;
      const originY = cursorY != null ? cursorY / window.innerHeight : 0.5;
      setExpandOrigin({ x: originX, y: originY });
      setCursorTransition(true);
      setExpandProgress(0);
      expandStartRef.current = 0;

      const duration = 800; // ms
      const animate = (ts: number) => {
        if (!expandStartRef.current) expandStartRef.current = ts;
        const elapsed = ts - expandStartRef.current;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        setExpandProgress(eased);

        if (progress < 1) {
          expandRafRef.current = requestAnimationFrame(animate);
        } else {
          // Transition complete — switch to console
          window.history.pushState({}, "", "#console");
          setView("console");
          window.scrollTo({ top: 0 });
          setCursorTransition(false);
          setExpandProgress(0);
        }
      };
      expandRafRef.current = requestAnimationFrame(animate);
    } else {
      // Going back to home: simple fade transition
      setTransitionTarget(target);
      setTransitioning(true);
    }
  }, [view, transitioning, cursorTransition]);

  // Handle non-console transitions (back to home)
  useEffect(() => {
    if (!transitioning || !transitionTarget) return;
    const timer = setTimeout(() => {
      window.history.pushState({}, "", window.location.pathname);
      setView(transitionTarget);
      window.scrollTo({ top: 0 });
      const fadeTimer = setTimeout(() => {
        setTransitioning(false);
        setTransitionTarget(null);
      }, 350);
      return () => clearTimeout(fadeTimer);
    }, 380);
    return () => clearTimeout(timer);
  }, [transitioning, transitionTarget]);

  // Handle browser back/forward
  useEffect(() => {
    function onPopState() {
      const next = window.location.hash === "#console" ? "console" : "home";
      if (next !== view) {
        setTransitionTarget(next);
        setTransitioning(true);
        setTimeout(() => {
          setView(next);
          window.scrollTo({ top: 0 });
          setTimeout(() => {
            setTransitioning(false);
            setTransitionTarget(null);
          }, 300);
        }, 350);
      }
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [view]);

  // Cleanup RAF on unmount
  useEffect(() => {
    return () => cancelAnimationFrame(expandRafRef.current);
  }, []);

  return (
    <>
      {/* Back-navigation transition overlay */}
      <div
        className={`transition-overlay ${transitioning ? "active" : ""}`}
        aria-hidden="true"
      />

      {/* Cursor-positioned expansion transition — forest green cinematic */}
      {cursorTransition && (
        <div className="globe-expansion-overlay" aria-hidden="true">
          {/* Green radial pulse from cursor position */}
          <div
            className="globe-expansion-vignette"
            style={{
              opacity: expandProgress,
              background: `radial-gradient(circle at ${expandOrigin.x * 100}% ${expandOrigin.y * 100}%, transparent 0%, rgba(39, 165, 103, ${0.18 * expandProgress}) ${5 + expandProgress * 15}%, rgba(16, 59, 41, ${0.35 + expandProgress * 0.45}) ${20 + expandProgress * 25}%, rgba(11, 42, 29, ${0.65 + expandProgress * 0.3}) ${50 + expandProgress * 20}%, rgba(11, 42, 29, ${0.80 + expandProgress * 0.15}) ${75 + expandProgress * 10}%)`,
            }}
          />
          {/* Text overlay */}
          <div
            className="globe-expansion-text"
            style={{
              opacity: expandProgress > 0.3 ? Math.min((expandProgress - 0.3) * 3, 1) : 0,
            }}
          >
            <span className="expansion-label">ENTERING</span>
            <span className="expansion-title">MISSION CONTROL</span>
          </div>
        </div>
      )}

      {view === "console" ? (
        <MissionConsole onBack={() => navigateTo("home")} />
      ) : (
        <Home onNavigate={(x, y) => navigateTo("console", x, y)} />
      )}
    </>
  );
}
