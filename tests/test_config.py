import unittest

import udo.config

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.conf_yaml = """
region: ca-north-2
ami: 'ami-global'
packages:
    - 'foo-base'
tags:
    gtag1: a
    gtag2: b
clusters:
    dev:
        tags:
            dtag1: c
        packages:
            - dev-pkg1
            - dev-pkg2
        keypair_name: devkey
        roles:
            webapp:
                packages:
                    - dev-webapp-pkg1
                ami: 'ami-dev-webapp'
                tags:
                    wtag1: d
    prod:
        ami: 'ami-prod'
"""

        self.conf = udo.config.Config()
        self.parsed = self.conf.parse(self.conf_yaml)
        self.assertTrue(self.parsed)
        pass

    def test_globals(self):
        # test global defaults
        self.assertEqual(self.conf.get('clusters', 'dev', 'ami'), 'ami-global')
        self.assertEqual(self.conf.get('clusters', 'prod', 'ami'), 'ami-prod')

    def test_merge_array(self):
        dev_pkgs_expected = [ 'foo-base', 'dev-pkg1', 'dev-pkg2' ];
        dev_pkgs_merged = self.conf.get('clusters', 'dev', 'packages')
        self.assertEqual(dev_pkgs_merged, dev_pkgs_expected)

    def test_merge_hash(self):
        self.assertEqual(self.conf.get('clusters', 'dev', 'tags'), { 'gtag1': 'a', 'gtag2': 'b', 'dtag1': 'c'})
        self.assertEqual(self.conf.get('clusters', 'dev', 'roles', 'webapp', 'tags'), { 'gtag1': 'a', 'gtag2': 'b', 'dtag1': 'c', 'wtag1': 'd' })

###

def main():
    unittest.main()

if __name__ == '__main__':
    main()