#!/usr/bin/env python

"""Base model objects for the CBAPI."""

from __future__ import absolute_import

from functools import wraps
import time
import json

from cbapi.six import python_2_unicode_compatible, iteritems

from .errors import ServerError
import logging
log = logging.getLogger(__name__)


class CreatableModelMixin(object):
    """TBD."""

    pass


# TODO: this doesn't exactly do what I want... this needs to be cleaned up before release
def immutable(cls):
    """Decorate a model object in such a way that allows it to be specified as "immutable"."""
    cls.__frozen = False

    def frozensetattr(self, key, value):
        """
        Set an attribute on this object, but disallow it if the object is frozen.

        Args:
            self (object): The object being changed by this attribute setting operation.
            key (str): The attribute being changed.
            value (object): The new value being set for the attribute.

        Returns:
            TBD
        """
        if self.__frozen and not hasattr(self, key):
            print("Class {} is frozen. Cannot set {} = {}"
                  .format(cls.__name__, key, value))
        else:
            object.__setattr__(self, key, value)

    def init_decorator(func):
        """
        Initialize the decorator on a function.

        Args:
            func (func): Function to be wrapped by this decorator.

        Returns:
            func: The wrapped function.
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            self.__frozen = True
        return wrapper

    cls.__setattr__ = frozensetattr
    cls.__init__ = init_decorator(cls.__init__)

    return cls


@python_2_unicode_compatible
class BaseModel(object):
    """The base "model" class for all objects that the CBAPI works with."""

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False):
        """
        Initialize the BaseModel object.

        Args:
            cb (BaseAPI): Reference to the CBAPI object.
            model_unique_id (object): Unique ID for the model object.
            initial_data (dict): Initial data for the model object.
            force_init (bool): True to force the object to be re-initialized from the server.
        """
        self._cb = cb
        if model_unique_id is not None:
            self._model_unique_id = str(model_unique_id)
        else:
            self._model_unique_id = None

        self._full_init = False
        self._info = {}

        self._last_refresh_time = 0
        if initial_data:
            self._set_initial_data(initial_data)
            self._last_refresh_time = time.time()

        self._base_initialized = True

        if force_init:
            self.refresh()

    def _set_initial_data(self, initial_data):
        if initial_data:
            self._info = dict(initial_data)

    def _set_model_unique_id(self):
        unique_id = self._info.get("id", None)
        if unique_id:
            self._model_unique_id = str(unique_id)

    @property
    def _stat_titles(self):
        return self._info.keys()

    @classmethod
    def new_object(cls, cb, item):
        """
        Create a new instance of the object from item data.

        Args:
            cb (BaseAPI): Reference to the CBAPI object.
            item (dict): Item data, as retrieved from the server.

        Returns:
            object: New instance of the object.
        """
        # TODO: do we ever need to evaluate item['unique_id'] which is the id + segment id?
        # TODO: is there a better way to handle this? (see how this is called from Query._search())
        return cb.select(cls, item['id'], initial_data=item)

    def refresh(self):
        """Refresh the object from the Carbon Black server."""
        self._retrieve_cb_info()

    def _retrieve_cb_info(self, query_parameters=None):
        if self._model_unique_id is not None:
            request_uri = self._build_api_request_uri()
            self._parse(self._cb.get_object(request_uri, query_parameters=query_parameters))
            self._full_init = True
            self._last_refresh_time = time.time()

    def _parse(self, obj):
        self._info = obj

    def _build_api_request_uri(self):
        baseuri = self.__class__.__dict__.get('urlobject', None)
        if self._model_unique_id is not None:
            return baseuri + "/%s" % self._model_unique_id
        else:
            return baseuri

    @property
    def webui_link(self):
        """
        Return a link associated with this object in the Carbon Black user interface.

        Returns:
            str: URL that can be used to view the object in the Carbon Black web user interface, or None if the Model
                does not support generating a Web user interface URL
        """
        return None

    def __dir__(self):
        """
        Fetch a list of all attribute names defined for this object.

        Returns:
            list: A list of strings, each of which represents an attribute name on the object.
        """
        if not self._full_init:
            self._retrieve_cb_info()

        return list(set().union(self.__dict__.keys(), self._info.keys()))

    def __getattr__(self, attrname):
        """
        Return the value of an attribute on this object.

        Args:
            attrname (str): Name of the attribute to return.

        Returns:
            object: The attribute value.
        """
        try:
            object.__getattribute__(self, "_base_initialized")
        except AttributeError:
            return super(BaseModel, self).__getattribute__(attrname)

        try:
            return self._attribute(attrname)
        except AttributeError:
            return super(BaseModel, self).__getattribute__(attrname)

    def _attribute(self, attrname, default=None):
        if attrname in self._info:
            return self._info[attrname]

        if not self._full_init:
            # fill in info from Cb
            self._retrieve_cb_info()

        if attrname in self._info:
            return self._info[attrname]

        return default

    def get(self, attrname, default_val=None):
        """
        Return the value of an attribute on this object.

        Args:
            attrname (str): Name of the attribute to be returned.
            default_val (object): The default value to be returned if the attribute is undefined.

        Returns:
            object: The attribute value, which may be default_val.
        """
        try:
            return self._attribute(attrname, default_val)
        except AttributeError:
            return default_val

    def __str__(self):
        """
        Return a representation of this object as a string.

        Returns:
            str: A representation of this object as a string.
        """
        ret = '{0:s}.{1:s}:\n'.format(self.__class__.__module__, self.__class__.__name__)
        if self.webui_link:
            ret += "-> available via web UI at %s\n" % self.webui_link

        ret += u'\n'.join(['%-20s : %s' %
                           (a, getattr(self, a, "")) for a in self._stat_titles])

        return ret

    def __repr__(self):
        """
        Return a representation of this object as a string.

        Returns:
            str: A representation of this object as a string.
        """
        return "<%s.%s: id %s> @ %s" % (self.__class__.__module__, self.__class__.__name__, self._model_unique_id,
                                        self._cb.session.server)

    @property
    def original_document(self):
        """
        Return the original document associated with this object.

        Returns:
            object: Original document associated with this object.
        """
        if not self._full_init:
            self._retrieve_cb_info()

        return self._info

    def to_html(self):
        """
        Return a representation of this object as HTML.

        Returns:
            str: HTML representation of the object.
        """
        ret = u"<h3>%s</h3>" % self.__class__.__name__
        ret += u"<table><tr><th>Key</th><th>Value</th></tr>\n"
        for a in self._stat_titles:
            ret += '<tr><td><b>%s</b></td><td>%s</td></tr>\n' % (a, getattr(self, a, ""))
        ret += u'</table>'

        return ret

    def _repr_html_(self):
        return ('<div style="max-height:1000px;'
                'max-width:1500px;overflow:auto;">\n' +
                self.to_html() + '\n</div>')


class MutableModel(BaseModel):
    """A model object that implements mutability, the ability to change its values."""

    def __init__(self, cb, model_unique_id, initial_data=None):
        """
        Initialize the MutableModel.

        Args:
            cb (BaseAPI): Reference to the CBAPI object.
            model_unique_id (object): Unique ID for the model object.
            initial_data (dict): Initial data for the model object.
        """
        super(MutableModel, self).__init__(cb, model_unique_id, initial_data)
        self._dirty_attributes = {}
        self._mutable_initialized = True

    def _target_val(self, attrname, val):
        if isinstance(val, BaseModel):
            original_type = type(self._info[attrname])
            return original_type(val._model_unique_id)
        else:
            return val

    def __setattr__(self, attrname, val):
        """
        Set an attribute on the model object.

        Args:
            attrname (str): Name of the attribute to be set.
            val (object): Value of the object to be set.

        Returns:
            TBD
        """
        try:
            object.__getattribute__(self, "_mutable_initialized")
        except AttributeError:
            return super(MutableModel, self).__setattr__(attrname, val)

        propobj = getattr(self.__class__, attrname, None)
        if isinstance(propobj, property):
            if propobj.fset is None:
                raise AttributeError("can't set attribute")
            return propobj.fset(self, val)

        # TODO: limit this to a list of "known" fields
        if attrname.startswith("_"):
            return super(MutableModel, self).__setattr__(attrname, val)

        if not self._full_init:
            self._retrieve_cb_info()

        # only allow updating fields already defined in the structure from Cb
        if attrname in self._info:
            target_val = self._target_val(attrname, val)

            # early exit if we attempt to set the field to its own value
            if target_val == self._info[attrname]:
                return

            # update dirty_attributes if necessary
            if attrname in self._dirty_attributes:
                if target_val == self._dirty_attributes[attrname]:
                    del self._dirty_attributes[attrname]
            else:
                self._dirty_attributes[attrname] = self._info.get(attrname, None)

            # finally, make the change
            self._info[attrname] = target_val
        else:
            super(MutableModel, self).__setattr__(attrname, val)

    def is_dirty(self):
        """
        Return True if this object has unsaved changes.

        Use MutableModel.save to upload the changes to the Carbon Black server.
        """
        return len(self._dirty_attributes) > 0

    def _update_object(self):
        if self._model_unique_id:
            log.debug("unique_id=%s" % self._model_unique_id)
            ret = self._cb.put_object(self._build_api_request_uri(), self._info)
        else:
            log.debug("new object")
            ret = self._cb.post_object(self._build_api_request_uri(), self._info)

        if ret.status_code not in (200, 204):
            try:
                message = json.loads(ret.text)[0]
            except Exception:
                message = ret.text

            raise ServerError(ret.status_code, message,
                              result="Did not update {} record.".format(self.__class__.__name__))
        else:
            try:
                message = ret.json()
                log.debug("Received response: %s" % message)
                if message.keys() == ["result"]:
                    post_result = message.get("result", None)

                    if post_result and post_result != "success":
                        raise ServerError(ret.status_code, post_result,
                                          result="Did not update {0:s} record.".format(self.__class__.__name__))
                    else:
                        self.refresh()
                else:
                    self._info = json.loads(ret.text)
                    self._full_init = True
            except Exception:
                self.refresh()

        if not self._model_unique_id:
            self._set_model_unique_id()

        self._dirty_attributes = {}
        return self._model_unique_id

    def refresh(self):
        """Refresh the contents of this obejct from the server."""
        super(MutableModel, self).refresh()
        self._dirty_attributes = {}

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

    def save(self):
        """
        Save changes to this object to the Carbon Black server.

        Raises:
            ServerError: If an error was returned by the Carbon Black server.
        """
        if not self.is_dirty():
            return

        return self._update_object()

    def reset(self):
        """Reset all changes made to this object."""
        for k, v in iteritems(self._dirty_attributes):
            self._info[k] = v

        self._dirty_attributes = {}

    # TODO: How do we delete this object from our LRU cache?
    def delete(self):
        """Delete this object."""
        return self._delete_object()

    def _join(self, join_cls, field_name):
        try:
            field_value = getattr(self, field_name)
        except AttributeError:
            return None

        if field_value is None:
            return None

        return self._cb.select(join_cls, field_value)
