import HeroSection from "@/components/hero/HeroSection";

export default function Home() {
  return (
    <main>
      <HeroSection />

      {/* Section 02 — Portfolio (próxima entrega) */}
      <div
        id="projetos"
        className="min-h-screen flex items-center justify-center"
        style={{ background: "#0B0C10" }}
      >
        <p
          className="text-[11px] tracking-[0.4em] uppercase"
          style={{ color: "rgba(197,198,199,0.15)", fontFamily: "var(--font-syne)" }}
        >
          Seção 02 — Portfólio de Megaprojetos
        </p>
      </div>

      {/* Section 03 — Engineering */}
      <div
        id="engenharia"
        className="min-h-screen flex items-center justify-center"
        style={{ background: "#0D1117" }}
      >
        <p
          className="text-[11px] tracking-[0.4em] uppercase"
          style={{ color: "rgba(197,198,199,0.15)", fontFamily: "var(--font-syne)" }}
        >
          Seção 03 — Engenharia de Precisão
        </p>
      </div>

      {/* Section 04 — Sustainability */}
      <div
        id="sustentabilidade"
        className="min-h-screen flex items-center justify-center"
        style={{ background: "#0B0C10" }}
      >
        <p
          className="text-[11px] tracking-[0.4em] uppercase"
          style={{ color: "rgba(197,198,199,0.15)", fontFamily: "var(--font-syne)" }}
        >
          Seção 04 — Sustentabilidade e Futuro
        </p>
      </div>
    </main>
  );
}
