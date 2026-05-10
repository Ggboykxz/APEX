export interface Theme {
  id: string;
  name: string;
  bg: string;
  surface: string;
  surfaceAlt: string;
  border: string;
  text: string;
  textDim: string;
  textBright: string;
  accent: string;
  accentAlt: string;
  success: string;
  error: string;
  warning: string;
  tool: string;
  agent: string;
}

export const themes: Record<string, Theme> = {
  apex: {
    id: "apex",
    name: "APEX Dark",
    bg: "#0D1117",
    surface: "#161B22",
    surfaceAlt: "#21262D",
    border: "#30363D",
    text: "#E6EDF3",
    textDim: "#8B949E",
    textBright: "#FFFFFF",
    accent: "#FF6B35",
    accentAlt: "#FF8F66",
    success: "#3FB950",
    error: "#F85149",
    warning: "#D29922",
    tool: "#79C0FF",
    agent: "#A371F7",
  },
  dracula: {
    id: "dracula",
    name: "Dracula",
    bg: "#282A36",
    surface: "#44475A",
    surfaceAlt: "#6272A4",
    border: "#6272A4",
    text: "#F8F8F2",
    textDim: "#6272A4",
    textBright: "#FFFFFF",
    accent: "#BD93F9",
    accentAlt: "#FF79C6",
    success: "#50FA7B",
    error: "#FF5555",
    warning: "#FFB86C",
    tool: "#8BE9FD",
    agent: "#FF79C6",
  },
  nord: {
    id: "nord",
    name: "Nord",
    bg: "#2E3440",
    surface: "#3B4252",
    surfaceAlt: "#434C5E",
    border: "#4C566A",
    text: "#ECEFF4",
    textDim: "#D8DEE9",
    textBright: "#FFFFFF",
    accent: "#88C0D0",
    accentAlt: "#81A1C1",
    success: "#A3BE8C",
    error: "#BF616A",
    warning: "#EBCB8B",
    tool: "#8FBCBB",
    agent: "#B48EAD",
  },
  tokyonight: {
    id: "tokyonight",
    name: "Tokyo Night",
    bg: "#1A1B26",
    surface: "#24283B",
    surfaceAlt: "#414868",
    border: "#414868",
    text: "#C0CAF5",
    textDim: "#565F89",
    textBright: "#FFFFFF",
    accent: "#7AA2F7",
    accentAlt: "#BB9AF7",
    success: "#9ECE6A",
    error: "#F7768E",
    warning: "#E0AF68",
    tool: "#7DCFFF",
    agent: "#BB9AF7",
  },
  gruvbox: {
    id: "gruvbox",
    name: "Gruvbox",
    bg: "#282828",
    surface: "#3C3836",
    surfaceAlt: "#504945",
    border: "#504945",
    text: "#EBDBB2",
    textDim: "#A89984",
    textBright: "#FFFFFF",
    accent: "#FABD2F",
    accentAlt: "#FABC2C",
    success: "#98971A",
    error: "#FB4934",
    warning: "#D79921",
    tool: "#83A598",
    agent: "#B16286",
  },
  github: {
    id: "github",
    name: "GitHub Dark",
    bg: "#0D1117",
    surface: "#161B22",
    surfaceAlt: "#21262D",
    border: "#30363D",
    text: "#E6EDF3",
    textDim: "#8B949E",
    textBright: "#FFFFFF",
    accent: "#58A6FF",
    accentAlt: "#79C0FF",
    success: "#3FB950",
    error: "#F85149",
    warning: "#D29922",
    tool: "#79C0FF",
    agent: "#A371F7",
  },
};

export function getTheme(id: string): Theme {
  return themes[id] || themes.apex;
}