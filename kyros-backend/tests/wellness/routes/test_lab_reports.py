"""Tests for /v1/wellness/lab-reports multipart upload and CRUD."""

import json

from httpx import AsyncClient

_DEVICE = "lab-reports-dev-001"

_PARSED_TESTS = [
    {
        "name": "HbA1c",
        "value": "6.2",
        "unit": "%",
        "ref_low": 4.0,
        "ref_high": 5.7,
        "flag": "high",
    }
]

_METADATA = {
    "report_date": "2026-05-20",
    "lab_name": "City Lab",
    "parsed": _PARSED_TESTS,
    "note": "Annual checkup",
}

_FAKE_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< >>\n%%EOF"


async def _ensure_user(client: AsyncClient, device_id: str = _DEVICE) -> None:
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})


def _upload_request(
    client: AsyncClient,
    device_id: str = _DEVICE,
    file_bytes: bytes = _FAKE_PDF,
    mime: str = "application/pdf",
    filename: str = "report.pdf",
    metadata: dict | None = None,
) -> object:
    meta = metadata or _METADATA
    return client.post(
        "/v1/wellness/lab-reports/",
        headers={"X-Device-Id": device_id},
        files={"file": (filename, file_bytes, mime)},
        data={"metadata": json.dumps(meta)},
    )


# ── upload ─────────────────────────────────────────────────────────────────────


async def test_upload_pdf_returns_201_with_signed_url(client: AsyncClient) -> None:
    await _ensure_user(client)
    r = await _upload_request(client)
    assert r.status_code == 201
    body = r.json()
    assert body["file_mime"] == "application/pdf"
    assert body["lab_name"] == "City Lab"
    assert body["signed_url"] is not None
    assert body["status"] == "active"
    assert len(body["parsed"]) == 1
    assert body["parsed"][0]["name"] == "HbA1c"


async def test_upload_jpeg_returns_201(client: AsyncClient) -> None:
    device_id = "lab-jpeg-device-00001"
    await _ensure_user(client, device_id)
    r = await _upload_request(
        client,
        device_id=device_id,
        file_bytes=b"\xff\xd8\xff\xe0fake jpeg",
        mime="image/jpeg",
        filename="scan.jpg",
    )
    assert r.status_code == 201
    assert r.json()["file_mime"] == "image/jpeg"


async def test_upload_too_large_returns_413(client: AsyncClient) -> None:
    device_id = "lab-large-device-0001"
    await _ensure_user(client, device_id)
    big_file = b"A" * (10 * 1024 * 1024 + 1)  # 10 MB + 1 byte
    r = await _upload_request(client, device_id=device_id, file_bytes=big_file)
    assert r.status_code == 413


async def test_upload_wrong_mime_returns_415(client: AsyncClient) -> None:
    device_id = "lab-mime-device-00001"
    await _ensure_user(client, device_id)
    r = await _upload_request(
        client,
        device_id=device_id,
        file_bytes=b"<html>not a lab report</html>",
        mime="text/html",
        filename="not_a_report.html",
    )
    assert r.status_code == 415


# ── list / get ────────────────────────────────────────────────────────────────


async def test_list_lab_reports(client: AsyncClient) -> None:
    device_id = "lab-list-device-00001"
    await _ensure_user(client, device_id)
    await _upload_request(client, device_id=device_id)
    await _upload_request(client, device_id=device_id)

    r = await client.get("/v1/wellness/lab-reports/", headers={"X-Device-Id": device_id})
    assert r.status_code == 200
    assert len(r.json()) >= 2


async def test_get_lab_report_returns_fresh_signed_url(client: AsyncClient) -> None:
    device_id = "lab-get-device-000001"
    await _ensure_user(client, device_id)
    r = await _upload_request(client, device_id=device_id)
    report_id = r.json()["id"]

    r = await client.get(
        f"/v1/wellness/lab-reports/{report_id}", headers={"X-Device-Id": device_id}
    )
    assert r.status_code == 200
    assert r.json()["signed_url"] is not None


# ── file download ─────────────────────────────────────────────────────────────


async def test_get_file_returns_200_matching_content(client: AsyncClient) -> None:
    device_id = "lab-file-dl-device001"
    await _ensure_user(client, device_id)
    r = await _upload_request(client, device_id=device_id, file_bytes=_FAKE_PDF)
    report_id = r.json()["id"]

    r = await client.get(
        f"/v1/wellness/lab-reports/{report_id}/file",
        headers={"X-Device-Id": device_id},
    )
    assert r.status_code == 200
    assert r.content == _FAKE_PDF
    assert "application/pdf" in r.headers.get("content-type", "")


async def test_get_file_wrong_user_returns_404(client: AsyncClient) -> None:
    device_a = "lab-file-cross-a-0001"
    device_b = "lab-file-cross-b-0001"
    await _ensure_user(client, device_a)
    await _ensure_user(client, device_b)

    r = await _upload_request(client, device_id=device_a)
    report_id = r.json()["id"]

    r = await client.get(
        f"/v1/wellness/lab-reports/{report_id}/file",
        headers={"X-Device-Id": device_b},
    )
    assert r.status_code == 404


# ── patch ─────────────────────────────────────────────────────────────────────


async def test_patch_parsed_json_reflects_on_get(client: AsyncClient) -> None:
    device_id = "lab-patch-device-0001"
    await _ensure_user(client, device_id)
    r = await _upload_request(client, device_id=device_id)
    report_id = r.json()["id"]

    new_parsed = [
        {
            "name": "Cholesterol",
            "value": "190",
            "unit": "mg/dL",
            "ref_low": None,
            "ref_high": 200.0,
            "flag": "normal",
        }
    ]
    r = await client.patch(
        f"/v1/wellness/lab-reports/{report_id}",
        headers={"X-Device-Id": device_id},
        json={"parsed": new_parsed},
    )
    assert r.status_code == 200

    r = await client.get(
        f"/v1/wellness/lab-reports/{report_id}", headers={"X-Device-Id": device_id}
    )
    assert r.status_code == 200
    assert r.json()["parsed"][0]["name"] == "Cholesterol"


# ── soft delete ────────────────────────────────────────────────────────────────


async def test_delete_soft_deletes_and_get_returns_404(client: AsyncClient) -> None:
    """
    Policy: GET /{id} returns 404 for deleted reports. File is retained for cleanup job.
    """
    device_id = "lab-delete-device-0001"
    await _ensure_user(client, device_id)
    r = await _upload_request(client, device_id=device_id)
    report_id = r.json()["id"]

    r = await client.delete(
        f"/v1/wellness/lab-reports/{report_id}", headers={"X-Device-Id": device_id}
    )
    assert r.status_code == 204

    # GET after soft delete → 404 (report treated as gone from user perspective)
    r = await client.get(
        f"/v1/wellness/lab-reports/{report_id}", headers={"X-Device-Id": device_id}
    )
    assert r.status_code == 404

    # Deleted report not in list
    r = await client.get("/v1/wellness/lab-reports/", headers={"X-Device-Id": device_id})
    report_ids = {rep["id"] for rep in r.json()}
    assert report_id not in report_ids
