from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("小梦", "yemengstar", "一个简单的 测试 插件", "0.1")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """插件初始化（启动时执行一次）"""
        logger.info("HelloWorld 插件已加载")

    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """HelloWorld 指令"""
        user_name = event.get_sender_name()   # 获取用户昵称
        message_str = event.message_str       # 获取用户发送的原始字符串
        logger.info(f"收到消息: {message_str}")

        # 返回一条纯文本结果
        yield event.plain_result(f"Hello, {user_name}, 你刚才发的是: {message_str}")

    async def terminate(self):
        """插件销毁（卸载时执行一次）"""
        logger.info("HelloWorld 插件已卸载")
