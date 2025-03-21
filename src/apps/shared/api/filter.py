import django_filters
from ..models.species import CabiSpecies
from ..models.urls import ScraperURL

class CabiSpeciesFilter(django_filters.FilterSet):
    scientific_name = django_filters.CharFilter(field_name='scientific_name', lookup_expr='icontains')
    hosts = django_filters.CharFilter(field_name='hosts', lookup_expr='icontains')
    distribution = django_filters.CharFilter(field_name='distribution', lookup_expr='icontains')

    class Meta:
        model = CabiSpecies
        fields = ['scientific_name', 'hosts', 'distribution']

class ScraperURLFilter(django_filters.FilterSet):
    sobrenombre = django_filters.CharFilter(field_name='sobrenombre', lookup_expr='icontains')
    estado_scrapeo = django_filters.CharFilter(field_name='estado_scrapeo', lookup_expr='icontains')

    class Meta:
        model = ScraperURL
        fields = ['sobrenombre', 'estado_scrapeo']