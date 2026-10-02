/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paytm: {
          primary: '#00baf2', // Paytm Light Blue
          dark: '#002970',    // Paytm Dark Blue
          light: '#f0f8ff',   // Soft blue background
          green: '#21c17a',   // Paytm Success Green
          red: '#ff585d',     // Paytm Error Red
          yellow: '#ffa900',  // Paytm Warning Yellow
        },
      },
    },
  },
  plugins: [],
}
