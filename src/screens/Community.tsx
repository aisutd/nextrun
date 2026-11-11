import React, { useState } from "react";
import { View, Image, Share, Pressable } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useApp } from "../state/AppContext";
import { keepImage } from "../state/storage";
import {
  Art,
  Badge,
  Button,
  Card,
  Chip,
  Chips,
  Icon,
  Input,
  Row,
  Segments,
  T,
} from "../components/ui";
import universities from "../data/universities.json";
import { assets } from "../theme/assets";
import { UploadFootage } from "./Camera";
import { accent } from "../theme/tokens";
function SchoolLogo({ id, size = 52 }: { id: string; size?: number }) {
  const u = universities.find((u) => u.id === id);
  return (
    <View
      style={{
        width: size,
        height: Math.round(size * 0.62),
        borderRadius: 10,
        borderWidth: 1,
        borderColor: "rgba(255,106,0,.35)",
        backgroundColor: "#0b0b0d",
        overflow: "hidden",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {u?.asset ? (
        <Image
          source={assets["uni-" + id]}
          resizeMode="contain"
          style={{ width: "100%", height: "100%" }}
        />
      ) : (
        <Icon name="club" color="#9aa0ab" size={26} />
      )}
    </View>
  );
}
export function ClubScreen() {
  const { data, setData, colors, notify } = useApp(),
    [tab, setTab] = useState("Find"),
    [inside, setInside] = useState(!!data.club),
    [query, setQuery] = useState(""),
    [name, setName] = useState(""),
    [school, setSchool] = useState(""),
    [feedTab, setFeedTab] = useState("Feed"),
    [kind, setKind] = useState("Post"),
    [post, setPost] = useState(""),
    [invite, setInvite] = useState(""),
    [note, setNote] = useState("");
  const c = data.club,
    admin = data.role !== "Member";
  function create(u?: (typeof universities)[number]) {
    const club = {
      name: u ? u.short + " Hoops" : name.trim(),
      university: u ? u.name : school || "Independent",
      city: u?.city || "",
      uid: u?.id || "",
      c1: u?.c1 || accent,
      c2: u?.c2 || "#0A0A0A",
      members: [],
      posts: [],
    };
    if (!club.name) return;
    setData((d) => ({ ...d, club, role: "Owner" }));
    setInside(true);
    notify(
      "Club ready: " + club.name,
      "You are the first member. Invite your teammates with their handles.",
      "club",
    );
  }
  async function logo() {
    const r = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 1,
    });
    if (!r.canceled) {
      const uri = await keepImage(r.assets[0].uri);
      setData((d) => ({
        ...d,
        club: d.club ? { ...d.club, logo: uri } : null,
      }));
    }
  }
  if (c && inside)
    return (
      <>
        <Button
          style={{ alignSelf: "flex-start", paddingVertical: 8 }}
          onPress={() => setInside(false)}
        >
          ‹ Club Hub
        </Button>
        <Card>
          <Row style={{ gap: 14 }}>
            {c.logo ? (
              <Image
                source={{ uri: c.logo }}
                style={{ width: 64, height: 64, borderRadius: 18 }}
              />
            ) : (
              <SchoolLogo id={c.uid} size={64} />
            )}
            <View style={{ flex: 1 }}>
              <T kind="strong" style={{ fontSize: 16 }}>
                {c.name}
              </T>
              <T kind="mono">{c.university}</T>
              {admin && (
                <Chip
                  style={{ marginTop: 8, alignSelf: "flex-start" }}
                  onPress={logo}
                >
                  {c.logo ? "Change logo" : "Add club logo"}
                </Chip>
              )}
            </View>
          </Row>
          <View
            style={{
              marginTop: 12,
              paddingTop: 12,
              borderTopWidth: 1,
              borderTopColor: colors.border,
            }}
          >
            <T kind="h3" style={{ fontSize: 14 }}>
              Join club link
            </T>
            <T kind="mono" style={{ marginTop: 2, marginBottom: 8 }}>
              Anyone who opens it can join {c.name}.
            </T>
            <Button
              primary
              style={{ margin: 0 }}
              onPress={() =>
                Share.share({
                  message: "Join " + c.name + " on NextRun",
                  url:
                    "nextrun://join?data=" +
                    encodeURIComponent(
                      JSON.stringify({
                        n: c.name,
                        s: c.university,
                        c1: c.c1,
                        c2: c.c2,
                        by: data.handle,
                      }),
                    ),
                })
              }
            >
              Generate join link
            </Button>
          </View>
        </Card>
        <Card style={{ backgroundColor: c.c1, padding: 20 }}>
          <Row>
            <SchoolLogo id={c.uid} size={64} />
            <View style={{ flex: 1 }}>
              <T kind="h2" style={{ color: "#fff" }}>
                {c.name}
              </T>
              <T style={{ color: "#fff", fontSize: 13, marginTop: 3 }}>
                {c.university} · {c.members.length + 1} members
              </T>
            </View>
            <Chip
              onPress={() => {
                setData((d) => ({ ...d, club: null }));
                setInside(false);
              }}
            >
              Leave
            </Chip>
          </Row>
        </Card>
        <T kind="mono" style={{ marginBottom: 6 }}>
          VIEWING AS
        </T>
        <Segments
          options={["Owner", "Admin", "Member"]}
          value={data.role}
          onChange={(role) => setData((d) => ({ ...d, role }))}
        />
        <Segments
          options={["Feed", "Members", "Leaderboard", "Upload"]}
          value={feedTab}
          onChange={setFeedTab}
        />
        {feedTab === "Feed" ? (
          <>
            <Card>
              {admin && (
                <Segments
                  options={["Post", "Announcement", "Event"]}
                  value={kind}
                  onChange={setKind}
                />
              )}
              <Row>
                <View style={{ flex: 1 }}>
                  <Input
                    value={post}
                    onChangeText={setPost}
                    placeholder={
                      admin
                        ? "Share an update, announcement or event"
                        : "Write a post"
                    }
                    style={{ marginBottom: 0 }}
                  />
                </View>
                <Button
                  primary
                  style={{ width: 80, margin: 0 }}
                  onPress={() => {
                    if (!post.trim()) return;
                    setData((d) => ({
                      ...d,
                      club: d.club
                        ? {
                            ...d.club,
                            posts: [
                              {
                                id: String(Date.now()),
                                handle: d.handle,
                                role: d.role,
                                kind: d.role === "Member" ? "Post" : kind,
                                text: post.trim(),
                              },
                              ...d.club.posts,
                            ],
                          }
                        : null,
                    }));
                    setPost("");
                  }}
                >
                  Post
                </Button>
              </Row>
            </Card>
            {c.posts.length ? (
              c.posts.map((p) => (
                <Card
                  key={p.id}
                  style={{
                    borderColor: p.kind !== "Post" ? accent : colors.border,
                  }}
                >
                  <Row style={{ justifyContent: "space-between" }}>
                    <T kind="strong">{p.handle}</T>
                    <Badge>{p.role}</Badge>
                    {admin && (
                      <Chip
                        onPress={() =>
                          setData((d) => ({
                            ...d,
                            club: d.club
                              ? {
                                  ...d.club,
                                  posts: d.club.posts.filter(
                                    (x) => x.id !== p.id,
                                  ),
                                }
                              : null,
                          }))
                        }
                      >
                        ✕
                      </Chip>
                    )}
                  </Row>
                  {p.kind !== "Post" && <Badge>{p.kind.toUpperCase()}</Badge>}
                  <T style={{ marginTop: 8 }}>{p.text}</T>
                </Card>
              ))
            ) : (
              <T kind="muted" style={{ textAlign: "center", marginTop: 14 }}>
                No posts yet. Start the conversation.
              </T>
            )}
          </>
        ) : feedTab === "Members" ? (
          <>
            <Card>
              {admin ? (
                <>
                  <T kind="h3">Invite players</T>
                  <Row style={{ marginTop: 10 }}>
                    <View style={{ flex: 1 }}>
                      <Input
                        placeholder="@handle"
                        value={invite}
                        onChangeText={setInvite}
                        style={{ marginBottom: 0 }}
                      />
                    </View>
                    <Button
                      primary
                      style={{ width: 90, margin: 0 }}
                      onPress={() => {
                        const h = invite.trim().replace(/^@/, "");
                        if (!/^[a-z0-9_]{3,16}$/i.test(h)) {
                          setNote(
                            "Handles are 3–16 letters, numbers or underscores.",
                          );
                          return;
                        }
                        setData((d) => ({
                          ...d,
                          club: d.club
                            ? {
                                ...d.club,
                                members: [
                                  ...d.club.members,
                                  { handle: "@" + h, role: "Member" },
                                ],
                              }
                            : null,
                        }));
                        setNote("Invite sent to @" + h);
                        setInvite("");
                      }}
                    >
                      Invite
                    </Button>
                  </Row>
                  {!!note && (
                    <T kind="mono" style={{ marginTop: 8 }}>
                      {note}
                    </T>
                  )}
                </>
              ) : (
                <T kind="muted">Only owners and admins can invite players.</T>
              )}
            </Card>
            <Card>
              <T kind="h3">Members · {c.members.length + 1}</T>
              {[{ handle: data.handle, role: data.role }, ...c.members].map(
                (m, i) => (
                  <Row
                    key={m.handle}
                    style={{
                      paddingVertical: 10,
                      borderTopWidth: 1,
                      borderTopColor: colors.border,
                    }}
                  >
                    <T style={{ flex: 1 }}>
                      {m.handle}
                      {i === 0 ? " (you)" : ""}
                    </T>
                    <Badge>{m.role}</Badge>
                    {i > 0 && data.role === "Owner" && (
                      <Chip
                        onPress={() =>
                          setData((d) => ({
                            ...d,
                            club: d.club
                              ? {
                                  ...d.club,
                                  members: d.club.members.map((x, j) =>
                                    j === i - 1
                                      ? {
                                          ...x,
                                          role:
                                            x.role === "Admin"
                                              ? "Member"
                                              : "Admin",
                                        }
                                      : x,
                                  ),
                                }
                              : null,
                          }))
                        }
                      >
                        {m.role === "Admin" ? "Demote" : "Promote"}
                      </Chip>
                    )}
                    {i > 0 && admin && (
                      <Chip
                        onPress={() =>
                          setData((d) => ({
                            ...d,
                            club: d.club
                              ? {
                                  ...d.club,
                                  members: d.club.members.filter(
                                    (_, j) => j !== i - 1,
                                  ),
                                }
                              : null,
                          }))
                        }
                      >
                        ✕
                      </Chip>
                    )}
                  </Row>
                ),
              )}
            </Card>
          </>
        ) : feedTab === "Upload" ? (
          <UploadFootage />
        ) : (
          <Card>
            <T kind="h3">Club leaderboard</T>
            {[{ handle: data.handle }, ...c.members].map((m, i) => (
              <Row
                key={m.handle}
                style={{
                  paddingVertical: 10,
                  borderTopWidth: 1,
                  borderTopColor: colors.border,
                }}
              >
                <T style={{ width: 18, color: accent }}>{i + 1}</T>
                <T style={{ flex: 1 }}>{m.handle}</T>
                <T kind="mono">
                  {i === 0
                    ? data.games.reduce((a, g) => a + g.xp, 0) + " PXP"
                    : "—"}
                </T>
              </Row>
            ))}
          </Card>
        )}
      </>
    );
  const words = query.toLowerCase().trim().split(/\s+/),
    list = universities.filter((u) =>
      words.every((w) =>
        (u.name + " " + u.short + " " + u.city).toLowerCase().includes(w),
      ),
    );
  return (
    <>
      {c && (
        <Card>
          <Row style={{ justifyContent: "space-between" }}>
            <View>
              <T kind="strong">{c.name}</T>
              <T kind="mono">Your club · {data.role}</T>
            </View>
            <Button
              primary
              style={{ width: 90, margin: 0 }}
              onPress={() => setInside(true)}
            >
              Open
            </Button>
          </Row>
        </Card>
      )}
      <View
        style={{
          borderRadius: 24,
          padding: 20,
          marginBottom: 12,
          overflow: "hidden",
          borderWidth: 1,
          borderColor: colors.edge,
        }}
      >
        <Art
          name="city"
          style={{
            position: "absolute",
            inset: 0,
            width: undefined,
            height: undefined,
          }}
        />
        <T kind="hud">Club hub</T>
        <T kind="h2" style={{ marginTop: 4 }}>
          Find your club
        </T>
        <T kind="muted" style={{ marginTop: 4 }}>
          Search for a club to join, or start your own.
        </T>
      </View>
      <Segments options={["Find", "Create"]} value={tab} onChange={setTab} />
      {tab === "Find" ? (
        <>
          <Input
            placeholder="Search universities (e.g. Baylor, DBU)"
            value={query}
            onChangeText={setQuery}
          />
          <T kind="mono" style={{ marginHorizontal: 2, marginBottom: 8 }}>
            Pick your university to start or join its NextRun club. Not listed?
            You can add it.
          </T>
          {list.map((u) => (
            <Card key={u.id}>
              <Row style={{ gap: 12 }}>
                <SchoolLogo id={u.id} />
                <View style={{ flex: 1 }}>
                  <T kind="strong">{u.name}</T>
                  <T kind="mono">{u.city}</T>
                </View>
                <Chip onPress={() => create(u)}>Select</Chip>
              </Row>
            </Card>
          ))}
          {query.length >= 2 && !list.length && (
            <Card>
              <T kind="strong">Add "{query}"</T>
              <T kind="mono">
                Not in the collection. Add it with a generic logo.
              </T>
              <Button
                onPress={() => {
                  setName(query);
                  setSchool(query);
                  setTab("Create");
                }}
              >
                Add
              </Button>
            </Card>
          )}
          <Button onPress={() => setTab("Create")}>
            Or create a custom club
          </Button>
        </>
      ) : (
        <Card>
          <T kind="h3">Register your club</T>
          <Input
            placeholder="Club name"
            value={name}
            onChangeText={setName}
            style={{ marginTop: 10 }}
          />
          <Input
            placeholder="University (search or type any)"
            value={school}
            onChangeText={setSchool}
          />
          <T kind="muted" style={{ marginBottom: 12 }}>
            Club colors
          </T>
          <Row style={{ marginBottom: 12 }}>
            <View
              style={{
                width: 42,
                height: 30,
                borderRadius: 6,
                backgroundColor: accent,
              }}
            />
            <View
              style={{
                width: 42,
                height: 30,
                borderRadius: 6,
                backgroundColor: "#0A0A0A",
              }}
            />
          </Row>
          <Button primary disabled={!name.trim()} onPress={() => create()}>
            Create club
          </Button>
        </Card>
      )}
    </>
  );
}
export function FriendsScreen() {
  const { data, setData, colors } = useApp(),
    [tab, setTab] = useState("Active"),
    [filter, setFilter] = useState("All"),
    [query, setQuery] = useState(""),
    [handle, setHandle] = useState(""),
    [error, setError] = useState(""),
    [selected, setSelected] = useState(""),
    [message, setMessage] = useState("");
  const f = data.friends.find((f) => f.name === selected) || data.friends[0];
  function add() {
    const h = handle.trim().replace(/^@/, ""),
      key = (s: string) => s.toLowerCase().replace(/^@/, "");
    if (!/^[a-z0-9_]{3,16}$/i.test(h)) {
      setError("Handles are 3 to 16 letters, numbers or underscores.");
      return;
    }
    if (key(h) === key(data.handle)) {
      setError("That is your own handle.");
      return;
    }
    if (data.friends.some((f) => key(f.name) === key(h))) {
      setError("Already in your crew.");
      return;
    }
    setData((d) => ({
      ...d,
      friends: [
        ...d.friends,
        {
          name: "@" + h,
          date: new Date().toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          }),
        },
      ],
    }));
    setHandle("");
    setError("");
  }
  return (
    <>
      <View
        style={{
          minHeight: 136,
          borderRadius: 22,
          paddingTop: 34,
          paddingHorizontal: 18,
          paddingBottom: 16,
          overflow: "hidden",
          marginBottom: 12,
          borderWidth: 1,
          borderColor: colors.border,
        }}
      >
        <Art
          name="court"
          style={{
            position: "absolute",
            inset: 0,
            width: undefined,
            height: undefined,
          }}
        />
        <Art
          name="crew"
          resizeMode="contain"
          style={{
            position: "absolute",
            inset: 0,
            width: undefined,
            height: undefined,
          }}
        />
        <T kind="hud">Squad</T>
        <T kind="h2" style={{ marginTop: 2 }}>
          The Crew
        </T>
        <T kind="mono">{data.friends.length} friends</T>
      </View>
      <Card>
        <Row style={{ gap: 8 }}>
          <View style={{ flex: 1 }}>
            <Input
              placeholder="Add a friend by handle (@name)"
              value={handle}
              onChangeText={setHandle}
              maxLength={17}
              style={{ margin: 0 }}
            />
          </View>
          <Button primary style={{ width: 84, margin: 0 }} onPress={add}>
            Add
          </Button>
        </Row>
        <T
          kind="mono"
          style={{ marginTop: 8, color: error ? "#ef4444" : undefined }}
        >
          {error ||
            "Friend requests are not connected yet, so friends are added on this device."}
        </T>
      </Card>
      <Card>
        <T kind="h3">Friend request link</T>
        <T kind="mono" style={{ marginTop: 2 }}>
          Send it to a teammate. Opening it offers to add you.
        </T>
        <Button
          primary
          style={{ marginTop: 10, marginBottom: 0 }}
          onPress={() =>
            Share.share({
              message: "Add " + data.handle + " on NextRun",
              url: "nextrun://friend?handle=" + encodeURIComponent(data.handle),
            })
          }
        >
          Generate my link
        </Button>
      </Card>
      <Input
        placeholder="Search friends"
        value={query}
        onChangeText={setQuery}
      />
      <Segments
        options={["Active", "Messages", "Rivalry"]}
        value={tab}
        onChange={setTab}
      />
      {tab === "Active" ? (
        <>
          <Chips
            options={["All", "Requests"]}
            value={filter}
            onChange={setFilter}
          />
          {filter === "Requests" ? (
            <Card>
              <T kind="muted" style={{ textAlign: "center" }}>
                No pending requests.
              </T>
            </Card>
          ) : data.friends.length ? (
            data.friends
              .filter((f) => f.name.toLowerCase().includes(query.toLowerCase()))
              .map((f) => (
                <Card key={f.name} style={{ paddingVertical: 11 }}>
                  <Row>
                    <View
                      style={{
                        width: 46,
                        height: 46,
                        borderRadius: 15,
                        overflow: "hidden",
                        backgroundColor: "#1a0a00",
                      }}
                    >
                      <Art name="avatar" />
                    </View>
                    <View style={{ flex: 1 }}>
                      <T kind="strong">{f.name}</T>
                      <T kind="mono">Added {f.date}</T>
                    </View>
                    <Chip
                      onPress={() =>
                        setData((d) => ({
                          ...d,
                          friends: d.friends.filter((x) => x.name !== f.name),
                        }))
                      }
                    >
                      ✕
                    </Chip>
                  </Row>
                </Card>
              ))
          ) : (
            <Card>
              <T kind="muted" style={{ textAlign: "center" }}>
                No friends yet. Add a teammate by handle above.
              </T>
            </Card>
          )}
        </>
      ) : tab === "Messages" ? (
        f ? (
          <>
            <Chips
              options={data.friends.map((f) => f.name)}
              value={f.name}
              onChange={setSelected}
            />
            <Card>
              <T
                kind="strong"
                style={{
                  paddingBottom: 10,
                  marginBottom: 10,
                  borderBottomWidth: 1,
                  borderBottomColor: colors.border,
                }}
              >
                {f.name}
              </T>
              {(data.messages[f.name] || []).map((m, i) => (
                <View
                  key={i}
                  style={{
                    maxWidth: "78%",
                    paddingVertical: 9,
                    paddingHorizontal: 12,
                    borderRadius: 16,
                    marginBottom: 8,
                    alignSelf: "flex-end",
                    backgroundColor: accent,
                  }}
                >
                  <T style={{ color: "#fff", fontSize: 13 }}>{m}</T>
                </View>
              ))}
              {!data.messages[f.name]?.length && (
                <T kind="muted" style={{ marginBottom: 10 }}>
                  No messages yet.
                </T>
              )}
              <Row>
                <View style={{ flex: 1 }}>
                  <Input
                    placeholder={"Message " + f.name}
                    value={message}
                    onChangeText={setMessage}
                    style={{ margin: 0 }}
                  />
                </View>
                <Button
                  primary
                  style={{ width: 70, margin: 0 }}
                  onPress={() => {
                    if (message.trim()) {
                      setData((d) => ({
                        ...d,
                        messages: {
                          ...d.messages,
                          [f.name]: [
                            ...(d.messages[f.name] || []),
                            message.trim(),
                          ],
                        },
                      }));
                      setMessage("");
                    }
                  }}
                >
                  Send
                </Button>
              </Row>
              <T kind="mono" style={{ marginTop: 8 }}>
                Messages stay on this device for now.
              </T>
            </Card>
          </>
        ) : (
          <Card>
            <T kind="muted" style={{ textAlign: "center" }}>
              Add a friend to start a conversation.
            </T>
          </Card>
        )
      ) : data.friends.length ? (
        data.friends.map((f) => {
          const games = data.games.filter((g) =>
              g.teams[1].some(
                (p) => p.n.toLowerCase() === f.name.toLowerCase(),
              ),
            ),
            w = games.filter((g) => g.res === "W").length,
            l = games.filter((g) => g.res === "L").length;
          return (
            <Card key={f.name} style={{ alignItems: "center" }}>
              <T kind="hud">Head to head</T>
              <Row style={{ marginVertical: 14 }}>
                <T>You</T>
                <T kind="h1" style={{ fontSize: 42, color: accent }}>
                  {w} – {l}
                </T>
                <T>{f.name}</T>
              </Row>
              <T kind="muted" style={{ textAlign: "center" }}>
                {games.length
                  ? `${games.length} games played.`
                  : `No games against ${f.name} yet. Put them on the opposing team when you log a game.`}
              </T>
            </Card>
          );
        })
      ) : (
        <Card>
          <T kind="muted" style={{ textAlign: "center" }}>
            Add a friend, then log games where they play on the other team to
            build a head to head record.
          </T>
        </Card>
      )}
    </>
  );
}
