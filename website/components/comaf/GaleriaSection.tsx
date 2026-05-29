"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { IMAGES } from "@/lib/comaf";

/* Masonry-style layout: alternating heights */
const LAYOUT = [
  { colSpan: 1, rowSpan: 2 },
  { colSpan: 1, rowSpan: 1 },
  { colSpan: 1, rowSpan: 1 },
  { colSpan: 2, rowSpan: 1 },
  { colSpan: 1, rowSpan: 1 },
  { colSpan: 1, rowSpan: 1 },
];

export default function GaleriaSection() {
  return (
    <section
      id="galeria"
      style={{ padding: "7rem clamp(1.5rem, 7vw, 8rem)", background: "#1A1208" }}
    >
      <div className="section-divider" style={{ marginBottom: "5rem" }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "3rem", flexWrap: "wrap", gap: "1rem" }}>
        <div>
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
            Galeria
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.1 }}
            style={{
              fontFamily: "var(--font-syne)", fontWeight: 800,
              fontSize: "clamp(1.8rem, 3.5vw, 3rem)",
              lineHeight: 1.05, color: "#F5EFE6",
            }}
          >
            Nossa <span style={{ color: "#C8A87A" }}>madeira</span><br />em detalhes
          </motion.h2>
        </div>
      </div>

      {/* Grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gridAutoRows: "220px",
        gap: "6px",
      }}>
        {IMAGES.gallery.map((src, i) => {
          const { colSpan, rowSpan } = LAYOUT[i] ?? { colSpan: 1, rowSpan: 1 };
          return (
            <motion.div
              key={src}
              initial={{ opacity: 0, scale: 0.97 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.6, delay: i * 0.08 }}
              whileHover={{ zIndex: 2 }}
              style={{
                gridColumn: `span ${colSpan}`,
                gridRow: `span ${rowSpan}`,
                position: "relative",
                overflow: "hidden",
                cursor: "pointer",
              }}
            >
              <motion.div
                style={{ position: "absolute", inset: 0 }}
                whileHover={{ scale: 1.07 }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              >
                <Image
                  src={src}
                  alt={`Comaf galeria ${i + 1}`}
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  style={{ objectFit: "cover" }}
                />
              </motion.div>

              {/* Hover overlay */}
              <motion.div
                initial={{ opacity: 0 }}
                whileHover={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                style={{
                  position: "absolute", inset: 0,
                  background: "rgba(200,168,122,0.12)",
                  border: "1px solid rgba(200,168,122,0.25)",
                }}
              />
            </motion.div>
          );
        })}
      </div>

      <style>{`
        @media (max-width: 640px) {
          #galeria .grid { grid-template-columns: 1fr 1fr !important; }
        }
      `}</style>
    </section>
  );
}
