"use client";

import { useDeskBookingState } from "./useDeskBookingState";
import { useDeskCatalog } from "./useDeskCatalog";
import { useDeskFeedback } from "./useDeskFeedback";
import { useDeskPatients } from "./useDeskPatients";
import { useDeskSubmit } from "./useDeskSubmit";

/** Composes the focused desk hooks into the single model consumed by DeskView. */
export function useReceptionDesk() {
  const feedback = useDeskFeedback();
  const booking = useDeskBookingState();
  const catalog = useDeskCatalog(booking.resetForServiceChange);
  const patients = useDeskPatients(feedback, booking.invalidate);
  const submit = useDeskSubmit({
    feedback,
    state: booking,
    catalog,
    selectedPatient: patients.selectedPatient,
  });

  /** Next-patient shortcut: keeps service and resources, clears patient, time and banners. */
  function startNext() {
    patients.clearSelection();
    booking.setLocalStart("");
    feedback.setMessage(null);
    feedback.setError(null);
  }

  const ready = catalog.sessionStatus === "ready" && catalog.catalogReady;
  const bootError =
    catalog.sessionStatus === "error" ? "نشست معتبر نیست" : catalog.catalogError;

  return {
    ready,
    bootError,
    query: patients.query,
    setQuery: patients.setQuery,
    patients: patients.patients,
    selectedPatient: patients.selectedPatient,
    selectPatient: patients.selectPatient,
    services: catalog.services,
    serviceId: catalog.serviceId,
    changeService: catalog.changeService,
    requirementsState: catalog.requirementsState,
    requirementsReady: catalog.requirementsReady,
    eligibleResources: submit.eligibleResources,
    selectedResourceIds: booking.selectedResourceIds,
    toggleResource: booking.toggleResource,
    selectionCheck: submit.selectionCheck,
    neededCount: submit.neededCount,
    localStart: booking.localStart,
    setLocalStart: booking.setLocalStart,
    firstName: patients.firstName,
    setFirstName: patients.setFirstName,
    lastName: patients.lastName,
    setLastName: patients.setLastName,
    birthDate: patients.birthDate,
    setBirthDate: patients.setBirthDate,
    message: feedback.message,
    error: feedback.error,
    submitting: submit.submitting,
    registering: patients.registering,
    pendingConflicts: booking.pendingConflicts,
    durationMinutes: catalog.durationMinutes,
    canSubmit: submit.canSubmit,
    patientSearching: patients.searching,
    patientSearched: patients.searched,
    clearPatient: patients.clearSelection,
    lastBooking: booking.lastBooking,
    startNext,
    searchPatients: patients.searchPatients,
    registerPatient: patients.registerPatient,
    submitAppointment: submit.submitAppointment,
    confirmOverlap: submit.confirmOverlap,
    dismissOverlap: submit.dismissOverlap,
  };
}

export type ReceptionDeskModel = ReturnType<typeof useReceptionDesk>;
