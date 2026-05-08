from importlib import import_module
from inspect import isclass
from pathlib import Path
from pkgutil import iter_modules

from DashAI.back.models.classes import base_path


def introspect_classes():
    """Discover and return all classes defined in the current package.

    Iterates over every module under the ``DashAI.back.models.classes`` package,
    imports each one, and collects all class objects, de-duplicating by class name.

    Returns
    -------
    dict
        A mapping of class name (``str``) to class object for every class found
        in the package's modules.
    """
    classes_dict = {}
    # iterate through the modules in the current package
    package_dir = Path(__file__).resolve().parent
    for _, module_name, _ in iter_modules([str(package_dir)]):
        # import the module and iterate through its attributes
        module = import_module(f"{base_path}.{module_name}")
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)

            if isclass(attribute):
                # Add the class to this package's variables
                class_name = attribute.__name__
                if class_name not in classes_dict:
                    classes_dict[class_name] = attribute
    return classes_dict


def filter_by_parent(parent_class_name):
    """Return all classes that are strict subclasses of the named parent class.

    Parameters
    ----------
    parent_class_name : str
        Name of the parent class to filter by.  Must be present in the dict
        returned by :func:`introspect_classes`.

    Returns
    -------
    dict
        A mapping of class name to class object for every class that is a
        subclass of the named parent (excluding the parent itself).
    """
    class_dict = introspect_classes()
    parent_class = class_dict[parent_class_name]
    filtered_dict = {}
    for class_name in class_dict:
        if (
            issubclass(class_dict[class_name], parent_class)
            and parent_class_name != class_name
        ):
            filtered_dict[class_name] = class_dict[class_name]
    return filtered_dict


def get_model_params_from_task(task_name):
    """Return a dictionary listing the available models for a given task name.

    Derives the expected model base-class name by stripping the ``"Task"``
    suffix and appending ``"Model"``, then delegates to ``filter_by_parent``
    to find all registered subclasses.

    Parameters
    ----------
    task_name : str
        Name of the task class (e.g. ``"TabularClassificationTask"``).

    Returns
    -------
    dict
        ``{"models": [<name>, ...]}`` on success, or
        ``{"error": "<model_class_name> not found"}`` if the derived class
        name is not registered.
    """
    model_class_name = f"{task_name[:-4]}Model"
    try:
        dict = filter_by_parent(model_class_name)
        return {"models": list(dict.keys())}
    except TypeError:
        return {"error": f"{model_class_name} not found"}
