export interface PassengerInput {
  first_name: string;
  last_name: string;
  date_of_birth: string;      // YYYY-MM-DD
  email: string;
  phone: string;
  address: string;
  postal_code: string;
}

export interface FlightSegmentInput {
  order: number;
  flight_date: string;                 // YYYY-MM-DD
  flight_number: string;
  airline: string;
  departure_airport_iata: string;
  arrival_airport_iata: string;
  planned_departure_time: string;      // ISO datetime
  planned_arrival_time: string;        // ISO datetime
  is_problem_flight: boolean;
}

export type DisruptionType = "CANCELLATION" | "DELAY" | "DENIED_BOARDING";
export type CancellationNotice = "MORE_THAN_14_DAYS" | "LESS_THAN_14_DAYS" | "ON_FLIGHT_DAY";
export type DelayDuration = "LESS_THAN_3H" | "MORE_THAN_3H" | "CONNECTION_LOST";
export type DeniedBoardingReason =
  | "OVERBOOKED" | "AGGRESSIVE_BEHAVIOR" | "INTOXICATION" | "UNSPECIFIED";
export type MotiveMentioned = "YES" | "NO" | "DONT_KNOW";
export type AirlineMotive =
  | "TECHNICAL" | "WEATHER" | "STRIKE" | "AIRPORT_ISSUE" | "CREW" | "OTHER";

export interface DisruptionInput {
  disruption_type: DisruptionType | "";               // "" only in draft state; rejected by schema
  cancellation_notice: CancellationNotice | null;
  delay_duration: DelayDuration | null;
  denied_boarding_voluntary: "YES" | "NO" | null;     // form-level string; schema converts to bool on transform if needed
  denied_boarding_reason: DeniedBoardingReason | null;
  airline_motive_mentioned: MotiveMentioned | null;
  airline_motive: AirlineMotive | null;
  incident_description: string;
}

export interface CasePayload {
  passenger: PassengerInput;
  reservation_number: string;
  segments: FlightSegmentInput[];
  disruption: DisruptionInput;
  // Runtime schema (`caseFormSchema`) enforces this must be `true` before submit;
  // typed as `boolean` here to match the RHF form value shape.
  gdpr_consent: boolean;
}

export interface DisruptionResponse {
  disruption_type: DisruptionType | "UNSPECIFIED";
  cancellation_notice: CancellationNotice | null;
  delay_duration: DelayDuration | null;
  denied_boarding_voluntary: "YES" | "NO" | null;
  denied_boarding_reason: DeniedBoardingReason | null;
  airline_motive_mentioned: MotiveMentioned | null;
  airline_motive: AirlineMotive | null;
  incident_description: string;
}

export interface CaseCreateResponse {
  id: string;
  status: "NEW" | "VALID" | "ASSIGNED" | "INVALID";
  created_at: string;
  account_email?: string;
  password_change_required?: boolean;
  distance_km: string | number | null;
  compensation_amount_eur: 250 | 400 | 600 | null;
  compensation_error: string | null;
  disruption: DisruptionResponse;
}

export interface AirportOption {
  iata: string;
  icao: string | null;
  name: string;
  city: string;
  country: string;
}
