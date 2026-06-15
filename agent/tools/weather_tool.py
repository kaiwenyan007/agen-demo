"""今日天气（Open-Meteo，用户需指定中国城市名）。"""

from __future__ import annotations

import httpx

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_today_weather",
        "description": "查询中国指定城市今日天气。用户问某地天气、气温、是否下雨时使用，必须传入城市名。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "中国城市名称，如北京、上海、深圳、杭州",
                },
            },
            "required": ["city"],
        },
    },
}

# WMO Weather interpretation codes (Open-Meteo)
_WMO_ZH: dict[int, str] = {
    0: "晴",
    1: "大部晴朗",
    2: "局部多云",
    3: "多云",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT = 8.0


def _weather_desc(code: int) -> str:
    return _WMO_ZH.get(code, f"天气码{code}")


def get_today_weather(city: str) -> str:
    """查询中国城市今日天气；city 必填。"""
    city = (city or "").strip()
    if not city:
        return "请提供中国城市名称后再查询，例如：北京、上海、深圳。"

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            geo_resp = client.get(
                _GEO_URL,
                params={
                    "name": city,
                    "count": 5,
                    "language": "zh",
                    "countryCode": "CN",
                },
            )
            geo_resp.raise_for_status()
            results = geo_resp.json().get("results") or []
            if not results:
                return (
                    f"未找到中国城市「{city}」。"
                    "请使用标准城市名（如北京、成都），暂仅支持中国大陆城市。"
                )

            loc = results[0]
            lat = loc["latitude"]
            lon = loc["longitude"]
            place = loc.get("name", city)
            admin1 = loc.get("admin1") or ""
            location_label = f"{place}（{admin1}）" if admin1 and admin1 != place else place

            fc_resp = client.get(
                _FORECAST_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": (
                        "weather_code,temperature_2m_max,temperature_2m_min,"
                        "precipitation_probability_max,wind_speed_10m_max"
                    ),
                    "timezone": "Asia/Shanghai",
                    "forecast_days": 1,
                },
            )
            fc_resp.raise_for_status()
            daily = fc_resp.json().get("daily") or {}
            dates = daily.get("time") or []
            if not dates:
                return f"天气服务未返回「{location_label}」的数据，请稍后重试。"

            date_str = dates[0]
            code = daily["weather_code"][0]
            t_max = daily["temperature_2m_max"][0]
            t_min = daily["temperature_2m_min"][0]
            pop = daily.get("precipitation_probability_max", [None])[0]
            wind = daily.get("wind_speed_10m_max", [None])[0]
            desc = _weather_desc(int(code))

            lines = [
                f"【今日天气 | {location_label} | {date_str}】",
                f"天气：{desc}",
                f"气温：{t_min:.0f}°C ~ {t_max:.0f}°C",
            ]
            if pop is not None:
                lines.append(f"降水概率：{pop}%")
            if wind is not None:
                lines.append(f"最大风速：{wind:.0f} km/h")
            lines.append("（以上数据来自天气服务，请原样告知用户，勿编造数值）")
            return "\n".join(lines)

    except httpx.TimeoutException:
        return "天气服务请求超时，请稍后重试。"
    except httpx.HTTPError as exc:
        return f"天气服务请求失败：{exc}"
    except (KeyError, IndexError, TypeError, ValueError):
        return "天气数据解析失败，请稍后重试。"
