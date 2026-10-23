"use client";

import { useState, type FormEvent } from "react";
import { PrimaryButton } from "./primary-button";
import { SurfaceCard } from "./surface-card";

const initialPosts = [
  { name: "PlayerOne", text: "Game today was crazy! 🔥" },
  { name: "Hooper23", text: "Who is in for Saturday 5v5?" },
];

export function ClubFeed({ avatars = false, light = false }: { avatars?: boolean; light?: boolean }) {
  const [posts, setPosts] = useState(initialPosts);
  const [comment, setComment] = useState("");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!comment.trim()) return;
    setPosts([...posts, { name: "You", text: comment.trim() }]);
    setComment("");
  }
  return <SurfaceCard light={light} gradientAngle={160.1041053599147} className="flex flex-col gap-[12px] p-[14px]">
    <h2 className={`relative font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Club feed</h2>
    <div aria-live="polite" className="relative flex flex-col gap-[12px]">{posts.map((post, index) => <div key={index} className="flex min-h-[38px] items-start gap-[10px]">
      {avatars ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={light ? "/figma/activity-light-avatar.svg" : "/figma/activity-avatar.svg"} alt="" width={38} height={38} className="block shrink-0 max-w-none" />
      ) : <span aria-hidden="true" className={`size-[38px] shrink-0 rounded-[12px] border bg-[radial-gradient(circle_32.689px_at_50%_30%,rgba(255,106,0,0.6),#1a0a00_78%)] ${light ? "border-blaze/45" : "border-blaze/[0.38]"}`} />}
      <div className="min-w-0 pt-px text-[13px]"><p className={`leading-[16px] font-bold ${light ? "text-[#0a0a0a]" : "text-white"}`}>{post.name}</p><p className={`mt-[-0.5px] leading-[18.85px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{post.text}</p></div>
    </div>)}</div>
    <form onSubmit={submit} className="relative flex h-[50px] items-center gap-[10px] pt-[2px]">
      <input aria-label="Write a comment" placeholder="Write a comment" value={comment} onChange={event => setComment(event.target.value)} className={`h-[46px] min-w-0 flex-1 rounded-[14px] border px-[13px] text-[15px] leading-[18px] font-medium placeholder:text-[#757575] ${light ? "border-[#e7e8ec] bg-[#f2f3f5] text-[#0a0a0a]" : "border-white/[0.09] bg-[#17171b] text-white"}`} />
      <PrimaryButton type="submit" className={`shrink-0 ${light ? "!w-[67.14px] !shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_6px_18px_rgba(255,106,0,0.35)]" : "!w-[67px]"}`}>Post</PrimaryButton>
    </form>
  </SurfaceCard>;
}
