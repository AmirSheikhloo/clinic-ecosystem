"use client";

import { useEffect, useRef, useState } from "react";
import { Alert } from "@/components/feedback/Alert";
import { SearchableCombobox } from "@/components/forms/SearchableCombobox";
import { Skeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { apiJson } from "@/lib/api";
import { FEATURE_FLAGS } from "@/lib/feature-flags";
import { useSession } from "@/components/session/SessionProvider";
import { P } from "@/lib/permissions";
import { BookingConfirmation } from "./BookingConfirmation";
import { BookingForm, type BillableItem } from "./BookingForm";
import { OverlapDialog } from "./OverlapDialog";
import { PatientPicker } from "./PatientPicker";
import { CashierPanel } from "./CashierPanel";
import { PatientQuickRegister } from "./PatientQuickRegister";
import { MultiPatientCartPanel } from "./MultiPatientCartPanel";
import {
  addLineToPatient,
  removeLineFromPatient,
  removePatientSlot,
  upsertPatientSlot,
  type CartPatientSlot,
} from "./multi-patient-cart";
import { PERSIAN_INSURANCE_CATALOG } from "./insurance-catalog";
import { useReceptionDesk } from "./useReceptionDesk";

type DeskStage = 1 | 2 | 3;

function StageRail({
  stage,
  patientDone,
  linesCount,
  onJump,
}: {
  stage: DeskStage;
  patientDone: boolean;
  linesCount: number;
  onJump: (s: DeskStage) => void;
}) {
  const steps: Array<{ id: DeskStage; title: string; enabled: boolean }> = [
    { id: 1, title: "شناسایی بیمار", enabled: true },
    { id: 2, title: "خدمت و نوبت", enabled: patientDone },
    { id: 3, title: "بازبینی صورتحساب", enabled: patientDone },
  ];
  return (
    <nav className="flex flex-wrap gap-2" aria-label="مراحل پذیرش" data-testid="desk-stage-rail">
      {steps.map((step) => {
        const active = stage === step.id;
        const done = step.id === 1 ? patientDone : step.id === 2 ? linesCount > 0 && stage === 3 : false;
        return (
          <button
            key={step.id}
            type="button"
            disabled={!step.enabled}
            aria-current={active ? "step" : undefined}
            className={`ds-btn ds-btn-sm ${active ? "ds-btn-primary" : "ds-btn-ghost"}`}
            onClick={() => onJump(step.id)}
            data-testid={`desk-stage-${step.id}`}
          >
            <span className="tabular-nums">{step.id}</span>
            <span>{step.title}</span>
            {done ? <span className="text-xs opacity-80">✓</span> : null}
          </button>
        );
      })}
    </nav>
  );
}

export function DeskView() {
  const desk = useReceptionDesk();
  const { can, status } = useSession();
  const searchInput = useRef<HTMLInputElement | null>(null);
  const [stage, setStage] = useState<DeskStage>(1);
  const [insuranceCode, setInsuranceCode] = useState("NONE");
  const [preferredPractitionerId, setPreferredPractitionerId] = useState("");
  const [billableItems, setBillableItems] = useState<BillableItem[]>([]);
  const [cartSlots, setCartSlots] = useState<CartPatientSlot[]>([]);
  const [showMulti, setShowMulti] = useState(false);

  useEffect(() => {
    if (desk.selectedPatient) setStage((s) => (s === 1 ? 2 : s));
  }, [desk.selectedPatient]);

  useEffect(() => {
    if (status !== "ready") return;
    if (!can(P.financeInvoiceView) && !can(P.inventoryView)) return;
    let cancelled = false;
    void apiJson<{ items: BillableItem[] }>("/api/v1/ops/billable-items", {
      fallbackMessage: "بارگذاری اقلام ناموفق بود",
    }).then((res) => {
      if (cancelled || !res.ok) return;
      setBillableItems(res.data.items ?? []);
    });
    return () => {
      cancelled = true;
    };
  }, [status, can]);

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
        <div className="grid gap-6 lg:grid-cols-[65fr_35fr]">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  function startNext() {
    desk.startNext();
    setInsuranceCode("NONE");
    setPreferredPractitionerId("");
    setStage(1);
    window.requestAnimationFrame(() => searchInput.current?.focus());
  }

  function goBack() {
    if (stage === 3) setStage(2);
    else if (stage === 2) setStage(1);
  }

  function addCurrentPatientToMultiCart() {
    if (!desk.selectedPatient) return;
    setCartSlots((prev) => upsertPatientSlot(prev, desk.selectedPatient!, insuranceCode));
    setShowMulti(true);
  }

  function addLineToMultiCart() {
    if (!desk.selectedPatient) return;
    const live = desk.liveDraftLine;
    if (!live) {
      desk.addDraftLine();
      return;
    }
    setCartSlots((prev) => {
      const withPatient = upsertPatientSlot(prev, desk.selectedPatient!, insuranceCode);
      return addLineToPatient(withPatient, desk.selectedPatient!.patient_profile_id, live);
    });
    setShowMulti(true);
    desk.addDraftLine();
  }

  return (
    <main className="space-y-5" data-testid="desk-page">
      <PageHeader
        title="میز پذیرش"
        description={
          <>
            پذیرش سه‌مرحله‌ای: شناسایی بیمار، انتخاب خدمت/منابع، بازبینی صورتحساب سرور.{" "}
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

      <StageRail
        stage={stage}
        patientDone={!!desk.selectedPatient}
        linesCount={desk.draftLines.length}
        onJump={(s) => {
          if (s === 1 || desk.selectedPatient) setStage(s);
        }}
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

      <div className="flex flex-wrap gap-2">
        {stage > 1 ? (
          <Button variant="ghost" size="sm" onClick={goBack} data-testid="desk-back">
            بازگشت (پیش‌نویس حفظ می‌شود)
          </Button>
        ) : null}
        {stage < 3 && desk.selectedPatient ? (
          <Button variant="ghost" size="sm" onClick={() => setStage((s) => (s === 1 ? 2 : 3))} data-testid="desk-forward">
            مرحله بعد
          </Button>
        ) : null}
        {FEATURE_FLAGS.multiPatientCart && desk.selectedPatient ? (
          <Button variant="ghost" size="sm" onClick={addCurrentPatientToMultiCart} data-testid="desk-add-multi-patient">
            افزودن بیمار به سبد چندنفره
          </Button>
        ) : null}
        <Button variant="subtle" size="sm" onClick={startNext} data-testid="desk-next-patient">
          بیمار بعدی
        </Button>
      </div>

      {/* 65/35 catalog/cart desktop — single page scroll (no nested scroll regression) */}
      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,65fr)_minmax(18rem,35fr)]">
        <div className="space-y-5 min-w-0">
          {stage === 1 || !desk.selectedPatient ? (
            <section className="ds-card space-y-4 p-5" aria-label="شناسایی بیمار" data-testid="desk-stage-patient">
              <h2 className="ds-section-title">1. شناسایی فشرده بیمار</h2>
              <p className="ds-hint">جستجوی دقیق کد ملی، تلفن، یا نام — ثبت درون‌خطی با استثناهای هویت/تماس مستقل.</p>
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
                  setStage(2);
                  window.requestAnimationFrame(() =>
                    document.querySelector<HTMLElement>("[data-testid='service-select-input']")?.focus(),
                  );
                }}
                onClear={desk.clearPatient}
                inputRef={searchInput}
              />
              <SearchableCombobox
                label="بیمه (فهرست قابل پیکربندی)"
                options={PERSIAN_INSURANCE_CATALOG.map((e) => ({
                  value: e.code,
                  label: e.nameFa,
                  description: e.coverageKind,
                  disabled: !e.clinicContractActive && e.code !== "NONE" && e.code !== "OTHER",
                }))}
                value={insuranceCode}
                onChange={setInsuranceCode}
                testId="desk-insurance"
                hint="قرارداد کلینیک در فهرست مشخص است؛ تسویه بیمه‌گر زنده فعال نیست."
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
                onRegister={(event) => {
                  desk.registerPatient(event);
                  setStage(2);
                }}
              />
            </section>
          ) : null}

          {stage >= 2 && desk.selectedPatient ? (
            <section className="ds-card space-y-4 p-5" aria-label="کاتالوگ و نوبت" data-testid="desk-stage-booking">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="ds-section-title">2. خدمت، منابع و زمان مستقل</h2>
                <Button variant="ghost" size="sm" onClick={() => setStage(1)} data-testid="desk-edit-patient">
                  تغییر بیمار
                </Button>
              </div>
              <BookingForm
                selectedPatient={desk.selectedPatient}
                services={desk.services}
                serviceId={desk.serviceId}
                onServiceChange={desk.changeService}
                requirementsState={desk.requirementsState}
                requirementsReady={desk.requirementsReady}
                eligibleResources={desk.eligibleResources}
                allResources={desk.resources}
                selectedResourceIds={desk.selectedResourceIds}
                onToggleResource={desk.toggleResource}
                selectionCheck={desk.selectionCheck}
                neededCount={desk.neededCount}
                localStart={desk.localStart}
                onLocalStartChange={desk.setLocalStart}
                durationMinutes={desk.durationMinutes}
                onDurationChange={desk.setDurationMinutes}
                pendingConflicts={desk.pendingConflicts}
                canSubmit={desk.canSubmit}
                submitting={desk.submitting}
                onSubmit={desk.submitAppointment}
                onAddToInvoice={() => {
                  if (showMulti || cartSlots.length > 0) addLineToMultiCart();
                  else desk.addDraftLine();
                }}
                canAddToInvoice={desk.canAddDraftLine}
                onSetWalkInNow={desk.setWalkInNow}
                queuedCount={desk.draftLines.length}
                onSubmitGroup={desk.submitGroup}
                canSubmitGroup={desk.canSubmitGroup}
                billableItems={billableItems}
                preferredPractitionerId={preferredPractitionerId}
                onPreferredPractitionerChange={setPreferredPractitionerId}
              />
              {desk.draftLines.length > 0 || desk.liveDraftLine ? (
                <Button variant="primary" onClick={() => setStage(3)} data-testid="desk-goto-review">
                  بازبینی صورتحساب
                </Button>
              ) : null}
            </section>
          ) : null}

          {stage === 3 ? (
            <section className="ds-card space-y-3 p-5 xl:hidden" aria-label="بازبینی موبایل" data-testid="desk-stage-review-mobile">
              <h2 className="ds-section-title">3. بازبینی صورتحساب</h2>
              <p className="ds-hint">پیش‌فاکتور زنده؛ ثبت نهایی سمت سرور است و با تکرار درخواست تکراری ساخته نمی‌شود.</p>
            </section>
          ) : null}

          {showMulti || cartSlots.length > 0 ? (
            <MultiPatientCartPanel
              slots={cartSlots}
              activePatientId={desk.selectedPatient?.patient_profile_id ?? null}
              onSelectPatient={(id) => {
                const slot = cartSlots.find((s) => s.patient.patient_profile_id === id);
                if (slot) {
                  desk.selectPatient(slot.patient);
                  setInsuranceCode(slot.insuranceCode);
                  setStage(2);
                }
              }}
              onRemovePatient={(id) => setCartSlots((prev) => removePatientSlot(prev, id))}
              onRemoveLine={(patientId, lineKey) =>
                setCartSlots((prev) => removeLineFromPatient(prev, patientId, lineKey))
              }
              onClear={() => {
                setCartSlots([]);
                setShowMulti(false);
              }}
            />
          ) : null}
        </div>

        <aside
          className="xl:sticky xl:top-4 space-y-4 min-w-0"
          aria-label="سبد و صندوق زنده"
          data-testid="desk-cart-column"
        >
          <div className="ds-card p-2" data-testid="desk-stage-review">
            <CashierPanel
              patient={desk.selectedPatient}
              lines={desk.draftLines}
              draft={stage >= 2 ? desk.liveDraftLine : null}
              onRemove={desk.removeDraftLine}
              lastBooking={desk.lastBooking}
              onCleared={() => desk.clearDraftLines()}
            />
          </div>
        </aside>
      </div>

      {desk.pendingConflicts ? (
        <OverlapDialog
          conflicts={desk.pendingConflicts}
          submitting={desk.submitting}
          onConfirm={desk.confirmOverlap}
          onDismiss={desk.dismissOverlap}
          lineLabel={desk.draftLines.find((line) => line.key === desk.pendingConflictLineId)?.serviceName}
        />
      ) : null}
    </main>
  );
}
