from rest_framework import serializers
from src.apps.shared.models.scraperURL import ScraperURL, Species, ReportComparison, SpeciesSubscription


class ScraperURLSerializer(serializers.ModelSerializer):
    time_choices_display = serializers.CharField(
        source="get_time_choices_display", read_only=True
    )
    estado_scrapeo = serializers.CharField(read_only=True)
    error_scrapeo = serializers.CharField(read_only=True)
    fecha_scraper = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, allow_null=True)

    class Meta:
        model = ScraperURL
        fields = (
            "id",
            "sobrenombre",
            "url",
            "time_choices",
            "fecha_scraper", 
            "time_choices_display",
            "estado_scrapeo",  
            "error_scrapeo",    
            "created_at",
            "updated_at",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.fecha_scraper is None:
            representation["fecha_scraper"] = "Aún no se ha realizado el proceso de scraper"
        
        if instance.estado_scrapeo == "fallido":
            representation["error_scrapeo"] = instance.error_scrapeo or "Error desconocido."

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
    scraper_source = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ReportComparison
        fields = '__all__'

class SpeciesSubscriptionSerializer(serializers.ModelSerializer):
    scientific_name = serializers.CharField(required=False)
    distribution = serializers.CharField(required=False)
    hosts = serializers.CharField(required=False)
    name_subscription = serializers.CharField(required=True)
    
    class Meta:
        model = SpeciesSubscription
        fields = ["id", "user", "scientific_name", "distribution", "hosts","name_subscription", "created_at"]
        read_only_fields = ["id", "user", "created_at"]
