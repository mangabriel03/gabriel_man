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

export interface CasePayload {
  passenger: PassengerInput;
  reservation_number: string;
  segments: FlightSegmentInput[];
  // Runtime schema (`caseFormSchema`) enforces this must be `true` before submit;
  // typed as `boolean` here to match the RHF form value shape.
  gdpr_consent: boolean;
}

export interface CaseCreateResponse {
  id: string;
  status: "NEW" | "VALID" | "ASSIGNED" | "INVALID";
  created_at: string;
  distance_km: string | number | null;
  compensation_amount_eur: 250 | 400 | 600 | null;
  compensation_error: string | null;
}

export interface AirportOption {
  iata: string;
  icao: string | null;
  name: string;
  city: string;
  country: string;
}
