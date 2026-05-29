"use client";

import { motion } from "framer-motion";
import { COMPANY } from "@/lib/comaf";

const INFO = [
  {
    label: "Endereço",
    value: COMPANY.address.full,
    href:  `https://maps.google.com/?q=${encodeURIComponent(COMPANY.address.full)}`,
    icon:  "◎",
  },
  {
    label: "Telefone",
    value: COMPANY.phone,
    href:  `tel:${COMPANY.phone}`,
    icon:  "◉",
  },
  {
    label: "WhatsApp",
    value: "(85) 99741-0355",
    href:  `https://wa.me/${COMPANY.whatsapp}?text=Olá! Gostaria de mais informações.`,
    icon:  "◈",
  },
  {
    label: "E-mail",
    value: COMPANY.email,
    href:  `mailto:${COMPANY.email}`,
    icon:  "◇",
  },
];

export default function ContatoSection() {
  return (
    <section
      id="contato"
      style={{ padding: "7rem clamp(1.5rem, 7vw, 8rem)", background: "#0F0B07" }}
    >
      <div className="section-divider" style={{ marginBottom: "5rem" }} />

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "5rem",
        alignItems: "start",
      }}>
        {/* Left — CTA */}
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
            Fale conosco
          </motion.p>

          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.1 }}
            style={{
              fontFamily: "var(--font-syne)", fontWeight: 800,
              fontSize: "clamp(2rem, 4vw, 3.5rem)",
              lineHeight: 1.05, color: "#F5EFE6",
              marginBottom: "1.5rem",
            }}
          >
            Pronto para seu<br />
            <span style={{ color: "#C8A87A" }}>próximo projeto?</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            style={{
              fontFamily: "var(--font-space-grotesk)", fontWeight: 300,
              fontSize: "1rem", lineHeight: 1.8,
              color: "rgba(245,239,230,0.55)", marginBottom: "2.5rem",
              maxWidth: "28rem",
            }}
          >
            Entre em contato pelo WhatsApp ou telefone e receba atendimento exclusivo
            da nossa equipe especializada. Fazemos orçamento sem compromisso.
          </motion.p>

          <motion.a
            href={`https://wa.me/${COMPANY.whatsapp}?text=Olá! Gostaria de um orçamento.`}
            target="_blank"
            rel="noopener noreferrer"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.3 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={{
              display: "inline-flex", alignItems: "center", gap: "0.75rem",
              background: "#C8A87A", color: "#0F0B07",
              fontFamily: "var(--font-space-grotesk)", fontWeight: 700,
              fontSize: "0.85rem", letterSpacing: "0.15em", textTransform: "uppercase",
              padding: "1.1rem 2.5rem", textDecoration: "none",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51a12.8 12.8 0 0 0-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/>
            </svg>
            Chamar no WhatsApp
          </motion.a>
        </div>

        {/* Right — Info cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0px" }}>
          {INFO.map((item, i) => (
            <motion.a
              key={item.label}
              href={item.href}
              target={item.href.startsWith("http") ? "_blank" : undefined}
              rel={item.href.startsWith("http") ? "noopener noreferrer" : undefined}
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ x: 6 }}
              style={{
                display: "flex", alignItems: "flex-start", gap: "1.25rem",
                padding: "1.5rem 0",
                borderBottom: "1px solid rgba(200,168,122,0.1)",
                textDecoration: "none",
                transition: "border-color 0.3s",
              }}
            >
              <span style={{
                fontFamily: "var(--font-syne)", fontSize: "1.1rem",
                color: "#C8A87A", flexShrink: 0, marginTop: "0.1rem",
              }}>
                {item.icon}
              </span>
              <div>
                <p style={{
                  fontFamily: "var(--font-space-grotesk)", fontSize: "0.65rem",
                  letterSpacing: "0.25em", textTransform: "uppercase",
                  color: "rgba(200,168,122,0.5)", marginBottom: "0.3rem",
                }}>
                  {item.label}
                </p>
                <p style={{
                  fontFamily: "var(--font-space-grotesk)", fontSize: "0.95rem",
                  color: "rgba(245,239,230,0.8)", lineHeight: 1.5,
                }}>
                  {item.value}
                </p>
              </div>
            </motion.a>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          #contato > div > div:last-child { grid-column: 1; }
          #contato > div { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </section>
  );
}
