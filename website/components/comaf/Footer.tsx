"use client";

import { motion } from "framer-motion";
import { COMPANY } from "@/lib/comaf";

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer style={{ background: "#0A0704", padding: "3rem clamp(1.5rem, 7vw, 8rem)" }}>
      <div className="section-divider" style={{ marginBottom: "3rem" }} />
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        flexWrap: "wrap", gap: "1.5rem",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <div style={{
            width: 22, height: 22,
            border: "1px solid rgba(200,168,122,0.4)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <div style={{ width: 8, height: 8, background: "#C8A87A", transform: "rotate(45deg)" }} />
          </div>
          <span style={{
            fontFamily: "var(--font-syne)", fontWeight: 700,
            fontSize: "0.85rem", letterSpacing: "0.2em",
            color: "#F5EFE6", textTransform: "uppercase",
          }}>
            Comaf Portas
          </span>
        </div>

        <p style={{
          fontFamily: "var(--font-space-grotesk)", fontSize: "0.7rem",
          letterSpacing: "0.1em", color: "rgba(245,239,230,0.3)",
        }}>
          {COMPANY.address.street} · {COMPANY.address.city} - {COMPANY.address.state}
        </p>

        <p style={{
          fontFamily: "var(--font-space-grotesk)", fontSize: "0.7rem",
          letterSpacing: "0.1em", color: "rgba(245,239,230,0.25)",
        }}>
          © {year} Comaf · CNPJ {COMPANY.cnpj}
        </p>
      </div>
    </footer>
  );
}
