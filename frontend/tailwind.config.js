/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'ancient': {
          'wood': '#8B4513',
          'roof': '#4A3728',
          'wall': '#F5E6D3',
          'gold': '#D4AF37',
          'red': '#8B0000',
        },
        'sensor': {
          'good': '#22C55E',
          'warning': '#EAB308',
          'danger': '#EF4444',
        }
      },
      fontFamily: {
        'chinese': ['"Noto Serif SC"', 'serif'],
      },
    },
  },
  plugins: [],
}
