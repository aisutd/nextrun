import React, { useState } from "react";
import { View } from "react-native";
import { useApp } from "../state/AppState";
import { Role, canRemove, normalizeHandle, validHandle } from "../state/model";
import {
  Avatar,
  Badge,
  Button,
  Card,
  Chips,
  Icon,
  Input,
  Label,
  Ring,
  Row,
  Scene,
  Section,
} from "../components/ui";
import { UploadFootage } from "../components/UploadFootage";
import { ColorField } from "../components/ColorField";
import { gradient, useTheme } from "../theme/theme";
const leaders = [
  ["PlayerOne", 248],
  ["Hooper23", 231],
  ["BallsLife", 219],
  ["CourtVision", 201],
  ["BucketsOnly", 190],
];
export function ClubHub() {
  const { s, patch } = useApp(),
    t = useTheme(),
    [name, setName] = useState(""),
    [school, setSchool] = useState(""),
    [c1, setC1] = useState("#FF6A00"),
    [c2, setC2] = useState("#0A0A0A"),
    [comment, setComment] = useState("");
  if (s.club && s.inClub) return <ManagedClub />;
  function create() {
    if (!name.trim()) return;
    patch({
      club: {
        name: name.trim(),
        school: school.trim() || "Independent",
        c1,
        c2,
        members: [
          { handle: "@Hooper23", role: "Admin" },
          { handle: "@BallsLife", role: "Member" },
        ],
        posts: [
          {
            handle: "@Hooper23",
            role: "Admin",
            kind: "Announcement",
            text: "Welcome to the club! First run this Saturday.",
          },
        ],
      },
      role: "Owner",
      clubTab: "Feed",
      inClub: true,
    });
  }
  return (
    <>
      {s.club && (
        <Card>
          <Row between>
            <View>
              <Label style={{ fontFamily: "Inter_600" }}>{s.club.name}</Label>
              <Label kind="mono">Your club · {s.role}</Label>
            </View>
            <Button
              primary
              onPress={() => patch({ inClub: true })}
              style={{ width: 90, marginBottom: 0 }}
            >
              Open
            </Button>
          </Row>
        </Card>
      )}
      {s.club ? (
        <ClubBanner />
      ) : (
        <Scene
          name="comm"
          style={{
            borderRadius: 24,
            paddingVertical: 20,
            paddingHorizontal: 18,
            marginBottom: 12,
            borderWidth: 1,
            borderColor: t.border,
            boxShadow: t.shadow,
          }}
        >
          <Row between>
            <View>
              <Label kind="hud">Club hub</Label>
              <Label kind="h2" style={{ marginTop: 4 }}>
                Westwood Ballers
              </Label>
              <Label kind="muted" style={{ marginTop: 4 }}>
                12 members · Dallas, TX
              </Label>
            </View>
            <View style={{ alignItems: "center" }}>
              <Ring value={72} size={84} />
              <Label kind="mono" style={{ marginTop: 2 }}>
                WIN RATE
              </Label>
            </View>
          </Row>
        </Scene>
      )}
      <Chips
        values={["Leaderboard", "Activity", "Tournaments", "Setup"]}
        value={s.hubTab}
        onChange={(hubTab) => patch({ hubTab })}
      />
      {s.hubTab === "Setup" ? (
        <>
          <Card>
            <Label kind="h3">Register your club</Label>
            <Input
              accessibilityLabel="Club name"
              placeholder="Club name"
              value={name}
              onChangeText={setName}
              style={{ marginTop: 10 }}
            />
            <Input
              accessibilityLabel="Associated school"
              placeholder="Associated school"
              value={school}
              onChangeText={setSchool}
            />
            <Row style={{ marginBottom: 12 }}>
              <Label kind="muted" style={{ flex: 1 }}>
                Club colors
              </Label>
              <ColorField
                label="Primary club color"
                value={c1}
                onChange={setC1}
              />
              <ColorField
                label="Secondary club color"
                value={c2}
                onChange={setC2}
              />
            </Row>
            <Button primary onPress={create}>
              Create club
            </Button>
          </Card>
          <UploadFootage />
        </>
      ) : s.hubTab === "Leaderboard" ? (
        <>
          <Card>
            <Label kind="h3">Top 5 this week</Label>
            {leaders.map(([n, score], i) => (
              <Row
                key={n}
                style={{
                  paddingVertical: 10,
                  borderTopWidth: 1,
                  borderColor: t.border,
                }}
              >
                <Label
                  kind="h3"
                  style={{
                    width: 22,
                    fontSize: 16,
                    color: i < 3 ? t.accent : t.muted,
                  }}
                >
                  {i + 1}
                </Label>
                <Avatar size={36} style={{ borderRadius: 12 }} />
                <Label style={{ flex: 1 }}>{n}</Label>
                <Label kind="mono" style={{ fontSize: 13, color: t.text }}>
                  {score}
                </Label>
              </Row>
            ))}
          </Card>
          <Section>Team stats</Section>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
            {[
              ["Points", "84.3", "+6.2%"],
              ["Rebounds", "36.7", "+4.8%"],
              ["Assists", "18.2", "+3.9%"],
              ["Steals", "9.4", "+2.7%"],
            ].map(([k, v, p]) => (
              <Card
                key={k}
                style={{ width: "48%", flexGrow: 1, marginBottom: 0 }}
              >
                <Label kind="mono">{k.toUpperCase()}</Label>
                <Label kind="h1" style={{ marginTop: 4, marginBottom: 2 }}>
                  {v}
                </Label>
                <Label
                  style={{
                    fontSize: 12,
                    fontFamily: "Inter_600",
                    color: "#22c55e",
                  }}
                >
                  ▲ {p}
                </Label>
              </Card>
            ))}
          </View>
        </>
      ) : s.hubTab === "Tournaments" ? (
        <Card>
          <Label kind="h3">Summer Showdown</Label>
          <Label kind="muted" style={{ marginTop: 6, marginBottom: 10 }}>
            8 teams · single elimination
          </Label>
          {[
            "Quarterfinals — Sat 4 PM",
            "Semifinals — Sun 2 PM",
            "Finals — Sun 6 PM",
          ].map((x) => (
            <Row
              key={x}
              style={{
                marginTop: 8,
                padding: 12,
                borderRadius: 14,
                backgroundColor: t.surface2,
                borderWidth: 1,
                borderColor: t.border,
              }}
            >
              <View
                style={{
                  width: 3,
                  height: 18,
                  borderRadius: 2,
                  backgroundColor: t.accent,
                }}
              />
              <Label style={{ fontSize: 13 }}>{x}</Label>
            </Row>
          ))}
        </Card>
      ) : (
        <Card>
          <Label kind="h3">Recent activity</Label>
          {[
            ["Game vs. Rivals", "W 78 – 62", "Apr 26", "ball"],
            ["Practice Session", "+3 new records", "Apr 24", "bolt"],
          ].map(([title, info, date, icon]) => (
            <Row
              key={title}
              style={{
                paddingVertical: 10,
                borderTopWidth: 1,
                borderColor: t.border,
              }}
            >
              <View
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: 12,
                  backgroundColor: t.accent,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon name={icon} size={20} color="#fff" />
              </View>
              <View style={{ flex: 1 }}>
                <Label style={{ fontFamily: "Inter_600" }}>{title}</Label>
                <Label kind="mono">{info}</Label>
              </View>
              <Label kind="mono">{date}</Label>
            </Row>
          ))}
        </Card>
      )}
      {["Activity", "Leaderboard"].includes(s.hubTab) && (
        <Card style={{ marginTop: 12 }}>
          <Label kind="h3">Club feed</Label>
          {s.feed.map((p, i) => (
            <Row key={i} style={{ marginTop: 12, alignItems: "flex-start" }}>
              <Avatar size={38} style={{ borderRadius: 12 }} />
              <View style={{ flex: 1 }}>
                <Label style={{ fontFamily: "Inter_600", fontSize: 13 }}>
                  {p.name}
                </Label>
                <Label kind="muted">{p.text}</Label>
              </View>
            </Row>
          ))}
          <Row style={{ marginTop: 14 }}>
            <Input
              accessibilityLabel="Write a comment"
              placeholder="Write a comment"
              value={comment}
              onChangeText={setComment}
              style={{ flex: 1, marginBottom: 0 }}
            />
            <Button
              primary
              style={{ width: 80, marginBottom: 0 }}
              onPress={() => {
                if (comment.trim()) {
                  patch({
                    feed: [
                      { name: s.handle || "You", text: comment.trim() },
                      ...s.feed,
                    ],
                  });
                  setComment("");
                }
              }}
            >
              Post
            </Button>
          </Row>
        </Card>
      )}
    </>
  );
}
function ClubBanner() {
  const { s } = useApp();
  if (!s.club) return null;
  return (
    <View
      style={[
        { padding: 20, borderRadius: 20, marginBottom: 12 },
        gradient(`linear-gradient(135deg,${s.club.c1},${s.club.c2})`),
      ]}
    >
      <Row>
        <Avatar
          initial={s.club.name[0].toUpperCase()}
          size={52}
          style={{ backgroundColor: "rgba(0,0,0,.35)" }}
        />
        <View style={{ flex: 1 }}>
          <Label kind="h2" style={{ color: "#fff" }}>
            {s.club.name}
          </Label>
          <Label style={{ fontSize: 13, color: "#fff", marginTop: 3 }}>
            {s.club.school} · {s.club.members.length + 1} members
          </Label>
        </View>
      </Row>
    </View>
  );
}
function ManagedClub() {
  const { s, patch } = useApp(),
    t = useTheme(),
    [post, setPost] = useState(""),
    [invite, setInvite] = useState("");
  const c = s.club!;
  const admin = s.role !== "Member",
    all = [{ handle: s.handle || "@you", role: s.role }, ...c.members];
  function postNow() {
    if (!post.trim()) return;
    patch({
      club: {
        ...c,
        posts: [
          {
            handle: s.handle || "@you",
            role: s.role,
            kind: admin ? s.postKind : "Post",
            text: post.trim(),
          },
          ...c.posts,
        ],
      },
    });
    setPost("");
  }
  return (
    <>
      <Button
        onPress={() => patch({ inClub: false })}
        style={{
          alignSelf: "flex-start",
          paddingVertical: 8,
          paddingHorizontal: 14,
          marginBottom: 12,
        }}
      >
        ‹ Club Hub
      </Button>
      <ClubBanner />
      <Label kind="mono" style={{ marginBottom: 6 }}>
        VIEWING AS
      </Label>
      <Chips
        values={["Owner", "Admin", "Member"]}
        value={s.role}
        onChange={(role) => patch({ role: role as Role })}
      />
      <Chips
        values={["Feed", "Members", "Leaderboard", "Upload"]}
        value={s.clubTab}
        onChange={(clubTab) => patch({ clubTab, note: "" })}
      />
      {s.clubTab === "Feed" ? (
        <>
          <Card>
            {admin && (
              <Chips
                values={["Post", "Announcement", "Event"]}
                value={s.postKind}
                onChange={(postKind) => patch({ postKind })}
              />
            )}
            <Row>
              <Input
                accessibilityLabel="Club post"
                placeholder={
                  admin
                    ? "Share an update, announcement or event"
                    : "Write a post"
                }
                value={post}
                onChangeText={setPost}
                onSubmitEditing={postNow}
                style={{ flex: 1, marginBottom: 0 }}
              />
              <Button
                primary
                style={{ width: 80, marginBottom: 0 }}
                onPress={postNow}
              >
                Post
              </Button>
            </Row>
          </Card>
          {c.posts.map((p, i) => (
            <Card
              key={i}
              style={p.kind !== "Post" ? { borderColor: t.accent } : undefined}
            >
              <Row between>
                <Row style={{ flex: 1, flexWrap: "wrap" }}>
                  <Avatar initial={p.handle.replace("@", "")[0]} size={38} />
                  <Label style={{ fontFamily: "Inter_600", fontSize: 13 }}>
                    {p.handle}
                  </Label>
                  <Badge>{p.role}</Badge>
                </Row>
                {admin && (
                  <Button
                    label="Delete post"
                    style={{
                      paddingVertical: 4,
                      paddingHorizontal: 10,
                      borderRadius: 999,
                      marginBottom: 0,
                    }}
                    onPress={() =>
                      patch({
                        club: {
                          ...c,
                          posts: c.posts.filter((_, j) => j !== i),
                        },
                      })
                    }
                  >
                    ✕
                  </Button>
                )}
              </Row>
              {p.kind !== "Post" && (
                <View style={{ alignSelf: "flex-start", marginTop: 8 }}>
                  <Badge>{p.kind.toUpperCase()}</Badge>
                </View>
              )}
              <Label style={{ marginTop: 8 }}>{p.text}</Label>
            </Card>
          ))}
          {!c.posts.length && (
            <Label kind="muted" style={{ textAlign: "center", marginTop: 14 }}>
              No posts yet. Start the conversation.
            </Label>
          )}
        </>
      ) : s.clubTab === "Members" ? (
        <>
          <Card>
            {admin ? (
              <>
                <Label kind="h3">Invite players</Label>
                <Row style={{ marginTop: 10 }}>
                  <Input
                    accessibilityLabel="Invite handle"
                    placeholder="@handle"
                    value={invite}
                    onChangeText={setInvite}
                    style={{ flex: 1, marginBottom: 0 }}
                  />
                  <Button
                    primary
                    style={{ width: 90, marginBottom: 0 }}
                    onPress={() => {
                      if (!validHandle(invite)) {
                        patch({
                          note: "Handles are 3–16 letters, numbers or underscores.",
                        });
                        return;
                      }
                      const h = normalizeHandle(invite);
                      patch({
                        club: {
                          ...c,
                          members: [
                            ...c.members,
                            { handle: h, role: "Member" },
                          ],
                        },
                        note: "Invite sent to " + h,
                      });
                      setInvite("");
                    }}
                  >
                    Invite
                  </Button>
                </Row>
                {!!s.note && (
                  <Label kind="mono" style={{ marginTop: 8 }}>
                    {s.note}
                  </Label>
                )}
              </>
            ) : (
              <Label kind="muted">
                Only owners and admins can invite players.
              </Label>
            )}
          </Card>
          <Card>
            <Label kind="h3">Members · {all.length}</Label>
            {all.map((m, i) => (
              <Row
                key={`${m.handle}-${i}`}
                style={{
                  paddingVertical: 10,
                  borderTopWidth: 1,
                  borderColor: t.border,
                  flexWrap: "wrap",
                }}
              >
                <Avatar initial={m.handle.replace("@", "")[0]} size={38} />
                <Label style={{ flex: 1 }}>
                  {m.handle}
                  {i === 0 ? " (you)" : ""}
                </Label>
                <Badge>{m.role}</Badge>
                {i > 0 && s.role === "Owner" && (
                  <Button
                    style={{
                      paddingVertical: 5,
                      paddingHorizontal: 8,
                      borderRadius: 999,
                      marginBottom: 0,
                    }}
                    textStyle={{ fontSize: 12 }}
                    onPress={() =>
                      patch({
                        club: {
                          ...c,
                          members: c.members.map((p, j) =>
                            j === i - 1
                              ? {
                                  ...p,
                                  role: p.role === "Admin" ? "Member" : "Admin",
                                }
                              : p,
                          ),
                        },
                      })
                    }
                  >
                    {m.role === "Admin" ? "Demote" : "Promote"}
                  </Button>
                )}
                {i > 0 && canRemove(s.role, m.role) && (
                  <Button
                    label={`Remove ${m.handle}`}
                    style={{
                      paddingVertical: 5,
                      paddingHorizontal: 8,
                      borderRadius: 999,
                      marginBottom: 0,
                    }}
                    textStyle={{ fontSize: 12 }}
                    onPress={() =>
                      patch({
                        club: {
                          ...c,
                          members: c.members.filter((_, j) => j !== i - 1),
                        },
                      })
                    }
                  >
                    ✕
                  </Button>
                )}
              </Row>
            ))}
          </Card>
        </>
      ) : s.clubTab === "Leaderboard" ? (
        <Card>
          <Label kind="h3">Top players this week</Label>
          {all.map((m, i) => (
            <Row
              key={`${m.handle}-${i}`}
              style={{
                paddingVertical: 10,
                borderTopWidth: 1,
                borderColor: t.border,
              }}
            >
              <Label
                style={{ fontFamily: "Inter_600", width: 18, color: t.accent }}
              >
                {i + 1}
              </Label>
              <Avatar initial={m.handle.replace("@", "")[0]} size={38} />
              <Label style={{ flex: 1 }}>{m.handle}</Label>
              <Label kind="mono" style={{ color: t.text }}>
                {248 - i * 19}
              </Label>
            </Row>
          ))}
        </Card>
      ) : (
        <UploadFootage />
      )}
    </>
  );
}
