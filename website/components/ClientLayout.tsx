"use client";

import { type ReactNode } from "react";
import SmoothScroller from "@/components/ui/SmoothScroller";
import CustomCursor from "@/components/ui/CustomCursor";

export default function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <SmoothScroller>
      <CustomCursor />
      {children}
    </SmoothScroller>
  );
}
