// Four playing styles, four colours, each readable on the dark pitch background. A style keeps its colour wherever
// it appears because the colour comes from its place in the (alphabetical) style list the API returns.
const PALETTE = ["#7BE0AD", "#F2C94C", "#FF8F6B", "#63C5EA", "#C9A7FF", "#F59DC8"];
export const NO_STYLE_COLOR = "#8FA89B";

export function styleColor(style: string | null, styles: readonly string[]): string {
  if (style === null) return NO_STYLE_COLOR;
  const index = styles.indexOf(style);
  return index < 0 ? NO_STYLE_COLOR : (PALETTE[index % PALETTE.length] ?? NO_STYLE_COLOR);
}
