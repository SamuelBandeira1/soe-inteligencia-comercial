import { useCallback, useEffect, useRef } from "react";

export interface MousePosition {
  x: number;   // normalised [-1, 1]
  y: number;   // normalised [-1, 1]
  rawX: number;
  rawY: number;
}

export function useMousePosition() {
  const position = useRef<MousePosition>({ x: 0, y: 0, rawX: 0, rawY: 0 });

  const handleMouseMove = useCallback((e: MouseEvent) => {
    position.current = {
      x:    (e.clientX / window.innerWidth)  * 2 - 1,
      y:   -((e.clientY / window.innerHeight) * 2 - 1),
      rawX: e.clientX,
      rawY: e.clientY,
    };
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [handleMouseMove]);

  return position;
}
