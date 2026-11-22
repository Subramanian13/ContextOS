/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#18212f',
        canvas: '#f4f6f8',
        brand: { 50: '#eef6ff', 100: '#d9eafe', 600: '#1667c8', 700: '#1057ad', 900: '#14365d' },
      },
      boxShadow: { panel: '0 1px 2px rgba(16,24,40,.04), 0 8px 24px rgba(16,24,40,.04)' },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
