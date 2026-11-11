module.exports = {
  content: ["./App.tsx", "./src/**/*.{ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: { orange: "#FF6A00" },
      fontFamily: {
        body: ["Inter"],
        heading: ["Montserrat-Italic"],
        mono: ["JetBrainsMono"],
      },
    },
  },
  plugins: [],
};
