module.exports = {
  content: ["./App.tsx", "./src/**/*.{ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      fontFamily: {
        body: ["Inter_400"],
        semibold: ["Inter_600"],
        heading: ["Montserrat_800Italic"],
        mono: ["JetBrainsMono_500"],
      },
    },
  },
  plugins: [],
};
