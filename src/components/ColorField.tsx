import React, { useState } from "react";
import { Pressable, View } from "react-native";
import { Input } from "./ui";
import { useTheme } from "../theme/theme";
/** Native counterpart of input[type=color]; accepts precise HTML hex values. */
export function ColorField({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (c: string) => void;
  label: string;
}) {
  const [open, show] = useState(false),
    [draft, set] = useState(value),
    t = useTheme();
  return (
    <View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        onPress={() => {
          set(value);
          show(!open);
        }}
        style={{
          width: 42,
          height: 28,
          borderWidth: 1,
          borderColor: t.border,
          padding: 3,
          backgroundColor: t.surface2,
        }}
      >
        <View style={{ flex: 1, backgroundColor: value }} />
      </Pressable>
      {open && (
        <Input
          accessibilityLabel={`${label} hex value`}
          value={draft}
          onChangeText={(v) => {
            set(v);
            if (/^#[0-9a-f]{6}$/i.test(v)) onChange(v);
          }}
          autoCapitalize="none"
          maxLength={7}
          style={{
            width: 105,
            marginTop: 6,
            marginBottom: 0,
            padding: 6,
            fontSize: 12,
          }}
        />
      )}
    </View>
  );
}
