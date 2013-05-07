# Copyright (c) 2013 Thomas Lotze
# See also LICENSE.txt

from ophelia.util import Namespace
import gc
import unittest

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class NamespaceTest(unittest.TestCase):

    def test_namespace_is_just_a_special_dict(self):
        n = Namespace()
        self.assertIsInstance(n, dict)

    def test_items_override_dict_members_on_reading(self):
        n = Namespace()
        n['update'] = 1
        self.assertEqual(1, n.update)

    def test_setting_attributes_affects_items(self):
        n = Namespace()
        self.assertNotIn('foo', n)
        n.foo = 1
        self.assertEqual(1, n['foo'])

    def test_deleting_attributes_affects_items(self):
        n = Namespace(foo=1)
        self.assertIn('foo', n)
        del n.foo
        self.assertNotIn('foo', n)

    def test_failed_attribute_reading_raises_attribute_error(self):
        n = Namespace()
        with self.assertRaises(AttributeError):
            n.foo

    def test_failed_attribute_deletion_raises_attribute_error(self):
        n = Namespace()
        with self.assertRaises(AttributeError):
            del n.foo

    def test_namespace_implementation_does_not_leak_memory(self):
        def count_namespaces():
            return sum(1 for o in gc.get_objects() if type(o) is Namespace)

        gc.collect()
        before = count_namespaces()
        Namespace()
        gc.collect()
        self.assertEqual(before, count_namespaces())
