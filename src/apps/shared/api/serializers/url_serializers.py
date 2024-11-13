from rest_framework import serializers
from ...models.scraper import ScraperURL


class ScraperURLSerializer(serializers.ModelSerializer):
    type_file_display = serializers.CharField(
        source="get_type_file_display", read_only=True
    )
    time_choices_display = serializers.CharField(
        source="get_time_choices_display", read_only=True
    )

    class Meta:
        model = ScraperURL
        fields = (
            "id",
            "type_file",
            "type_file_display",
            "url",
            "short_url",
            "time_choices",
            "time_choices_display",
            "created_at",
            "updated_at",
        )
