import unittest
import os

from lib.RandomDocumentGenerator import RandomDocumentGenerator

class TestRandomDocumentGenerator(unittest.TestCase):
    def setUp(self):
        self.rdg = RandomDocumentGenerator(verbose=False)
        self.vandy_phrases = [
                "vanderbilt",
                "university",
                "research",
                "vandy",
                "professor",
                "scholastic",
                "commodore",
                "cornelius",
                "school",
                "computer science",
                "compsci",
                "academic",
                "innovation",
                "distributed systems",
                "distrosys",
                "nashville",
                "tn",
                "tennessee",
                "knowledge",
                "immersive",
                "community",
                "faculty",
                "groundbreaking",
                "engineering",
                "technology",
                "education",
                "impact",
                "cyber-physical",
                "biophotonics",
                "biomedical imaging",
                "entrepreneur",
                "collaboration",
                "international"
            ]
    def test_get_parent_folder(self):
        parent_folder = self.rdg.get_parent_folder()
        self.assertEqual(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            parent_folder
        )
    def test_generate_random_string_of_length(self):
        """ Generate a random string of letters/numbers of size N,
        Reference: https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits """
        rand_string = self.rdg.generate_random_string_of_length(10)
        self.assertEqual(
            10,
            len(rand_string)
        )

    def test_random_vandy_phrase(self):
        self.assertTrue(
            self.rdg.random_vandy_phrase() in self.vandy_phrases
        )

    def test_generate_random_json_document(self):
        random_doc = self.rdg.generate_random_json_document(doc_size=25, key_size=25,value_size=25)
        self.assertEqual(25 + 1, len(random_doc.keys()))
        for key,val in random_doc.items():
            self.assertTrue(key == "vandy_phrase" or len(key) == 25)
            self.assertTrue(val in self.vandy_phrases or len(val) == 25)


    def test_get_random_json_doc(self):
        self.assertTrue(isinstance(self.rdg.get_random_json_doc(),dict))

if __name__ == "__main__":
    unittest.main()