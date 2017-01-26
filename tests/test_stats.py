import unittest
from resync_tools.stats import Stats


class TestStats(unittest.TestCase):

    def test01_init(self):
        s = Stats()
        self.assertEqual(s.lengths, [])
