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
            "time_choices",
            "time_choices_display",
            "created_at",
            "updated_at",
        )
    def validate_url(self, value):
        
        instance = self.instance
        if instance and instance.url == value:
            return value

        if ScraperURL.objects.filter(url=value).exists():
            raise serializers.ValidationError("Esta URL ya ha sido registrada.")
        
        return value
