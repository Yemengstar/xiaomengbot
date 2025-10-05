import aiohttp
import traceback
from typing import Optional, List

from astrbot.api.all import (
    Star, Context, register,
    AstrMessageEvent, command_group,
    MessageEventResult, llm_tool
)
from astrbot.api import logger

# ==============================
# 1) HTML 模板
# ==============================

CURRENT_WEATHER_TEMPLATE = """
<html>
<head>
  <meta charset="UTF-8"/>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 1280px;
      height: 720px;
      background-color: #fff;
    }
    .weather-container {
      width: 100%;
      height: 100%;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      font-family: sans-serif;
      font-size: 30px;
      color: #333;
    }
    h2 { color: #4e6ef2; font-size: 40px; }
    .info { margin: 8px 0; }
    .source { font-size: 16px; color: #999; margin-top: 12px; }
  </style>
</head>
<body>
  <div class="weather-container">
    <h2>当前天气</h2>
    <div class="info"><strong>城市:</strong> {{ city }}</div>
    <div class="info"><strong>天气:</strong> {{ text }}</div>
    <div class="info"><strong>气温:</strong> {{ temp }}℃ (体感: {{ feelsLike }}℃)</div>
    <div class="info"><strong>湿度:</strong> {{ humidity }}%</div>
    <div class="info"><strong>风向:</strong> {{ windDir }}</div>
    <div class="info"><strong>风速:</strong> {{ windSpeed }} km/h</div>
    <div class="source">数据来源: 和风天气</div>
  </div>
</body>
</html>
"""

FORECAST_TEMPLATE = """
<html>
<head>
  <meta charset="UTF-8"/>
  <style>
    html, body { margin:0; padding:0; width:1280px; height:720px; background:#fff; }
    .container { padding:16px; font-family:sans-serif; color:#333; }
    h2 { color:#4e6ef2; font-size:40px; margin-bottom:8px; }
    .day { margin:8px 0; padding:8px; border-bottom:1px solid #eee; }
    .source { font-size:16px; color:#999; margin-top:12px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>未来{{ total_days }}天天气预报</h2>
    <div><strong>城市:</strong> {{ city }}</div>
    {% for day in days %}
      <div class="day">
        <div><strong>{{ day.fxDate }}</strong></div>
        <div>白天: {{ day.textDay }} — {{ day.tempMax }}℃</div>
        <div>夜晚: {{ day.textNight }} — {{ day.tempMin }}℃</div>
        <div>湿度: {{ day.humidity }}%  风速: {{ day.windSpeedDay }} km/h</div>
      </div>
    {% endfor %}
    <div class="source">数据来源: 和风天气</div>
  </div>
</body>
</html>
"""

# ==============================
# 2) 插件类
# ==============================

@register(
    "astrbot_plugin_weather-qweather",
    "yemengstar",
    "一个基于和风天气API的天气查询插件",
    "0.1.0"
)
class WeatherPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.api_key = config.get("qweather_api_key", "fbf6abe122a249abbf74b478f26428fc")
        self.default_city = config.get("default_city", "北京")
        self.send_mode = config.get("send_mode", "image")  # "image" 或 "text"

    # =============================
    # 命令组 /weather
    # =============================
    @command_group("weather")
    def weather_group(self):
        """天气相关命令组 /weather current | forecast | help"""
        pass

    @weather_group.command("current")
    async def weather_current(self, event: AstrMessageEvent, city: Optional[str] = None):
        if not city:
            city = self.default_city
        data = await self.get_current_weather_by_city(city)
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
    async def weather_forecast(self, event: AstrMessageEvent, city: Optional[str] = None):
        if not city:
            city = self.default_city
        data = await self.get_forecast_weather_by_city(city)
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

    # =============================
    # 和风天气 API
    # =============================
    async def get_current_weather_by_city(self, city: str) -> Optional[dict]:
        try:
            url = "https://devapi.qweather.com/v7/weather/now"
            params = {"key": self.api_key, "location": city}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    if "now" not in data:
                        return None
                    return {**data["now"], "city": city}
        except Exception as e:
            logger.error(f"get_current_weather error: {e}")
            logger.error(traceback.format_exc())
            return None

    async def get_forecast_weather_by_city(self, city: str) -> Optional[List[dict]]:
        try:
            url = "https://devapi.qweather.com/v7/weather/3d"
            params = {"key": self.api_key, "location": city}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    if "daily" not in data:
                        return None
                    return data["daily"]
        except Exception as e:
            logger.error(f"get_forecast_weather error: {e}")
            logger.error(traceback.format_exc())
            return None

    # =============================
    # 渲染 HTML
    # =============================
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
