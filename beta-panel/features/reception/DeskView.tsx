"use client";

import { useRef } from "react";
import { Alert } from "@/components/feedback/Alert";
import { Skeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { BookingConfirmation } from "./BookingConfirmation";
import { BookingForm } from "./BookingForm";
import { OverlapDialog } from "./OverlapDialog";
import { PatientPicker } from "./PatientPicker";
import { CashierPanel } from "./CashierPanel";
import { PatientQuickRegister } from "./PatientQuickRegister";
import { useReceptionDesk } from "./useReceptionDesk";

function StepHeading({ step, title, done }: { step: number; title: string; done?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="grid size-7 place-items-center rounded-full bg-[var(--ds-primary)] text-sm font-semibold text-[var(--ds-on-primary)]"
        aria-hidden="true"
        data-done={done}
      >
        {step}
      </span>
      <h2 className="ds-section-title">{title}</h2>
    </div>
  );
}

export function DeskView() {
  const desk = useReceptionDesk();
  const searchInput = useRef<HTMLInputElement | null>(null);

  if (desk.bootError) {
    return (
      <Alert tone="danger" testId="desk-boot-error">
        {desk.bootError}
      </Alert>
    );
  }

  if (!desk.ready) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="در حال آماده‌سازی میز پذیرش">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  function startNext() {
    desk.startNext();
    window.requestAnimationFrame(() => searchInput.current?.focus());
  }

  return (
    <main className="space-y-6" data-testid="desk-page">
      <PageHeader
        title="میز پذیرش"
        description={
          <>
            بیمار را پیدا یا ثبت کنید، خدمت و منابع را انتخاب کنید و نوبت را در چند مرحله ثبت کنید.{" "}
            <a
              className="text-[var(--ds-primary)] underline-offset-2 hover:underline"
              href="/appointments?view=list&status=CHECKED_IN&date=today"
              data-testid="waiting-room-link"
            >
              نوبت‌های با حضور ثبت‌شده (امروز)
            </a>
          </>
        }
      />

      {desk.message && desk.lastBooking ? (
        <BookingConfirmation message={desk.message} booking={desk.lastBooking} onNext={startNext} />
      ) : desk.message ? (
        <Alert tone="ok" testId="desk-status">
          {desk.message}
        </Alert>
      ) : null}
      {desk.error ? (
        <Alert tone="danger" testId="desk-error">
          {desk.error}
        </Alert>
      ) : null}

      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
        <section className="ds-card space-y-4 p-5" aria-label="انتخاب بیمار">
          <StepHeading step={1} title="بیمار" done={!!desk.selectedPatient} />
          <PatientPicker
            query={desk.query}
            onQueryChange={desk.setQuery}
            onSearch={desk.searchPatients}
            patients={desk.patients}
            searching={desk.patientSearching}
            searched={desk.patientSearched}
            selectedPatient={desk.selectedPatient}
            onSelect={(patient) => {
              desk.selectPatient(patient);
              window.requestAnimationFrame(() => document.querySelector<HTMLElement>("[data-testid='service-select']")?.focus());
            }}
            onClear={desk.clearPatient}
            inputRef={searchInput}
          />
          <PatientQuickRegister
            firstName={desk.firstName}
            lastName={desk.lastName}
            birthDate={desk.birthDate}
            nationalId={desk.nationalId}
            phone={desk.phone}
            identityType={desk.identityType}
            identityExceptionReason={desk.identityExceptionReason}
            onFirstNameChange={desk.setFirstName}
            onLastNameChange={desk.setLastName}
            onBirthDateChange={desk.setBirthDate}
            onNationalIdChange={desk.setNationalId}
            onPhoneChange={desk.setPhone}
            onIdentityTypeChange={desk.setIdentityType}
            onIdentityExceptionReasonChange={desk.setIdentityExceptionReason}
            registering={desk.registering}
            onRegister={desk.registerPatient}
          />
        </section>

        <section className="ds-card space-y-4 p-5" aria-label="مشخصات نوبت">
          <StepHeading step={2} title="نوبت" />
          <BookingForm
            selectedPatient={desk.selectedPatient}
            services={desk.services}
            serviceId={desk.serviceId}
            onServiceChange={desk.changeService}
            requirementsState={desk.requirementsState}
            requirementsReady={desk.requirementsReady}
            eligibleResources={desk.eligibleResources}
            selectedResourceIds={desk.selectedResourceIds}
            onToggleResource={desk.toggleResource}
            selectionCheck={desk.selectionCheck}
            neededCount={desk.neededCount}
            localStart={desk.localStart}
            onLocalStartChange={desk.setLocalStart}
            durationMinutes={desk.durationMinutes}
            pendingConflicts={desk.pendingConflicts}
            canSubmit={desk.canSubmit}
            submitting={desk.submitting}
            onSubmit={desk.submitAppointment}
            onAddToInvoice={desk.addDraftLine}
            canAddToInvoice={desk.canAddDraftLine}
            onSetWalkInNow={desk.setWalkInNow}
            queuedCount={desk.draftLines.length}
            onSubmitGroup={desk.submitGroup}
            canSubmitGroup={desk.canSubmitGroup}
          />
        </section>

        <CashierPanel
          patient={desk.selectedPatient}
          lines={desk.draftLines}
          draft={desk.liveDraftLine}
          onRemove={desk.removeDraftLine}
          lastBooking={desk.lastBooking}
          onCleared={() => desk.clearDraftLines()}
        />
      </div>

      {desk.pendingConflicts ? (
        <OverlapDialog
          conflicts={desk.pendingConflicts}
          submitting={desk.submitting}
          onConfirm={desk.confirmOverlap}
          onDismiss={desk.dismissOverlap}
          lineLabel={
            desk.draftLines.find((line) => line.key === desk.pendingConflictLineId)?.serviceName
          }
        />
      ) : null}
    </main>
  );
}
