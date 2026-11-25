from src.appointment_form import AppointmentRequest, patient_notification


def test_portal_notification_excludes_patient_identifier():
    request = AppointmentRequest("patient-42", "visit-7", "2026-10-25 14:00", "North Clinic", "portal")
    notification = patient_notification(request)
    assert notification.channel == "portal"
    assert notification.message == "Your appointment is scheduled for 2026-10-25 14:00 at North Clinic."
    assert request.patient_id not in notification.message
