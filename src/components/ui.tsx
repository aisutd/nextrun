import React, { useEffect, useRef } from "react";
import {
  Text,
  View,
  Pressable,
  TextInput,
  ScrollView,
  Image,
  Animated,
  AccessibilityInfo,
  StyleSheet,
  type TextProps,
  type ViewProps,
  type StyleProp,
  type ViewStyle,
  type TextInputProps,
} from "react-native";
import { useApp } from "../state/AppContext";
import { accent, typography as f } from "../theme/tokens";
import { playSound } from "../state/sound";
import { assets } from "../theme/assets";
export function T({
  kind = "body",
  style,
  ...props
}: TextProps & {
  kind?: "body" | "muted" | "mono" | "hud" | "h1" | "h2" | "h3" | "strong";
}) {
  const { colors } = useApp();
  const styles = {
    body: { fontFamily: f.body, fontSize: 14, color: colors.text },
    muted: {
      fontFamily: f.body,
      fontSize: 13,
      lineHeight: 18.85,
      color: colors.muted,
    },
    mono: { fontFamily: f.mono, fontSize: 11, color: colors.muted },
    hud: {
      fontFamily: f.mono,
      fontSize: 10,
      letterSpacing: 2.2,
      color: accent,
      textTransform: "uppercase" as const,
    },
    h1: {
      fontFamily: f.heading,
      fontSize: 28,
      lineHeight: 30.8,
      letterSpacing: -0.28,
      color: colors.text,
    },
    h2: {
      fontFamily: f.heading,
      fontSize: 20,
      letterSpacing: -0.2,
      color: colors.text,
    },
    h3: {
      fontFamily: f.heading,
      fontSize: 15,
      letterSpacing: -0.15,
      color: colors.text,
    },
    strong: { fontFamily: f.semibold, fontSize: 14, color: colors.text },
  };
  return (
    <Text {...props} allowFontScaling={false} style={[styles[kind], style]} />
  );
}
export function Row({ style, ...props }: ViewProps) {
  return (
    <View className="flex-row items-center gap-2.5" style={style} {...props} />
  );
}
export function Card({ style, ...props }: ViewProps) {
  const { colors, data } = useApp();
  return (
    <View
      className="mb-3 rounded-[18px] border p-3.5"
      style={[
        {
          backgroundColor: colors.surface,
          borderColor: data.theme === "dark" ? colors.edge : colors.border,
          boxShadow:
            data.theme === "light"
              ? "0 10px 28px rgba(18,20,30,.07), 0 1px 2px rgba(18,20,30,.06)"
              : "0 0 26px rgba(255,106,0,.10)",
        },
        style,
      ]}
      {...props}
    />
  );
}
export function Button({
  children,
  onPress,
  primary = false,
  disabled = false,
  style,
  label,
}: {
  children: React.ReactNode;
  onPress?: () => void;
  primary?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  label?: string;
}) {
  const { colors } = useApp();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={() => {
        playSound();
        onPress?.();
      }}
      style={({ pressed }) => [
        {
          minHeight: 48,
          padding: 14,
          borderRadius: 16,
          borderWidth: 1,
          borderColor: primary ? accent : colors.border,
          backgroundColor: primary ? accent : colors.surface,
          marginBottom: 10,
          alignItems: "center",
          justifyContent: "center",
          opacity: disabled ? 0.4 : 1,
          transform: [{ scale: pressed ? 0.97 : 1 }],
          boxShadow: primary
            ? "0 6px 18px rgba(255,106,0,.3)"
            : "0 1px 2px rgba(18,20,30,.06)",
        },
        style,
      ]}
    >
      {primary && (
        <Image
          source={assets["primary"]}
          style={[
            StyleSheet.absoluteFill,
            { width: undefined, height: undefined, borderRadius: 15 },
          ]}
        />
      )}
      <Row style={{ justifyContent: "center" }}>
        {typeof children === "string" ? (
          <T
            style={{
              fontFamily: f.semibold,
              fontSize: 15,
              color: primary ? "#fff" : colors.text,
              textAlign: "center",
            }}
          >
            {children}
          </T>
        ) : (
          children
        )}
      </Row>
    </Pressable>
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
  const { data, colors } = useApp();
  return (
    <Image
      accessibilityIgnoresInvertColors
      source={assets[`icon-${name}-${data.theme}`] || assets["icon-ball-light"]}
      style={{ width: size, height: size, tintColor: color || colors.text }}
    />
  );
}
export function IconButton({
  name,
  onPress,
  label,
  badge,
}: {
  name: string;
  onPress: () => void;
  label: string;
  badge?: number;
}) {
  const { colors } = useApp();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={() => {
        playSound();
        onPress?.();
      }}
      style={{
        width: 42,
        height: 44,
        borderRadius: 14,
        borderWidth: 1,
        borderColor: colors.border,
        backgroundColor: colors.surface,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Icon name={name} />
      {!!badge && (
        <View
          style={{
            position: "absolute",
            right: -6,
            top: -6,
            backgroundColor: accent,
            borderRadius: 20,
            paddingHorizontal: 7,
            paddingVertical: 2,
          }}
        >
          <T kind="mono" style={{ color: "#fff", fontSize: 10 }}>
            {badge}
          </T>
        </View>
      )}
    </Pressable>
  );
}
export function Input({
  label,
  style,
  ...props
}: TextInputProps & { label?: string }) {
  const { colors } = useApp();
  return (
    <View style={{ flexShrink: 1 }}>
      {label && (
        <T kind="mono" style={{ marginBottom: 6 }}>
          {label}
        </T>
      )}
      <TextInput
        {...props}
        accessibilityLabel={
          props.accessibilityLabel || label || props.placeholder
        }
        placeholderTextColor={colors.muted}
        autoCapitalize={props.autoCapitalize || "none"}
        style={[
          {
            minHeight: 46,
            borderWidth: 1,
            borderColor: colors.border,
            backgroundColor: colors.secondary,
            color: colors.text,
            borderRadius: 14,
            padding: 13,
            fontFamily: f.medium,
            fontSize: 15,
            marginBottom: 10,
          },
          style,
        ]}
      />
    </View>
  );
}
export function Chip({
  children,
  selected = false,
  onPress,
  style,
}: {
  children: React.ReactNode;
  selected?: boolean;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useApp();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={() => {
        playSound();
        onPress?.();
      }}
      style={({ pressed }) => [
        {
          minHeight: 44,
          borderRadius: 999,
          borderWidth: 1,
          borderColor: selected ? accent : colors.border,
          backgroundColor: selected ? "rgba(255,106,0,.10)" : colors.surface,
          paddingHorizontal: 14,
          paddingVertical: 10,
          justifyContent: "center",
          alignItems: "center",
          transform: [{ scale: pressed ? 0.96 : 1 }],
        },
        style,
      ]}
    >
      <T
        style={{
          fontFamily: f.semibold,
          fontSize: 12,
          color: selected ? accent : colors.text,
        }}
      >
        {children}
      </T>
    </Pressable>
  );
}
export function Chips({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange: (s: string) => void;
}) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{
        gap: 8,
        paddingVertical: 8,
        paddingHorizontal: 6,
      }}
      style={{ marginHorizontal: -6, marginTop: -8, marginBottom: 4 }}
    >
      {options.map((o) => (
        <Chip key={o} selected={o === value} onPress={() => onChange(o)}>
          {o}
        </Chip>
      ))}
    </ScrollView>
  );
}
export function Segments({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange: (s: string) => void;
}) {
  const { colors } = useApp();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={{ marginBottom: 12, flexGrow: 0 }}
    >
      <Row
        style={{
          gap: 0,
          borderWidth: 1,
          borderColor: colors.edge,
          borderRadius: 12,
          overflow: "hidden",
          backgroundColor: colors.surface,
        }}
      >
        {options.map((o) => (
          <Pressable
            key={o}
            accessibilityRole="tab"
            accessibilityState={{ selected: value === o }}
            onPress={() => onChange(o)}
            style={{
              minHeight: 44,
              paddingHorizontal: 20,
              paddingVertical: 8,
              justifyContent: "center",
              backgroundColor: o === value ? accent : "transparent",
            }}
          >
            <T
              kind="mono"
              style={{
                fontSize: 13,
                letterSpacing: 0.78,
                color: o === value ? "#fff" : colors.muted,
              }}
            >
              {o}
            </T>
          </Pressable>
        ))}
      </Row>
    </ScrollView>
  );
}
export function Badge({ children }: { children: React.ReactNode }) {
  return (
    <View
      style={{
        paddingVertical: 3,
        paddingHorizontal: 8,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: "rgba(255,106,0,.35)",
        backgroundColor: "rgba(255,106,0,.15)",
        alignSelf: "flex-start",
      }}
    >
      <T kind="mono" style={{ fontSize: 10, color: accent }}>
        {children}
      </T>
    </View>
  );
}
export function Bar({ value = 0 }: { value?: number }) {
  const { colors } = useApp();
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: Math.round(value * 100) }}
      style={{
        height: 7,
        backgroundColor: colors.track,
        borderRadius: 8,
        overflow: "hidden",
        marginTop: 8,
      }}
    >
      <View
        style={{
          width: `${Math.max(0, Math.min(1, value)) * 100}%`,
          height: "100%",
          backgroundColor: accent,
          borderRadius: 8,
        }}
      />
    </View>
  );
}
export function Section({ children }: { children: React.ReactNode }) {
  return (
    <Row
      style={{ marginTop: 20, marginBottom: 10, marginHorizontal: 2, gap: 8 }}
    >
      <View
        style={{
          width: 3,
          height: 15,
          borderRadius: 2,
          backgroundColor: accent,
        }}
      />
      <T kind="h3">{children}</T>
    </Row>
  );
}
export function Stats({
  items,
  columns = 3,
}: {
  items: [string | number, string][];
  columns?: number;
}) {
  const { colors } = useApp();
  return (
    <View className="flex-row flex-wrap gap-2">
      {items.map(([v, k]) => (
        <View
          key={k}
          style={{
            width: `${(100 - (columns - 1) * 2.25) / columns}%`,
            flexGrow: 1,
            backgroundColor: colors.secondary,
            borderColor: colors.border,
            borderWidth: 1,
            borderRadius: 14,
            padding: 10,
            alignItems: "center",
          }}
        >
          <T kind="h2" style={{ fontSize: 22 }}>
            {v}
          </T>
          <T kind="muted" style={{ fontSize: 11, textAlign: "center" }}>
            {k}
          </T>
        </View>
      ))}
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
  const { colors } = useApp();
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityLabel={label}
      accessibilityState={{ checked: value }}
      onPress={onChange}
      style={{ width: 46, height: 44, justifyContent: "center" }}
    >
      <View
        style={{
          width: 46,
          height: 26,
          borderRadius: 26,
          borderWidth: 1,
          borderColor: colors.border,
          backgroundColor: value ? accent : colors.secondary,
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
            backgroundColor: value ? "#fff" : colors.muted,
          }}
        />
      </View>
    </Pressable>
  );
}
export function Dots({ step, total = 7 }: { step: number; total?: number }) {
  const { colors } = useApp();
  return (
    <Row style={{ justifyContent: "center", gap: 6, marginVertical: 14 }}>
      {Array.from({ length: total }, (_, i) => (
        <View
          key={i}
          style={{
            width: i === step ? 22 : 7,
            height: 7,
            borderRadius: 7,
            backgroundColor: i === step ? accent : colors.border,
          }}
        />
      ))}
    </Row>
  );
}
export function Logo() {
  return (
    <Row style={{ gap: 0 }}>
      <T kind="h2" style={{ fontSize: 24 }}>
        Next
        <T kind="h2" style={{ fontSize: 24, color: accent }}>
          Run
        </T>
      </T>
      <Icon name="ball" size={22} color={accent} />
    </Row>
  );
}
export function Art({
  name,
  style,
  resizeMode = "cover",
}: {
  name: string;
  style?: StyleProp<ViewStyle>;
  resizeMode?: "cover" | "contain" | "stretch";
}) {
  const { data } = useApp();
  return (
    <Image
      source={assets[`${name}-${data.theme}`] || assets[name]}
      resizeMode={resizeMode}
      style={[{ width: "100%", height: "100%" }, style] as any}
    />
  );
}
export function Float({ children }: { children: React.ReactNode }) {
  const a = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    let loop: Animated.CompositeAnimation | undefined;
    AccessibilityInfo.isReduceMotionEnabled().then((reduced) => {
      if (reduced) return;
      loop = Animated.loop(
        Animated.sequence([
          Animated.timing(a, {
            toValue: -3,
            duration: 1700,
            useNativeDriver: true,
          }),
          Animated.timing(a, {
            toValue: 0,
            duration: 1700,
            useNativeDriver: true,
          }),
        ]),
      );
      loop.start();
    });
    return () => loop?.stop();
  }, [a]);
  return (
    <Animated.View style={{ transform: [{ translateY: a }] }}>
      {children}
    </Animated.View>
  );
}
export function Slider({
  value,
  min,
  max,
  onChange,
  label,
}: {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
  label: string;
}) {
  const { colors } = useApp(),
    width = useRef(1);
  function move(x: number) {
    onChange(
      Math.max(min, Math.min(max, min + ((max - min) * x) / width.current)),
    );
  }
  return (
    <View
      accessibilityRole="adjustable"
      accessibilityLabel={label}
      accessibilityValue={{ min, max, now: value }}
      accessibilityActions={[{ name: "increment" }, { name: "decrement" }]}
      onAccessibilityAction={(e) =>
        onChange(
          Math.max(
            min,
            Math.min(
              max,
              value + (e.nativeEvent.actionName === "increment" ? 1 : -1),
            ),
          ),
        )
      }
      onLayout={(e) => (width.current = e.nativeEvent.layout.width)}
      onStartShouldSetResponder={() => true}
      onMoveShouldSetResponder={() => true}
      onResponderGrant={(e) => move(e.nativeEvent.locationX)}
      onResponderMove={(e) => move(e.nativeEvent.locationX)}
      style={{ height: 44, justifyContent: "center", marginVertical: 6 }}
    >
      <View
        style={{ height: 10, backgroundColor: colors.track, borderRadius: 10 }}
      />
      <View
        pointerEvents="none"
        style={{
          position: "absolute",
          left: 0,
          width: `${((value - min) / (max - min)) * 100}%`,
          height: 10,
          backgroundColor: accent,
          borderRadius: 10,
        }}
      />
      <View
        pointerEvents="none"
        style={{
          position: "absolute",
          left: `${((value - min) / (max - min)) * 100}%`,
          marginLeft: -13,
          width: 26,
          height: 26,
          borderRadius: 26,
          backgroundColor: "#fff",
          borderWidth: 4,
          borderColor: accent,
        }}
      />
    </View>
  );
}
