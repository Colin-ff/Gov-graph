// Chart colour roles for the analytics SVG charts. The app is light-theme only
// (see Layout.tsx), so these target the light chart surface.
//
// The categorical hues are the data-viz reference order (validated CVD-safe on
// the light surface for the first four adjacent slots — see the dataviz skill).
// Charts that use them (gender donut, representation bars) always pair colour
// with a visible label/legend, satisfying the sub-3:1 contrast relief rule.

// Fixed categorical order — assign in order, never cycled.
export const CATEGORICAL = [
  "#2a78d6", // blue
  "#008300", // green
  "#e87ba4", // magenta
  "#eda100", // yellow
  "#1baf7a", // aqua
  "#eb6834", // orange
  "#4a3aa7", // violet
  "#e34948", // red
] as const;

// "unknown" gender is pinned to a neutral gray so it never impersonates a hue.
export const UNKNOWN_GRAY = "#898781";

// Primary single-hue (matches the app's blue-600 used across buttons/nav).
export const PRIMARY = "#2563eb";

// Chart chrome / ink (light surface).
export const INK_PRIMARY = "#0b0b0b";
export const INK_SECONDARY = "#52514e";
export const INK_MUTED = "#898781";
export const GRIDLINE = "#e1e0d9";
export const AXIS = "#c3c2b7";

// Fixed hues for the three representation buckets (stable across renders).
export const REPRESENTATION_COLORS: Record<string, string> = {
  student: CATEGORICAL[0], // blue
  faculty: CATEGORICAL[1], // green
  external: CATEGORICAL[2], // magenta
};

// Deterministic colour for a gender label: "unknown" -> gray, otherwise assign
// by the label's position in the sorted key list so a group's colours are stable.
export function genderColor(label: string, sortedKeys: string[]): string {
  if (label === "unknown") return UNKNOWN_GRAY;
  const nonUnknown = sortedKeys.filter((k) => k !== "unknown");
  const idx = nonUnknown.indexOf(label);
  return CATEGORICAL[idx % CATEGORICAL.length];
}
