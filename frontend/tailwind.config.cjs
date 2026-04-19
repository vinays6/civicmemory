/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'on-surface-variant':        '#c2c6d6',
        'surface-container-low':     '#1c1b1b',
        'surface':                   '#131313',
        'surface-container':         '#201f1f',
        'primary-container':         '#4d8eff',
        'on-background':             '#e5e2e1',
        'on-surface':                '#e5e2e1',
        'surface-bright':            '#3a3939',
        'secondary':                 '#ffb3ad',
        'outline-variant':           '#424754',
        'outline':                   '#8c909f',
        'surface-container-highest': '#353534',
        'surface-tint':              '#adc6ff',
        'surface-container-high':    '#2a2a2a',
        'surface-dim':               '#131313',
        'surface-container-lowest':  '#0e0e0e',
        'primary':                   '#adc6ff',
        'on-primary':                '#002e6a',
        'tertiary':                  '#f7be1d',
        'surface-variant':           '#353534',
        'primary-fixed-dim':         '#adc6ff',
        'tertiary-fixed-dim':        '#f7be1d',
      },
      borderRadius: {
        'DEFAULT': '0.125rem',
        'lg':      '0.25rem',
        'xl':      '0.5rem',
        'full':    '0.75rem',
      },
      fontFamily: {
        display:  ['Fraunces', 'ui-serif', 'Georgia', 'serif'],
        sans:     ['Geist', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono:     ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        // Legacy aliases kept for any old callsites
        headline: ['Fraunces', 'ui-serif', 'Georgia', 'serif'],
        body:     ['Geist', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        label:    ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'editorial':       '0 1px 0 0 rgba(255,255,255,0.04) inset, 0 20px 40px -24px rgba(0,0,0,0.8)',
        'editorial-hover': '0 1px 0 0 rgba(173,198,255,0.12) inset, 0 24px 48px -20px rgba(0,0,0,0.9)',
      },
    },
  },
  plugins: [],
}
