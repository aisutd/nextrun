import React, { useEffect, useRef } from "react";
import { Animated, Easing, Platform, StyleProp, ViewStyle } from "react-native";
import { useApp } from "../state/AppState";
export function useLoop(duration: number) {
  const { reducedMotion } = useApp(),
    value = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    value.setValue(0);
    if (reducedMotion) return;
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(value, {
          toValue: 1,
          duration,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: Platform.OS !== "web",
        }),
        Animated.timing(value, {
          toValue: 0,
          duration,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: Platform.OS !== "web",
        }),
      ]),
    );
    animation.start();
    return () => animation.stop();
  }, [duration, reducedMotion, value]);
  return value;
}
export function Hang({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const value = useLoop(6000);
  const { reducedMotion } = useApp();
  return (
    <Animated.View
      style={[
        style,
        {
          transformOrigin: "50% 0%",
          transform: [
            {
              rotate: value.interpolate({
                inputRange: [0, 1],
                outputRange: reducedMotion
                  ? ["0deg", "0deg"]
                  : ["-.6deg", ".6deg"],
              }),
            },
          ],
        },
      ]}
    >
      {children}
    </Animated.View>
  );
}
export function Pulse({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const value = useLoop(1000);
  return (
    <Animated.View
      style={[
        style,
        {
          opacity: value.interpolate({
            inputRange: [0, 1],
            outputRange: [1, 0.5],
          }),
        },
      ]}
    >
      {children}
    </Animated.View>
  );
}
export function Sweep({
  height,
  children,
  style,
}: {
  height: number;
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const value = useLoop(2000);
  return (
    <Animated.View
      style={[
        style,
        {
          transform: [
            {
              translateY: value.interpolate({
                inputRange: [0, 1],
                outputRange: [0, height],
              }),
            },
          ],
        },
      ]}
    >
      {children}
    </Animated.View>
  );
}
