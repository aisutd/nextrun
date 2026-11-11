import React, { useState } from "react";
import { Image, View, Pressable } from "react-native";
import { useApp } from "../state/AppContext";
import { T, Art, Row } from "./ui";
import { assets } from "../theme/assets";
import design from "../data/design.json";
import { nrEval } from "../state/progression";
import { nrAvg } from "../state/mastery";
import type { CardOptions } from "../state/types";
export function TitleBadge({
  name,
  size = 46,
  rank,
  locked = false,
}: {
  name: string;
  size?: number;
  rank?: number;
  locked?: boolean;
}) {
  return (
    <View style={{ width: size, height: size, opacity: locked ? 0.5 : 1 }}>
      <Image
        source={assets[`badge-${name}`]}
        style={{
          width: size,
          height: size,
          borderRadius: size * 0.24,
          borderWidth: Math.max(1.5, size * 0.035),
          borderColor: locked ? "#6b6f7a" : "#FF6A00",
        }}
      />
      {rank !== undefined && (
        <View
          style={{
            position: "absolute",
            right: -size * 0.06,
            bottom: -size * 0.06,
            borderRadius: size * 0.17,
            backgroundColor: "#0b0b0e",
            paddingHorizontal: size * 0.07,
            borderWidth: 1.5,
            borderColor: "#FF6A00",
          }}
        >
          <T
            style={{
              fontSize: size * 0.22,
              color: "#fff",
              fontFamily: "Montserrat-800",
            }}
          >
            {locked ? "?" : rank === 10 ? "X" : rank}
          </T>
        </View>
      )}
    </View>
  );
}
export function PlayerCard({
  options,
  mini = false,
  forceFront = false,
  flipped,
  onFlip,
}: {
  flipped?: boolean;
  onFlip?: () => void;
  options?: CardOptions;
  mini?: boolean;
  forceFront?: boolean;
}) {
  const { data, title, overall } = useApp(),
    [localFlip, setFlip] = useState(false),
    flip = flipped ?? localFlip,
    c = options || {
      ...data.card,
      shape: "Standard",
      style: "Orange",
      font: "Montserrat",
      name: data.handle,
      num: "24",
      pos: data.position || "PG",
      image: "",
    },
    sh =
      design.shapes[c.shape as keyof typeof design.shapes] ||
      design.shapes.Standard,
    nm = c.name || data.handle || "@playerone",
    avg = nrAvg(data.games),
    font =
      c.font === "Montserrat"
        ? "Montserrat-Italic-800"
        : c.font === "Inter"
          ? "Inter-600"
          : c.font === "JetBrains Mono"
            ? "JetBrainsMono-500"
            : c.font.replace(/ /g, "") +
              (c.font === "Russo One"
                ? "-400"
                : c.font === "Bebas Neue"
                  ? "-400"
                  : "-700");
  const stats: [
    [string | number, string],
    [string | number, string],
    [string | number, string],
    [string | number, string],
    [string | number, string],
    [string | number, string],
  ] = [
    [avg?.fg != null ? avg.fg.toFixed(1) + "%" : "—", "FG"],
    [avg?.tp != null ? avg.tp.toFixed(1) + "%" : "—", "3PT"],
    [nrEval(data.games).tot.mvp, "MVP"],
    [avg?.ppg != null ? avg.ppg.toFixed(1) : "—", "PPG"],
    [avg?.apg != null ? avg.apg.toFixed(1) : "—", "APG"],
    [avg?.rpg != null ? avg.rpg.toFixed(1) : "—", "RPG"],
  ];
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={
        flip ? "Show front of player card" : "Show player card stats"
      }
      onPress={() => {
        if (!forceFront) {
          if (onFlip) onFlip();
          else setFlip(!flip);
        }
      }}
      style={{
        width: mini ? 78 : 224,
        height: mini ? 108 : 310,
        alignSelf: "center",
        marginBottom: mini ? 0 : 14,
      }}
    >
      <View
        style={{
          width: 224,
          height: 310,
          transform: mini
            ? [{ scale: 0.348 }, { translateX: -210 }, { translateY: -290 }]
            : [],
        }}
      >
        <Image
          source={
            assets[`card-${c.style}-${c.shape}-${c.pat}`] ||
            assets["card-Orange-Standard-Hex"]
          }
          style={{ position: "absolute", width: 224, height: 310 }}
        />
        {!flip || forceFront ? (
          <>
            {c.image ? (
              <Image
                source={{ uri: c.image }}
                resizeMode="cover"
                style={{
                  position: "absolute",
                  top: 15,
                  left: 18,
                  width: 188,
                  height: 260,
                  borderRadius: c.shape === "Rounded" ? 32 : 0,
                }}
              />
            ) : (
              <Art
                name="avatar"
                resizeMode="contain"
                style={{
                  position: "absolute",
                  left: 10,
                  bottom: 34,
                  width: 210,
                  height: 210,
                }}
              />
            )}
            <View style={{ position: "absolute", left: sh.ip, top: sh.it }}>
              <T
                style={{
                  fontFamily: font,
                  fontSize: 58,
                  lineHeight: 58 * 0.9,
                  letterSpacing: -2.32,
                  color: "#fff",
                  textShadowColor: "rgba(0,0,0,.4)",
                  textShadowOffset: { width: 0, height: 3 },
                  textShadowRadius: 1,
                }}
              >
                {overall}
              </T>
              <T
                style={{
                  fontFamily: "JetBrainsMono-500",
                  fontSize: 11,
                  letterSpacing: 0.88,
                  backgroundColor: "rgba(10,10,12,.86)",
                  borderLeftWidth: 3,
                  borderLeftColor: c.c1,
                  color: "#fff",
                  paddingVertical: 3,
                  paddingHorizontal: 8,
                  alignSelf: "flex-start",
                  marginTop: 5,
                }}
              >
                {c.pos || "PG"}
              </T>
            </View>
            <View
              style={{ position: "absolute", right: sh.ip, bottom: sh.ib + 66 }}
            >
              {data.games.length ? (
                <TitleBadge name="allstar" size={36} />
              ) : (
                <Image
                  source={assets.crest}
                  style={{ width: 36, height: 36 }}
                />
              )}
            </View>
            <View
              style={{
                position: "absolute",
                left: sh.ip,
                right: sh.ip,
                bottom: sh.ib,
                alignItems: sh.al === "c" ? "center" : "flex-end",
                gap: 3,
              }}
            >
              <T
                numberOfLines={1}
                adjustsFontSizeToFit
                style={{
                  fontFamily: "JetBrainsMono-500",
                  fontSize: 10,
                  color: "#fff",
                  letterSpacing: 1.2,
                  paddingVertical: 4,
                  paddingHorizontal: 9,
                  backgroundColor: "rgba(10,10,12,.82)",
                }}
              >
                #{c.num || "24"} · {title}
              </T>
              <T
                adjustsFontSizeToFit
                numberOfLines={1}
                minimumFontScale={0.3}
                style={{
                  fontFamily: font,
                  fontSize: 26,
                  lineHeight: 28.6,
                  color: "#fff",
                  letterSpacing: 0.52,
                  paddingHorizontal: 11,
                  paddingTop: 3,
                  paddingBottom: 4,
                  borderBottomWidth: 3,
                  borderBottomColor: c.c1,
                  backgroundColor: "rgba(6,6,8,.92)",
                  textTransform: "uppercase",
                }}
              >
                {nm}
              </T>
            </View>
          </>
        ) : (
          <View
            style={{
              position: "absolute",
              left: sh.ip,
              right: sh.ip,
              top: sh.it,
              bottom: sh.ib,
              justifyContent: "center",
              gap: 8,
            }}
          >
            <T
              style={{
                color: "#fff",
                fontFamily: "JetBrainsMono-500",
                fontSize: 8,
                letterSpacing: 1.6,
                textAlign: "center",
              }}
            >
              NEXTRUN · CAREER
            </T>
            <T
              numberOfLines={1}
              adjustsFontSizeToFit
              style={{
                fontFamily: font,
                fontSize: 22,
                color: "#fff",
                textTransform: "uppercase",
                backgroundColor: "#060608",
                padding: 5,
                borderBottomWidth: 3,
                borderBottomColor: c.c1,
              }}
            >
              {nm}
            </T>
            <View className="flex-row flex-wrap gap-1.5">
              {stats.map(([v, k]) => (
                <View
                  key={k}
                  style={{
                    width: "47%",
                    backgroundColor: "rgba(6,6,8,.72)",
                    borderLeftWidth: 3,
                    borderLeftColor: c.c1,
                    paddingVertical: 6,
                    paddingHorizontal: 8,
                  }}
                >
                  <T style={{ fontFamily: font, fontSize: 19, color: "#fff" }}>
                    {v}
                  </T>
                  <T
                    style={{
                      fontFamily: "JetBrainsMono-500",
                      fontSize: 8,
                      letterSpacing: 1.12,
                      color: "#fff",
                    }}
                  >
                    {k}
                  </T>
                </View>
              ))}
            </View>
          </View>
        )}
        {c.frame !== "None" && (
          <Image
            source={assets[`card-frame-${c.shape}-${c.frame}`]}
            style={{ position: "absolute", width: 224, height: 310 }}
          />
        )}
      </View>
    </Pressable>
  );
}
