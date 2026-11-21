import React from "react";
import { Platform, TextStyle, View } from "react-native";
import { Label } from "./ui";
export function OutlineNumber({
  text,
  font,
  fill,
}: {
  text: string;
  font: string;
  fill: string;
}) {
  const style: TextStyle = { fontFamily: font, fontSize: 28, lineHeight: 34 };
  if (Platform.OS === "web")
    return (
      <Label
        style={[
          style,
          { color: "transparent", WebkitTextStroke: "1.2px #fff" } as TextStyle,
        ]}
      >
        {text}
      </Label>
    );
  return (
    <View>
      <Label style={[style, { color: "transparent" }]}>{text}</Label>
      {[
        [-1.2, 0],
        [1.2, 0],
        [0, -1.2],
        [0, 1.2],
        [-0.85, -0.85],
        [0.85, 0.85],
        [-0.85, 0.85],
        [0.85, -0.85],
      ].map(([x, y], i) => (
        <Label
          key={i}
          style={[
            style,
            { position: "absolute", left: x, top: y, color: "#fff" },
          ]}
        >
          {text}
        </Label>
      ))}
      <Label
        style={[style, { position: "absolute", left: 0, top: 0, color: fill }]}
      >
        {text}
      </Label>
    </View>
  );
}
