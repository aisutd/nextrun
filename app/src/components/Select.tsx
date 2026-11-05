import React, { useState } from "react";
import { Modal, Pressable, ScrollView, View } from "react-native";
import { Label, Row } from "./ui";
import { useTheme } from "../theme/theme";
export function Select({
  value,
  values,
  onChange,
  label,
}: {
  value: string;
  values: string[];
  onChange: (v: string) => void;
  label: string;
}) {
  const [open, show] = useState(false),
    t = useTheme();
  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        onPress={() => show(true)}
        style={{
          padding: 13,
          borderRadius: 14,
          borderWidth: 1,
          borderColor: t.border,
          backgroundColor: t.surface2,
        }}
      >
        <Row between>
          <Label style={{ fontFamily: "Inter_500", fontSize: 15 }}>
            {value}
          </Label>
          <Label>⌄</Label>
        </Row>
      </Pressable>
      <Modal
        visible={open}
        transparent
        animationType="fade"
        onRequestClose={() => show(false)}
      >
        <Pressable
          onPress={() => show(false)}
          style={{
            flex: 1,
            backgroundColor: "rgba(0,0,0,.5)",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
          }}
        >
          <View
            style={{
              width: "100%",
              maxWidth: 350,
              maxHeight: "70%",
              padding: 12,
              borderRadius: 16,
              backgroundColor: t.surface,
            }}
          >
            <ScrollView>
              {values.map((v) => (
                <Pressable
                  key={v}
                  accessibilityRole="button"
                  onPress={() => {
                    onChange(v);
                    show(false);
                  }}
                  style={{
                    padding: 14,
                    borderRadius: 10,
                    backgroundColor: value === v ? t.surface2 : "transparent",
                  }}
                >
                  <Label>{v}</Label>
                </Pressable>
              ))}
            </ScrollView>
          </View>
        </Pressable>
      </Modal>
    </>
  );
}
