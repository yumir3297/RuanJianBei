import unittest

from app.services.itinerary.catalog import (
    AmbiguousSpot, CatalogIntegrityError, PublishedAttraction, UnknownSpot,
    build_catalog_snapshot, parse_spot_reference,
)


def _spot(code: str, title: str, aliases=()) -> PublishedAttraction:
    return PublishedAttraction(
        site_id="site-1", spot_code=code, entry_id=f"entry-{code}",
        published_revision_id=f"revision-{code}", title=title, aliases=tuple(aliases),
    )


class ItineraryCatalogTests(unittest.TestCase):
    def test_catalog_refuses_duplicate_spot_codes_within_a_site(self):
        with self.assertRaisesRegex(CatalogIntegrityError, "重复"):
            build_catalog_snapshot("site-1", [_spot("LS-01", "梵宫"), _spot("LS-01", "梵宫新版本")])

    def test_exact_alias_collision_is_ambiguous_instead_of_guessing(self):
        catalog = build_catalog_snapshot("site-1", [
            _spot("LS-01", "梵宫", ["灵山大佛景区"]),
            _spot("LS-02", "五印坛城", ["灵山大佛景区"]),
        ])
        result = parse_spot_reference("灵山大佛景区", catalog)
        self.assertIsInstance(result, AmbiguousSpot)
        self.assertEqual([item.spot_code for item in result.candidates], ["LS-01", "LS-02"])

    def test_unknown_reference_is_not_mapped_by_fuzzy_name(self):
        catalog = build_catalog_snapshot("site-1", [_spot("LS-01", "梵宫")])
        self.assertIsInstance(parse_spot_reference("梵宫附近的停车场", catalog), UnknownSpot)

    def test_coordinates_require_explicit_evidence(self):
        row = PublishedAttraction("site-1", "LS-01", "entry-1", "revision-1", "梵宫",
                                  latitude=31.0, longitude=120.0)
        with self.assertRaisesRegex(CatalogIntegrityError, "依据"):
            build_catalog_snapshot("site-1", [row])

    def test_catalog_digest_does_not_depend_on_source_row_order(self):
        first = _spot("LS-01", "梵宫", ["灵山"])
        second = _spot("LS-02", "五印坛城")
        self.assertEqual(
            build_catalog_snapshot("site-1", [first, second]).digest,
            build_catalog_snapshot("site-1", [second, first]).digest,
        )
