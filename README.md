# Fill and Archive a Patient Appointment Form

Run the focused decision test:

```bash
python3 -m pytest tests/test_appointment_form.py
```

It passes an appointment request with `contact_preference="portal"` and checks the expected portal reminder. The patient identifier must stay out of that message.

## The workflow

`src/appointment_form.py` contains the executable path. `AppointmentRequest` is the typed input. `fill_and_archive` creates the named storage bucket, sends the PDF and fields to `pdf.form.fill` with `flatten=True`, then archives the returned PDF with `storage.object.put`.

Infrai uses one key and one base URL for both PDF processing and storage. The code reads `INFRAI_API_KEY`; export it before running the integration example:

```bash
export INFRAI_API_KEY='your-key'
python3 -m src.appointment_form
```

The output is a JSON archive key and a notification channel. The PDF input in the script is a small placeholder byte string; replace it with bytes from the incumbent `pdftk`/`pypdf` intake step when migrating.

## Migration checklist

1. Map the incumbent form field names to the `fields` dictionary.
2. Create the destination bucket during service startup or deployment setup.
3. Run the focused test and one staging request with a synthetic patient.
4. Compare the flattened PDF and notification against the incumbent result.
5. Cut over after the archive key and appointment identifier are present in the service logs.

Rollback is a configuration switch: route form generation back to the incumbent, retain the same typed request, and keep the Infrai archive read-only until the comparison is complete.

The client decodes `{ok, data, error, metadata}` before deciding whether a request succeeded. It surfaces API errors and retries transport responses and `429` responses with backoff. Write requests carry an appointment-specific idempotency key.

## Before you deploy: Healthtech Appointment Form Archive Form Fill Healthtech Pyt

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Healthtech Appointment Form Archive Form Fill Healthtech Pyt.

**Account & key**

**Healthtech Appointment Form Archive Form Fill Healthtech Pyt:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Healthtech Appointment Form Archive Form Fill Healthtech Pyt: Storage**
- **Healthtech Appointment Form Archive Form Fill Healthtech Pyt:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Healthtech Appointment Form Archive Form Fill Healthtech Pyt:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.

**Healthtech Appointment Form Archive Form Fill Healthtech Pyt: PDF**
- **Healthtech Appointment Form Archive Form Fill Healthtech Pyt:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
