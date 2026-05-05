from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ACI_Backend.objects.siem_schema_retrieval import siem_schema_retrieval_service


class _FakeSIEMWrapper:
	def get_available_fields(self):
		return {
			"agent.id": {"type": "keyword", "searchable": True, "aggregatable": True},
			"rule.level": {"type": "long", "searchable": True, "aggregatable": False},
			"non.searchable": {"type": "text", "searchable": False, "aggregatable": False},
			"bad.field": "invalid",
		}

	def get_field_count(self, field):
		mapping = {
			"agent.id": 42,
			"rule.level": 0,
		}
		return mapping.get(field, 0)


class SIEMSchemaRetrievalServiceTests(SimpleTestCase):
	def test_build_payload_filters_non_searchable_and_zero_counts(self):
		fields, counts = siem_schema_retrieval_service._build_siem_schema_payload(
			siem_wrapper=_FakeSIEMWrapper()
		)

		self.assertEqual(set(fields.keys()), {"agent.id"})
		self.assertEqual(fields["agent.id"], {"type": "keyword", "aggregatable": True})
		self.assertEqual(counts, {"agent.id": 42})

	@patch(
		"ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_service.refresh_siem_schema"
	)
	@patch(
		"ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_service.load_cached_siem_schema"
	)
	def test_cache_hit_does_not_refresh(self, mocked_load_cached, mocked_refresh):
		mocked_load_cached.return_value = ({"agent.id": {"type": "keyword"}}, {"agent.id": 42})

		fields, counts = siem_schema_retrieval_service.get_siem_schema_cache_first(
			siem_wrapper=object(),
			siem_id=1,
		)

		self.assertEqual(fields, {"agent.id": {"type": "keyword"}})
		self.assertEqual(counts, {"agent.id": 42})
		mocked_refresh.assert_not_called()

	@patch(
		"ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_service.refresh_siem_schema"
	)
	@patch(
		"ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_service.load_cached_siem_schema"
	)
	def test_cache_miss_refreshes_immediately(self, mocked_load_cached, mocked_refresh):
		mocked_load_cached.return_value = (None, None)
		mocked_refresh.return_value = ({"agent.id": {"type": "keyword"}}, {"agent.id": 42})

		fields, counts = siem_schema_retrieval_service.get_siem_schema_cache_first(
			siem_wrapper=object(),
			siem_id=5,
		)

		self.assertEqual(fields, {"agent.id": {"type": "keyword"}})
		self.assertEqual(counts, {"agent.id": 42})
		mocked_refresh.assert_called_once()

	@override_settings(SIEM_SCHEMA_RETRIEVAL_CACHE_TTL_SECONDS=60)
	@patch(
		"ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_service.redis_client"
	)
	@patch(
		"ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_service._build_siem_schema_payload"
	)
	def test_refresh_persists_payload_with_ttl(self, mocked_build_payload, mocked_redis):
		mocked_build_payload.return_value = (
			{"agent.id": {"type": "keyword", "aggregatable": True}},
			{"agent.id": 42},
		)

		fields, counts = siem_schema_retrieval_service.refresh_siem_schema(
			siem_wrapper=object(), siem_id=9
		)

		self.assertEqual(fields, {"agent.id": {"type": "keyword", "aggregatable": True}})
		self.assertEqual(counts, {"agent.id": 42})
		self.assertEqual(mocked_redis.set.call_count, 2)
