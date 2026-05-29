"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { motion, useInView } from "framer-motion";
import { gsap } from "@/lib/gsap";
import { ScrollTrigger } from "@/lib/gsap";
import { COMPANY, IMAGES, STATS } from "@/lib/comaf";

function Counter({ target, suffix }: { target: number; suffix: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  useEffect(() => {
    if (!inView || !ref.current) return;
    const obj = { val: 0 };
    gsap.to(obj, {
      val: target,
      duration: 2,
      ease: "power2.out",
      onUpdate() {
        if (ref.current) ref.current.textContent = Math.round(obj.val).toLocaleString("pt-BR") + suffix;
      },
    });
  }, [inView, target, suffix]);

  return <span ref={ref}>0{suffix}</span>;
}

export default function SobreSection() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!sectionRef.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".sobre-img-wrap",
        { clipPath: "inset(0 100% 0 0)" },
        {
          clipPath: "inset(0 0% 0 0)",
          duration: 1.4,
          ease: "power4.inOut",
          scrollTrigger: {
            trigger: ".sobre-img-wrap",
            start: "top 75%",
          },
        }
      );
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  const years = new Date().getFullYear() - COMPANY.founded;

  return (
    <section
      ref={sectionRef}
      id="sobre"
      style={{ padding: "7rem clamp(1.5rem, 7vw, 8rem)", background: "#0F0B07" }}
    >
      <div className="section-divider" style={{ marginBottom: "5rem" }} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "5rem", alignItems: "center" }}>
        {/* Image */}
        <div
          className="sobre-img-wrap"
          style={{ position: "relative", aspectRatio: "4/5", overflow: "hidden" }}
        >
          <Image
            src={IMAGES.sobre}
            alt="Oficina Comaf"
            fill
            sizes="(max-width: 768px) 100vw, 50vw"
            style={{ objectFit: "cover" }}
          />
          {/* Amber corner accent */}
          <div style={{
            position: "absolute", bottom: 0, left: 0,
            width: "40%", height: "3px",
            background: "linear-gradient(to right, #C8A87A, transparent)",
          }} />
          <div style={{
            position: "absolute", bottom: 0, left: 0,
            width: "3px", height: "30%",
            background: "linear-gradient(to top, #C8A87A, transparent)",
          }} />

          {/* Years badge */}
          <div style={{
            position: "absolute", top: "2rem", right: "2rem",
            background: "rgba(15,11,7,0.85)", backdropFilter: "blur(12px)",
            border: "1px solid rgba(200,168,122,0.3)",
            padding: "1.25rem 1.5rem", textAlign: "center",
          }}>
            <p style={{
              fontFamily: "var(--font-syne)", fontWeight: 800,
              fontSize: "2.5rem", color: "#C8A87A", lineHeight: 1,
            }}>{years}</p>
            <p style={{
              fontFamily: "var(--font-space-grotesk)", fontSize: "0.65rem",
              letterSpacing: "0.2em", textTransform: "uppercase",
              color: "rgba(245,239,230,0.5)", marginTop: "0.3rem",
            }}>anos</p>
          </div>
        </div>

        {/* Text */}
        <div>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5 }}
            style={{
              fontFamily: "var(--font-space-grotesk)", fontSize: "0.7rem",
              letterSpacing: "0.3em", textTransform: "uppercase",
              color: "#C8A87A", marginBottom: "1rem",
            }}
          >
            Nossa história
          </motion.p>

          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7, delay: 0.1 }}
            style={{
              fontFamily: "var(--font-syne)", fontWeight: 800,
              fontSize: "clamp(2rem, 3.5vw, 3.2rem)",
              lineHeight: 1.05, color: "#F5EFE6", marginBottom: "1.5rem",
            }}
          >
            Madeira de qualidade,<br />
            <span style={{ color: "#C8A87A" }}>entregue com cuidado</span>
          </motion.h2>

          <motion.div
            initial={{ scaleX: 0, transformOrigin: "left" }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.3 }}
            style={{
              height: "1px", maxWidth: "12rem",
              background: "linear-gradient(to right, #C8A87A, transparent)",
              marginBottom: "1.5rem",
            }}
          />

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6, delay: 0.25 }}
            style={{
              fontFamily: "var(--font-space-grotesk)", fontWeight: 300,
              fontSize: "1rem", lineHeight: 1.8,
              color: "rgba(245,239,230,0.65)", marginBottom: "1.5rem",
            }}
          >
            Fundada em 2005 no coração de Fortaleza, a Comaf nasceu com uma missão clara:
            levar ao mercado as melhores madeiras com qualidade, respeito e ética.
          </motion.p>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6, delay: 0.35 }}
            style={{
              fontFamily: "var(--font-space-grotesk)", fontWeight: 300,
              fontSize: "1rem", lineHeight: 1.8,
              color: "rgba(245,239,230,0.65)", marginBottom: "3rem",
            }}
          >
            Atendemos construtoras, marceneiros e clientes particulares com o mesmo cuidado.
            Nosso estoque amplo e equipe especializada garantem a solução certa para cada projeto.
          </motion.p>

          {/* Stats grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            {STATS.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.4 + i * 0.1 }}
                style={{
                  padding: "1.25rem",
                  borderTop: "1px solid rgba(200,168,122,0.2)",
                }}
              >
                <p style={{
                  fontFamily: "var(--font-syne)", fontWeight: 700,
                  fontSize: "1.8rem", color: "#C8A87A", lineHeight: 1,
                }}>
                  <Counter target={stat.value} suffix={stat.suffix} />
                </p>
                <p style={{
                  fontFamily: "var(--font-space-grotesk)", fontSize: "0.7rem",
                  letterSpacing: "0.1em", textTransform: "uppercase",
                  color: "rgba(245,239,230,0.4)", marginTop: "0.35rem",
                }}>
                  {stat.label}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Mobile: stack */}
      <style>{`
        @media (max-width: 768px) {
          #sobre > div > div:first-child { grid-column: 1; }
          #sobre > div { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </section>
  );
}
