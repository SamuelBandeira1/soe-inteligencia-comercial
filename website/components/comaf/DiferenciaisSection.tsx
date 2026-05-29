"use client";

import { motion } from "framer-motion";
import { DIFERENCIAIS } from "@/lib/comaf";

export default function DiferenciaisSection() {
  return (
    <section
      id="diferenciais"
      style={{ padding: "7rem clamp(1.5rem, 7vw, 8rem)", background: "#0F0B07" }}
    >
      <div className="section-divider" style={{ marginBottom: "5rem" }} />

      {/* Header */}
      <div style={{ maxWidth: "36rem", marginBottom: "5rem" }}>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          style={{
            fontFamily: "var(--font-space-grotesk)", fontSize: "0.7rem",
            letterSpacing: "0.3em", textTransform: "uppercase",
            color: "#C8A87A", marginBottom: "0.8rem",
          }}
        >
          Por que escolher a Comaf
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.1 }}
          style={{
            fontFamily: "var(--font-syne)", fontWeight: 800,
            fontSize: "clamp(2rem, 4vw, 3.5rem)",
            lineHeight: 1.05, color: "#F5EFE6",
          }}
        >
          Nossos <span style={{ color: "#C8A87A" }}>diferenciais</span>
        </motion.h2>
      </div>

      {/* Cards */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
        gap: "1px",
        background: "rgba(200,168,122,0.08)",
      }}>
        {DIFERENCIAIS.map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, delay: i * 0.12 }}
            whileHover={{ background: "rgba(200,168,122,0.04)" }}
            style={{
              background: "#0F0B07",
              padding: "2.5rem 2rem",
              position: "relative",
              transition: "background 0.3s",
            }}
          >
            <span style={{
              display: "block",
              fontFamily: "var(--font-syne)", fontSize: "1.5rem",
              color: "#C8A87A", marginBottom: "1.25rem",
            }}>
              {item.icon}
            </span>
            <h3 style={{
              fontFamily: "var(--font-syne)", fontWeight: 700,
              fontSize: "1.1rem", color: "#F5EFE6", marginBottom: "0.75rem",
            }}>
              {item.title}
            </h3>
            <p style={{
              fontFamily: "var(--font-space-grotesk)", fontWeight: 300,
              fontSize: "0.9rem", lineHeight: 1.7,
              color: "rgba(245,239,230,0.5)",
            }}>
              {item.description}
            </p>

            {/* Counter badge */}
            <div style={{
              position: "absolute", top: "1.5rem", right: "1.5rem",
              fontFamily: "var(--font-syne)", fontSize: "0.7rem",
              color: "rgba(200,168,122,0.25)",
            }}>
              0{i + 1}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Floating ambient quote */}
      <motion.blockquote
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, delay: 0.4 }}
        style={{
          marginTop: "5rem",
          borderLeft: "2px solid #C8A87A",
          paddingLeft: "2rem",
          maxWidth: "42rem",
        }}
      >
        <p style={{
          fontFamily: "var(--font-syne)", fontWeight: 600,
          fontSize: "clamp(1.1rem, 2vw, 1.5rem)",
          color: "rgba(245,239,230,0.7)",
          fontStyle: "italic", lineHeight: 1.6,
        }}>
          "Qualidade, respeito e ética — esses são os valores que guiam cada madeira que sai da Comaf."
        </p>
        <footer style={{
          marginTop: "1rem",
          fontFamily: "var(--font-space-grotesk)", fontSize: "0.75rem",
          letterSpacing: "0.2em", textTransform: "uppercase",
          color: "#C8A87A",
        }}>
          — Comaf Portas, fundada em 2005
        </footer>
      </motion.blockquote>
    </section>
  );
}
