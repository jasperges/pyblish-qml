import os
import sys
import inspect
import traceback

import pyblish.api

from . import ipc, settings, _state
try:
    from .vendor.Qt import QtWidgets, QtCore, QtGui
except ImportError:
    pass

def register_dispatch_wrapper(wrapper):
    """Register a dispatch wrapper for servers

    The wrapper must have this exact signature:
        (func, *args, **kwargs)

    """

    signature = inspect.getargspec(wrapper)
    if any([len(signature.args) != 1,
            signature.varargs is None,
            signature.keywords is None]):
        raise TypeError("Wrapper signature mismatch")

    _state["dispatchWrapper"] = wrapper


def deregister_dispatch_wrapper():
    _state.pop("dispatchWrapper")


def dispatch_wrapper():
    return _state.get("dispatchWrapper")


def current_server():
    return _state.get("currentServer")


def install():
    """Perform first time install

    Attributes:
        initial_port (int, optional): Port from which to start
            looking for available ports, defaults to 9001

    """

    if _state.get("installed"):
        sys.stdout.write("Already installed, uninstalling..\n")
        uninstall()

    install_callbacks()
    install_host()

    _state["installed"] = True


def uninstall():
    """Clean up traces of Pyblish QML"""
    uninstall_callbacks()
    sys.stdout.write("Pyblish QML shutdown successful.\n")


def _show_splash():
    """Try to show a splash screen when launching Pyblish QML

    Returns:
        QtWidget or None

    """
    if "QtWidgets" in globals() and QtWidgets.QApplication.instance():
        from .splash import Splash
        splash = Splash()
        splash.show()
        return splash


def show(parent=None):
    """Attempt to show GUI

    Requires install() to have been run first, and
    a live instance of Pyblish QML in the background.

    """

    # Automatically install if not already installed.
    if not _state.get("installed"):
        install()

    # Show existing GUI
    if _state.get("currentServer"):
        server = _state["currentServer"]
        proxy = ipc.server.Proxy(server)

        try:
            proxy.show(settings.to_dict())
            return server

        except IOError:
            # The running instance has already been closed.
            _state.pop("currentServer")

    splash = _show_splash()

    def on_shown():
        try:
            splash.close()
        except (RuntimeError, AttributeError):
            # Splash already closed or doesn't exist.
            pass

        pyblish.api.deregister_callback(*callback)

    callback = "pyblishQmlShown", on_shown
    pyblish.api.register_callback(*callback)

    try:
        service = ipc.service.Service()
        server = ipc.server.Server(service)
    except:
        # If for some reason, the GUI fails to show.
        traceback.print_exc()
        return on_shown()

    proxy = ipc.server.Proxy(server)
    proxy.show(settings.to_dict())

    # Store reference to server for future calls
    _state["currentServer"] = server

    print("Success. QML server available as "
          "pyblish_qml.api.current_server()")

    return server


def install_callbacks():
    pyblish.api.register_callback("instanceToggled", _toggle_instance)
    pyblish.api.register_callback("pluginToggled", _toggle_plugin)


def uninstall_callbacks():
    pyblish.api.deregister_callback("instanceToggled", _toggle_instance)
    pyblish.api.deregister_callback("pluginToggled", _toggle_plugin)


def _toggle_instance(instance, new_value, old_value):
    """Alter instance upon visually toggling it"""
    instance.data["publish"] = new_value


def _toggle_plugin(plugin, new_value, old_value):
    """Alter plugin upon visually toggling it"""
    plugin.active = new_value


def register_python_executable(path):
    """Expose Python executable to server

    The Python executable must be compatible with the
    version of PyQt5 installed or provided on the system.

    """

    assert os.path.isfile(path), "Must be a file, such as python.exe"

    _state["pythonExecutable"] = path


def registered_python_executable():
    return _state.get("pythonExecutable")


def register_pyqt5(path):
    """Expose PyQt5 to Python

    The exposed PyQt5 must be compatible with the exposed Python.

    Arguments:
        path (str): Absolute path to directory containing PyQt5

    """

    _state["pyqt5"] = path


def install_host():
    """Install required components into supported hosts

    An unsupported host will still run, but may encounter issues,
    especially with threading.

    """

    for install in (_install_maya,
                    _install_houdini,
                    _install_nuke,
                    _install_hiero,
                    _install_blender,
                    ):
        try:
            install()
        except ImportError:
            pass
        else:
            break


def _on_application_quit():
    """Automatically kill QML on host exit"""

    try:
        _state["currentServer"].popen.kill()

    except KeyError:
        # No server started
        pass

    except OSError:
        # Already dead
        pass


def _connect_application_quit():
    """Run _on_application_quit on host exit

    Do the best thing possible for the current host.

    """

    if "QtWidgets" in globals():
        app = QtWidgets.QApplication.instance()
        if app:
            app.aboutToQuit.connect(_on_application_quit)
        else:
            import atexit
            atexit.register(_on_application_quit)


def _install_maya():
    """Helper function to Autodesk Maya support"""
    from maya import utils

    def threaded_wrapper(func, *args, **kwargs):
        return utils.executeInMainThreadWithResult(
            func, *args, **kwargs)

    sys.stdout.write("Setting up Pyblish QML in Maya\n")
    register_dispatch_wrapper(threaded_wrapper)

    _connect_application_quit()

    # Configure GUI
    settings.ContextLabel = "Maya"
    settings.WindowTitle = "Pyblish (Maya)"


def _install_houdini():
    """Helper function to SideFx Houdini support"""
    import hdefereval

    def threaded_wrapper(func, *args, **kwargs):
        return hdefereval.executeInMainThreadWithResult(
            func, *args, **kwargs)

    sys.stdout.write("Setting up Pyblish QML in Houdini\n")
    register_dispatch_wrapper(threaded_wrapper)

    _connect_application_quit()

    settings.ContextLabel = "Houdini"
    settings.WindowTitle = "Pyblish (Houdini)"


def _install_nuke():
    """Helper function to The Foundry Nuke support"""
    import nuke

    if "--hiero" in nuke.rawArgs or "--studio" in nuke.rawArgs:
        raise ImportError

    def threaded_wrapper(func, *args, **kwargs):
        return nuke.executeInMainThreadWithResult(
            func, args, kwargs)

    sys.stdout.write("Setting up Pyblish QML in Nuke\n")
    register_dispatch_wrapper(threaded_wrapper)

    _connect_application_quit()

    settings.ContextLabel = "Nuke"
    settings.WindowTitle = "Pyblish (Nuke)"


def _install_hiero():
    """Helper function to The Foundry Hiero support"""
    import hiero
    import nuke

    if "--hiero" not in nuke.rawArgs:
        raise ImportError

    def threaded_wrapper(func, *args, **kwargs):
        return hiero.core.executeInMainThreadWithResult(
            func, args, kwargs)

    sys.stdout.write("Setting up Pyblish QML in Hiero\n")
    register_dispatch_wrapper(threaded_wrapper)

    _connect_application_quit()

    settings.ContextLabel = "Hiero"
    settings.WindowTitle = "Pyblish (Hiero)"


def _install_blender():
    """Helper function to Blender support"""
    import bpy

    sys.stdout.write("Setting up Pyblish QML in Blender\n")

    _connect_application_quit()

    # Configure GUI
    settings.ContextLabel = "Blender"
    settings.WindowTitle = "Pyblish (Blender)"
