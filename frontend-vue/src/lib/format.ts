import type { Market } from "@/types";

export const currencySymbol = (m: Market): string => (m === "bist" ? "₺" : "$");

/** Market-aware money: "$1,234" (nasdaq) / "1.234 ₺" (bist). */
export function money(amount: number, market: Market): string {
  const n = amount.toLocaleString(market === "bist" ? "tr-TR" : "en-US", {
    maximumFractionDigits: 0,
  });
  return market === "bist" ? `${n} ₺` : `$${n}`;
}
