from rest_framework import serializers
from src.apps.shared.models.urls import ScraperURL

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

