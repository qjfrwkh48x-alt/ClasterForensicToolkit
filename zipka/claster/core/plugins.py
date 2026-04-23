"""
Plugin system for extending Claster Forensic Toolkit functionality.
Plugins are Python modules or packages that conform to the PluginBase interface.
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from abc import ABC, abstractmethod
from claster.core.logger import get_logger
from claster.core.exceptions import PluginError
from claster.core.config import get_config

logger = get_logger(__name__)

class PluginBase(ABC):
    """Abstract base class for all Claster plugins."""

    # Plugin metadata
    name: str = "Unnamed Plugin"
    version: str = "0.1.0"
    author: str = ""
    description: str = ""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(f"plugin.{self.name}")

    @abstractmethod
    def initialize(self) -> None:
        """Called when plugin is loaded. Perform setup here."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Called when plugin is unloaded. Clean up resources."""
        pass

    def get_info(self) -> Dict[str, str]:
        """Return plugin metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description
        }

class PluginManager:
    """
    Manages loading, initialization, and unloading of plugins.
    """

    def __init__(self):
        self._plugins: Dict[str, PluginBase] = {}
        self._plugin_classes: Dict[str, Type[PluginBase]] = {}

    def discover_plugins(self, directories: Optional[List[str]] = None) -> List[str]:
        """
        Scan directories for Python files containing PluginBase subclasses.

        Args:
            directories: List of directory paths to scan. If None, use config.

        Returns:
            List of discovered plugin module names.
        """
        if directories is None:
            config = get_config()
            directories = config.plugin_directories

        discovered = []
        for dir_path in directories:
            plugin_dir = Path(dir_path)
            if not plugin_dir.exists():
                logger.debug(f"Plugin directory does not exist: {plugin_dir}")
                continue

            # Add to sys.path temporarily
            sys.path.insert(0, str(plugin_dir.parent))
            for py_file in plugin_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                module_name = py_file.stem
                try:
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    # Find PluginBase subclasses
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, PluginBase) and obj is not PluginBase:
                            self._plugin_classes[obj.name] = obj
                            discovered.append(obj.name)
                            logger.info(f"Discovered plugin: {obj.name} v{obj.version} from {py_file}")
                except Exception as e:
                    logger.error(f"Failed to load plugin from {py_file}: {e}")

            sys.path.pop(0)

        return discovered

    def load_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """
        Instantiate and initialize a plugin by name.

        Args:
            plugin_name: Name of the plugin (must match PluginBase.name).

        Returns:
            Plugin instance if loaded successfully, else None.
        """
        if plugin_name in self._plugins:
            logger.warning(f"Plugin '{plugin_name}' already loaded.")
            return self._plugins[plugin_name]

        if plugin_name not in self._plugin_classes:
            logger.error(f"Plugin '{plugin_name}' not discovered.")
            return None

        try:
            plugin_class = self._plugin_classes[plugin_name]
            plugin_instance = plugin_class()
            plugin_instance.initialize()
            self._plugins[plugin_name] = plugin_instance
            logger.info(f"Loaded plugin: {plugin_name} v{plugin_instance.version}")
            return plugin_instance
        except Exception as e:
            logger.error(f"Failed to load plugin '{plugin_name}': {e}")
            raise PluginError(f"Failed to load plugin '{plugin_name}': {e}")

    def unload_plugin(self, plugin_name: str) -> None:
        """Shutdown and remove a plugin."""
        if plugin_name in self._plugins:
            try:
                self._plugins[plugin_name].shutdown()
                del self._plugins[plugin_name]
                logger.info(f"Unloaded plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Error during plugin shutdown '{plugin_name}': {e}")

    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """Get a loaded plugin instance by name."""
        return self._plugins.get(plugin_name)

    def list_plugins(self) -> List[Dict[str, str]]:
        """Return metadata for all discovered plugins."""
        return [cls().get_info() for cls in self._plugin_classes.values()]

    def shutdown_all(self) -> None:
        """Unload all plugins."""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)

# Global plugin manager instance
plugin_manager = PluginManager()