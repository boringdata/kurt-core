"""Tests for the Apify registry module."""

from kurt.integrations.apify.registry import (
    ACTOR_REGISTRY,
    PLATFORM_DEFAULTS,
    PROFILE_ACTORS,
    ActorConfig,
    get_actor_config,
    get_default_actor,
    get_profile_actor,
    guess_source_from_actor,
    list_actors,
    list_platforms,
)


class TestActorRegistry:
    """Test ACTOR_REGISTRY contents."""

    def test_registry_contains_twitter_actors(self):
        """Test registry has Twitter actors."""
        assert "apidojo/tweet-scraper" in ACTOR_REGISTRY
        assert "apidojo/twitter-user-scraper" in ACTOR_REGISTRY

    def test_registry_contains_linkedin_actors(self):
        """Test registry has LinkedIn actors."""
        assert "curious_coder/linkedin-post-search-scraper" in ACTOR_REGISTRY
        assert "apimaestro/linkedin-profile-detail" in ACTOR_REGISTRY

    def test_registry_contains_threads_actors(self):
        """Test registry has Threads actors."""
        assert "apidojo/threads-scraper" in ACTOR_REGISTRY

    def test_registry_contains_substack_actors(self):
        """Test registry has Substack actors."""
        assert "epctex/substack-scraper" in ACTOR_REGISTRY
        assert "curious_coder/substack-scraper" in ACTOR_REGISTRY

    def test_all_actors_have_required_fields(self):
        """Test all actors have required fields."""
        for actor_id, config in ACTOR_REGISTRY.items():
            assert isinstance(config, ActorConfig)
            assert config.actor_id == actor_id
            assert config.source_name is not None
            assert len(config.source_name) > 0


class TestPlatformDefaults:
    """Test PLATFORM_DEFAULTS mapping."""

    def test_twitter_default(self):
        """Test Twitter default actor."""
        assert PLATFORM_DEFAULTS.get("twitter") == "apidojo/tweet-scraper"

    def test_linkedin_default(self):
        """Test LinkedIn default actor."""
        assert PLATFORM_DEFAULTS.get("linkedin") == "curious_coder/linkedin-post-search-scraper"

    def test_threads_default(self):
        """Test Threads default actor."""
        assert PLATFORM_DEFAULTS.get("threads") == "apidojo/threads-scraper"

    def test_substack_default(self):
        """Test Substack default actor."""
        assert PLATFORM_DEFAULTS.get("substack") == "epctex/substack-scraper"


class TestProfileActors:
    """Test PROFILE_ACTORS mapping."""

    def test_twitter_profile_actor(self):
        """Test Twitter profile actor."""
        assert PROFILE_ACTORS.get("twitter") == "apidojo/twitter-user-scraper"

    def test_linkedin_profile_actor(self):
        """Test LinkedIn profile actor."""
        assert PROFILE_ACTORS.get("linkedin") == "apimaestro/linkedin-profile-detail"

    def test_substack_profile_actor(self):
        """Test Substack profile actor."""
        assert PROFILE_ACTORS.get("substack") == "epctex/substack-scraper"


class TestGetActorConfig:
    """Test get_actor_config function."""

    def test_get_existing_actor(self):
        """Test getting an existing actor config."""
        config = get_actor_config("apidojo/tweet-scraper")
        assert config is not None
        assert config.actor_id == "apidojo/tweet-scraper"
        assert config.source_name == "twitter"

    def test_get_nonexistent_actor(self):
        """Test getting a nonexistent actor returns None."""
        config = get_actor_config("nonexistent/actor")
        assert config is None


class TestGetDefaultActor:
    """Test get_default_actor function."""

    def test_get_twitter_default(self):
        """Test getting Twitter default actor."""
        assert get_default_actor("twitter") == "apidojo/tweet-scraper"

    def test_get_linkedin_default(self):
        """Test getting LinkedIn default actor."""
        assert get_default_actor("linkedin") == "curious_coder/linkedin-post-search-scraper"

    def test_case_insensitive(self):
        """Test that lookup is case insensitive."""
        assert get_default_actor("TWITTER") == "apidojo/tweet-scraper"
        assert get_default_actor("Twitter") == "apidojo/tweet-scraper"

    def test_unknown_platform(self):
        """Test unknown platform returns None."""
        assert get_default_actor("unknown") is None


class TestGetProfileActor:
    """Test get_profile_actor function."""

    def test_get_twitter_profile_actor(self):
        """Test getting Twitter profile actor."""
        assert get_profile_actor("twitter") == "apidojo/twitter-user-scraper"

    def test_get_linkedin_profile_actor(self):
        """Test getting LinkedIn profile actor."""
        assert get_profile_actor("linkedin") == "apimaestro/linkedin-profile-detail"

    def test_case_insensitive(self):
        """Test that lookup is case insensitive."""
        assert get_profile_actor("TWITTER") == "apidojo/twitter-user-scraper"

    def test_unknown_platform(self):
        """Test unknown platform returns None."""
        assert get_profile_actor("unknown") is None


class TestListActors:
    """Test list_actors function."""

    def test_returns_list(self):
        """Test that list_actors returns a list."""
        actors = list_actors()
        assert isinstance(actors, list)
        assert len(actors) > 0

    def test_actor_dict_structure(self):
        """Test that each actor dict has required keys."""
        actors = list_actors()
        for actor in actors:
            assert "actor_id" in actor
            assert "source_name" in actor
            assert "description" in actor

    def test_all_registered_actors_listed(self):
        """Test that all registered actors are in the list."""
        actors = list_actors()
        actor_ids = {a["actor_id"] for a in actors}
        for registered_id in ACTOR_REGISTRY.keys():
            assert registered_id in actor_ids


class TestListPlatforms:
    """Test list_platforms function."""

    def test_returns_list(self):
        """Test that list_platforms returns a list."""
        platforms = list_platforms()
        assert isinstance(platforms, list)
        assert len(platforms) > 0

    def test_contains_expected_platforms(self):
        """Test that expected platforms are in the list."""
        platforms = list_platforms()
        assert "twitter" in platforms
        assert "linkedin" in platforms
        assert "threads" in platforms
        assert "substack" in platforms


class TestGuessSourceFromActor:
    """Test guess_source_from_actor function."""

    def test_twitter_actors(self):
        """Test guessing Twitter from actor name."""
        assert guess_source_from_actor("apidojo/tweet-scraper") == "twitter"
        assert guess_source_from_actor("quacker/twitter-scraper") == "twitter"

    def test_linkedin_actors(self):
        """Test guessing LinkedIn from actor name."""
        assert guess_source_from_actor("curious_coder/linkedin-post-search-scraper") == "linkedin"

    def test_threads_actors(self):
        """Test guessing Threads from actor name."""
        assert guess_source_from_actor("apidojo/threads-scraper") == "threads"

    def test_substack_actors(self):
        """Test guessing Substack from actor name."""
        assert guess_source_from_actor("epctex/substack-scraper") == "substack"

    def test_unknown_actor(self):
        """Test default to 'apify' for unknown actors."""
        assert guess_source_from_actor("unknown/generic-scraper") == "apify"


class TestActorConfig:
    """Test ActorConfig dataclass."""

    def test_create_config(self):
        """Test creating ActorConfig."""
        config = ActorConfig(
            actor_id="test/actor",
            source_name="test",
            description="Test actor",
        )

        assert config.actor_id == "test/actor"
        assert config.source_name == "test"
        assert config.description == "Test actor"

    def test_config_with_build_input(self):
        """Test ActorConfig with build_input function."""
        def builder(query, max_items, kwargs):
            return {"q": query, "limit": max_items}

        config = ActorConfig(
            actor_id="test/actor",
            source_name="test",
            build_input=builder,
        )

        result = config.build_input("search", 10, {})
        assert result == {"q": "search", "limit": 10}


class TestInputBuilders:
    """Test the input builder functions via actor configs."""

    def test_twitter_search_input(self):
        """Test Twitter search input builder."""
        config = get_actor_config("apidojo/tweet-scraper")
        assert config is not None
        assert config.build_input is not None

        result = config.build_input("AI agents", 50, {"sort": "Top"})
        assert "searchTerms" in result
        assert result["searchTerms"] == ["AI agents"]
        assert result["maxItems"] == 50
        assert result["sort"] == "Top"

    def test_twitter_profile_input(self):
        """Test Twitter profile input builder."""
        config = get_actor_config("apidojo/twitter-user-scraper")
        assert config is not None
        assert config.build_input is not None

        result = config.build_input("@elonmusk", 100, {})
        assert "handles" in result
        assert result["handles"] == ["@elonmusk"]

    def test_linkedin_search_input(self):
        """Test LinkedIn search input builder."""
        config = get_actor_config("curious_coder/linkedin-post-search-scraper")
        assert config is not None
        assert config.build_input is not None

        result = config.build_input("data engineering", 20, {})
        assert "searchUrl" in result
        assert "data engineering" in result["searchUrl"]

    def test_substack_newsletter_input(self):
        """Test Substack newsletter input builder."""
        config = get_actor_config("epctex/substack-scraper")
        assert config is not None
        assert config.build_input is not None

        result = config.build_input("https://newsletter.substack.com", 25, {})
        assert "startUrls" in result
        assert result["maxItems"] == 25
