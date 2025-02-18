from checks.remotesettings.collections_consistency import has_inconsistencies, run
from tests.utils import patch_async


FAKE_AUTH = ""
COLLECTION_URL = "/buckets/{}/collections/{}"
RECORDS_URL = COLLECTION_URL + "/records"
RESOURCES = [
    {
        "source": {"bucket": "blog-workspace", "collection": "articles"},
        "preview": {"bucket": "blog-preview", "collection": "articles"},
        "destination": {"bucket": "blog", "collection": "articles"},
    },
    {
        "source": {"bucket": "security-workspace", "collection": "blocklist"},
        "destination": {"bucket": "security", "collection": "blocklist"},
    },
]


async def test_has_inconsistencies_no_preview(mock_responses):
    server_url = "http://fake.local/v1"
    records = [{"id": "abc", "last_modified": 42}, {"id": "def", "last_modified": 41}]

    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(
        collection_url, payload={"data": {"id": "blocklist", "status": "signed"}}
    )
    records_url = server_url + RECORDS_URL.format("security-workspace", "blocklist")
    mock_responses.get(records_url, payload={"data": records})
    records_url = server_url + RECORDS_URL.format("security", "blocklist")
    mock_responses.get(records_url, payload={"data": records})

    assert await has_inconsistencies(server_url, FAKE_AUTH, RESOURCES[1]) is None


async def test_has_inconsistencies_no_status(mock_responses):
    server_url = "http://fake.local/v1"
    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(collection_url, payload={"data": {"id": "blocklist"}})

    result = await has_inconsistencies(server_url, FAKE_AUTH, RESOURCES[1])

    assert '"status" attribute missing' in result


async def test_has_inconsistencies_work_in_progress_status(mock_responses):
    server_url = "http://fake.local/v1"
    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(
        collection_url,
        payload={"data": {"id": "blocklist", "status": "work-in-progress"}},
    )

    result = await has_inconsistencies(server_url, FAKE_AUTH, RESOURCES[1])

    assert result is None


async def test_has_inconsistencies_unsupported_status(mock_responses):
    server_url = "http://fake.local/v1"
    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(
        collection_url, payload={"data": {"id": "blocklist", "status": "to-resign"}}
    )

    result = await has_inconsistencies(server_url, FAKE_AUTH, RESOURCES[1])

    assert "Unexpected status" in result


async def test_unexpected_review_status(mock_responses):
    server_url = "http://fake.local/v1"
    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(
        collection_url, payload={"data": {"id": "blocklist", "status": "to-review"}}
    )

    result = await has_inconsistencies(server_url, FAKE_AUTH, RESOURCES[1])

    assert result == "security-workspace/blocklist should not have 'to-review' status"


async def test_has_inconsistencies_to_review_preview_differs(mock_responses):
    server_url = "http://fake.local/v1"
    resource = {
        "source": {"bucket": "security-workspace", "collection": "blocklist"},
        "preview": {"bucket": "security-preview", "collection": "blocklist"},
        "destination": {"bucket": "security", "collection": "blocklist"},
    }
    records = [
        {"id": "abc", "last_modified": 42},
        {"id": "def", "title": "a", "last_modified": 41},
        {"id": "ghi", "last_modified": 40},
        {"id": "jkl", "last_modified": 39},
    ]

    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(
        collection_url, payload={"data": {"id": "blocklist", "status": "to-review"}}
    )
    records_url = server_url + RECORDS_URL.format("security-workspace", "blocklist")
    mock_responses.get(records_url, payload={"data": records})
    records_url = server_url + RECORDS_URL.format("security-preview", "blocklist")
    mock_responses.get(
        records_url,
        payload={
            "data": records[:1]
            + [
                {"id": "def", "title": "b", "last_modified": 123},
                {"id": "jkl", "title": "bam", "last_modified": 456},
            ]
        },
    )

    result = await has_inconsistencies(server_url, FAKE_AUTH, resource)

    assert "1 record present in source but missing in preview ('ghi')" in result
    assert "2 records differ between source and preview ('def', 'jkl')" in result


async def test_has_inconsistencies_preview_differs(mock_responses):
    server_url = "http://fake.local/v1"
    resource = {
        "source": {"bucket": "security-workspace", "collection": "blocklist"},
        "preview": {"bucket": "security-preview", "collection": "blocklist"},
        "destination": {"bucket": "security", "collection": "blocklist"},
    }
    records = [{"id": "abc", "last_modified": 42}, {"id": "def", "last_modified": 41}]

    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(
        collection_url, payload={"data": {"id": "blocklist", "status": "signed"}}
    )
    records_url = server_url + RECORDS_URL.format("security-workspace", "blocklist")
    mock_responses.get(
        records_url, payload={"data": records + [{"id": "xyz", "last_modified": 40}]}
    )
    records_url = server_url + RECORDS_URL.format("security-preview", "blocklist")
    mock_responses.get(records_url, payload={"data": records})
    records_url = server_url + RECORDS_URL.format("security", "blocklist")
    mock_responses.get(records_url, payload={"data": records})

    result = await has_inconsistencies(server_url, FAKE_AUTH, resource)

    assert "1 record present in source but missing in preview ('xyz')" in result


async def test_has_inconsistencies_no_preview_destination_differs(mock_responses):
    server_url = "http://fake.local/v1"
    resource = {
        "source": {"bucket": "security-workspace", "collection": "blocklist"},
        "destination": {"bucket": "security", "collection": "blocklist"},
    }
    records = [{"id": "abc", "last_modified": 42}, {"id": "def", "last_modified": 41}]

    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(
        collection_url, payload={"data": {"id": "blocklist", "status": "signed"}}
    )
    records_url = server_url + RECORDS_URL.format("security-workspace", "blocklist")
    mock_responses.get(records_url, payload={"data": records})
    records_url = server_url + RECORDS_URL.format("security", "blocklist")
    mock_responses.get(
        records_url, payload={"data": records + [{"id": "xyz", "last_modified": 40}]}
    )

    result = await has_inconsistencies(server_url, FAKE_AUTH, resource)

    assert "1 record present in destination but missing in source ('xyz')" in result


async def test_has_inconsistencies_destination_differs(mock_responses):
    server_url = "http://fake.local/v1"
    resource = {
        "source": {"bucket": "security-workspace", "collection": "blocklist"},
        "preview": {"bucket": "security-preview", "collection": "blocklist"},
        "destination": {"bucket": "security", "collection": "blocklist"},
    }
    records = [{"id": "abc", "last_modified": 42}, {"id": "def", "last_modified": 41}]

    collection_url = server_url + COLLECTION_URL.format(
        "security-workspace", "blocklist"
    )
    mock_responses.get(
        collection_url, payload={"data": {"id": "blocklist", "status": "signed"}}
    )
    records_url = server_url + RECORDS_URL.format("security-workspace", "blocklist")
    mock_responses.get(records_url, payload={"data": records})
    records_url = server_url + RECORDS_URL.format("security-preview", "blocklist")
    mock_responses.get(records_url, payload={"data": records})
    records_url = server_url + RECORDS_URL.format("security", "blocklist")
    mock_responses.get(
        records_url, payload={"data": records + [{"id": "xyz", "last_modified": 40}]}
    )

    result = await has_inconsistencies(server_url, FAKE_AUTH, resource)

    assert "1 record present in destination but missing in preview ('xyz')" in result


async def test_positive(mock_responses):
    server_url = "http://fake.local/v1"

    module = "checks.remotesettings.collections_consistency"
    with patch_async(f"{module}.fetch_signed_resources", return_value=RESOURCES):
        with patch_async(f"{module}.has_inconsistencies", return_value=None):

            status, data = await run(server_url, FAKE_AUTH)

    assert status is True
    assert data == {}


async def test_negative(mock_responses):
    server_url = "http://fake.local/v1"

    m = "checks.remotesettings.collections_consistency"
    with patch_async(f"{m}.fetch_signed_resources", return_value=RESOURCES):
        with patch_async(f"{m}.has_inconsistencies", return_value="Some error"):
            status, data = await run(server_url, FAKE_AUTH)

    assert status is False
    print(data)
    assert data == {"blog/articles": "Some error", "security/blocklist": "Some error"}
