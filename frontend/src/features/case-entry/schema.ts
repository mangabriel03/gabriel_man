import { z } from "zod";

const PHONE_REGEX = /^\+?[0-9\s\-()]{7,30}$/;
const IATA_REGEX = /^[A-Z]{3}$/;
const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIMES = new Set(["application/pdf", "image/jpeg", "image/png"]);
const INCIDENT_DESCRIPTION_MAX = 2000;

function fileValidator() {
  return z
    .instanceof(File, { message: "File is required." })
    .refine((f) => f.size <= MAX_FILE_BYTES, "File exceeds 5 MB.")
    .refine(
      (f) => ALLOWED_MIMES.has(f.type),
      "Unsupported file type; allowed: PDF, JPG, PNG.",
    );
}

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Expected date as YYYY-MM-DD.");

const isoDatetime = z
  .string()
  .refine((s) => !Number.isNaN(Date.parse(s)), "Expected a valid datetime.");

export const passengerSchema = z.object({
  first_name: z.string().min(1, "Required."),
  last_name: z.string().min(1, "Required."),
  date_of_birth: isoDate.refine(
    (s) => new Date(s) < new Date(new Date().toDateString()),
    "Date of birth must be before today.",
  ),
  email: z.string().email("Enter a valid email address."),
  phone: z.string().regex(PHONE_REGEX, "Enter a valid phone number."),
  address: z.string().min(1, "Required."),
  postal_code: z.string().min(1, "Required.").max(20),
});

export const segmentSchema = z
  .object({
    order: z.number().int().min(0).max(4),
    flight_date: isoDate,
    flight_number: z.string().min(1, "Required.").max(10),
    airline: z.string().min(1, "Required.").max(80),
    departure_airport_iata: z.string().regex(IATA_REGEX, "Pick an airport."),
    arrival_airport_iata: z.string().regex(IATA_REGEX, "Pick an airport."),
    planned_departure_time: isoDatetime,
    planned_arrival_time: isoDatetime,
    is_problem_flight: z.boolean(),
  })
  .refine(
    (s) => Date.parse(s.planned_arrival_time) > Date.parse(s.planned_departure_time),
    { path: ["planned_arrival_time"], message: "Arrival must be after departure." },
  );

const DISRUPTION_TYPE = z.enum(["CANCELLATION", "DELAY", "DENIED_BOARDING"]);
const CANCELLATION_NOTICE = z.enum(["MORE_THAN_14_DAYS", "LESS_THAN_14_DAYS", "ON_FLIGHT_DAY"]);
const DELAY_DURATION = z.enum(["LESS_THAN_3H", "MORE_THAN_3H", "CONNECTION_LOST"]);
const DENIED_BOARDING_REASON = z.enum(["OVERBOOKED", "AGGRESSIVE_BEHAVIOR", "INTOXICATION", "UNSPECIFIED"]);
const MOTIVE_MENTIONED = z.enum(["YES", "NO", "DONT_KNOW"]);
const AIRLINE_MOTIVE = z.enum(["TECHNICAL", "WEATHER", "STRIKE", "AIRPORT_ISSUE", "CREW", "OTHER"]);

/**
 * Draft-shape disruption schema. Mirrors backend DisruptionSerializer.
 * Optional fields are nullable to allow un-selected radios to persist as null in sessionStorage.
 */
export const disruptionSchema = z
  .object({
    disruption_type: DISRUPTION_TYPE.or(z.literal("")).refine(
      (v): v is z.infer<typeof DISRUPTION_TYPE> => v !== "",
      { message: "Please pick a disruption type." },
    ),
    cancellation_notice: CANCELLATION_NOTICE.nullable(),
    delay_duration: DELAY_DURATION.nullable(),
    denied_boarding_voluntary: z.enum(["YES", "NO"]).nullable(),
    denied_boarding_reason: DENIED_BOARDING_REASON.nullable(),
    airline_motive_mentioned: MOTIVE_MENTIONED.nullable(),
    airline_motive: AIRLINE_MOTIVE.nullable(),
    incident_description: z
      .string()
      .trim()
      .min(1, "Please describe the incident.")
      .max(INCIDENT_DESCRIPTION_MAX, `Maximum ${INCIDENT_DESCRIPTION_MAX} characters.`),
  })
  .superRefine((val, ctx) => {
    if (val.disruption_type === "CANCELLATION") {
      if (!val.cancellation_notice) {
        ctx.addIssue({ code: "custom", path: ["cancellation_notice"], message: "Required." });
      }
      if (!val.airline_motive_mentioned) {
        ctx.addIssue({ code: "custom", path: ["airline_motive_mentioned"], message: "Required." });
      }
      if (val.airline_motive_mentioned === "YES" && !val.airline_motive) {
        ctx.addIssue({ code: "custom", path: ["airline_motive"], message: "Required." });
      }
    } else if (val.disruption_type === "DELAY") {
      if (!val.delay_duration) {
        ctx.addIssue({ code: "custom", path: ["delay_duration"], message: "Required." });
      }
      if (!val.airline_motive_mentioned) {
        ctx.addIssue({ code: "custom", path: ["airline_motive_mentioned"], message: "Required." });
      }
      if (val.airline_motive_mentioned === "YES" && !val.airline_motive) {
        ctx.addIssue({ code: "custom", path: ["airline_motive"], message: "Required." });
      }
    } else if (val.disruption_type === "DENIED_BOARDING") {
      if (!val.denied_boarding_voluntary) {
        ctx.addIssue({ code: "custom", path: ["denied_boarding_voluntary"], message: "Required." });
      }
      if (val.denied_boarding_voluntary === "NO" && !val.denied_boarding_reason) {
        ctx.addIssue({ code: "custom", path: ["denied_boarding_reason"], message: "Required." });
      }
    }
  });

export const caseFormSchema = z
  .object({
    passenger: passengerSchema,
    reservation_number: z.string().min(1, "Required.").max(30),
    segments: z.array(segmentSchema).min(1).max(5),
    disruption: disruptionSchema,
    gdpr_consent: z
      .boolean()
      .refine((v) => v === true, {
        message: "You must accept the GDPR policy to submit.",
      }),
    boarding_pass: fileValidator(),
    id_document: fileValidator(),
  })
  .refine(
    (v) => v.segments.filter((s) => s.is_problem_flight).length === 1,
    {
      path: ["segments"],
      message: "Exactly one segment must be marked as the problem flight.",
    },
  );

export type CaseFormValues = z.infer<typeof caseFormSchema>;
export type DisruptionFormValues = z.infer<typeof disruptionSchema>;
