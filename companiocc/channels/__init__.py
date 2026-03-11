"""Chat channels module with plugin architecture."""

from companiocc.channels.base import BaseChannel
from companiocc.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
