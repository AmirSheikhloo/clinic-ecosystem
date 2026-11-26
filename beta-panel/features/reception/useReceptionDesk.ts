"use client";

import { useMemo } from "react";
import { useDeskBookingState } from "./useDeskBookingState";
import { useDeskCatalog } from "./useDeskCatalog";
import { useDeskDraftLines } from "./useDeskDraftLines";
import { useDeskFeedback } from "./useDeskFeedback";
import { useDeskPatients } from "./useDeskPatients";
import { useDeskSubmit } from "./useDeskSubmit";

/** Composes the focused desk hooks into the single model consumed by DeskView. */
export function useReceptionDesk() {
  const feedback = useDeskFeedback();
  const booking = useDeskBookingState();
  const catalog = useDeskCatalog(booking.resetForServiceChange);
  const patients = useDeskPatients(feedback, booking.invalidate);
  const drafts = useDeskDraftLines();
  const submit = useDeskSubmit({
    feedback,
    state: booking,
    catalog,
    selectedPatient: patients.selectedPatient,
    draftLines: drafts.draftLines,
    clearDraftLines: drafts.clearDraftLines,
  });

  /** Next-patient shortcut: keeps service and resources, clears patient, time and banners. */
  function startNext() {
    patients.clearSelection();
    booking.setLocalStart("");
    drafts.clearDraftLines();
    feedback.setMessage(null);
    feedback.setError(null);
  }

  const resourceNames = useMemo(
    () =>
      submit.eligibleResources
        .filter((resource) => booking.selectedResourceIds.includes(resource.id))
        .map((resource) => resource.resource_name),
    [submit.eligibleResources, booking.selectedResourceIds],
  );

  const lineArgs = {
    serviceId: catalog.serviceId,
    services: catalog.services,
    resourceIds: booking.selectedResourceIds,
    resourceNames,
    localStart: booking.localStart,
    durationMinutes: catalog.durationMinutes,
    selectionOk: submit.selectionCheck.ok,
  };

  function addDraftLine() {
    if (!drafts.addDraftLine(lineArgs)) {
      feedback.setError("برای افزودن خدمت، بیمار/خدمت/منابع/زمان را کامل کنید");
      return;
    }
    feedback.setError(null);
    feedback.setMessage("خدمت به پیش‌فاکتور اضافه شد — می‌توانید خدمت دیگری انتخاب کنید");
    catalog.changeService("");
    booking.resetForServiceChange();
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
    nationalId: patients.nationalId,
    setNationalId: patients.setNationalId,
    phone: patients.phone,
    setPhone: patients.setPhone,
    identityType: patients.identityType,
    setIdentityType: patients.setIdentityType,
    identityExceptionReason: patients.identityExceptionReason,
    setIdentityExceptionReason: patients.setIdentityExceptionReason,
    message: feedback.message,
    error: feedback.error,
    submitting: submit.submitting,
    registering: patients.registering,
    pendingConflicts: booking.pendingConflicts,
    pendingConflictLineId: booking.pendingConflictLineId,
    durationMinutes: catalog.durationMinutes,
    canSubmit: submit.canSubmit,
    patientSearching: patients.searching,
    patientSearched: patients.searched,
    clearPatient: patients.clearSelection,
    lastBooking: booking.lastBooking,
    draftLines: drafts.draftLines,
    liveDraftLine: drafts.liveDraftLine(lineArgs),
    addDraftLine,
    canAddDraftLine:
      !!patients.selectedPatient &&
      catalog.requirementsReady &&
      submit.selectionCheck.ok &&
      !!booking.localStart &&
      !submit.submitting,
    removeDraftLine: drafts.removeDraftLine,
    setWalkInNow: () => drafts.setWalkInNow(booking.markWalkInNow),
    canSubmitGroup: drafts.draftLines.length > 0 && !!patients.selectedPatient && !submit.submitting,
    submitGroup: submit.submitGroup,
    startNext,
    searchPatients: patients.searchPatients,
    registerPatient: patients.registerPatient,
    submitAppointment: submit.submitAppointment,
    confirmOverlap: submit.confirmOverlap,
    dismissOverlap: submit.dismissOverlap,
  };
}

export type ReceptionDeskModel = ReturnType<typeof useReceptionDesk>;
