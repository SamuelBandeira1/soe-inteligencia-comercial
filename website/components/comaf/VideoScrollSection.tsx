"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { gsap } from "@/lib/gsap";
import { ScrollTrigger } from "@/lib/gsap";

/* ─────────────────────────────────────────────────────────────
   Scroll-driven "video" section
   ─ Section pins for 300vh of scroll travel
   ─ Background image zooms 1.0 → 1.6 (parallax depth)
   ─ 4 story beats with clip-path text reveals
   ─ Progress bar fills as you scroll
   ─ Dark vignette tightens toward center as story progresses
   ───────────────────────────────────────────────────────────── */

const BEATS = [
  {
    progress: 0,
    headline: "Da floresta",
    sub:      "Madeiras selecionadas das melhores origens do Brasil",
    align:    "left",
  },
  {
    progress: 0.28,
    headline: "Ao corte preciso",
    sub:      "Processamento com tecnologia e tradição artesanal",
    align:    "right",
  },
  {
    progress: 0.55,
    headline: "Com cuidado",
    sub:      "Cada peça inspecionada antes de chegar até você",
    align:    "center",
  },
  {
    progress: 0.8,
    headline: "À sua obra",
    sub:      "Madeiras prontas para transformar qualquer projeto",
    align:    "left",
  },
] as const;

/* Unsplash image sequence — simulates video frames */
const FRAMES = [
  "https://images.unsplash.com/photo-1516455590571-18256e5bb9ff?auto=format&fit=crop&w=1920&q=90",
  "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=1920&q=90",
  "https://images.unsplash.com/photo-1573164713988-8665fc963095?auto=format&fit=crop&w=1920&q=90",
  "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&w=1920&q=90",
];

export default function VideoScrollSection() {
  const wrapRef    = useRef<HTMLDivElement>(null);
  const imgRef     = useRef<HTMLDivElement>(null);
  const progRef    = useRef<HTMLDivElement>(null);
  const vigRef     = useRef<HTMLDivElement>(null);
  const beatsRef   = useRef<(HTMLDivElement | null)[]>([]);
  const frameRefs  = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (!wrapRef.current) return;

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger:  wrapRef.current,
          start:    "top top",
          end:      "+=300%",
          pin:      true,
          scrub:    1,
          anticipatePin: 1,
        },
      });

      /* ── 1. Background zoom ── */
      tl.fromTo(imgRef.current,
        { scale: 1 },
        { scale: 1.55, ease: "none" },
        0
      );

      /* ── 2. Vignette tightens ── */
      tl.fromTo(vigRef.current,
        { opacity: 0.4 },
        { opacity: 0.82, ease: "none" },
        0
      );

      /* ── 3. Progress bar ── */
      tl.fromTo(progRef.current,
        { scaleX: 0 },
        { scaleX: 1, ease: "none" },
        0
      );

      /* ── 4. Image crossfade ── */
      FRAMES.forEach((_, i) => {
        if (i === 0) return;
        const start = i / FRAMES.length;
        const el = frameRefs.current[i];
        if (!el) return;
        tl.fromTo(el,
          { opacity: 0 },
          { opacity: 1, duration: 0.25, ease: "power1.inOut" },
          start
        );
      });

      /* ── 5. Story beats — clip-path reveal ── */
      BEATS.forEach((beat, i) => {
        const el = beatsRef.current[i];
        if (!el) return;

        const inAt  = beat.progress;
        const outAt = i < BEATS.length - 1 ? BEATS[i + 1].progress - 0.04 : 1.0;

        tl.fromTo(el,
          { clipPath: "inset(0 100% 0 0)", opacity: 0 },
          { clipPath: "inset(0 0% 0 0)", opacity: 1, duration: 0.12, ease: "power2.out" },
          inAt
        );

        if (i < BEATS.length - 1) {
          tl.to(el,
            { clipPath: "inset(0 0 0 100%)", opacity: 0, duration: 0.1, ease: "power2.in" },
            outAt
          );
        }
      });
    }, wrapRef);

    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={wrapRef}
      style={{ position: "relative", width: "100%", height: "100svh", overflow: "hidden", background: "#0A0704" }}
    >
      {/* ── Image frame stack ── */}
      {FRAMES.map((src, i) => (
        <div
          key={src}
          ref={el => { frameRefs.current[i] = el; }}
          style={{
            position: "absolute", inset: 0,
            opacity: i === 0 ? 1 : 0,
            zIndex: i,
          }}
        >
          <div
            ref={i === 0 ? imgRef : undefined}
            style={{
              position: "absolute", inset: "-10%",
              transformOrigin: "center center",
            }}
          >
            <Image
              src={src}
              alt=""
              fill
              priority={i === 0}
              sizes="100vw"
              style={{ objectFit: "cover" }}
            />
          </div>
        </div>
      ))}

      {/* ── Vignette ── */}
      <div
        ref={vigRef}
        style={{
          position: "absolute", inset: 0, zIndex: 20, pointerEvents: "none",
          background: "radial-gradient(ellipse at center, transparent 30%, rgba(10,7,4,0.9) 100%)",
        }}
      />

      {/* ── Persistent bottom-left label ── */}
      <div style={{
        position: "absolute", top: "2rem", left: "clamp(1.5rem, 5vw, 5rem)",
        zIndex: 30, display: "flex", alignItems: "center", gap: "0.75rem",
      }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#C8A87A" }} />
        <span style={{
          fontFamily: "var(--font-space-grotesk)", fontSize: "0.65rem",
          letterSpacing: "0.3em", textTransform: "uppercase",
          color: "rgba(200,168,122,0.6)",
        }}>
          Nossa jornada
        </span>
      </div>

      {/* ── Story beat text overlays ── */}
      {BEATS.map((beat, i) => (
        <div
          key={beat.headline}
          ref={el => { beatsRef.current[i] = el; }}
          style={{
            position: "absolute", zIndex: 30,
            ...(beat.align === "left"  && { left:  "clamp(1.5rem, 7vw, 8rem)", bottom: "14%" }),
            ...(beat.align === "right" && { right: "clamp(1.5rem, 7vw, 8rem)", bottom: "14%" }),
            ...(beat.align === "center" && {
              left: "50%", bottom: "14%",
              transform: "translateX(-50%)", textAlign: "center",
            }),
            maxWidth: "42rem",
            clipPath: "inset(0 100% 0 0)",
            opacity: 0,
          }}
        >
          <h2 style={{
            fontFamily: "var(--font-syne)", fontWeight: 800,
            fontSize: "clamp(2.5rem, 6vw, 5.5rem)",
            lineHeight: 0.95, letterSpacing: "-0.02em",
            color: "#F5EFE6",
            textShadow: "0 4px 40px rgba(0,0,0,0.8)",
          }}>
            {beat.headline}
          </h2>
          <p style={{
            fontFamily: "var(--font-space-grotesk)", fontWeight: 300,
            fontSize: "clamp(0.85rem, 1.3vw, 1.05rem)",
            color: "rgba(245,239,230,0.65)",
            marginTop: "0.75rem", lineHeight: 1.6,
          }}>
            {beat.sub}
          </p>
        </div>
      ))}

      {/* ── Progress bar ── */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        height: "2px", background: "rgba(200,168,122,0.12)", zIndex: 30,
      }}>
        <div
          ref={progRef}
          style={{
            height: "100%", background: "#C8A87A",
            transformOrigin: "left", transform: "scaleX(0)",
          }}
        />
      </div>

      {/* ── Scroll hint ── */}
      <div style={{
        position: "absolute", bottom: "2rem", right: "clamp(1.5rem, 5vw, 5rem)",
        zIndex: 30, display: "flex", alignItems: "center", gap: "0.5rem",
      }}>
        <span style={{
          fontFamily: "var(--font-space-grotesk)", fontSize: "0.62rem",
          letterSpacing: "0.3em", textTransform: "uppercase",
          color: "rgba(200,168,122,0.4)",
        }}>
          Continue descendo
        </span>
        <div style={{
          width: "1px", height: "2rem",
          background: "linear-gradient(to bottom, #C8A87A, transparent)",
          animation: "scrollPulse 2s ease-in-out infinite",
        }} />
      </div>
    </div>
  );
}
