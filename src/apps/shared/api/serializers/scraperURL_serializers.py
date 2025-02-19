from rest_framework import serializers
from src.apps.shared.models.scraperURL import ScraperURL, Species, ReportComparison


class ScraperURLSerializer(serializers.ModelSerializer):
    time_choices_display = serializers.CharField(
        source="get_time_choices_display", read_only=True
    )

    class Meta:
        model = ScraperURL
        fields = (
            "id",
            "sobrenombre",
            "url",
            "time_choices",
            "fecha_scraper", 
            "time_choices_display",
            "created_at",
            "updated_at",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.fecha_scraper is None:
            representation["fecha_scraper"] = "Aún no se ha realizado el proceso de scraper"
        return representation

    def validate_url(self, value):
        instance = self.instance
        if instance and instance.url == value:
            return value

        if ScraperURL.objects.filter(url=value).exists():
            raise serializers.ValidationError("Esta URL ya ha sido registrada.")

        return value
class SpeciesSerializer(serializers.ModelSerializer):
    sobrenombre = serializers.CharField(source='scraper_source.sobrenombre', read_only=True)  

    class Meta:
        model = Species
        fields = '__all__' 
        extra_fields = ['sobrenombre']

class ReportComparisonSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='scraper_source.url', read_only=True)
    scraper_source_id = serializers.IntegerField(source='scraper_source.id', read_only=True)


    class Meta:
        model = ReportComparison
        fields = '__all__'