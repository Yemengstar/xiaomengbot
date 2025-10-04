import aiohttp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

API_KEY = "fbf6abe122a249abbf74b478f26428fc"
BASE_URL = "https://devapi.qweather.com/v7/weather/now"

@register("weather_plugin", "yemengstar", "一个简单的天气查询插件", "0.1.2")
class WeatherPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """插件初始化"""
        logger.info("天气插件已加载")

    @filter.command()
    async def get_weather(self, ctx: Context, event: AstrMessageEvent):
        """
        当用户发送 xx天气 时触发
        """
        msg = event.message_str.strip()

        if not msg.endswith("天气"):
            return  # 不处理其他消息

        city = msg[:-2]  # 去掉“天气”，得到城市名
        if not city:
            yield event.plain_result("请发送 城市+天气，例如：北京天气")
            return

        # 调用和风天气 API
        async with aiohttp.ClientSession() as session:
            try:
                params = {"location": city, "key": API_KEY}
                async with session.get(BASE_URL, params=params) as resp:
                    data = await resp.json()
                    logger.info(data)

                    if "now" not in data:
                        yield event.plain_result(f"未能获取 {city} 的天气，请确认城市名称。")
                        return

                    now = data["now"]
                    text = now["text"]      # 天气情况
                    temp = now["temp"]      # 温度
                    humidity = now["humidity"]  # 湿度
                    wind_dir = now["windDir"]

                    result = f"{city}：{text}，气温 {temp}℃，湿度 {humidity}%，风向 {wind_dir}"
                    yield event.plain_result(result)

            except Exception as e:
                logger.error(f"获取天气失败: {e}")
                yield event.plain_result("查询天气失败，请稍后再试。")

    async def terminate(self):
        """插件销毁"""
        logger.info("天气插件已卸载")
