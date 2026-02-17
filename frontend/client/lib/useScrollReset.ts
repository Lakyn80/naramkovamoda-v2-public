import { useEffect } from "react";

export function useScrollResetOnChange(key: string) {
  useEffect(() => {
    if (typeof window === "undefined") return;
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [key]);
}
