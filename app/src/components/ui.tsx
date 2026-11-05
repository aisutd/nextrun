import React, { useEffect, useRef } from "react";
import {
  Animated,
  Image,
  Platform,
  Pressable,
  ScrollView,
  StyleProp,
  StyleSheet,
  Text,
  TextInput,
  TextStyle,
  View,
  ViewStyle,
  TextInputProps,
} from "react-native";
import { useLoop } from "./Motion";
import { useApp } from "../state/AppState";
import { artwork } from "../theme/artwork";
import { gradient, mix, rgba, useTheme } from "../theme/theme";
export function Label({
  children,
  kind = "body",
  style,
  numberOfLines,
}: {
  children?: React.ReactNode;
  kind?: "body" | "muted" | "mono" | "hud" | "h1" | "h2" | "h3";
  style?: StyleProp<TextStyle>;
  numberOfLines?: number;
}) {
  const t = useTheme();
  const variants: Record<string, TextStyle> = {
    body: { fontFamily: "Inter_400", fontSize: 14 },
    muted: {
      fontFamily: "Inter_400",
      fontSize: 13,
      lineHeight: 18.85,
      color: t.muted,
    },
    mono: { fontFamily: "JetBrainsMono_500", fontSize: 11, color: t.muted },
    hud: {
      fontFamily: "JetBrainsMono_500",
      fontSize: 10,
      letterSpacing: 2.2,
      textTransform: "uppercase",
      color: t.accent,
    },
    h1: {
      fontFamily: "Montserrat_800Italic",
      fontSize: 28,
      lineHeight: 30.8,
      letterSpacing: -0.28,
    },
    h2: {
      fontFamily: "Montserrat_800Italic",
      fontSize: 20,
      letterSpacing: -0.2,
    },
    h3: {
      fontFamily: "Montserrat_800Italic",
      fontSize: 15,
      letterSpacing: -0.15,
    },
  };
  return (
    <Text
      numberOfLines={numberOfLines}
      style={[{ color: t.text }, variants[kind], style]}
    >
      {children}
    </Text>
  );
}
export function Row({
  children,
  between = false,
  style,
}: {
  children: React.ReactNode;
  between?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <View
      className="flex-row items-center gap-[10px]"
      style={[between && { justifyContent: "space-between" }, style]}
    >
      {children}
    </View>
  );
}
export function Card({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const t = useTheme();
  return (
    <View
      className="p-[14px] rounded-[18px] mb-3 border"
      style={[
        {
          backgroundColor: t.surface,
          borderColor: t.border,
          boxShadow: t.shadow,
        },
        !t.light &&
          gradient(
            "linear-gradient(160deg,rgba(255,255,255,.05),rgba(255,255,255,.008))",
          ),
        style,
      ]}
    >
      {children}
    </View>
  );
}
export function Icon({
  name,
  size = 22,
  color,
}: {
  name: string;
  size?: number;
  color?: string;
}) {
  const t = useTheme();
  return (
    <Image
      accessibilityIgnoresInvertColors
      source={artwork[`${name}-accent`]}
      style={{ width: size, height: size, tintColor: color || t.accent }}
      resizeMode="contain"
    />
  );
}
export function Button({
  children,
  onPress,
  primary = false,
  disabled = false,
  style,
  textStyle,
  label,
}: {
  children: React.ReactNode;
  onPress?: () => void;
  primary?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
  label?: string;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        {
          padding: 14,
          borderRadius: 16,
          borderWidth: 1,
          borderColor: primary ? t.accent : t.border,
          backgroundColor: primary ? t.accent : t.surface,
          marginBottom: 10,
          boxShadow: primary ? t.glow : t.shadow,
          opacity: disabled ? 0.4 : 1,
          transform: [{ scale: pressed ? 0.97 : 1 }],
        },
        primary &&
          gradient(
            `linear-gradient(180deg,${mix(t.accent, "#ffffff", 0.86)},${t.accent})`,
          ),
        style,
      ]}
    >
      {typeof children === "string" ? (
        <Label
          style={[
            {
              fontFamily: "Inter_600",
              fontSize: 15,
              textAlign: "center",
              color: primary ? t.on : t.text,
            },
            textStyle,
          ]}
        >
          {children}
        </Label>
      ) : (
        children
      )}
    </Pressable>
  );
}
export function IconButton({
  name,
  onPress,
  label,
}: {
  name: string;
  onPress: () => void;
  label: string;
}) {
  return (
    <Button
      onPress={onPress}
      label={label}
      style={{
        width: 42,
        height: 42,
        padding: 0,
        marginBottom: 0,
        borderRadius: 14,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Icon name={name} color={useTheme().text} />
    </Button>
  );
}
export function Input(props: TextInputProps) {
  const t = useTheme();
  const [focus, setFocus] = React.useState(false);
  return (
    <TextInput
      placeholderTextColor={t.muted}
      {...props}
      onFocus={(e) => {
        setFocus(true);
        props.onFocus?.(e);
      }}
      onBlur={(e) => {
        setFocus(false);
        props.onBlur?.(e);
      }}
      style={[
        {
          padding: 13,
          borderRadius: 14,
          borderWidth: 1,
          borderColor: focus ? t.accent : t.border,
          backgroundColor: t.surface2,
          color: t.text,
          fontFamily: "Inter_500",
          fontSize: 15,
          marginBottom: 10,
          minWidth: 0,
        },
        focus && { boxShadow: `0 0 0 3px ${rgba(t.accent, 0.18)}` },
        props.style,
      ]}
    />
  );
}
export function Chips({
  values,
  value,
  onChange,
  compact = false,
  font,
}: {
  values: string[];
  value: string;
  onChange: (v: string) => void;
  compact?: boolean;
  font?: boolean;
}) {
  const t = useTheme();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={{
        marginHorizontal: -6,
        marginTop: compact ? -8 : -6,
        flexGrow: 0,
      }}
      contentContainerStyle={{
        paddingHorizontal: 6,
        paddingTop: compact ? 8 : 6,
        paddingBottom: 12,
        gap: 8,
      }}
    >
      {values.map((v) => (
        <Pressable
          key={v}
          accessibilityRole="button"
          accessibilityState={{ selected: v === value }}
          onPress={() => onChange(v)}
          style={({ pressed }) => [
            {
              paddingVertical: 10,
              paddingHorizontal: 14,
              borderRadius: 999,
              borderWidth: 1,
              borderColor: v === value ? t.accent : t.border,
              backgroundColor:
                v === value
                  ? compact
                    ? rgba(t.accent, 0.1)
                    : t.accent
                  : t.surface,
              boxShadow: v === value ? t.glow : undefined,
              transform: [{ scale: pressed ? 0.96 : 1 }],
            },
            v === value &&
              !compact &&
              gradient(
                `linear-gradient(180deg,${mix(t.accent, "#ffffff", 0.86)},${t.accent})`,
              ),
          ]}
        >
          <Label
            style={{
              fontFamily: font ? fontName(v) : "Inter_600",
              fontSize: 12,
              color:
                v === value && !compact ? t.on : compact ? t.text : t.muted,
            }}
          >
            {v}
          </Label>
        </Pressable>
      ))}
    </ScrollView>
  );
}
export const fontName = (f: string) =>
  ({
    Montserrat: "Montserrat_800",
    Inter: "Inter_600",
    "JetBrains Mono": "JetBrainsMono_500",
    "Bebas Neue": "BebasNeue",
    "Playfair Display": "PlayfairDisplay",
    "Russo One": "RussoOne",
  })[f] || f;
export function Section({ children }: { children: React.ReactNode }) {
  const t = useTheme();
  return (
    <Row
      style={{ marginTop: 20, marginHorizontal: 2, marginBottom: 10, gap: 8 }}
    >
      <View
        style={{
          width: 3,
          height: 15,
          borderRadius: 2,
          backgroundColor: t.accent,
          boxShadow: t.glow,
        }}
      />
      <Label kind="h3">{children}</Label>
    </Row>
  );
}
export function Badge({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<TextStyle>;
}) {
  const t = useTheme();
  return (
    <Label
      kind="mono"
      style={[
        {
          fontSize: 10,
          color: t.accent,
          borderWidth: 1,
          borderColor: rgba(t.accent, 0.35),
          backgroundColor: rgba(t.accent, 0.15),
          borderRadius: 20,
          paddingVertical: 3,
          paddingHorizontal: 8,
          overflow: "hidden",
        },
        style,
      ]}
    >
      {children}
    </Label>
  );
}
export function Progress({ value }: { value: number }) {
  const t = useTheme();
  return (
    <View
      style={{
        height: 7,
        borderRadius: 8,
        backgroundColor: t.surface2,
        marginTop: 8,
        overflow: "hidden",
      }}
    >
      <View
        style={[
          {
            height: "100%",
            width: `${value}%`,
            borderRadius: 8,
            backgroundColor: t.accent,
            boxShadow: t.glow,
          },
          gradient(`linear-gradient(90deg,${t.darkAccent},${t.accent})`),
        ]}
      />
    </View>
  );
}
export function Stats({ value, label }: { value: string; label: string }) {
  const t = useTheme();
  return (
    <View
      className="flex-1 items-center p-[10px] rounded-[14px] border"
      style={{ backgroundColor: t.surface2, borderColor: t.border }}
    >
      <Label kind="h2" style={{ fontSize: 22 }}>
        {value}
      </Label>
      <Label kind="mono" style={{ fontFamily: "Inter_400", fontSize: 11 }}>
        {label}
      </Label>
    </View>
  );
}
export function Toggle({
  value,
  onChange,
  label,
}: {
  value: boolean;
  onChange: () => void;
  label: string;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityLabel={label}
      accessibilityState={{ checked: value }}
      onPress={onChange}
      style={{
        width: 46,
        height: 26,
        borderRadius: 26,
        borderWidth: 1,
        borderColor: t.border,
        backgroundColor: value ? t.accent : t.surface2,
        boxShadow: value ? t.glow : undefined,
      }}
    >
      <View
        style={{
          position: "absolute",
          top: 2,
          left: value ? 22 : 2,
          width: 20,
          height: 20,
          borderRadius: 20,
          backgroundColor: value ? "#fff" : t.muted,
        }}
      />
    </Pressable>
  );
}
export function Avatar({
  size = 46,
  initial,
  style,
}: {
  size?: number;
  initial?: string;
  style?: StyleProp<ViewStyle>;
}) {
  const t = useTheme();
  return (
    <View
      style={[
        {
          width: size,
          height: size,
          borderRadius: initial ? size / 2 : 15,
          flexShrink: 0,
          borderWidth: 1,
          borderColor: rgba(t.accent, 0.38),
          backgroundColor: "#1a0a00",
          alignItems: "center",
          justifyContent: initial ? "center" : "flex-end",
          overflow: "hidden",
        },
        gradient(
          `radial-gradient(circle at 50% 30%,${rgba(t.accent, 0.6)},#1a0a00 78%)`,
        ),
        style,
      ]}
    >
      {initial ? (
        <Label
          style={{
            fontFamily: "Montserrat_800",
            color: "#fff",
            fontSize: size * 0.37,
          }}
        >
          {initial}
        </Label>
      ) : (
        <Image
          source={artwork.avatar}
          style={{
            width: "70%",
            height: "82%",
            tintColor: "#fff",
            opacity: 0.88,
            marginBottom: -3,
          }}
          resizeMode="contain"
        />
      )}
    </View>
  );
}
export function Logo() {
  const t = useTheme();
  return (
    <Row style={{ gap: 4 }}>
      <Label style={{ fontFamily: "Montserrat_800Italic", fontSize: 24 }}>
        Next
        <Label
          style={{
            fontFamily: "Montserrat_800Italic",
            fontSize: 24,
            color: t.accent,
          }}
        >
          Run
        </Label>
      </Label>
      <Image
        source={artwork.run}
        style={{ width: 22, height: 22, tintColor: t.accent }}
        resizeMode="contain"
      />
    </Row>
  );
}
export function Scene({
  name,
  children,
  style,
  overlay = true,
}: {
  name: string;
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  overlay?: boolean;
}) {
  const { s } = useApp(),
    t = useTheme(),
    value = useLoop(22000);
  const aliases: Record<string, string> = { shoes: "court", comm: "city" };
  const key = aliases[name] || name;
  return (
    <View style={[{ position: "relative", overflow: "hidden" }, style]}>
      <Animated.View
        pointerEvents="none"
        style={[
          {
            position: "absolute",
            left: overlay ? "-8%" : 0,
            top: overlay ? "-8%" : 0,
            width: overlay ? "116%" : "100%",
            height: overlay ? "116%" : "100%",
          },
          overlay && {
            transform: [
              {
                scale: value.interpolate({
                  inputRange: [0, 1],
                  outputRange: [1, 1.07],
                }),
              },
            ],
          },
        ]}
      >
        <Image
          source={artwork[`scene-${key}-${s.theme}-base`]}
          style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
          resizeMode="cover"
        />
        <Image
          source={artwork[`scene-${key}-${s.theme}-accent`]}
          style={[
            StyleSheet.absoluteFill,
            { width: "100%", height: "100%", tintColor: t.accent },
          ]}
          resizeMode="cover"
        />
      </Animated.View>
      {overlay && (
        <View
          pointerEvents="none"
          style={[
            StyleSheet.absoluteFill,
            gradient(
              t.light
                ? "linear-gradient(180deg,rgba(255,255,255,.05),rgba(244,243,240,.8))"
                : "linear-gradient(180deg,rgba(0,0,0,.1),rgba(0,0,0,.7))",
            ),
          ]}
        />
      )}
      {children}
    </View>
  );
}
export function Dots({ index, total = 5 }: { index: number; total?: number }) {
  const t = useTheme();
  return (
    <Row style={{ justifyContent: "center", gap: 6, marginVertical: 14 }}>
      {Array.from({ length: total }, (_, i) => (
        <View
          key={i}
          style={{
            width: i === index ? 22 : 7,
            height: 7,
            borderRadius: 7,
            backgroundColor: i === index ? t.accent : t.border,
          }}
        />
      ))}
    </Row>
  );
}
export function Ring({ value, size }: { value: number; size: number }) {
  const t = useTheme();
  return (
    <View
      style={{
        width: size,
        height: size,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Image
        source={artwork["ring-track"]}
        style={[
          StyleSheet.absoluteFill,
          { width: "100%", height: "100%", tintColor: t.ring },
        ]}
      />
      <Image
        source={artwork["ring-72"]}
        style={[
          StyleSheet.absoluteFill,
          { width: "100%", height: "100%", tintColor: t.accent },
        ]}
      />
      <Label
        style={{
          position: "absolute",
          fontFamily: "Montserrat_800Italic",
          fontSize: 28,
        }}
      >
        {value}%
      </Label>
    </View>
  );
}
export function Flip({
  flipped,
  front,
  back,
  style,
}: {
  flipped: boolean;
  front: React.ReactNode;
  back: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const { reducedMotion } = useApp(),
    v = useRef(new Animated.Value(flipped ? 1 : 0)).current;
  useEffect(() => {
    Animated.timing(v, {
      toValue: flipped ? 1 : 0,
      duration: reducedMotion ? 0 : 700,
      useNativeDriver: Platform.OS !== "web",
    }).start();
  }, [flipped, reducedMotion, v]);
  return (
    <View
      style={[
        {
          width: 224,
          height: 310,
          alignSelf: "center",
          marginTop: 4,
          marginBottom: 14,
        },
        style,
      ]}
    >
      <Animated.View
        pointerEvents={flipped ? "none" : "auto"}
        style={[
          StyleSheet.absoluteFill,
          {
            backfaceVisibility: "hidden",
            transform: [
              { perspective: 900 },
              {
                rotateY: v.interpolate({
                  inputRange: [0, 1],
                  outputRange: ["0deg", "180deg"],
                }),
              },
            ],
          },
        ]}
      >
        {front}
      </Animated.View>
      <Animated.View
        pointerEvents={flipped ? "auto" : "none"}
        style={[
          StyleSheet.absoluteFill,
          {
            backfaceVisibility: "hidden",
            transform: [
              { perspective: 900 },
              {
                rotateY: v.interpolate({
                  inputRange: [0, 1],
                  outputRange: ["180deg", "360deg"],
                }),
              },
            ],
          },
        ]}
      >
        {back}
      </Animated.View>
    </View>
  );
}
