import { useCallback, useEffect, useRef, useState } from "react";
import Home from "./pages/Home";
import MissionConsole from "./pages/MissionConsole";
import Globe from "./components/Globe";

/** Lightweight same-tab router using History API so browser back works. */
export default function App() {
  const [view, setView] = useState<"home" | "console">(() =>
    window.location.hash === "#console" ? "console" : "home"
  );
  const [transitioning, setTransitioning] = useState(false);
  const [transitionTarget, setTransitionTarget] = useState<"home" | "console" | null>(null);

  // Cinematic globe expansion state
  const [globeExpanding, setGlobeExpanding] = useState(false);
  const [expandProgress, setExpandProgress] = useState(0);
  const expandRafRef = useRef<number>(0);
  const expandStartRef = useRef<number>(0);

  const navigateTo = useCallback((target: "home" | "console") => {
    if (target === view || transitioning || globeExpanding) return;

    if (target === "console") {
      // Cinematic globe expansion transition
      setGlobeExpanding(true);
      setExpandProgress(0);
      expandStartRef.current = 0;

      const duration = 900; // ms
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
          // Expansion complete — now switch to console
          window.history.pushState({}, "", "#console");
          setView("console");
          window.scrollTo({ top: 0 });
          setGlobeExpanding(false);
          setExpandProgress(0);
        }
      };
      expandRafRef.current = requestAnimationFrame(animate);
    } else {
      // Going back to home: simple fade transition
      setTransitionTarget(target);
      setTransitioning(true);
    }
  }, [view, transitioning, globeExpanding]);

  // Handle non-console transitions
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
      {/* Cinematic transition overlay for back-navigation */}
      <div
        className={`transition-overlay ${transitioning ? "active" : ""}`}
        aria-hidden="true"
      />

      {/* Cinematic globe expansion overlay */}
      {globeExpanding && (
        <div className="globe-expansion-overlay" aria-hidden="true">
          <div className="globe-expansion-container">
            <Globe
              scrollProgress={0.3}
              mode="expanding"
              expandProgress={expandProgress}
              size={800}
            />
          </div>
          <div
            className="globe-expansion-vignette"
            style={{ opacity: expandProgress * 0.95 }}
          />
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
        <Home onNavigate={() => navigateTo("console")} />
      )}
    </>
  );
}
