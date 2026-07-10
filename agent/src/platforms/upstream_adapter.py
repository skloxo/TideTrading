import asyncio
import logging
from typing import Any, Optional

from src.platforms.base import BasePlatformAdapter, IncomingMessage
from src.channels.bus.events import OutboundMessage, InboundMessage
from src.channels.bus.queue import MessageBus

logger = logging.getLogger(__name__)

class UpstreamChannelAdapter(BasePlatformAdapter):
    """Adapter that wraps an upstream BaseChannel to run under PlatformManager."""

    def __init__(self, channel_class: Any, channel_id: str, name: str, config_dict: dict, tenant_id: str):
        self.channel_class = channel_class
        self.channel_id = channel_id
        self._name = name
        self.config_dict = config_dict
        self.tenant_id = tenant_id
        self.channel: Any = None
        self.bus: Optional[MessageBus] = None
        self._listener_task: Optional[asyncio.Task] = None

    @property
    def platform_name(self) -> str:
        return self.channel_class.name

    async def initialize(self, manager: Any) -> None:
        self.bus = MessageBus()
        self.channel = self.channel_class(self.config_dict, self.bus)
        
        async def listen_inbound():
            try:
                queue = self.bus.inbound_queue
                while True:
                    inbound_msg = await queue.get()
                    try:
                        from src.config.paths import active_tenant_var
                        active_tenant_var.set(self.tenant_id)
                        
                        msg = IncomingMessage(
                            platform=self.platform_name,
                            chat_id=inbound_msg.chat_id,
                            message_id=inbound_msg.message_id or "",
                            content=inbound_msg.content,
                            sender_id=inbound_msg.sender_id,
                            timestamp=inbound_msg.timestamp or asyncio.get_event_loop().time(),
                            raw_payload=inbound_msg.metadata or {},
                        )
                        await manager.handle_incoming_message(msg)
                    except Exception as e:
                        logger.error("Error routing inbound message for tenant %s: %s", self.tenant_id, e)
                    finally:
                        queue.task_done()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("Inbound listener task failed for adapter %s: %s", self.platform_name, e)

        self._listener_task = asyncio.create_task(listen_inbound())
        await self.channel.start()
        logger.info("Initialized and started upstream adapter %s for tenant %s", self.platform_name, self.tenant_id)

    async def send_message(self, chat_id: str, content: str, title: Optional[str] = None) -> str:
        if not self.channel:
            raise RuntimeError("Channel not initialized")
        
        msg = OutboundMessage(
            channel=self.platform_name,
            chat_id=chat_id,
            content=content,
            metadata={"title": title} if title else {},
        )
        await self.channel.send(msg)
        return msg.message_id or ""

    async def update_message(self, chat_id: str, message_id: str, content: str, title: Optional[str] = None) -> None:
        pass

    async def close(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
        if self.channel:
            await self.channel.stop()
        logger.info("Closed upstream adapter %s for tenant %s", self.platform_name, self.tenant_id)
