# 和风天气插件

一个基于 **和风天气 API (QWeather)** 的天气查询插件，支持 **实时天气** 和 **未来 3 天天气预报**，并支持 **文字模式** 或 **渲染为图片卡片** 两种展示方式。

## 功能特性

* 支持 `/weather current <城市>` 查询当前实时天气
* 支持 `/weather forecast <城市>` 查询未来 3 天天气预报
* 支持 `/weather help` 查看帮助
* 支持文字模式输出，也可图片
* 数据来源于 [QWeather 和风天气](https://dev.qweather.com/)


## 配置说明

在插件配置中配置以下内容：

```json
{
  "qweather_api_key": "你的和风天气API密钥",
  "default_city": "西安",
  "send_mode": "text",
  "qweather_base": "api.qweather.com"
}
```

参数说明：

* `qweather_api_key`：在 [和风天气控制台](https://dev.qweather.com/) 申请的 API Key
* `default_city`：默认查询的城市（如果用户未指定）
* `send_mode`：输出模式，支持 `"text"` 或 `"image"`
* `qweather_base`：和风天气 API 域名，一般为 `api.qweather.com`

## 使用方法

启动 AstrBot 后，可以使用以下命令：

```
/weather current 北京
```

查询北京实时天气。

```
/weather forecast 上海
```

查询上海未来 3 天天气预报。

```
/weather help
```

显示帮助信息。


## 开源协议
本插件代码在GitHub开源。