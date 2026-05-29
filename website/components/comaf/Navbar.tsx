"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { COMPANY } from "@/lib/comaf";

const LINKS = [
  { label: "Início",       href: "#inicio" },
  { label: "Sobre",        href: "#sobre" },
  { label: "Produtos",     href: "#produtos" },
  { label: "Diferenciais", href: "#diferenciais" },
  { label: "Contato",      href: "#contato" },
];

export default function ComafNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, "change", (v) => setScrolled(v > 60));

  return (
    <motion.nav
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
      style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 50,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "1.1rem clamp(1.5rem, 5vw, 5rem)",
        backdropFilter: scrolled ? "blur(24px) saturate(180%)" : "none",
        backgroundColor: scrolled ? "rgba(15,11,7,0.88)" : "transparent",
        borderBottom: scrolled ? "1px solid rgba(200,168,122,0.1)" : "1px solid transparent",
        transition: "background-color 0.4s, backdrop-filter 0.4s, border-color 0.4s",
      }}
    >
      {/* Logo */}
      <a href="#inicio" style={{ display: "flex", alignItems: "center", gap: "0.6rem", textDecoration: "none" }}>
        <div style={{
          width: 28, height: 28,
          border: "1px solid rgba(200,168,122,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{ width: 10, height: 10, background: "#C8A87A", transform: "rotate(45deg)" }} />
        </div>
        <span style={{
          fontFamily: "var(--font-syne)", fontWeight: 800,
          fontSize: "1rem", letterSpacing: "0.2em",
          color: "#F5EFE6", textTransform: "uppercase",
        }}>
          Comaf
        </span>
      </a>

      {/* Links */}
      <ul style={{
        display: "flex", alignItems: "center", gap: "2.5rem",
        listStyle: "none",
      }}>
        {LINKS.map(({ label, href }) => (
          <li key={href} style={{ display: "none", ["@media(min-width:768px)" as string]: { display: "block" } }}>
            <a
              href={href}
              style={{
                fontFamily: "var(--font-space-grotesk)", fontSize: "0.72rem",
                letterSpacing: "0.18em", textTransform: "uppercase",
                color: "rgba(245,239,230,0.5)", textDecoration: "none",
                transition: "color 0.3s",
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.color = "#C8A87A"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.color = "rgba(245,239,230,0.5)"; }}
            >
              {label}
            </a>
          </li>
        ))}
      </ul>

      {/* WhatsApp CTA */}
      <motion.a
        href={`https://wa.me/${COMPANY.whatsapp}?text=Olá! Gostaria de um orçamento.`}
        target="_blank"
        rel="noopener noreferrer"
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        style={{
          display: "flex", alignItems: "center", gap: "0.5rem",
          background: "#C8A87A", color: "#0F0B07",
          fontFamily: "var(--font-space-grotesk)", fontWeight: 600,
          fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase",
          padding: "0.6rem 1.2rem", textDecoration: "none",
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51a12.8 12.8 0 0 0-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/>
        </svg>
        WhatsApp
      </motion.a>
    </motion.nav>
  );
}
