#!/usr/bin/env python

import threading
import Queue
import logging
from collections import defaultdict
from functools import wraps
import time
from copy import deepcopy
import traceback

log = logging.getLogger(__name__)


class EventRegistry(threading.Thread):
    def __init__(self):
        super(EventRegistry, self).__init__()

        self._registry = None
        self._registry_lock = threading.RLock()
        self._error_lock = threading.RLock()
        self._errors = []
        self.clear()
        self._callback_queue = Queue.Queue()
        self.daemon = True

    def register(self, event_type, func, *args, **kwargs):
        with self._registry_lock:
            log.debug("Registering function {0} for event_type {1}".format(func, event_type))
            self._registry[event_type].append({"func": func, "args": args, "kwargs": kwargs})

    @property
    def event_types(self):
        with self._registry_lock:
            return self._registry.keys()

    def eval_callback(self, event_type, event_data, cb):
        with self._registry_lock:
            callbacks = self._registry.get(event_type, [])

        for callback in callbacks:
            self._callback_queue.put((callback, cb, event_type, event_data))

    def clear(self):
        with self._registry_lock:
            self._registry = defaultdict(list)

    # TODO: evaluate concurrent.futures.ThreadPoolExecutor for this
    def run(self):
        log.debug("starting event registry thread")
        while True:
            callback, cb, event_type, event_data = self._callback_queue.get()

            kwargs = callback["kwargs"]
            kwargs["cb"] = cb
            kwargs["event_type"] = event_type
            kwargs["event_data"] = event_data

            try:
                callback["func"](*callback["args"], **kwargs)
            except Exception:
                with self._error_lock:
                    self._errors.append({"exception": traceback.format_exc(), "timestamp": time.time(),
                                         "callback_func": callback["func"].__name__,
                                         "event_type": event_type, "event_data": event_data})

    @property
    def errors(self):
        with self._error_lock:
            errs = deepcopy(self._errors)
        return errs


registry = EventRegistry()


def on_event(event_type=None):
    def decorator(func):
        registry.register(event_type, func)

        @wraps(func)
        def f(*args, **kwargs):
            return func(*args, **kwargs)

        return f
    return decorator


registry.start()
