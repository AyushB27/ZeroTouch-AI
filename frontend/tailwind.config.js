/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#f0f4ff',
          100: '#dbe4ff',
          200: '#bfcfff',
          300: '#93abff',
          400: '#6080ff',
          500: '#3355ff',
          600: '#1a33f5',
          700: '#1328e0',
          800: '#1522b5',
          900: '#172191',
          950: '#111457',
        },
      },
    },
  },
  plugins: [],
}
