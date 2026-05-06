/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          light: '#EF5350',
          DEFAULT: '#D32F2F',
          dark: '#B71C1C',
        },
        background: '#FAF9F6',
      },
    },
  },
  plugins: [],
}
