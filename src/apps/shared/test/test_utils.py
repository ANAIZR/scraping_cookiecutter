import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from src.apps.shared.utils.notify_change import check_new_species_and_notify, notify_user_of_new_species
from src.apps.shared.models.scraperURL import Species, SpeciesSubscription
from src.apps.users.models import User

@pytest.mark.django_db
@patch("src.apps.shared.utils.notify_change.notify_user_of_new_species")
def test_check_new_species_and_notify(mock_notify_user):
    user = User.objects.create_user(
        username="newuser",
        last_name="UserLastName",
        email="new@example.com",
        password="securepassword",
        system_role=2
    )


    species = Species.objects.create(
        scientific_name="Ficus elastica",
        created_at=timezone.now(),
        scraper_source=None  
    )

    subscription = SpeciesSubscription.objects.create(
        user=user,
        scientific_name="Ficus elastica"
    )

    check_new_species_and_notify(["https://example.com"])

    mock_notify_user.assert_called_once_with(user, subscription, [species])
@pytest.mark.django_db
@patch("src.apps.shared.utils.notify_change.notify_user_of_new_species")
def test_check_new_species_and_notify_no_new_species(mock_notify_user):

    check_new_species_and_notify(["https://example.com"])

    mock_notify_user.assert_not_called()

@patch("src.apps.shared.utils.notify_change.EmailService.send_email")
def test_notify_user_of_new_species(mock_send_email):
    user = MagicMock(email="user@example.com")
    subscription = MagicMock(scientific_name="Ficus elastica", distribution="South America", hosts="Insects")

    species = [
        MagicMock(scientific_name="Ficus elastica", source_url="https://example.com/species1"),
        MagicMock(scientific_name="Ficus elastica", source_url="https://example.com/species2"),
    ]

    notify_user_of_new_species(user, subscription, species)

    mock_send_email.assert_called_once()

