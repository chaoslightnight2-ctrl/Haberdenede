import unittest
from news_generation import package_schema
from quality_gate import spoken_text


class SpokenCtaSchemaTests(unittest.TestCase):
    def test_spoken_enum_and_punctuation_free_contract_agree(self):
        for channel in ('Türkiye’den Haber', 'Global Haber'):
            value = package_schema(['gündem'], channel)['properties']['cta']['enum'][0]
            self.assertEqual(value, spoken_text(value))
            self.assertIn(spoken_text(channel), value)
            self.assertTrue(value.endswith(' kanalına abone ol'))

    def test_turkish_letters_are_not_replaced_by_ascii(self):
        value = package_schema(['gündem'], 'Türkiye’den Haber')['properties']['cta']['enum'][0]
        self.assertIn('Türkiye', value)
        self.assertIn('kanalına', value)
        self.assertNotIn('’', value)
