import type {
  AirlineMotive,
  CancellationNotice,
  DelayDuration,
  DeniedBoardingReason,
  DisruptionType,
  MotiveMentioned,
} from "./types";

export const DISRUPTION_TYPES: readonly { value: DisruptionType; label: string }[] = [
  { value: "CANCELLATION",    label: "Cancellation" },
  { value: "DELAY",           label: "Delay" },
  { value: "DENIED_BOARDING", label: "Denied boarding" },
] as const;

export const CANCELLATION_NOTICES: readonly { value: CancellationNotice; label: string }[] = [
  { value: "MORE_THAN_14_DAYS", label: "More than 14 days before the flight" },
  { value: "LESS_THAN_14_DAYS", label: "Less than 14 days before the flight" },
  { value: "ON_FLIGHT_DAY",     label: "On the day of the flight" },
] as const;

export const DELAY_DURATIONS: readonly { value: DelayDuration; label: string }[] = [
  { value: "LESS_THAN_3H",    label: "Less than 3 hours" },
  { value: "MORE_THAN_3H",    label: "More than 3 hours" },
  { value: "CONNECTION_LOST", label: "Connection lost" },
] as const;

export const DENIED_BOARDING_REASONS: readonly { value: DeniedBoardingReason; label: string }[] = [
  { value: "OVERBOOKED",          label: "Overbooked" },
  { value: "AGGRESSIVE_BEHAVIOR", label: "Aggressive behaviour" },
  { value: "INTOXICATION",        label: "Intoxication" },
  { value: "UNSPECIFIED",         label: "Not specified" },
] as const;

export const MOTIVE_MENTIONED: readonly { value: MotiveMentioned; label: string }[] = [
  { value: "YES",        label: "Yes" },
  { value: "NO",         label: "No" },
  { value: "DONT_KNOW",  label: "Don't know" },
] as const;

export const AIRLINE_MOTIVES: readonly { value: AirlineMotive; label: string }[] = [
  { value: "TECHNICAL",     label: "Technical issue" },
  { value: "WEATHER",       label: "Weather" },
  { value: "STRIKE",        label: "Strike" },
  { value: "AIRPORT_ISSUE", label: "Airport issue" },
  { value: "CREW",          label: "Crew" },
  { value: "OTHER",         label: "Other" },
] as const;

export const INCIDENT_DESCRIPTION_MAX = 2000;
