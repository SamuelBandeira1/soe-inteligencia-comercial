"use client";

import { useEffect, useRef } from "react";
import { gsap } from "@/lib/gsap";

const TITLE = "ESTRUTURAS QUE DEFINEM O HORIZONTE";

export default function HeroText() {
  const containerRef = useRef<HTMLDivElement>(null);
  const lineRef      = useRef<HTMLDivElement>(null);
  const subRef       = useRef<HTMLParagraphElement>(null);
  const ctaRef       = useRef<HTMLDivElement>(null);
  const metaRef      = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chars = containerRef.current.querySelectorAll<HTMLElement>(".char");

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ delay: 0.8 });

      tl.fromTo(
        chars,
        { yPercent: 110, opacity: 0, rotateX: -80 },
        {
          yPercent: 0,
          opacity: 1,
          rotateX: 0,
          duration: 1.1,
          stagger: { amount: 0.55, ease: "power2.inOut" },
          ease: "power4.out",
        }
      )
        .fromTo(
          lineRef.current,
          { scaleX: 0, transformOrigin: "left center" },
          { scaleX: 1, duration: 0.9, ease: "power3.out" },
          "-=0.5"
        )
        .fromTo(
          subRef.current,
          { opacity: 0, y: 22 },
          { opacity: 1, y: 0, duration: 0.7, ease: "power3.out" },
          "-=0.4"
        )
        .fromTo(
          ctaRef.current,
          { opacity: 0, y: 22 },
          { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" },
          "-=0.35"
        )
        .fromTo(
          metaRef.current,
          { opacity: 0 },
          { opacity: 1, duration: 0.6, ease: "power2.out" },
          "-=0.3"
        );
    }, containerRef);

    return () => ctx.revert();
  }, []);

  const words = TITLE.split(" ");

  return (
    <div
      ref={containerRef}
      style={{ maxWidth: "72rem", perspective: "1200px" }}
      aria-label={TITLE}
    >
      {/* Main headline — split into characters */}
      <h1
        style={{
          fontFamily: "var(--font-syne)",
          fontWeight: 800,
          fontSize: "clamp(2.4rem, 6.5vw, 6.5rem)",
          lineHeight: 0.95,
          letterSpacing: "-0.01em",
          color: "#C5C6C7",
          marginBottom: "2rem",
        }}
      >
        {words.map((word, wi) => (
          <span
            key={wi}
            style={{ display: "inline-block", overflow: "hidden", marginRight: "0.3em" }}
          >
            {Array.from(word).map((char, ci) => (
              <span
                key={ci}
                className="char"
                style={{
                  display: "inline-block",
                  transformOrigin: "bottom center",
                }}
              >
                {char}
              </span>
            ))}
          </span>
        ))}
      </h1>

      {/* Gradient rule */}
      <div
        ref={lineRef}
        style={{
          height: "1px",
          maxWidth: "36rem",
          marginBottom: "1.5rem",
          background: "linear-gradient(to right, #FF4500, #00D2FF, transparent)",
        }}
      />

      {/* Subtitle */}
      <p
        ref={subRef}
        style={{
          fontFamily: "var(--font-space-grotesk)",
          fontWeight: 300,
          fontSize: "clamp(0.85rem, 1.4vw, 1.15rem)",
          letterSpacing: "0.25em",
          textTransform: "uppercase",
          color: "rgba(197,198,199,0.65)",
          marginBottom: "2.5rem",
        }}
      >
        Engenharia Siderúrgica de Alta Performance
      </p>

      {/* CTAs */}
      <div ref={ctaRef} style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
        <a
          href="#projetos"
          style={{
            display: "inline-flex", alignItems: "center", gap: "0.75rem",
            fontFamily: "var(--font-space-grotesk)",
            fontSize: "0.75rem", letterSpacing: "0.2em", textTransform: "uppercase",
            color: "#C5C6C7", textDecoration: "none",
            padding: "1rem 2rem",
            border: "1px solid rgba(0,210,255,0.3)",
            transition: "border-color 0.3s, color 0.3s",
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLAnchorElement;
            el.style.borderColor = "#00D2FF";
            el.style.color = "#00D2FF";
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLAnchorElement;
            el.style.borderColor = "rgba(0,210,255,0.3)";
            el.style.color = "#C5C6C7";
          }}
        >
          <span>Explorar Projetos</span>
          <span style={{ transition: "transform 0.2s" }}>→</span>
        </a>

        <a
          href="#engenharia"
          style={{
            fontFamily: "var(--font-space-grotesk)",
            fontSize: "0.75rem", letterSpacing: "0.2em", textTransform: "uppercase",
            color: "rgba(197,198,199,0.4)", textDecoration: "none",
            transition: "color 0.3s",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.color = "#C5C6C7"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.color = "rgba(197,198,199,0.4)"; }}
        >
          Nossa Engenharia
        </a>
      </div>

      {/* Data strip */}
      <div
        ref={metaRef}
        style={{
          display: "flex", gap: "3rem", marginTop: "4rem",
          paddingTop: "2rem",
          borderTop: "1px solid rgba(197,198,199,0.08)",
        }}
      >
        {[
          { value: "38+", label: "Anos de experiência" },
          { value: "1.200", label: "Projetos entregues" },
          { value: "92%", label: "Aço reciclado" },
        ].map(({ value, label }) => (
          <div key={label}>
            <p
              style={{
                fontFamily: "var(--font-syne)", fontWeight: 700,
                fontSize: "1.75rem", color: "#00D2FF",
                lineHeight: 1,
              }}
            >
              {value}
            </p>
            <p
              style={{
                fontFamily: "var(--font-space-grotesk)",
                fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase",
                color: "rgba(197,198,199,0.4)", marginTop: "0.3rem",
              }}
            >
              {label}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
