"""
Event bus for inter-module communication.
Allows decoupled modules to react to forensic events (e.g., new evidence, detected anomaly).
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import threading
from claster.core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class Event:
    """Base event class."""
    name: str
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""

class EventBus:
    """
    Simple publish-subscribe event bus.
    Thread-safe.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """
        Subscribe a callback to an event.

        Args:
            event_name: Name of the event to listen for.
            callback: Function that accepts an Event object.
        """
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)
            logger.debug(f"Subscribed to event '{event_name}': {callback.__name__}")

    def unsubscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """Remove a subscription."""
        with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(callback)
                    logger.debug(f"Unsubscribed from event '{event_name}': {callback.__name__}")
                except ValueError:
                    pass

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event object to publish.
        """
        with self._lock:
            subscribers = self._subscribers.get(event.name, []).copy()

        if not subscribers:
            logger.debug(f"No subscribers for event '{event.name}'")
            return

        logger.debug(f"Publishing event '{event.name}' to {len(subscribers)} subscriber(s)")
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event handler {callback.__name__} for event '{event.name}': {e}")

    def clear(self) -> None:
        """Remove all subscriptions."""
        with self._lock:
            self._subscribers.clear()

# Global event bus instance
event_bus = EventBus()