# Copyright (c) 2013 Brendan Curran-Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Functions and Classes from attrdict, modified for Python3"""

from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, MutableMapping, Sequence
import re

"""A right-favoring Mapping merge."""


def merge(left, right):
    """
    Merge two mappings objects together, combining overlapping Mappings, favoring right-values
    left: The left Mapping object.
    right: The right (favored) Mapping object.
    NOTE: This is not commutative (merge(a,b) != merge(b,a)).
    """
    merged = {}

    left_keys = frozenset(left)
    right_keys = frozenset(right)

    # Items only in the left Mapping
    for key in left_keys - right_keys:
        merged[key] = left[key]

    # Items only in the right Mapping
    for key in right_keys - left_keys:
        merged[key] = right[key]

    # in both
    for key in left_keys & right_keys:
        left_value = left[key]
        right_value = right[key]

        if (isinstance(left_value, Mapping) and isinstance(right_value, Mapping)):  # recursive merge
            merged[key] = merge(left_value, right_value)
        else:  # overwrite with right value
            merged[key] = right_value

    return merged


"""
Mixin Classes for Attr-support.
"""


class Attr(Mapping):
    """
    A mixin class for a mapping that allows for attribute-style access of values.
    A key may be used as an attribute if:
     * It is a string
     * It matches /^[A-Za-z][A-Za-z0-9_]*$/ (i.e., a public attribute)
     * The key doesn't overlap with any class attributes (for Attr,
        those would be 'get', 'items', 'keys', 'values', 'mro', and
        'register').
    If a values which is accessed as an attribute is a Sequence-type
    (and is not a string/bytes), it will be converted to a
    _sequence_type with any mappings within it converted to Attrs.
    NOTE: This means that if _sequence_type is not None, then a
        sequence accessed as an attribute will be a different object
        than if accessed as an attribute than if it is accessed as an
        item.
    """
    @abstractmethod
    def _configuration(self):
        """All required state for building a new instance with the same settings as the current object."""

    @classmethod
    def _constructor(cls, mapping, configuration):
        """
        A standardized constructor used internally by Attr.
        mapping: A mapping of key-value pairs. It is HIGHLY recommended
            that you use this as the internal key-value pair mapping, as
            that will allow nested assignment (e.g., attr.foo.bar = baz)
        configuration: The return value of Attr._configuration
        """
        raise NotImplementedError("You need to implement this")

    def __call__(self, key):
        """
        Dynamically access a key-value pair.
        key: A key associated with a value in the mapping.
        This differs from __getitem__, because it returns a new instance
        of an Attr (if the value is a Mapping object).
        """
        if key not in self:
            raise AttributeError(
                "'{cls} instance has no attribute '{name}'".format(
                    cls=self.__class__.__name__, name=key
                )
            )

        return self._build(self[key])

    def __getattr__(self, key):
        """Access an item as an attribute."""
        if key not in self or not self._valid_name(key):
            raise AttributeError(
                "'{cls}' instance has no attribute '{name}'".format(
                    cls=self.__class__.__name__, name=key
                )
            )

        return self._build(self[key])

    def __add__(self, other):
        """
        Add a mapping to this Attr, creating a new, merged Attr.
        other: A mapping.
        NOTE: Addition is not commutative. a + b != b + a.
        """
        if not isinstance(other, Mapping):
            return NotImplemented

        return self._constructor(merge(self, other), self._configuration())

    def __radd__(self, other):
        """
        Add this Attr to a mapping, creating a new, merged Attr.
        other: A mapping.
        NOTE: Addition is not commutative. a + b != b + a.
        """
        if not isinstance(other, Mapping):
            return NotImplemented

        return self._constructor(merge(other, self), self._configuration())

    def _build(self, obj):
        """Conditionally convert an object to allow for recursive mapping access.
        obj: An object that was a key-value pair in the mapping. If obj
            is a mapping, self._constructor(obj, self._configuration())
            will be called. If obj is a non-string/bytes sequence, and
            self._sequence_type is not None, the obj will be converted
            to type _sequence_type and build will be called on its
            elements.
        """
        if isinstance(obj, Mapping):
            obj = self._constructor(obj, self._configuration())
        elif (isinstance(obj, Sequence) and not isinstance(obj, (str, bytes))):
            sequence_type = getattr(self, '_sequence_type', None)

            if sequence_type:
                obj = sequence_type(self._build(element) for element in obj)

        return obj

    @classmethod
    def _valid_name(cls, key):
        """
        Check whether a key is a valid attribute name.
        A key may be used as an attribute if:
         * It is a string
         * It matches /^[A-Za-z][A-Za-z0-9_]*$/ (i.e., a public attribute)
         * The key doesn't overlap with any class attributes (for Attr,
            those would be 'get', 'items', 'keys', 'values', 'mro', and
            'register').
        """
        return (
            isinstance(key, str) and
            re.match('^[A-Za-z][A-Za-z0-9_]*$', key) and
            not hasattr(cls, key)
        )


class MutableAttr(Attr, MutableMapping, metaclass=ABCMeta):
    """A mixin class for a mapping that allows for attribute-style access of values."""
    def _setattr(self, key, value):
        """Add an attribute to the object, without attempting to add it as a key to the mapping."""
        super(MutableAttr, self).__setattr__(key, value)

    def __setattr__(self, key, value):
        """
        Add an attribute.
        key: The name of the attribute
        value: The attributes contents
        """
        if self._valid_name(key):
            self[key] = value
        elif getattr(self, '_allow_invalid_attributes', True):
            super(MutableAttr, self).__setattr__(key, value)
        else:
            raise TypeError(
                "'{cls}' does not allow attribute creation.".format(
                    cls=self.__class__.__name__
                )
            )

    def _delattr(self, key):
        """Delete an attribute from the object, without attempting to remove it from the mapping."""
        super(MutableAttr, self).__delattr__(key)

    def __delattr__(self, key, force=False):
        """
        Delete an attribute.
        key: The name of the attribute
        """
        if self._valid_name(key):
            del self[key]
        elif getattr(self, '_allow_invalid_attributes', True):
            super(MutableAttr, self).__delattr__(key)
        else:
            raise TypeError(
                "'{cls}' does not allow attribute deletion.".format(
                    cls=self.__class__.__name__
                )
            )


"""
A dict that implements MutableAttr.
"""


class AttrDict(dict, MutableAttr):
    """A dict that implements MutableAttr."""
    def __init__(self, *args, **kwargs):
        """Initilize the AttrDict"""
        super(AttrDict, self).__init__(*args, **kwargs)

        self._setattr('_sequence_type', tuple)
        self._setattr('_allow_invalid_attributes', False)

    def _configuration(self):
        """The configuration for an attrmap instance."""
        return self._sequence_type

    def __getstate__(self):
        """Serialize the object."""
        return (
            self.copy(),
            self._sequence_type,
            self._allow_invalid_attributes
        )

    def __setstate__(self, state):
        """Deserialize the object."""
        mapping, sequence_type, allow_invalid_attributes = state
        self.update(mapping)
        self._setattr('_sequence_type', sequence_type)
        self._setattr('_allow_invalid_attributes', allow_invalid_attributes)

    def __repr__(self):
        """Override offical string representation."""
        return f'AttrDict({super(AttrDict, self).__repr__()})'

    @classmethod
    def _constructor(cls, mapping, configuration):
        """A standardized constructor."""
        attr = cls(mapping)
        attr._setattr('_sequence_type', configuration)

        return attr