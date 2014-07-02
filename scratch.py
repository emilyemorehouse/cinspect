import re
import os
from os.path import expanduser, exists, join
SOURCE_DIR = expanduser(os.getenv('PY_SOURCE_DIR', '~/software/random/cpython'))

import inspect

class InspectObject(object):
    """ A dumb wrapper around the object we are trying to inspect. """

    def __init__(self, obj):
        self.obj = obj

    def getfile(self):
        return inspect.getfile(self.obj)

    # fixme: we should ideally be returning only one pattern, by looking up the
    # PyMethodDef mapping, but for now, we follow a heuristic, and return
    # multiple possible patterns. Hence the name, getpatterns!
    def getpatterns(self):
        raise NotImplementedError

class PythonObject(InspectObject):
    pass

class BuiltinFunction(InspectObject):
    def getfile(self):
        return join(SOURCE_DIR, 'Python', 'bltinmodule.c')

    def getpatterns(self):
        function_name = 'builtin_%s' % self.obj.__name__
        pattern = (
            'static PyObject\s*\*\s*'
            '%s\s*\(.*?\)\s*?\n{[\s\S]*?\n}' % function_name
        )

        yield pattern

class BuiltinMethod(InspectObject):
    def getfile(self):
        path = join(SOURCE_DIR, 'Objects', '%sobject.c' % self.type_name)
        if not exists(path):
            raise Exception('Could not find source file - %s!' % path)

        return path

    def getpatterns(self):
        for name_pattern in ('%s%s', '%s_%s'):
            function_name = name_pattern % (self.type_name, self.obj.__name__)
            pattern = (
                'static PyObject\s*\*\s*'
                '%s\s*\(.*?\)\s*?\n{[\s\S]*?\n}' % function_name
            )

            yield pattern

    @property
    def type_name(self):
        ## fixme: a hack to handle classmethods...
        if isinstance(self.obj.__self__, type):
            type_name = self.obj.__self__.__name__

        else:
            type_name = type(self.obj.__self__).__name__

        return type_name


class MethodDescriptor(BuiltinMethod):
    @property
    def type_name(self):
        return self.obj.__objclass__.__name__


def get_inspect_object(obj):
    """ Returns the object wrapped in the appropriate InspectObject class. """

    try:
        inspect.getfile(obj)
    except TypeError:
        # The code to deal with this case is below
        pass
    else:
        return PythonObject(obj)

    if inspect.isbuiltin(obj):
        if map.__module__ == obj.__module__:
            # functions like map, reduce, len, ...
            return BuiltinFunction(obj)
        elif obj.__module__ is None:
            # fixme: we could possibly check in `types` to see if it's really a
            # built-in...
            return BuiltinMethod(obj)
        else:
            raise NotImplementedError

    elif inspect.ismethoddescriptor(obj):
        return MethodDescriptor(obj)

    else:
        raise NotImplementedError


def getfile(obj):
    if not isinstance(obj, InspectObject):
        obj = get_inspect_object(obj)
    return obj.getfile()


def getsource(obj):

    if not isinstance(obj, InspectObject):
        obj = get_inspect_object(obj)

    with open(obj.getfile()) as f:
        full_source = f.read()

    for pattern in obj.getpatterns():
        matches = re.findall(pattern, full_source)
        if len(matches) == 1:
            source = matches[0]
            break
    else:
        raise Exception('Too few or too many definitions...')

    return source
