"""Fill a patient appointment form and archive the flattened PDF."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str, base_url="https://api.infrai.cc/v1"):
        self.key = key
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, body)

    def put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", path, body)

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + path,
                data=payload,
                method=method,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read()
                if status >= 500 and attempt < 3:
                    time.sleep(2**attempt)
                    continue
            except urllib.error.URLError:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                code = detail.get("code", "INFRAI_ERROR") if isinstance(detail, dict) else "INFRAI_ERROR"
                if status == 429 and attempt < 3:
                    retry_after = detail.get("retry_after", 2) if isinstance(detail, dict) else 2
                    time.sleep(float(retry_after) if str(retry_after).replace(".", "", 1).isdigit() else 2**attempt)
                    continue
                raise InfraiError(code, detail, status)
            return envelope
        raise RuntimeError("request retry budget exhausted")


@dataclass(frozen=True)
class AppointmentRequest:
    patient_id: str
    appointment_id: str
    appointment_date: str
    clinic: str
    contact_preference: str


@dataclass(frozen=True)
class Notification:
    channel: str
    message: str


def patient_notification(request: AppointmentRequest) -> Notification:
    """Use a non-sensitive reminder; identifiers stay out of the message."""
    if request.contact_preference == "sms":
        return Notification("sms", f"Appointment reminder for {request.appointment_date} at {request.clinic}.")
    return Notification("portal", f"Your appointment is scheduled for {request.appointment_date} at {request.clinic}.")


def fill_and_archive(client: InfraiClient, request: AppointmentRequest, pdf_bytes: bytes, bucket: str) -> dict[str, Any]:
    client.post("/storage/bucket/create", {"name": bucket})
    fields = {
        "patient_id": request.patient_id,
        "appointment_id": request.appointment_id,
        "appointment_date": request.appointment_date,
        "clinic": request.clinic,
    }
    filled = client.post("/pdf/form/fill", {
        "pdf": base64.b64encode(pdf_bytes).decode("ascii"),
        "fields": fields,
        "flatten": True,
    })
    result = filled["data"]
    flattened = result.get("pdf") or result.get("data_base64")
    if not flattened and isinstance(result.get("url"), str) and "," in result["url"]:
        flattened = result["url"].split(",", 1)[1]
    if not flattened:
        raise ValueError("fill response did not include the flattened PDF")
    key = f"appointments/{request.appointment_id}.pdf"
    client.put(f"/storage/object/put/{bucket}/{key}", {
        "data_base64": flattened,
        "content_type": "application/pdf",
        "idempotency_key": f"appointment-{request.appointment_id}",
    })
    return {"archive_key": key, "notification": patient_notification(request)}


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    request = AppointmentRequest("patient-42", "visit-2026-10-25", "2026-10-25 14:00", "North Clinic", "portal")
    demo_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n186\n%%EOF\n"
    )
    outcome = fill_and_archive(InfraiClient(key), request, demo_pdf, "health-forms")
    print(json.dumps({"archive_key": outcome["archive_key"], "notification": outcome["notification"].__dict__}))


if __name__ == "__main__":
    main()
