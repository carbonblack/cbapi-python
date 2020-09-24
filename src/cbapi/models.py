#!/usr/bin/env python

from __future__ import absolute_import

from copy import deepcopy

from cbapi.six import python_2_unicode_compatible

import base64
import os.path
from cbapi.six import iteritems, add_metaclass, integer_types
from cbapi.six.moves import range
from .response.utils import convert_from_cb, convert_to_cb
import yaml
import json
import time
from .errors import ApiError, ServerError, InvalidObjectError
from .oldmodels import BaseModel
import logging
from datetime import datetime
from cbapi.utils import calculate_elapsed_time

log = logging.getLogger(__name__)


class CreatableModelMixin(object):
    pass


class CbMetaModel(type):
    model_base_directory = os.path.dirname(__file__)
    model_classes = []

    def __new__(mcs, name, bases, clsdict):
        swagger_meta_file = clsdict.pop("swagger_meta_file", None)
        model_data = {}
        if swagger_meta_file:
            with open(os.path.join(mcs.model_base_directory, swagger_meta_file), 'rb') as f:
                model_data = yaml.safe_load(f.read())


        clsdict["__doc__"] = "Represents a %s object in the Carbon Black server.\n\n" % (name,)
        for field_name, field_info in iteritems(model_data.get("properties", {})):
            docstring = field_info.get("description", None)
            if docstring:
                clsdict["__doc__"] += ":ivar %s: %s\n" % (field_name, docstring)

        foreign_keys = clsdict.pop("foreign_keys", {})

        cls = super(CbMetaModel, mcs).__new__(mcs, name, bases, clsdict)
        mcs.model_classes.append(cls)

        cls._valid_fields = []
        cls._required_fields = model_data.get("required", [])
        cls._default_value = {}

        for field_name, field_info in iteritems(model_data.get("properties", {})):
            cls._valid_fields.append(field_name)

            default_value = field_info.get("default", None)
            if default_value:
                cls._default_value[field_name] = default_value

            field_format = field_info.get("type", "string")
            field_format = field_info.get("format", field_format)

            if field_format.startswith('int'):
                setattr(cls, field_name, FieldDescriptor(field_name, coerce_to=int))
            elif field_format == "iso-date-time":
                setattr(cls, field_name, IsoDateTimeFieldDescriptor(field_name))
            elif field_format == "epoch-ms-date-time":
                setattr(cls, field_name, EpochDateTimeFieldDescriptor(field_name, 1000.0))
            elif field_format == "boolean":
                setattr(cls, field_name, FieldDescriptor(field_name, coerce_to=bool))
            elif field_format == "array":
                setattr(cls, field_name, ArrayFieldDescriptor(field_name))
            elif field_format == "object":
                setattr(cls, field_name, ObjectFieldDescriptor(field_name))
            elif field_format == "double":
                setattr(cls, field_name, FieldDescriptor(field_name, coerce_to=float))
            elif field_format == "byte":
                setattr(cls, field_name, BinaryFieldDescriptor(field_name))
            else:
                setattr(cls, field_name, FieldDescriptor(field_name))

        for fk_name, fk_info in iteritems(foreign_keys):
            setattr(cls, fk_name, ForeignKeyFieldDescriptor(fk_name, fk_info[0], fk_info[1]))

        return cls


class FieldDescriptor(object):
    def __init__(self, field_name, coerce_to=None, default_value=None):
        self.att_name = field_name
        self.default_value = default_value
        self.coerce_to = coerce_to

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            if self.att_name not in instance._info and not instance._full_init:
                instance.refresh()

            value = instance._info.get(self.att_name, self.default_value)
            coerce_type = self.coerce_to or type(value)
            if value is None:
                return None
            return coerce_type(value)

    def __set__(self, instance, value):
        coerce_type = self.coerce_to or type(value)
        value = coerce_type(value)
        instance._set(self.att_name, value)


class ArrayFieldDescriptor(FieldDescriptor):
    def __get__(self, instance, instance_type=None):
        ret = super(ArrayFieldDescriptor, self).__get__(instance, instance_type)
        return ret or []


# TODO: this is a kludge to avoid writing "small" models?
class ObjectFieldDescriptor(FieldDescriptor):
    def __get__(self, instance, instance_type=None):
        ret = super(ObjectFieldDescriptor, self).__get__(instance, instance_type)
        return ret or {}


class IsoDateTimeFieldDescriptor(FieldDescriptor):
    def __init__(self, field_name):
        super(IsoDateTimeFieldDescriptor, self).__init__(field_name)

    def __get__(self, instance, instance_type=None):
        d = super(IsoDateTimeFieldDescriptor, self).__get__(instance, instance_type)
        return convert_from_cb(d)

    def __set__(self, instance, value):
        parsed_date = convert_to_cb(value)
        super(IsoDateTimeFieldDescriptor, self).__set__(instance, parsed_date)


class EpochDateTimeFieldDescriptor(FieldDescriptor):
    def __init__(self, field_name, multiplier=1.0):
        super(EpochDateTimeFieldDescriptor, self).__init__(field_name)
        self.multiplier = float(multiplier)

    def __get__(self, instance, instance_type=None):
        d = super(EpochDateTimeFieldDescriptor, self).__get__(instance, instance_type)
        if type(d) is float or type(d) in integer_types:
            epoch_seconds = d / self.multiplier
            return datetime.utcfromtimestamp(epoch_seconds)
        else:
            return datetime.utcfromtimestamp(0)      # default to epoch time (1970-01-01) if we have a non-numeric type

    def __set__(self, instance, value):
        if isinstance(value, datetime):
            new_value = calculate_elapsed_time(value - self.epoch) * self.multiplier
        else:
            new_value = value
        super(EpochDateTimeFieldDescriptor, self).__set__(instance, new_value)


class ForeignKeyFieldDescriptor(FieldDescriptor):
    def __init__(self, field_name, join_model, join_field=None):
        super(ForeignKeyFieldDescriptor, self).__init__(field_name)
        self.join_model = join_model
        if join_field is None:
            self.join_field = field_name + "_id"
        else:
            self.join_field = join_field

    def __get__(self, instance, instance_type=None):
        foreign_id = getattr(instance, self.join_field)
        return instance._cb.select(self.join_model, foreign_id)

    def __set__(self, instance, value):
        if type(value, BaseModel) or type(value, NewBaseModel):
            setattr(self, self.join_field, getattr(value, "_model_unique_id"))
        else:
            setattr(self, self.join_field, value)


class BinaryFieldDescriptor(FieldDescriptor):
    def __get__(self, instance, instance_type=None):
        d = super(BinaryFieldDescriptor, self).__get__(instance, instance_type)
        return base64.b64decode(d)

    def __set__(self, instance, value):
        super(BinaryFieldDescriptor, self).__set__(instance, base64.b64encode(value))


@python_2_unicode_compatible
@add_metaclass(CbMetaModel)
class NewBaseModel(object):
    primary_key = "id"

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=False):
        """
        Base model for
        :param cb:
        :param model_unique_id:
        :param initial_data:
        :param force_init:
        :param full_doc:
        :return:
        """
        self._cb = cb
        self._last_refresh_time = 0

        if initial_data is not None:
            self._info = initial_data
        else:
            self._info = {}

        if model_unique_id is not None:
            self._info[self.__class__.primary_key] = model_unique_id

        self._dirty_attributes = {}
        self._full_init = full_doc

        if force_init:
            self.refresh()

    @property
    def _model_unique_id(self):
        return self._info.get(self.__class__.primary_key, None)

    @classmethod
    def new_object(cls, cb, item, **kwargs):
        return cb.select(cls, item[cls.primary_key], initial_data=item, **kwargs)

    def __getattr__(self, item):
        try:
            super(NewBaseModel, self).__getattribute__(item)
        except AttributeError:
            pass         # fall through to the rest of the logic...

        # try looking up via self._info, if we already have it.
        if item in self._info:
            return self._info[item]

        # if we're still here, let's load the object if we haven't done so already.
        if not self._full_init:
            self._refresh()

        # try one more time.
        if item in self._info:
            return self._info[item]
        else:
            raise AttributeError("'{0}' object has no attribute '{1}'".format(self.__class__.__name__,
                                                                              item))

    def __setattr__(self, attrname, val):
        if attrname.startswith("_"):
            super(NewBaseModel, self).__setattr__(attrname, val)
        else:
            raise AttributeError("Field {0:s} is immutable".format(attrname))

    def get(self, attrname, default_val=None):
        return getattr(self, attrname, default_val)

    def _set(self, attrname, new_value):
        pass

    def refresh(self):
        return self._refresh()

    def _refresh(self):
        if self._model_unique_id is not None and self.__class__.primary_key not in self._dirty_attributes.keys():
            self._info = self._parse(self._retrieve_cb_info())

            self._full_init = True
            self._last_refresh_time = time.time()
            return True
        return False

    def _build_api_request_uri(self, http_method="GET"):
        baseuri = self.__class__.__dict__.get('urlobject', None)
        if self._model_unique_id is not None:
            return baseuri + "/%s" % self._model_unique_id
        else:
            return baseuri

    def _retrieve_cb_info(self):
        request_uri = self._build_api_request_uri()
        return self._cb.get_object(request_uri)

    def _parse(self, obj):
        return obj

    @property
    def original_document(self):
        if not self._full_init:
            self.refresh()

        return self._info

    def __repr__(self):
        if self._model_unique_id is not None:
            return "<%s.%s: id %s> @ %s" % (self.__class__.__module__, self.__class__.__name__, self._model_unique_id,
                                            self._cb.session.server)
        else:
            return "<%s.%s object at %s> @ %s" % (self.__class__.__module__, self.__class__.__name__, hex(id(self)),
                                                  self._cb.session.server)

    def __str__(self):
        lines = []
        lines.append("{0:s} object, bound to {1:s}.".format(self.__class__.__name__, self._cb.session.server))
        if self._last_refresh_time:
            lines.append(" Last refreshed at {0:s}".format(time.ctime(self._last_refresh_time)))
        if not self._full_init:
            lines.append(" Partially initialized. Use .refresh() to load all attributes")
        lines.append("-"*79)
        lines.append("")

        for attr in sorted(self._info):
            status = "   "
            if attr in self._dirty_attributes:
                if self._dirty_attributes[attr] is None:
                    status = "(+)"
                else:
                    status = "(*)"
            try:
                val = str(self._info[attr])
            except UnicodeDecodeError:
                val = repr(self._info[attr])
            if len(val) > 50:
                val = val[:47] + u"..."
            lines.append(u"{0:s} {1:>20s}: {2:s}".format(status, attr, val))

        return "\n".join(lines)

    def _join(self, join_cls, field_name):
        try:
            field_value = getattr(self, field_name)
        except AttributeError:
            return None

        if field_value is None:
            return None

        return self._cb.select(join_cls, field_value)


class UnrefreshableModel(NewBaseModel):
    """Represents a model that can't be refreshed, i.e. for which ``reset()``
    is not a valid operation.
    """
    def refresh(self):
        raise ApiError("refresh() called on an unrefreshable model")


class MutableBaseModel(NewBaseModel):
    _new_object_http_method = "POST"
    _change_object_http_method = "PUT"
    _new_object_needs_primary_key = False

    def __setattr__(self, attrname, val):
        # allow subclasses to define their own property setters
        propobj = getattr(self.__class__, attrname, None)
        if isinstance(propobj, property) and propobj.fset:
            return propobj.fset(self, val)

        if not attrname.startswith("_") and attrname not in self.__class__._valid_fields:
            if attrname in self._info:
                log.warning("Changing field not included in Swagger definition: {0:s}".format(attrname))
                self._set(attrname, val)
            else:
                print("Trying to set attribute {0:s}".format(attrname))
        else:
            object.__setattr__(self, attrname, val)

    def _set(self, attrname, new_value):
        # ensure that we are operating on the full object first
        if not self._full_init and self._model_unique_id is not None:
            self.refresh()

        # extract unique ID if we're updating a "joined" field
        if isinstance(new_value, NewBaseModel):
            new_value = new_value._model_unique_id

        # early exit if we attempt to set the field to its own value
        if new_value == self._info.get(attrname, None):
            return

        # update dirty_attributes if necessary
        if attrname in self._dirty_attributes:
            if new_value == self._dirty_attributes[attrname]:
                del self._dirty_attributes[attrname]
        else:
            self._dirty_attributes[attrname] = self._info.get(attrname, None)

        # finally, make the change
        self._info[attrname] = new_value

    def refresh(self):
        if self._refresh():
            self._dirty_attributes = {}

    def is_dirty(self):
        return len(self._dirty_attributes) > 0

    def _update_object(self):
        if self.__class__.primary_key in self._dirty_attributes.keys() or self._model_unique_id is None:
            new_object_info = deepcopy(self._info)
            try:
                if not self._new_object_needs_primary_key:
                    del(new_object_info[self.__class__.primary_key])
            except Exception:
                pass
            log.debug("Creating a new {0:s} object".format(self.__class__.__name__))
            ret = self._cb.api_json_request(self.__class__._new_object_http_method, self.urlobject,
                                            data=new_object_info)
        else:
            log.debug("Updating {0:s} with unique ID {1:s}".format(self.__class__.__name__, str(self._model_unique_id)))
            http_method = self.__class__._change_object_http_method
            ret = self._cb.api_json_request(http_method, self._build_api_request_uri(http_method=http_method),
                                            data=self._info)

        return self._refresh_if_needed(ret)

    def _refresh_if_needed(self, request_ret):
        refresh_required = False

        if request_ret.status_code not in range(200, 300):
            try:
                message = json.loads(request_ret.text)[0]
            except Exception:
                message = request_ret.text

            raise ServerError(request_ret.status_code, message,
                              result="Did not update {} record.".format(self.__class__.__name__))
        else:
            try:
                message = request_ret.json()
                log.debug("Received response: %s" % message)
                if list(message.keys()) == ["result"]:
                    post_result = message.get("result", None)

                    if post_result and post_result != "success":
                        raise ServerError(request_ret.status_code, post_result,
                                          result="Did not update {0:s} record.".format(self.__class__.__name__))
                    else:
                        refresh_required = True
                else:
                    self._info = json.loads(request_ret.text)
                    if message.keys() == ["id"]:
                        # if all we got back was an ID, try refreshing to get the entire record.
                        log.debug("Only received an ID back from the server, forcing a refresh")
                        refresh_required = True
                    else:
                        self._full_init = True
            except Exception:
                refresh_required = True

        self._dirty_attributes = {}
        if refresh_required:
            self.refresh()
        return self._model_unique_id

    def save(self):
        if not self.is_dirty():
            return

        self.validate()
        self._update_object()
        return self

    def reset(self):
        for k, v in iteritems(self._dirty_attributes):
            if v is None:
                del self._info[k]
            else:
                self._info[k] = v

        self._dirty_attributes = {}

    # TODO: How do we delete this object from our LRU cache?
    def delete(self):
        return self._delete_object()

    def _delete_object(self):
        if self._model_unique_id:
            ret = self._cb.delete_object(self._build_api_request_uri())
        else:
            return

        if ret.status_code not in (200, 204):
            try:
                message = json.loads(ret.text)[0]
            except Exception:
                message = ret.text
            raise ServerError(ret.status_code, message, result="Did not delete {0:s}.".format(str(self)))

    def validate(self):
        if not self._full_init:
            self.refresh()

        diff = list(set(self.__class__._required_fields) - set(self._info.keys()))
        if not diff:
            return True
        else:
            raise InvalidObjectError("Missing fields: [%s]" % (", ".join(diff)))

    def __repr__(self):
        r = super(MutableBaseModel, self).__repr__()
        if self.is_dirty():
            r += " (*)"
        return r
