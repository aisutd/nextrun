import React from "react";
import { Text, View } from "react-native";
/** The source's conic four-color G, clipped into four native quadrants. */
export function GoogleMark() {
  return (
    <View style={{ width: 18, height: 21 }}>
      {["#ea4335", "#fbbc05", "#34a853", "#4285f4"].map((color, i) => (
        <View
          key={color}
          style={{
            position: "absolute",
            left: i === 0 || i === 1 ? 9 : 0,
            top: i === 1 || i === 2 ? 10.5 : 0,
            width: 9,
            height: 10.5,
            overflow: "hidden",
          }}
        >
          <Text
            style={{
              position: "absolute",
              left: i === 0 || i === 1 ? -9 : 0,
              top: i === 1 || i === 2 ? -10.5 : 0,
              width: 18,
              height: 21,
              fontFamily: "Inter_600",
              fontSize: 18,
              color,
              lineHeight: 21,
              textAlign: "center",
            }}
          >
            G
          </Text>
        </View>
      ))}
    </View>
  );
}
