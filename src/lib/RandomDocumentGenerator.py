""" Generate and write random JSON documents out to a random/ folder."""

import string
import random
import json
import logging
import os
from yaspin import yaspin
from pathlib import Path

class RandomDocumentGenerator:
    def __init__(self, verbose=False):
        self.verbose = False
        self.random_docs_folder = os.path.join(os.path.dirname(__file__),'random_docs')
        Path(self.random_docs_folder).mkdir(parents=True, exist_ok=True)
        self.set_logger()

    def get_parent_folder(self):
        return os.path.dirname(os.path.abspath(__file__))

    def debug(self, msg):
        self.logger.debug(msg, extra=self.prefix)

    def info(self, msg):
        self.logger.info(msg, extra=self.prefix)

    def error(self, msg):
        self.logger.error(msg, extra=self.prefix)

    def set_logger(self, prefix=None):
        if not prefix:
            self.prefix = {'prefix': f'RandomDocumentGenerator'}
        else:
            self.prefix = {'prefix': prefix}
        self.logger = logging.getLogger(f'RandomDataGenerator')
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(prefix)s - %(message)s')
        handler.setFormatter(formatter)
        for h in self.logger.handlers:
            self.logger.removeHandler(h)
        self.logger.addHandler(handler)

    def generate_random_string_of_length(self, size):
        """ Generate a random string of letters/numbers of size N,
        Reference: https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits """
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))

    def random_vandy_phrase(self):
        vandy_phrases_file = os.path.join(os.path.dirname(__file__),'vandy_phrases.json')
        f = open(vandy_phrases_file)
        vandy_phrases = json.load(f)['vandy_phrases']
        f.close()
        return random.choice(vandy_phrases)

    def generate_random_json_document(self, doc_size=25, key_size=25, value_size=25):
        """ Generate a random JSON document with doc_size pairs of key/vals"""
        doc = {}
        for _ in range(doc_size):
            key = self.generate_random_string_of_length(key_size)
            value = self.generate_random_string_of_length(value_size)
            doc[key] = value
        # Add a random vandy phrase that is searchable
        doc['vandy_phrase'] = self.random_vandy_phrase()
        return doc

    def get_random_json_doc(self):
        """ Get one of the pre-generated random JSON documents (as JSON, not a file pointer) """
        choices = os.listdir(self.random_docs_folder)
        random_doc_filename = random.choice(choices)
        random_doc_fullpath = os.path.join(self.random_docs_folder, random_doc_filename)
        f = open(random_doc_fullpath)
        response = json.load(f)
        f.close()
        return response

    def generate_random_docs(self, num_docs=1000, doc_size=25, key_size=25, value_size=25):
        """ Generate self.num_docs random JSON documents and write them to random_docs folder """
        self.info("Populating random sample document data (random_docs folder)")
        with yaspin().white.bold.shark.on_blue as sp:
            for i in range(num_docs):
                self.debug(f'Generating random JSON document {i}')
                doc = self.generate_random_json_document(doc_size=doc_size, key_size=key_size, value_size=value_size)
                filename = f'{self.generate_random_string_of_length(10)}.json'
                self.debug(f'Writing document <doc_size={doc_size},key_size={key_size},value_size={value_size}> to {filename}')
                with open(f'{self.random_docs_folder}/{filename}', 'w') as f:
                    json.dump(doc, f)
        self.info("Successfully generated sample data!")
def main():
    """ Run this before testing to set up test data samples. Generates 5000 random JSON documents. Subsets can be used to """
    gen = RandomDocumentGenerator(verbose=True)
    gen.generate_random_docs(num_docs=5000, doc_size=50, key_size=30, value_size=30)

if __name__ == "__main__":
    main()