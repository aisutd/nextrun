"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { PrimaryButton } from "./primary-button";
import { ProgressDots } from "./progress-dots";

/** Local draft only. Permanent handle reservation requires the account service. */
export function PlayerHandleForm() {
  const router = useRouter();
  const [handle, setHandle] = useState("");
  const valid = /^[A-Za-z0-9_]{3,16}$/.test(handle);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (valid) {
      sessionStorage.setItem("nextrun.playerHandleDraft", handle);
      router.push("/player/face-scan");
    }
  }
  return (
    <form onSubmit={submit} className="relative z-0 flex w-full flex-col px-[16px] pt-[47.4px]" aria-labelledby="handle-title">
      <h1 id="handle-title" className="min-h-[62px] font-display text-[28px] leading-[30.8px] font-extrabold tracking-[-0.28px] text-white italic">Create your player<br />handle</h1>
      <p className="mt-[8.19px] text-[13px] leading-[19px] text-muted">This is permanent. You can&apos;t change it later.</p>
      <label htmlFor="player-handle" className="sr-only">Player handle</label>
      <input id="player-handle" name="handle" value={handle} onChange={event => setHandle(event.target.value)} placeholder="@playername" required minLength={3} maxLength={16} pattern="[A-Za-z0-9_]{3,16}" autoComplete="username" autoCapitalize="none" spellCheck={false} aria-describedby="handle-rules" className="mt-[17.85px] h-[46px] w-full rounded-[14px] border border-white/[0.09] bg-[#17171b] px-[13px] py-[13px] text-[15px] leading-[18px] font-medium text-white placeholder:text-[#757575] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blaze" />
      <p id="handle-rules" className="mt-[11px] min-h-[15px] font-mono text-[11px] leading-[15px] text-muted">3–16 characters: letters, numbers, underscore.</p>
      <PrimaryButton type="submit" disabled={!valid} data-figma-destination="3345:3347" className="mt-[13px]">Continue</PrimaryButton>
      <div className="mt-[15px]"><ProgressDots activeStep={2} /></div>
    </form>
  );
}
