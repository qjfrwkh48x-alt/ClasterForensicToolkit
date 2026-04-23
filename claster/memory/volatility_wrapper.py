"""
Wrapper for Volatility 3 framework to run plugins and parse output.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from claster.core.logger import get_logger

logger = get_logger(__name__)

# Try to locate Volatility 3
VOLATILITY_PATH = os.environ.get('VOLATILITY3_PATH', 'volatility3')

class VolatilityWrapper:
    """Simple interface to Volatility 3."""

    def __init__(self, memory_dump: str):
        self.dump_path = Path(memory_dump)
        if not self.dump_path.exists():
            raise FileNotFoundError(f"Memory dump not found: {memory_dump}")
        self.vol_exe = VOLATILITY_PATH

    def run_plugin(self, plugin: str, **kwargs) -> str:
        """
        Run a Volatility plugin and return its output.

        Args:
            plugin: Plugin name (e.g., 'windows.pslist.PsList').
            **kwargs: Additional arguments for the plugin.

        Returns:
            Plugin output as string (JSON if supported).
        """
        cmd = [
            sys.executable, '-m', 'volatility3',
            '-f', str(self.dump_path),
            plugin,
            '--output', 'json'
        ]
        for key, value in kwargs.items():
            cmd.extend([f'--{key}', str(value)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=300
            )
            if result.returncode != 0:
                logger.error(f"Volatility plugin {plugin} failed: {result.stderr}")
                return ""
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f"Volatility plugin {plugin} timed out.")
            return ""
        except Exception as e:
            logger.error(f"Error running Volatility: {e}")
            return ""

def run_volatility_plugin(dump_path: str, plugin: str, output_dir: Optional[str] = None) -> str:
    """
    Convenience function to run a Volatility plugin on a memory dump.

    Args:
        dump_path: Path to memory dump.
        plugin: Plugin name.
        output_dir: Optional directory to change to before running (for file output plugins).

    Returns:
        Plugin output as string.
    """
    original_dir = os.getcwd()
    if output_dir:
        os.chdir(output_dir)
    try:
        vol = VolatilityWrapper(dump_path)
        return vol.run_plugin(plugin)
    finally:
        if output_dir:
            os.chdir(original_dir)