import unittest

import udo.config

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.conf_yaml = """
region: ca-north-2
global:
    ami: 'ami-global'
    packages:
        - 'foo-base'
clusters:
    dev:
        packages:
            - dev-pkg1
            - dev-pkg2
        keypair_name: devkey
        roles:
            webapp:
                packages:
                    - dev-webapp-pkg1
                ami: 'ami-dev-webapp'
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


###

def main():
    unittest.main()

if __name__ == '__main__':
    main()
