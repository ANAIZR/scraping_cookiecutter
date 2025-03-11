from rest_framework import serializers
from src.apps.shared.models.species import Species, ReportComparison, SpeciesSubscription, CabiSpecies


class SpeciesCabiSerializer(serializers.ModelSerializer):
    sobrenombre = serializers.CharField(source='scraper_source.sobrenombre', read_only=True)  

    class Meta:
        model = CabiSpecies
        fields = '__all__' 
        extra_fields = ['sobrenombre']


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
