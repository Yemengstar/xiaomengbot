import aiohttp
import traceback
from typing import Optional, List

from astrbot.api.all import (
    Star, Context, register,
    AstrMessageEvent, command_group,
    MessageEventResult
)

from astrbot.api import logger


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
      font-family: "Microsoft YaHei", sans-serif;
      background: linear-gradient(135deg, #6db3f2, #1e69de);
      color: #fff;
    }
    .weather-container {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
    }
    .card {
      background: rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(10px);
      border-radius: 16px;
      padding: 40px 60px;
      box-shadow: 0 8px 20px rgba(0,0,0,0.2);
    }
    h2 {
      font-size: 56px;
      margin: 0 0 30px;
      color: #fff;
      font-weight: 700;
    }
    .weather-info {
      font-size: 32px;
      margin: 10px 0;
    }
    .weather-info strong {
      color: #ffe082;
    }
    .source-info {
      margin-top: 30px;
      font-size: 20px;
      color: #ddd;
    }
  </style>
</head>
<body>
  <div class="weather-container">
    <div class="card">
      <h2>当前天气</h2>
      <div class="weather-info"><strong>城市:</strong> {{ city }}</div>
      <div class="weather-info"><strong>天气:</strong> {{ text }}</div>
      <div class="weather-info"><strong>温度:</strong> {{ temp }}℃</div>
      <div class="weather-info"><strong>湿度:</strong> {{ humidity }}%</div>
      <div class="weather-info"><strong>风速:</strong> {{ windSpeed }} km/h</div>
      <div class="source-info">数据来源: 和风天气（QWeather）</div>
    </div>
  </div>
</body>
</html>

"""

FORECAST_TEMPLATE = """
<html>
<head>
  <meta charset="UTF-8"/>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 1280px;
      height: 720px;
      font-family: "Microsoft YaHei", sans-serif;
      background: linear-gradient(135deg, #89f7fe, #66a6ff);
      color: #fff;
    }
    .forecast-container {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
    }
    .card {
      background: rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(10px);
      border-radius: 16px;
      padding: 30px 50px;
      box-shadow: 0 6px 16px rgba(0,0,0,0.2);
      width: 90%;
      max-width: 1000px;
    }
    h2 {
      font-size: 48px;
      margin: 0 0 20px;
      font-weight: 700;
    }
    .city-info {
      font-size: 28px;
      margin-bottom: 20px;
      color: #ffe082;
    }
    .day-item {
      text-align: left;
      background: rgba(255,255,255,0.1);
      border-radius: 12px;
      padding: 16px 24px;
      margin: 10px 0;
      font-size: 26px;
    }
    .day-title {
      font-weight: bold;
      font-size: 30px;
      margin-bottom: 8px;
      color: #ffeb3b;
    }
    .source-info {
      margin-top: 25px;
      font-size: 20px;
      color: #eee;
    }
  </style>
</head>
<body>
  <div class="forecast-container">
    <div class="card">
      <h2>未来{{ total_days }}天天气预报</h2>
      <div class="city-info"><strong>城市:</strong> {{ city }}</div>
      {% for day in days %}
      <div class="day-item">
        <div class="day-title">{{ day.date }}</div>
        <div><strong>白天:</strong> {{ day.text_day }} — {{ day.high }}℃</div>
        <div><strong>夜晚:</strong> {{ day.text_night }} — {{ day.low }}℃</div>
        <div><strong>湿度:</strong> {{ day.humidity }}%　<strong>风速:</strong> {{ day.wind_speed }} km/h</div>
      </div>
      {% endfor %}
      <div class="source-info">数据来源: 和风天气（QWeather）</div>
    </div>
  </div>
</body>
</html>
"""


# ==============================
# 插件类
# ==============================

@register(
    "小梦bot",
    "yemengstar",
    "一个基于和风天气API的天气查询插件",
    "0.3.2"
)
class WeatherPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.api_key = config.get("qweather_api_key", "")
        self.default_city = config.get("default_city", "上海")
        self.send_mode = config.get("send_mode", "text")
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
        msg = (
            "=== 和风天气插件命令列表 ===\n"
            "/weather current <城市>  查看当前实况\n"
            "/weather forecast <城市> 查看未来3天天气预报\n"
            "/weather help            显示本帮助\n"
            )
        yield event.plain_result(msg)

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
            url = f"https://{self.api_base}/v7/weather/now"
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
            url = f"https://{self.api_base}/v7/weather/3d"
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
