from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tools.custom.weather_forecast import TOOL_SPEC, run


class WeatherForecastTests(unittest.TestCase):
    def _mock_resp(self, payload: str):
        resp = MagicMock()
        resp.read.return_value = payload.encode("utf-8")
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "weather_forecast")

    def test_empty_location(self) -> None:
        result = run({"location": " "}, {})
        self.assertIn("error", result)

    def test_invalid_unit(self) -> None:
        result = run({"location": "Paris", "temperature_unit": "kelvin"}, {})
        self.assertIn("error", result)

    def test_no_geocode_result(self) -> None:
        responses = [self._mock_resp('{"results": []}')]
        with patch("urllib.request.urlopen", side_effect=responses):
            result = run({"location": "NoSuchCity"}, {})
        self.assertIn("error", result)

    def test_success(self) -> None:
        geocode = self._mock_resp(
            '{"results":[{"name":"Paris","country":"France","latitude":48.85,"longitude":2.35}]}'
        )
        weather = self._mock_resp(
            '{"timezone":"Europe/Paris","current":{"temperature_2m":24.5,"wind_speed_10m":12.3,"weather_code":3},'
            '"daily":{"time":["2026-07-23"],"temperature_2m_max":[29.0],"temperature_2m_min":[18.0],'
            '"precipitation_probability_max":[20]}}'
        )
        with patch("urllib.request.urlopen", side_effect=[geocode, weather]):
            result = run({"location": "Paris", "days": 1}, {})
        self.assertEqual(result["location"]["name"], "Paris")
        self.assertEqual(len(result["forecast"]), 1)
        self.assertEqual(result["forecast"][0]["temp_max"], 29.0)


if __name__ == "__main__":
    unittest.main()
