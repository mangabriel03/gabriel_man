import { useFormContext, useWatch } from "react-hook-form";
import { Navigate, Route, Routes } from "react-router-dom";

import { ChangePasswordPage } from "./features/auth/ChangePasswordPage";
import { LoginPage } from "./features/auth/LoginPage";
import { AdminHomePage } from "./features/admin/AdminHomePage";
import { AdminCaseListPage } from "./features/admin/AdminCaseListPage";
import { AdminSystemPage } from "./features/admin/AdminSystemPage";
import { UserListPage } from "./features/admin/UserListPage";
import { CaseCreatedPage } from "./features/case-entry/wizard/CaseCreatedPage";
import { ReviewStep } from "./features/case-entry/wizard/ReviewStep";
import { WizardLayout } from "./features/case-entry/wizard/WizardLayout";
import { WizardStep } from "./features/case-entry/wizard/WizardStep";
import { ConnectingFlightsSection } from "./features/case-entry/sections/ConnectingFlightsSection";
import { DisruptionInfoSection } from "./features/case-entry/sections/DisruptionInfoSection";
import { DocumentsSection } from "./features/case-entry/sections/DocumentsSection";
import { FlightItinerarySection } from "./features/case-entry/sections/FlightItinerarySection";
import { GdprSection } from "./features/case-entry/sections/GdprSection";
import { PassengerDetailsSection } from "./features/case-entry/sections/PassengerDetailsSection";
import type { CaseFormValues } from "./features/case-entry/schema";
import sectionStyles from "./features/case-entry/sections/sections.module.css";

function DocumentsStep() {
  const { control } = useFormContext<CaseFormValues>();
  const values = useWatch({ control });
  const looksHydrated =
    Boolean(values?.disruption?.disruption_type) ||
    Boolean(values?.passenger?.first_name);
  const missingFiles = !values?.boarding_pass || !values?.id_document;
  const showBanner = looksHydrated && missingFiles;

  return (
    <>
      {showBanner && (
        <div className={sectionStyles.notice} role="status">
          Files aren't kept when you refresh the page — please re-upload your
          boarding pass and ID.
        </div>
      )}
      <DocumentsSection />
    </>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/case/new" element={<WizardLayout />}>
        <Route
          path="itinerary"
          element={
            <WizardStep index={0} nextPath="../connecting-flights" fields={["segments.0"]}>
              <FlightItinerarySection />
            </WizardStep>
          }
        />
        <Route
          path="connecting-flights"
          element={
            <WizardStep index={1} nextPath="../disruption" fields={["segments"]}>
              <ConnectingFlightsSection />
            </WizardStep>
          }
        />
        <Route
          path="disruption"
          element={
            <WizardStep index={2} nextPath="../passenger" fields={["disruption"]}>
              <DisruptionInfoSection />
            </WizardStep>
          }
        />
        <Route
          path="passenger"
          element={
            <WizardStep index={3} nextPath="../documents" fields={["passenger", "reservation_number"]}>
              <PassengerDetailsSection />
            </WizardStep>
          }
        />
        <Route
          path="documents"
          element={
            <WizardStep index={4} nextPath="../consent" fields={["boarding_pass", "id_document"]}>
              <DocumentsStep />
            </WizardStep>
          }
        />
        <Route
          path="consent"
          element={
            <WizardStep index={5} nextPath="../review" fields={["gdpr_consent"]}>
              <GdprSection />
            </WizardStep>
          }
        />
        <Route path="review" element={<ReviewStep />} />
      </Route>
      <Route path="/case/created/:id" element={<CaseCreatedPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/account/change-password" element={<ChangePasswordPage />} />
      <Route path="/admin" element={<AdminHomePage />} />
      <Route path="/admin/cases" element={<AdminCaseListPage />} />
      <Route path="/admin/system" element={<AdminSystemPage />} />
      <Route path="/admin/users" element={<UserListPage />} />
      <Route path="/" element={<Navigate to="/case/new/itinerary" replace />} />
      <Route path="*" element={<Navigate to="/case/new/itinerary" replace />} />
    </Routes>
  );
}