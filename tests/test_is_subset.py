import unittest
import logging

from janus_client.message_transaction import is_subset

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class TestClass(unittest.TestCase):
    def test_sanity(self):
        """Sanity test"""
        self.assertTrue(is_subset(dict_1={"a": 1}, dict_2={"a": 1}))

    def test_empty_dict(self):
        self.assertTrue(is_subset(dict_1={"a": 1}, dict_2={}))
        self.assertTrue(is_subset(dict_1={}, dict_2={}))
        self.assertFalse(is_subset(dict_1={}, dict_2={"a": 1}))

    def test_ignored_types(self):
        self.assertTrue(is_subset(dict_1={"a": 1, "b": None}, dict_2={"b": None}))
        self.assertTrue(is_subset(dict_1={"a": 1, "b": 2}, dict_2={"b": None}))
        self.assertFalse(is_subset(dict_1={"a": 1, "b": 2}, dict_2={"b": 3}))
        self.assertFalse(is_subset(dict_1={"a": 1, "b": 2}, dict_2={"c": None}))

    def test_invalid_input(self):
        self.assertRaises(TypeError, is_subset, dict_1="", dict_2={})
        self.assertRaises(TypeError, is_subset, dict_1={}, dict_2="")
        self.assertRaises(TypeError, is_subset, dict_1="", dict_2="")

    def test_recursive_check(self):
        self.assertTrue(
            is_subset(
                dict_1={"a": 1, "b": {"c": 2, "d": 3}}, dict_2={"a": 1, "b": {"c": 2}}
            )
        )
        self.assertTrue(
            is_subset(
                dict_1={"a": 1, "b": {"c": 2, "d": 3, "e": {"f": 4}}},
                dict_2={"a": 1, "b": {"e": {}}},
            )
        )
        self.assertTrue(
            is_subset(
                dict_1={"a": 1, "b": {"c": 2, "d": 3, "e": {"f": 4}}},
                dict_2={"a": 1, "b": {"c": None, "e": {}}},
            )
        )
        self.assertTrue(
            is_subset(
                dict_1={"a": 1, "b": {"c": 2, "d": 3, "e": {"f": 4}}},
                dict_2={"a": 1, "b": {"e": None}},
            )
        )
        self.assertTrue(
            is_subset(
                dict_1={"a": 1, "b": {"c": 2, "d": 3, "e": {"f": 4}}},
                dict_2={"a": 1, "b": {"e": {"f": None}}},
            )
        )
        self.assertFalse(
            is_subset(
                dict_1={"a": 1, "b": {"c": 2, "d": 3, "e": {"f": 4}}},
                dict_2={"a": 1, "b": {"e": {"f": None, "g": None}}},
            )
        )
