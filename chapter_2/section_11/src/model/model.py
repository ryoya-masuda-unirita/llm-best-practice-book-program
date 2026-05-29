import json

from pydantic import BaseModel, ConfigDict, Field


class WeatherCondition(BaseModel):
    """天気予報の情報を格納するモデル"""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    period_name: str = Field(..., description="予報期間の名前（例: 今夜、明日、明後日など）")
    temperature: int = Field(..., description="気温（華氏）")
    temperature_unit: str = Field(..., description="温度の単位（F または C）")
    wind_speed: str = Field(..., description="風速")
    wind_direction: str = Field(..., description="風向き")
    forecast_summary: str = Field(..., description="天気予報の要約")


class ClothingRecommendation(BaseModel):
    """服装提案を格納するモデル"""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    clothing_type: str = Field(..., description="服装の種類（例: アウター、トップス、ボトムスなど）")
    item_suggestion: str = Field(..., description="具体的なアイテムの提案")
    reason: str = Field(..., description="その服装を提案する理由")


class OutfitResponse(BaseModel):
    """天気に基づく服装提案のレスポンスモデル"""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    location: str = Field(..., description="場所の説明（緯度・経度から推定）")
    weather_summary: str = Field(..., description="今日の天気の概要")
    current_weather: WeatherCondition = Field(..., description="現在または直近の天気予報情報")
    outfit_recommendations: list[ClothingRecommendation] = Field(
        ..., description="推奨される服装アイテムのリスト（最低3つ）", min_length=3
    )
    additional_advice: str = Field(..., description="その他のアドバイス（傘、日焼け止めなど）")

    @staticmethod
    def detailed_model() -> dict:
        """詳細なモデル構造を返すメソッド"""
        params = {
            "location": "string; 場所の説明（緯度・経度から推定）",
            "weather_summary": "string; 今日の天気の概要",
            "current_weather": {
                "period_name": "string; 予報期間の名前",
                "temperature": "number; 気温（華氏）",
                "temperature_unit": "string; 温度の単位",
                "wind_speed": "string; 風速",
                "wind_direction": "string; 風向き",
                "forecast_summary": "string; 天気予報の要約",
            },
            "outfit_recommendations": [
                {
                    "clothing_type": "string; 服装の種類（例: アウター、トップス、ボトムスなど）",
                    "item_suggestion": "string; 具体的なアイテムの提案",
                    "reason": "string; その服装を提案する理由",
                }
                for _ in range(3)
            ],
            "additional_advice": "string; その他のアドバイス（傘、日焼け止めなど）",
        }
        return params

    def save_as_json(self, file_path: str) -> None:
        """Save the outfit response as a JSON file."""

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)
