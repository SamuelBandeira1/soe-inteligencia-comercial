"use client";

import { Canvas } from "@react-three/fiber";
import { Suspense, type MutableRefObject } from "react";
import SteelScene from "./SteelScene";
import type { MousePosition } from "@/hooks/useMousePosition";

interface SteelCanvasProps {
  mousePosition: MutableRefObject<MousePosition>;
}

export default function SteelCanvas({ mousePosition }: SteelCanvasProps) {
  return (
    <Canvas
      dpr={[1, 1.5]}
      camera={{ position: [0, 0, 6.5], fov: 42 }}
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
        toneMapping: 0, /* NoToneMapping — we control colour ourselves */
      }}
      style={{ background: "transparent" }}
    >
      <Suspense fallback={null}>
        <SteelScene mousePosition={mousePosition} />
      </Suspense>
    </Canvas>
  );
}
