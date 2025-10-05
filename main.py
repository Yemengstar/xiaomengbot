import aiohttp
import traceback
from typing import Optional, List

from astrbot.api.all import (
    Star, Context, register,
    AstrMessageEvent, command_group,
    MessageEventResult
)
from astrbot.api import logger

# ==============================
# HTML 模板（略）
# ==============================

CURRENT_WEATHER_TEMPLATE = """..."""  # 保持不变，见你原代码
FORECAST_TEMPLATE = """..."""         # 保持不变，见你原代码

# ==============================
# 插件类
# ==============================

@register(
    "astrbot_plugin_weather-qweather",
    "yemengstar",
    "一个基于和风天气API的天气查询插件（新版）",
    "0.3.0"
)
class WeatherPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.api_key = config.get("qweather_api_key", "")
        self.default_city = config.get("default_city", "北京")
        self.send_mode = config.get("send_mode", "image")
        self.api_base = config.get("qweather_base", "")

    # ========== 命令组 ==========
    @command_group("weather")
    def weather_group(self):
        """天气相关命令组 /weather current | forecast | help"""
        pass

    @weather_group.command("current")
    async def weather_current(self, event: AstrMessageEvent, city: str):
        if not city:
            city = self.default_city
        location_id = await self.get_location_id(city)
        if not location_id:
            yield event.plain_result(f"无法识别城市: {city}")
            return
        data = await self.get_current_weather(location_id, city)
        if not data:
            yield event.plain_result(f"查询 [{city}] 当前天气失败")
            return
        if self.send_mode == "image":
            url = await self.render_current_weather(data)
            yield event.image_result(url)
        else:
            yield event.plain_result(
                f"{city} 当前天气:\n"
                f"天气: {data['text']} 气温: {data['temp']}℃ (体感 {data['feelsLike']}℃)\n"
                f"湿度: {data['humidity']}% 风向: {data['windDir']} 风速: {data['windSpeed']} km/h"
            )

    @weather_group.command("forecast")
    async def weather_forecast(self, event: AstrMessageEvent, city: str):
        if not city:
            city = self.default_city
        location_id = await self.get_location_id(city)
        if not location_id:
            yield event.plain_result(f"无法识别城市: {city}")
            return
        data = await self.get_forecast_weather(location_id)
        if not data:
            yield event.plain_result(f"查询 [{city}] 天气预报失败")
            return
        if self.send_mode == "image":
            url = await self.render_forecast_weather(city, data)
            yield event.image_result(url)
        else:
            text = f"未来{len(data)}天天气预报 ({city}):\n"
            for day in data:
                text += (
                    f"{day['fxDate']}: 白天 {day['textDay']} {day['tempMax']}℃ | "
                    f"夜晚 {day['textNight']} {day['tempMin']}℃ | "
                    f"湿度 {day['humidity']}% 风速 {day['windSpeedDay']} km/h\n"
                )
            yield event.plain_result(text)

    @weather_group.command("help")
    async def weather_help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "=== 天气查询插件命令 ===\n"
            "/weather current <城市>  查询当前天气\n"
            "/weather forecast <城市> 查询未来3天天气\n"
            "/weather help            显示帮助"
        )

    # ========== 城市转 Location ID ==========
    async def get_location_id(self, city_name: str) -> Optional[str]:
        try:
            url = f"https://{self.api_base}/geo/v2/city/lookup"
            params = {"location": city_name}
            headers = {"X-QW-Api-Key": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    data = await resp.json()
                    if "location" not in data or not data["location"]:
                        return None
                    return data["location"][0]["id"]  # 返回第一个匹配项的 ID
        except Exception as e:
            logger.error(f"get_location_id error: {e}")
            logger.error(traceback.format_exc())
            return None

    # ========== 当前天气查询 ==========
    async def get_current_weather(self, location_id: str, city: str) -> Optional[dict]:
        try:
            url = f"{self.api_base}/v7/weather/now"
            params = {"location": location_id}
            headers = {"X-QW-Api-Key": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    data = await resp.json()
                    if "now" not in data:
                        return None
                    return {**data["now"], "city": city}
        except Exception as e:
            logger.error(f"get_current_weather error: {e}")
            logger.error(traceback.format_exc())
            return None

    # ========== 天气预报查询 ==========
    async def get_forecast_weather(self, location_id: str) -> Optional[List[dict]]:
        try:
            url = f"{self.api_base}/v7/weather/3d"
            params = {"location": location_id}
            headers = {"X-QW-Api-Key": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    data = await resp.json()
                    if "daily" not in data:
                        return None
                    return data["daily"]
        except Exception as e:
            logger.error(f"get_forecast_weather error: {e}")
            logger.error(traceback.format_exc())
            return None

    # ========== 渲染 HTML ==========
    async def render_current_weather(self, data: dict) -> str:
        return await self.html_render(
            CURRENT_WEATHER_TEMPLATE,
            data,
            return_url=True
        )

    async def render_forecast_weather(self, city: str, days: List[dict]) -> str:
        return await self.html_render(
            FORECAST_TEMPLATE,
            {"city": city, "days": days, "total_days": len(days)},
            return_url=True
        )
