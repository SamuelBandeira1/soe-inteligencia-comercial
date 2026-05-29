"use client";

import { useEffect, useRef } from "react";
import { gsap } from "@/lib/gsap";

const NAV_LINKS = [
  { label: "Projetos",          href: "#projetos" },
  { label: "Engenharia",        href: "#engenharia" },
  { label: "Sustentabilidade",  href: "#sustentabilidade" },
  { label: "Contato",           href: "#contato" },
];

export default function Navbar() {
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!navRef.current) return;

    gsap.fromTo(
      navRef.current,
      { y: -50, opacity: 0 },
      { y: 0, opacity: 1, duration: 1, delay: 0.3, ease: "power3.out" }
    );

    const onScroll = () => {
      if (!navRef.current) return;
      const scrolled = window.scrollY > 60;
      navRef.current.style.backdropFilter = scrolled ? "blur(24px) saturate(180%)" : "none";
      navRef.current.style.backgroundColor = scrolled
        ? "rgba(11,12,16,0.75)"
        : "transparent";
      navRef.current.style.borderBottomColor = scrolled
        ? "rgba(0,210,255,0.08)"
        : "transparent";
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      ref={navRef}
      style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 50,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "1.25rem 3rem",
        borderBottom: "1px solid transparent",
        transition: "background-color 0.4s, backdrop-filter 0.4s, border-color 0.4s",
      }}
    >
      {/* Logo mark */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <div
          style={{
            width: 32, height: 32,
            border: "1px solid rgba(0,210,255,0.4)",
            transform: "rotate(45deg)",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <div style={{ width: 10, height: 10, background: "#FF4500" }} />
        </div>
        <span
          style={{
            fontFamily: "var(--font-syne)", fontWeight: 700,
            fontSize: "1.25rem", letterSpacing: "0.2em", color: "#C5C6C7",
          }}
        >
          SOE
        </span>
      </div>

      {/* Nav links */}
      <ul style={{ display: "flex", alignItems: "center", gap: "2.5rem", listStyle: "none" }}>
        {NAV_LINKS.map(({ label, href }) => (
          <li key={href}>
            <a
              href={href}
              style={{
                fontFamily: "var(--font-space-grotesk)",
                fontSize: "0.75rem", letterSpacing: "0.2em",
                textTransform: "uppercase", color: "rgba(197,198,199,0.55)",
                textDecoration: "none", transition: "color 0.3s",
                position: "relative",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.color = "#00D2FF";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.color = "rgba(197,198,199,0.55)";
              }}
            >
              {label}
            </a>
          </li>
        ))}
      </ul>

      {/* CTA button */}
      <a
        href="#contato"
        style={{
          fontFamily: "var(--font-space-grotesk)",
          fontSize: "0.7rem", letterSpacing: "0.2em", textTransform: "uppercase",
          color: "#C5C6C7", textDecoration: "none",
          padding: "0.6rem 1.25rem",
          border: "1px solid rgba(255,69,0,0.4)",
          transition: "border-color 0.3s, color 0.3s, background 0.3s",
        }}
        onMouseEnter={(e) => {
          const el = e.currentTarget as HTMLAnchorElement;
          el.style.borderColor = "#FF4500";
          el.style.color = "#FF4500";
          el.style.background = "rgba(255,69,0,0.08)";
        }}
        onMouseLeave={(e) => {
          const el = e.currentTarget as HTMLAnchorElement;
          el.style.borderColor = "rgba(255,69,0,0.4)";
          el.style.color = "#C5C6C7";
          el.style.background = "transparent";
        }}
      >
        Fale Conosco
      </a>
    </nav>
  );
}
