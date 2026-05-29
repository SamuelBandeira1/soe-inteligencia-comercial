"use client";

import Image from "next/image";
import { type Variants, motion } from "framer-motion";
import { PRODUCTS, COMPANY } from "@/lib/comaf";

const cardVariants: Variants = {
  hidden:  { opacity: 0, y: 40 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.6, delay: i * 0.1, ease: "easeOut" },
  }),
};

export default function ProdutosSection() {
  return (
    <section
      id="produtos"
      style={{ padding: "7rem clamp(1.5rem, 7vw, 8rem)", background: "#1A1208" }}
    >
      <div className="section-divider" style={{ marginBottom: "5rem" }} />

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "4rem", flexWrap: "wrap", gap: "1.5rem" }}>
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
            Nosso catálogo
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.1 }}
            style={{
              fontFamily: "var(--font-syne)", fontWeight: 800,
              fontSize: "clamp(2rem, 4vw, 3.5rem)",
              lineHeight: 1.0, color: "#F5EFE6",
            }}
          >
            Produtos &<br />
            <span style={{ color: "#C8A87A" }}>Materiais</span>
          </motion.h2>
        </div>

        <motion.a
          href={`https://wa.me/${COMPANY.whatsapp}?text=Olá! Gostaria de saber mais sobre os produtos.`}
          target="_blank"
          rel="noopener noreferrer"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
          style={{
            fontFamily: "var(--font-space-grotesk)", fontSize: "0.75rem",
            letterSpacing: "0.2em", textTransform: "uppercase",
            color: "#C8A87A", textDecoration: "none",
            borderBottom: "1px solid rgba(200,168,122,0.4)",
            paddingBottom: "0.25rem",
            transition: "color 0.3s, border-color 0.3s",
          }}
          whileHover={{ color: "#E8C49A" }}
        >
          Consultar preços via WhatsApp →
        </motion.a>
      </div>

      {/* Product grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
        gap: "1.5px",
        background: "rgba(200,168,122,0.08)",
      }}>
        {PRODUCTS.map((product, i) => (
          <motion.div
            key={product.id}
            custom={i}
            variants={cardVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-60px" }}
            style={{
              background: "#1A1208",
              overflow: "hidden",
              position: "relative",
              cursor: "pointer",
            }}
            whileHover="hover"
          >
            {/* Image */}
            <motion.div
              style={{ position: "relative", aspectRatio: "4/3", overflow: "hidden" }}
              variants={{ hover: { scale: 1 } }}
            >
              <motion.div
                style={{ position: "absolute", inset: 0 }}
                variants={{ hover: { scale: 1.06 } }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              >
                <Image
                  src={product.image}
                  alt={product.title}
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  style={{ objectFit: "cover" }}
                />
              </motion.div>

              {/* Gradient overlay */}
              <div style={{
                position: "absolute", inset: 0,
                background: "linear-gradient(to top, rgba(26,18,8,0.9) 0%, rgba(26,18,8,0.2) 60%, transparent 100%)",
              }} />

              {/* Tag */}
              <div style={{
                position: "absolute", top: "1rem", left: "1rem",
                background: "rgba(15,11,7,0.8)", backdropFilter: "blur(8px)",
                border: "1px solid rgba(200,168,122,0.25)",
                padding: "0.3rem 0.75rem",
              }}>
                <span style={{
                  fontFamily: "var(--font-space-grotesk)", fontSize: "0.6rem",
                  letterSpacing: "0.2em", textTransform: "uppercase", color: "#C8A87A",
                }}>
                  {product.tag}
                </span>
              </div>
            </motion.div>

            {/* Text */}
            <div style={{ padding: "1.5rem" }}>
              <h3 style={{
                fontFamily: "var(--font-syne)", fontWeight: 700,
                fontSize: "1.15rem", color: "#F5EFE6", marginBottom: "0.6rem",
              }}>
                {product.title}
              </h3>
              <p style={{
                fontFamily: "var(--font-space-grotesk)", fontWeight: 300,
                fontSize: "0.875rem", lineHeight: 1.65,
                color: "rgba(245,239,230,0.5)",
              }}>
                {product.description}
              </p>

              <motion.div
                variants={{ hover: { opacity: 1, y: 0 } }}
                initial={{ opacity: 0, y: 6 }}
                transition={{ duration: 0.3 }}
                style={{ marginTop: "1.25rem" }}
              >
                <a
                  href={`https://wa.me/${COMPANY.whatsapp}?text=Olá! Tenho interesse em ${product.title}. Pode me ajudar?`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontFamily: "var(--font-space-grotesk)", fontSize: "0.7rem",
                    letterSpacing: "0.2em", textTransform: "uppercase",
                    color: "#C8A87A", textDecoration: "none",
                    display: "inline-flex", alignItems: "center", gap: "0.4rem",
                  }}
                >
                  Consultar preço →
                </a>
              </motion.div>
            </div>

            {/* Bottom amber line — appears on hover */}
            <motion.div
              variants={{ hover: { scaleX: 1 } }}
              initial={{ scaleX: 0 }}
              style={{
                position: "absolute", bottom: 0, left: 0, right: 0,
                height: "2px", background: "#C8A87A",
                transformOrigin: "left",
              }}
              transition={{ duration: 0.4 }}
            />
          </motion.div>
        ))}
      </div>
    </section>
  );
}
