import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { DisruptionInfoSection } from "../src/features/case-entry/sections/DisruptionInfoSection";
import { caseFormSchema, type CaseFormValues } from "../src/features/case-entry/schema";
import { emptyValues } from "../src/features/case-entry/wizard/empty-values";

function Wrap() {
  const methods = useForm<CaseFormValues>({
    resolver: zodResolver(caseFormSchema),
    defaultValues: emptyValues,
    mode: "onTouched",
  });
  return (
    <FormProvider {...methods}>
      <DisruptionInfoSection />
    </FormProvider>
  );
}

describe("DisruptionInfoSection", () => {
  it("does not offer UNSPECIFIED as a disruption type", () => {
    render(<Wrap />);
    expect(screen.queryByLabelText(/unspecified/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/cancellation/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^delay$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/denied boarding/i)).toBeInTheDocument();
  });

  it("reveals cancellation notice when CANCELLATION is picked", async () => {
    const user = userEvent.setup();
    render(<Wrap />);
    await user.click(screen.getByLabelText(/cancellation/i));
    expect(
      screen.getByText(/when were you informed of the cancellation/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/on the day of the flight/i)).toBeInTheDocument();
  });

  it("reveals delay duration when DELAY is picked", async () => {
    const user = userEvent.setup();
    render(<Wrap />);
    await user.click(screen.getByLabelText(/^delay$/i));
    expect(screen.getByText(/how long was the delay/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/more than 3 hours/i)).toBeInTheDocument();
  });

  it("reveals reason only when voluntary=NO on denied boarding", async () => {
    const user = userEvent.setup();
    render(<Wrap />);
    await user.click(screen.getByLabelText(/denied boarding/i));
    expect(
      screen.getByText(/was boarding denied voluntarily/i),
    ).toBeInTheDocument();
    // Reason block hidden initially
    expect(
      screen.queryByText(/reason boarding was denied/i),
    ).not.toBeInTheDocument();
    await user.click(screen.getByLabelText(/no, i was denied/i));
    expect(
      screen.getByText(/reason boarding was denied/i),
    ).toBeInTheDocument();
  });

  it("reveals airline motive only when mentioned=YES", async () => {
    const user = userEvent.setup();
    render(<Wrap />);
    await user.click(screen.getByLabelText(/^delay$/i));
    // Mentioned block appears
    expect(
      screen.getByText(/did the airline mention a reason/i),
    ).toBeInTheDocument();
    // Motive block hidden initially
    expect(
      screen.queryByText(/which reason did the airline give/i),
    ).not.toBeInTheDocument();
    await user.click(screen.getAllByLabelText(/^yes$/i)[0]);
    expect(
      screen.getByText(/which reason did the airline give/i),
    ).toBeInTheDocument();
  });
});
