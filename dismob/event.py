# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Any, Callable, List, TypeVar, get_type_hints
from discord.ext import commands

T = TypeVar('T', bound=Callable[..., Any])

class Event:
    def __init__(self, callback_signature: T) -> None:
        """
        Initialize an event system with a specific callback signature.
        
        Args:
            callback_signature: A function that defines the parameter types callbacks should have
        """
        self._handlers: List[T] = []
        self._signature = callback_signature
        self.parameters = get_type_hints(callback_signature)
    
    def register(self, callback: T) -> bool:
        """
        Register a callback function if not already registered.
        
        Args:
            callback: The function to be called when the event is broadcast
            
        Returns:
            bool: True if callback was registered, False if it was already registered
            
        Raises:
            TypeError: If the callback signature doesn't match the event signature
        """
        cb_signature = get_type_hints(callback)
        if cb_signature != self.parameters:
            raise TypeError(f"Callback signature `{cb_signature}` does not match event signature `{self.parameters}`")
        
        if callback not in self._handlers:
            self._handlers.append(callback)
            return True
        return False

    def unregister(self, callback: T) -> bool:
        """
        Unregister a callback function.
        
        Args:
            callback: The function to be unregistered
            
        Returns:
            bool: True if callback was found and removed, False otherwise
        """
        if callback in self._handlers:
            self._handlers.remove(callback)
            return True
        return False

    def dispatch(self, *args: Any, **kwargs: Any) -> None:
        """
        Dispatch to all registered callbacks.
        
        Args:
            *args: Positional arguments to pass to the callbacks
            **kwargs: Keyword arguments to pass to the callbacks
            
        Raises:
            TypeError: If the arguments don't match the callback signature
        """
        # Validate arguments against signature
        try:
            self._signature(*args, **kwargs)
        except TypeError as e:
            raise TypeError(f"Invalid arguments for event dispatch: {str(e)}")
            
        for handler in self._handlers[:]:  # Create a copy to allow handlers to unregister themselves
            handler(*args, **kwargs)
    
    def clear(self) -> None:
        """Clear all callbacks."""
        self._handlers.clear()


class BotEvents:
    """
    A collection of events for the bot.
    
    Attributes:
        on_ready: Event triggered when the bot is ready.
    """
    def template_callback(bot: commands.Bot) -> None: pass
    on_ready = Event(template_callback)
    
    @staticmethod
    def clear() -> None:
        """Clear all events."""
        BotEvents.on_ready.clear()