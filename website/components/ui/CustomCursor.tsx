"use client";

import { useEffect, useRef, useState } from "react";
import { gsap } from "@/lib/gsap";

export default function CustomCursor() {
  const dotRef  = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;

    const dot  = dotRef.current!;
    const ring = ringRef.current!;

    let mx = 0, my = 0;
    let rx = 0, ry = 0;
    let rafId: number;

    const onMove = (e: MouseEvent) => {
      mx = e.clientX;
      my = e.clientY;
      gsap.set(dot, { x: mx - 4, y: my - 4 });
    };

    const loop = () => {
      rx += (mx - rx) * 0.1;
      ry += (my - ry) * 0.1;
      gsap.set(ring, { x: rx - 20, y: ry - 20 });
      rafId = requestAnimationFrame(loop);
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    rafId = requestAnimationFrame(loop);

    const enter = () =>
      gsap.to(ring, { scale: 2, borderColor: "#FF4500", duration: 0.25, ease: "power2.out" });
    const leave = () =>
      gsap.to(ring, { scale: 1, borderColor: "#00D2FF", duration: 0.25, ease: "power2.out" });

    const attach = () => {
      document.querySelectorAll("a, button, [data-cursor]").forEach((el) => {
        el.addEventListener("mouseenter", enter);
        el.addEventListener("mouseleave", leave);
      });
    };
    attach();

    return () => {
      window.removeEventListener("mousemove", onMove);
      cancelAnimationFrame(rafId);
      document.querySelectorAll("a, button, [data-cursor]").forEach((el) => {
        el.removeEventListener("mouseenter", enter);
        el.removeEventListener("mouseleave", leave);
      });
    };
  }, [mounted]);

  if (!mounted) return null;

  return (
    <>
      <div
        ref={dotRef}
        style={{
          position: "fixed", top: 0, left: 0, width: 8, height: 8,
          borderRadius: "50%", background: "#00D2FF",
          zIndex: 9999, pointerEvents: "none", willChange: "transform",
          mixBlendMode: "difference",
        }}
      />
      <div
        ref={ringRef}
        style={{
          position: "fixed", top: 0, left: 0, width: 40, height: 40,
          borderRadius: "50%", border: "1px solid #00D2FF",
          zIndex: 9998, pointerEvents: "none", willChange: "transform",
          transition: "border-color 0.25s",
        }}
      />
    </>
  );
}
