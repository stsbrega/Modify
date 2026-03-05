"""Tests for the LLM provider registry."""

from app.llm.registry import PROVIDER_REGISTRY, get_provider, get_public_registry


# ---------------------------------------------------------------------------
# Registry data integrity
# ---------------------------------------------------------------------------


class TestRegistryIntegrity:
    def test_has_seven_providers(self):
        assert len(PROVIDER_REGISTRY) == 7

    def test_ids_are_unique(self):
        ids = [p["id"] for p in PROVIDER_REGISTRY]
        assert len(ids) == len(set(ids))

    def test_required_fields_present(self):
        required = {"id", "name", "model", "base_url", "type", "placeholder", "hint_url"}
        for provider in PROVIDER_REGISTRY:
            assert required.issubset(provider.keys()), f"Missing fields in {provider['id']}"

    def test_known_provider_ids(self):
        ids = {p["id"] for p in PROVIDER_REGISTRY}
        expected = {"anthropic", "openai", "gemini", "groq", "together", "deepseek", "mistral"}
        assert ids == expected

    def test_types_are_valid(self):
        valid_types = {"openai_compatible", "anthropic"}
        for provider in PROVIDER_REGISTRY:
            assert provider["type"] in valid_types, f"Invalid type for {provider['id']}"

    def test_anthropic_is_only_native_provider(self):
        """Only Anthropic uses the native API; all others are OpenAI-compatible."""
        anthropic_providers = [p for p in PROVIDER_REGISTRY if p["type"] == "anthropic"]
        assert len(anthropic_providers) == 1
        assert anthropic_providers[0]["id"] == "anthropic"

    def test_non_anthropic_providers_have_base_url(self):
        for p in PROVIDER_REGISTRY:
            if p["type"] == "openai_compatible":
                assert p["base_url"] is not None, f"{p['id']} missing base_url"
                assert p["base_url"].startswith("https://"), f"{p['id']} base_url not HTTPS"


# ---------------------------------------------------------------------------
# get_provider
# ---------------------------------------------------------------------------


class TestGetProvider:
    def test_known_provider(self):
        result = get_provider("openai")
        assert result is not None
        assert result["id"] == "openai"
        assert result["name"] == "OpenAI"

    def test_all_known_providers_found(self):
        for p in PROVIDER_REGISTRY:
            assert get_provider(p["id"]) is not None

    def test_unknown_provider_returns_none(self):
        assert get_provider("nonexistent") is None

    def test_empty_string_returns_none(self):
        assert get_provider("") is None

    def test_case_sensitive(self):
        """Provider IDs are lowercase; uppercase should not match."""
        assert get_provider("OpenAI") is None
        assert get_provider("ANTHROPIC") is None


# ---------------------------------------------------------------------------
# get_public_registry
# ---------------------------------------------------------------------------


class TestGetPublicRegistry:
    def test_returns_list(self):
        result = get_public_registry()
        assert isinstance(result, list)

    def test_same_count_as_full_registry(self):
        assert len(get_public_registry()) == len(PROVIDER_REGISTRY)

    def test_public_fields_only(self):
        """Public registry should NOT expose base_url or type."""
        allowed_keys = {"id", "name", "model", "placeholder", "hint_url"}
        for entry in get_public_registry():
            assert set(entry.keys()) == allowed_keys, f"Unexpected keys in {entry['id']}"

    def test_no_base_url_leaked(self):
        for entry in get_public_registry():
            assert "base_url" not in entry

    def test_no_type_leaked(self):
        for entry in get_public_registry():
            assert "type" not in entry

    def test_ids_match_full_registry(self):
        public_ids = {e["id"] for e in get_public_registry()}
        full_ids = {p["id"] for p in PROVIDER_REGISTRY}
        assert public_ids == full_ids
