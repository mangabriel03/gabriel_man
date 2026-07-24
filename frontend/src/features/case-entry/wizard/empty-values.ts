import type { CaseFormValues } from "../schema";

export const emptyValues: CaseFormValues = {
  passenger: {
    first_name: "",
    last_name: "",
    date_of_birth: "",
    email: "",
    phone: "",
    address: "",
    postal_code: "",
  },
  reservation_number: "",
  segments: [
    {
      order: 0,
      flight_date: "",
      flight_number: "",
      airline: "",
      departure_airport_iata: "",
      arrival_airport_iata: "",
      planned_departure_time: "",
      planned_arrival_time: "",
      is_problem_flight: true,
    },
  ],
  // `disruption_type` starts as "" so radios render un-selected; schema requires user to pick one.
  disruption: {
    disruption_type: "" as unknown as CaseFormValues["disruption"]["disruption_type"],
    cancellation_notice: null,
    delay_duration: null,
    denied_boarding_voluntary: null,
    denied_boarding_reason: null,
    airline_motive_mentioned: null,
    airline_motive: null,
    incident_description: "",
  },
  gdpr_consent: false,
  boarding_pass: undefined as unknown as File,
  id_document: undefined as unknown as File,
};
