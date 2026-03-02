import os
import unittest

from src.api import osm_poi_config


class TestOsmPoiConfig(unittest.TestCase):
    def setUp(self):
        osm_poi_config.load_osm_poi_overpass_query_config.cache_clear()
        os.environ.pop("OSM_POI_OVERPASS_TAG_KEYS", None)
        os.environ.pop("OSM_POI_OVERPASS_ELEMENT_TYPES", None)

    def test_defaults_include_craft_and_all_element_types(self):
        cfg = osm_poi_config.load_osm_poi_overpass_query_config()
        self.assertIn("craft", cfg.tag_keys)
        self.assertEqual(cfg.element_types, ("node", "way", "relation"))

    def test_build_query_includes_extended_fragments(self):
        cfg = osm_poi_config.load_osm_poi_overpass_query_config()
        q = osm_poi_config.build_osm_poi_overpass_query(
            radius_m=120,
            lat_s="47.000000",
            lon_s="8.000000",
            tag_keys=cfg.tag_keys,
            element_types=cfg.element_types,
        )
        # New/extended coverage: craft + leisure/tourism for way/relation.
        self.assertIn("node(around:120,47.000000,8.000000)[name][craft];", q)
        self.assertIn("way(around:120,47.000000,8.000000)[name][leisure];", q)
        self.assertIn("relation(around:120,47.000000,8.000000)[name][tourism];", q)

    def test_env_csv_parsing_and_validation(self):
        os.environ["OSM_POI_OVERPASS_TAG_KEYS"] = "amenity,invalid-key,shop,,CRAFT,shop"
        os.environ["OSM_POI_OVERPASS_ELEMENT_TYPES"] = "node,foo,WAY"
        osm_poi_config.load_osm_poi_overpass_query_config.cache_clear()

        cfg = osm_poi_config.load_osm_poi_overpass_query_config()
        self.assertEqual(cfg.tag_keys, ("amenity", "shop", "craft"))
        self.assertEqual(cfg.element_types, ("node", "way"))


if __name__ == "__main__":
    unittest.main()
