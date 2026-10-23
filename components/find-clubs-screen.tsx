import { ScreenShell } from "./screen-shell";
import { PrimaryLink } from "./primary-button";
import { ProgressDots } from "./progress-dots";
import { ClubListCard, type ClubListing } from "./club-list-card";

const clubs: readonly ClubListing[] = [
  { id: "ut-dallas-hoops", name: "UT Dallas Hoops", distance: "2.4" },
  { id: "smu-club-ball", name: "SMU Club Ball", distance: "6.1" },
  { id: "dallas-pickup-crew", name: "Dallas Pickup Crew", distance: "3.3" },
];

export function FindClubsScreen() {
  return (
    <ScreenShell artwork="/figma/clubs-court.svg" label="Find local clubs">
      <div className="relative h-[840px] w-full overflow-hidden">
        <h1 className="absolute inset-x-[16px] top-[48px] font-display text-[28px] leading-[30.8px] font-extrabold tracking-[-0.28px] text-white italic">Find local clubs</h1>
        <p className="absolute inset-x-[16px] top-[78.22px] text-[13px] leading-[18.85px] text-muted">Allow location to discover campus clubs and pickup<br className="max-[350px]:hidden" /> groups near you.</p>
        <div className="absolute inset-x-[16px] top-[130.48px]"><ClubListCard clubs={clubs} /></div>
        <div className="absolute inset-x-[16px] top-[317.48px]"><PrimaryLink href="/player/recording-tutorial">Continue</PrimaryLink></div>
        <div className="absolute inset-x-[16px] top-[380.48px]"><ProgressDots activeStep={4} /></div>
      </div>
    </ScreenShell>
  );
}
