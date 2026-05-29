"use client";

import dynamic from "next/dynamic";
import { useRef } from "react";
import { useMousePosition } from "@/hooks/useMousePosition";
import Navbar from "@/components/ui/Navbar";
import HeroText from "./HeroText";

/* ssr: false MUST live inside a Client Component (Next.js 16 requirement) */
const SteelCanvas = dynamic(() => import("./SteelCanvas"), { ssr: false });

export default function HeroSection() {
  const mousePosition = useMousePosition();
  const sectionRef    = useRef<HTMLElement>(null);

  return (
    <section
      ref={sectionRef}
      className="hero-grid scanlines"
      style={{
        position: "relative",
        width: "100%",
        height: "100svh",
        overflow: "hidden",
        background: "#0B0C10",
      }}
    >
      {/* Navigation */}
      <Navbar />

      {/* 3-D Canvas — absolutely fills the section */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 0,
        }}
      >
        <SteelCanvas mousePosition={mousePosition} />
      </div>

      {/* Vignette — radial shadow toward edges */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 2,
          pointerEvents: "none",
          background:
            "radial-gradient(ellipse at center, transparent 35%, rgba(11,12,16,0.65) 100%)",
        }}
      />

      {/* Bottom fade to next section */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          left: 0, right: 0, bottom: 0,
          height: "14rem",
          zIndex: 3,
          pointerEvents: "none",
          background: "linear-gradient(to top, #0B0C10 0%, transparent 100%)",
        }}
      />

      {/* Hero text content */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          paddingLeft: "clamp(1.5rem, 6vw, 7rem)",
          paddingTop: "5rem",
        }}
      >
        <HeroText />
      </div>

      {/* Scroll indicator */}
      <div
        style={{
          position: "absolute",
          bottom: "2.5rem",
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-space-grotesk)",
            fontSize: "0.65rem", letterSpacing: "0.35em",
            textTransform: "uppercase", color: "rgba(197,198,199,0.35)",
          }}
        >
          Scroll
        </span>
        <div
          style={{
            width: "1px", height: "3.5rem",
            background: "linear-gradient(to bottom, #00D2FF, transparent)",
            animation: "scrollPulse 2s ease-in-out infinite",
          }}
        />
      </div>

      <style>{`
        @keyframes scrollPulse {
          0%, 100% { opacity: 0.4; transform: scaleY(1); }
          50%       { opacity: 1;   transform: scaleY(1.15); }
        }
      `}</style>
    </section>
  );
}
