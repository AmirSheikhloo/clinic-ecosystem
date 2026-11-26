import { PatientProfileView } from "@/features/patients/PatientProfileView";

export default async function PatientProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PatientProfileView patientId={id} />;
}
