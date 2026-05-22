import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import App from './App';

// "Cadence brand" theme — derived from the logo:
//   • Teal primary (#2BA89E) is the top dot of the staff
//   • Coral secondary (#D17753) is the second dot
//   • Sage neutral (#7F9081) is the third dot — used for muted accents
//   • Warm orange (#F37726) is the first dot — used for highlight states
//   • Warm cream paper colour matches the logo backdrop
//   • Stone-200 / stone-300 dividers replace the cooler slate divider
const TEAL = '#2BA89E';
const TEAL_DARK = '#1f8278';
const TEAL_LIGHT = '#4dbdb3';
const TEAL_50 = '#e6f5f3';
const CORAL = '#D17753';
const CORAL_DARK = '#a85a3b';
const SAGE = '#7F9081';
const ORANGE = '#F37726';

const theme = createTheme({
  palette: {
    primary: {
      main: TEAL,
      light: TEAL_LIGHT,
      dark: TEAL_DARK,
      contrastText: '#ffffff',
    },
    secondary: {
      main: CORAL,
      dark: CORAL_DARK,
      contrastText: '#ffffff',
    },
    error: { main: '#b91c1c' },
    warning: { main: '#c2410c' },        // burnt-orange, harmonises with coral/orange
    success: { main: '#15803d' },
    info: { main: SAGE },                // sage as informational — quiet
    background: {
      default: '#faf9f5',                // cream, matches the logo backdrop
      paper: '#ffffff',
    },
    text: {
      primary: '#1c1917',                // stone-900 — warmer than slate
      secondary: '#57534e',              // stone-600
      disabled: '#a8a29e',                // stone-400
    },
    divider: '#e7e5e4',                  // stone-200, same family as the staff lines
    grey: {
      50:  '#fafaf9',
      100: '#f5f5f4',
      200: '#e7e5e4',
      300: '#d6d3d1',
      400: '#a8a29e',
      500: '#78716c',
      600: '#57534e',
      700: '#44403c',
      800: '#292524',
      900: '#1c1917',
    },
  },
  typography: {
    fontFamily:
      '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    fontSize: 14,
    h1: { fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontWeight: 600, letterSpacing: '-0.015em' },
    h4: { fontWeight: 600, letterSpacing: '-0.01em' },
    h5: { fontWeight: 600, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600, letterSpacing: '-0.005em' },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    button: { fontWeight: 500, textTransform: 'none', letterSpacing: 0 },
    body1: { lineHeight: 1.55 },
    body2: { lineHeight: 1.55 },
    caption: { letterSpacing: 0 },
  },
  shape: { borderRadius: 8 },
  shadows: [
    'none',
    '0 1px 2px 0 rgba(28, 25, 23, 0.04)',
    '0 1px 2px 0 rgba(28, 25, 23, 0.06), 0 1px 3px 0 rgba(28, 25, 23, 0.04)',
    '0 2px 4px 0 rgba(28, 25, 23, 0.06), 0 1px 2px 0 rgba(28, 25, 23, 0.04)',
    '0 4px 6px -1px rgba(28, 25, 23, 0.08), 0 2px 4px -2px rgba(28, 25, 23, 0.04)',
    ...Array(20).fill('0 8px 16px -4px rgba(28, 25, 23, 0.10), 0 4px 6px -2px rgba(28, 25, 23, 0.04)'),
  ] as any,
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { fontFeatureSettings: '"cv11", "ss01"' },
        code: {
          fontFamily:
            '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: '0.92em',
        },
        pre: {
          fontFamily:
            '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        },
      },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0, color: 'default' },
      styleOverrides: {
        root: {
          backgroundColor: '#ffffff',
          color: '#1c1917',
          borderBottom: '1px solid #e7e5e4',
          backgroundImage: 'none',
        },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          border: '1px solid #e7e5e4',
          backgroundImage: 'none',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500, borderRadius: 6 },
        outlined: { borderColor: '#e7e5e4' },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { fontWeight: 500, borderRadius: 6 },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          borderColor: '#e7e5e4',
          color: '#57534e',
          '&.Mui-selected': {
            backgroundColor: TEAL_50,
            color: TEAL_DARK,
            '&:hover': { backgroundColor: '#d0ebe7' },
          },
        },
      },
    },
    MuiTextField: {
      defaultProps: { variant: 'outlined', size: 'small' },
    },
    MuiOutlinedInput: {
      styleOverrides: { root: { backgroundColor: '#ffffff' } },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            fontWeight: 600,
            color: '#57534e',
            fontSize: '0.78rem',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          },
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: '#1c1917',
          fontSize: '0.78rem',
          padding: '6px 10px',
          borderRadius: 6,
        },
        arrow: { color: '#1c1917' },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { backgroundColor: '#f5f5f4' },
        bar: { borderRadius: 4 },
      },
    },
  },
});

// Re-exported palette constants so component code can reference brand colours
// without copying hex strings (used by Recharts, custom chips, etc.)
export const BRAND_COLORS = {
  teal: TEAL,
  tealDark: TEAL_DARK,
  tealLight: TEAL_LIGHT,
  teal50: TEAL_50,
  coral: CORAL,
  sage: SAGE,
  orange: ORANGE,
};

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>
);
