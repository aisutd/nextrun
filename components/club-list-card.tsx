import { SurfaceCard } from "./surface-card";

export type ClubListing = { id: string; name: string; distance: string };

/** Static listings from Figma. JOIN badges have no defined prototype actions. */
export function ClubListCard({ clubs }: { clubs: readonly ClubListing[] }) {
  return (
    <SurfaceCard aria-labelledby="nearby-clubs-title" className="p-[14px]">
      <h2 id="nearby-clubs-title" className="relative h-[18px] font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] text-white italic">Near you</h2>
      <ul className="relative">
        {clubs.map(club => (
          <li key={club.id} className="flex h-[42px] items-center justify-between border-t border-white/[0.09] py-[10px]">
            <span className="text-[14px] leading-[17px] text-white">{club.name} · {club.distance} mi</span>
            <span className="flex h-[21px] w-[42px] shrink-0 items-center justify-center rounded-[20px] border border-blaze/[0.35] bg-blaze/[0.15] px-[8px] py-[3px] font-mono text-[10px] leading-[13px] font-semibold text-blaze">JOIN</span>
          </li>
        ))}
      </ul>
    </SurfaceCard>
  );
}
