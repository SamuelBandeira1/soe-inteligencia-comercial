"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { gsap } from "@/lib/gsap";
import { COMPANY, IMAGES } from "@/lib/comaf";

const TITLE_WORDS = COMPANY.tagline.split(" ");

export default function HeroSection() {
  const lineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!lineRef.current) return;
    gsap.fromTo(
      lineRef.current,
      { scaleX: 0, transformOrigin: "left" },
      { scaleX: 1, duration: 1.2, delay: 1.4, ease: "power3.out" }
    );
  }, []);

  return (
    <section
      id="inicio"
      style={{ position: "relative", width: "100%", height: "100svh", overflow: "hidden" }}
    >
      {/* Background image */}
      <Image
        src={IMAGES.hero}
        alt="Madeiras Comaf"
        fill
        priority
        sizes="100vw"
        style={{ objectFit: "cover", objectPosition: "center" }}
      />

      {/* Dark overlays */}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(to right, rgba(15,11,7,0.92) 0%, rgba(15,11,7,0.65) 60%, rgba(15,11,7,0.3) 100%)",
        zIndex: 1,
      }} />
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(to top, #0F0B07 0%, transparent 40%)",
        zIndex: 2,
      }} />

      {/* Wood grain overlay */}
      <div className="wood-grain" style={{ position: "absolute", inset: 0, zIndex: 2, pointerEvents: "none" }} />

      {/* Content */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 10,
        display: "flex", alignItems: "center",
        paddingLeft: "clamp(1.5rem, 7vw, 8rem)",
        paddingTop: "5rem",
      }}>
        <div style={{ maxWidth: "52rem" }}>

          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            style={{
              display: "inline-flex", alignItems: "center", gap: "0.5rem",
              border: "1px solid rgba(200,168,122,0.35)",
              padding: "0.4rem 1rem", marginBottom: "2rem",
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#C8A87A", flexShrink: 0 }} />
            <span style={{
              fontFamily: "var(--font-space-grotesk)",
              fontSize: "0.7rem", letterSpacing: "0.25em", textTransform: "uppercase",
              color: "#C8A87A",
            }}>
              Madeireira em Fortaleza · Desde 2005
            </span>
          </motion.div>

          {/* Headline — word by word */}
          <h1
            style={{
              fontFamily: "var(--font-syne)", fontWeight: 800,
              fontSize: "clamp(2.8rem, 7vw, 6.5rem)",
              lineHeight: 0.95, letterSpacing: "-0.02em",
              color: "#F5EFE6", marginBottom: "1.5rem",
            }}
            aria-label={COMPANY.tagline}
          >
            {TITLE_WORDS.map((word, i) => (
              <motion.span
                key={word}
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.5 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}
                style={{ display: "inline-block", marginRight: "0.3em" }}
              >
                {word}
              </motion.span>
            ))}
          </h1>

          {/* Amber divider line — animated via GSAP */}
          <div
            ref={lineRef}
            style={{
              height: "2px", width: "100%", maxWidth: "28rem", marginBottom: "1.5rem",
              background: "linear-gradient(to right, #C8A87A, #E8C49A, transparent)",
            }}
          />

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 1.1 }}
            style={{
              fontFamily: "var(--font-space-grotesk)", fontWeight: 300,
              fontSize: "clamp(0.9rem, 1.5vw, 1.15rem)",
              color: "rgba(245,239,230,0.6)", marginBottom: "2.5rem",
              maxWidth: "36rem", lineHeight: 1.7,
            }}
          >
            Especialistas em portas de madeira, virgas, tábuas e madeiras para construção.
            Atendimento exclusivo e estoque completo para sua obra.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 1.3 }}
            style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}
          >
            <a
              href={`https://wa.me/${COMPANY.whatsapp}?text=Olá! Vim pelo site e gostaria de um orçamento.`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex", alignItems: "center", gap: "0.6rem",
                background: "#C8A87A", color: "#0F0B07",
                fontFamily: "var(--font-space-grotesk)", fontWeight: 600,
                fontSize: "0.8rem", letterSpacing: "0.15em", textTransform: "uppercase",
                padding: "1rem 2rem", textDecoration: "none",
                transition: "background 0.3s, transform 0.2s",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLAnchorElement).style.background = "#E8C49A";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(-2px)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLAnchorElement).style.background = "#C8A87A";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(0)";
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51a12.8 12.8 0 0 0-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/>
              </svg>
              Pedir Orçamento
            </a>

            <a
              href="#produtos"
              style={{
                display: "inline-flex", alignItems: "center", gap: "0.5rem",
                border: "1px solid rgba(200,168,122,0.4)",
                color: "#C8A87A", textDecoration: "none",
                fontFamily: "var(--font-space-grotesk)", fontWeight: 400,
                fontSize: "0.8rem", letterSpacing: "0.15em", textTransform: "uppercase",
                padding: "1rem 2rem",
                transition: "border-color 0.3s, color 0.3s",
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLAnchorElement;
                el.style.borderColor = "#C8A87A";
                el.style.color = "#E8C49A";
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLAnchorElement;
                el.style.borderColor = "rgba(200,168,122,0.4)";
                el.style.color = "#C8A87A";
              }}
            >
              Ver Produtos
            </a>
          </motion.div>
        </div>
      </div>

      {/* Bottom info bar */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 1.6 }}
        style={{
          position: "absolute", bottom: "2.5rem", left: 0, right: 0,
          zIndex: 10, paddingInline: "clamp(1.5rem, 7vw, 8rem)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          flexWrap: "wrap", gap: "1rem",
        }}
      >
        <a
          href={`tel:${COMPANY.phone}`}
          style={{
            display: "flex", alignItems: "center", gap: "0.5rem",
            color: "rgba(245,239,230,0.5)", textDecoration: "none",
            fontFamily: "var(--font-space-grotesk)", fontSize: "0.8rem",
            letterSpacing: "0.1em", transition: "color 0.3s",
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.color = "#C8A87A"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.color = "rgba(245,239,230,0.5)"; }}
        >
          <span style={{ color: "#C8A87A" }}>☎</span> {COMPANY.phone}
        </a>
        <p style={{
          fontFamily: "var(--font-space-grotesk)", fontSize: "0.75rem",
          letterSpacing: "0.15em", color: "rgba(245,239,230,0.35)",
          textTransform: "uppercase",
        }}>
          Antonio Bezerra · Fortaleza - CE
        </p>
      </motion.div>

      {/* Scroll indicator */}
      <div style={{
        position: "absolute", bottom: "2.5rem", left: "50%", transform: "translateX(-50%)",
        zIndex: 10, display: "flex", flexDirection: "column", alignItems: "center", gap: "0.4rem",
      }}>
        <div style={{
          width: "1px", height: "3rem",
          background: "linear-gradient(to bottom, #C8A87A, transparent)",
          animation: "scrollPulse 2s ease-in-out infinite",
        }} />
      </div>

      <style>{`
        @keyframes scrollPulse {
          0%, 100% { opacity: 0.3; }
          50%       { opacity: 0.9; }
        }
      `}</style>
    </section>
  );
}
