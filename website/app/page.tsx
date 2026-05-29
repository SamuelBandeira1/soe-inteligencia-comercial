import ComafNavbar        from "@/components/comaf/Navbar";
import HeroSection        from "@/components/comaf/HeroSection";
import VideoScrollSection from "@/components/comaf/VideoScrollSection";
import SobreSection       from "@/components/comaf/SobreSection";
import ProdutosSection    from "@/components/comaf/ProdutosSection";
import DiferenciaisSection from "@/components/comaf/DiferenciaisSection";
import GaleriaSection     from "@/components/comaf/GaleriaSection";
import ContatoSection     from "@/components/comaf/ContatoSection";
import Footer             from "@/components/comaf/Footer";

export default function Home() {
  return (
    <>
      <ComafNavbar />
      <main>
        <HeroSection />
        <VideoScrollSection />
        <SobreSection />
        <ProdutosSection />
        <DiferenciaisSection />
        <GaleriaSection />
        <ContatoSection />
      </main>
      <Footer />
    </>
  );
}
