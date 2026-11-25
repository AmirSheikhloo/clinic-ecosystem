"use client";

import { PatientSearchPanel } from "./PatientSearchPanel";
import { BookingForm } from "./BookingForm";
import { OverlapDialog } from "./OverlapDialog";
import { useReceptionDesk } from "./useReceptionDesk";

export function DeskView() {
  const desk = useReceptionDesk();

  if (desk.bootError) {
    return (
      <p className="ds-alert-danger" role="alert" data-testid="desk-boot-error">
        {desk.bootError}
      </p>
    );
  }

  if (!desk.ready) {
    return (
      <p className="animate-fade-in text-[var(--ds-text-muted)]">
        در حال آماده‌سازی میز پذیرش…
      </p>
    );
  }

  return (
    <main className="space-y-8 animate-rise" data-testid="desk-page">
      <header>
        <h1 className="text-2xl font-bold text-[var(--ds-primary-strong)]">میز پذیرش</h1>
        <p className="text-[var(--ds-text-muted)]">
          جستجو/ثبت بیمار مصنوعی، انتخاب خدمت و منابع معتبر، ثبت نوبت دستی — ارقام نمایشی لاتین
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-2">
        <PatientSearchPanel
          query={desk.query}
          onQueryChange={desk.setQuery}
          onSearch={desk.searchPatients}
          patients={desk.patients}
          selectedPatient={desk.selectedPatient}
          onSelectPatient={desk.selectPatient}
          firstName={desk.firstName}
          lastName={desk.lastName}
          birthDate={desk.birthDate}
          onFirstNameChange={desk.setFirstName}
          onLastNameChange={desk.setLastName}
          onBirthDateChange={desk.setBirthDate}
          registering={desk.registering}
          onRegister={desk.registerPatient}
        />
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
        />
      </section>

      {desk.pendingConflicts && (
        <OverlapDialog
          conflicts={desk.pendingConflicts}
          submitting={desk.submitting}
          onConfirm={desk.confirmOverlap}
          onDismiss={desk.dismissOverlap}
        />
      )}

      {desk.message && (
        <p className="ds-alert-ok" role="status" data-testid="desk-status">
          {desk.message}
        </p>
      )}
      {desk.error && (
        <p className="ds-alert-danger" role="alert" data-testid="desk-error">
          {desk.error}
        </p>
      )}
    </main>
  );
}
