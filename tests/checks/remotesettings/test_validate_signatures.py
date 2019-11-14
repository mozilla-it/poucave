import pytest

from checks.remotesettings.validate_signatures import run, validate_signature
from tests.utils import patch_async


MODULE = "checks.remotesettings.validate_signatures"
COLLECTION_URL = "/buckets/{}/collections/{}"
RECORDS_URL = COLLECTION_URL + "/records"
CERT = """-----BEGIN CERTIFICATE-----
MIIDBTCCAougAwIBAgIIFcbkDrCrHAkwCgYIKoZIzj0EAwMwgaMxCzAJBgNVBAYT
AlVTMRwwGgYDVQQKExNNb3ppbGxhIENvcnBvcmF0aW9uMS8wLQYDVQQLEyZNb3pp
bGxhIEFNTyBQcm9kdWN0aW9uIFNpZ25pbmcgU2VydmljZTFFMEMGA1UEAww8Q29u
dGVudCBTaWduaW5nIEludGVybWVkaWF0ZS9lbWFpbEFkZHJlc3M9Zm94c2VjQG1v
emlsbGEuY29tMB4XDTE5MDgyMzIyNDQzMVoXDTE5MTExMTIyNDQzMVowgakxCzAJ
BgNVBAYTAlVTMRMwEQYDVQQIEwpDYWxpZm9ybmlhMRYwFAYDVQQHEw1Nb3VudGFp
biBWaWV3MRwwGgYDVQQKExNNb3ppbGxhIENvcnBvcmF0aW9uMRcwFQYDVQQLEw5D
bG91ZCBTZXJ2aWNlczE2MDQGA1UEAxMtcGlubmluZy1wcmVsb2FkLmNvbnRlbnQt
c2lnbmF0dXJlLm1vemlsbGEub3JnMHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEX6Zd
vZ32rj9rDdRInp0kckbMtAdxOQxJ7EVAEZB2KOLUyotQL6A/9YWrMB4Msb4hfvxj
Nw05CS5/J4qUmsTkKLXQskjRe9x96uOXxprWiVwR4OLYagkJJR7YG1mTXmFzo4GD
MIGAMA4GA1UdDwEB/wQEAwIHgDATBgNVHSUEDDAKBggrBgEFBQcDAzAfBgNVHSME
GDAWgBSgHUoXT4zCKzVF8WPx2nBwp8744TA4BgNVHREEMTAvgi1waW5uaW5nLXBy
ZWxvYWQuY29udGVudC1zaWduYXR1cmUubW96aWxsYS5vcmcwCgYIKoZIzj0EAwMD
aAAwZQIxAOi2Eusi6MtEPOARiU+kZIi1vPnzTI71cA2ZIpzZ9aYg740eoJml8Guz
3oC6yXiIDAIwSy4Eylf+/nSMA73DUclcCjZc2yfRYIogII+krXBxoLkbPJcGaitx
qvRy6gQ1oC/z
-----END CERTIFICATE-----
"""


async def test_positive(mock_responses):
    server_url = "http://fake.local/v1"
    changes_url = server_url + RECORDS_URL.format("monitor", "changes")
    mock_responses.get(
        changes_url,
        payload={
            "data": [
                {"id": "abc", "bucket": "bid", "collection": "cid", "last_modified": 42}
            ]
        },
    )

    mock_responses.get(
        server_url + RECORDS_URL.format("bid", "cid"),
        payload={"data": []},
        headers={"ETag": '"42"'},
    )

    mock_responses.get(
        server_url + COLLECTION_URL.format("bid", "cid"),
        payload={"data": {"signature": {}}},
    )

    with patch_async(f"{MODULE}.validate_signature"):
        status, data = await run(server_url, ["bid"], root_hash="AA")

    assert status is True
    assert data == {}


async def test_negative(mock_responses, mock_aioresponses):
    server_url = "http://fake.local/v1"
    x5u_url = "http://fake-x5u-url/"
    changes_url = server_url + RECORDS_URL.format("monitor", "changes")
    mock_responses.get(
        changes_url,
        payload={
            "data": [
                {"id": "abc", "bucket": "bid", "collection": "cid", "last_modified": 42}
            ]
        },
    )
    mock_aioresponses.get(x5u_url, body=CERT)

    metadata = {"signature": {"x5u": x5u_url, "signature": ""}}

    with patch_async(
        f"{MODULE}.download_collection_data", return_value=(metadata, [], 42),
    ):
        status, data = await run(server_url, ["bid"], root_hash="AA")

    assert status is False
    assert data == {
        "bid/cid": "CertificateExpired(datetime.datetime(2019, 11, 11, 22, 44, 31))"
    }


async def test_missing_signature():
    with pytest.raises(AssertionError) as exc_info:
        await validate_signature(verifier=None, metadata={}, records=[], timestamp=42)
    assert exc_info.value.args[0] == "Missing signature"
