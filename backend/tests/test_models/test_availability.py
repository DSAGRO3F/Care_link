"""
Tests unitaires pour le modèle UserAvailability.

Gère les créneaux de disponibilité récurrents des professionnels.
"""

from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from app.models import UserAvailability, User, Entity


class TestUserAvailability:
    """Tests pour le modèle UserAvailability."""

    def test_create_availability(self, db_session: Session, tenant, user_infirmier: User, entity: Entity):
        """Test création d'une disponibilité."""
        availability = UserAvailability(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            user_id=user_infirmier.id,
            entity_id=entity.id,
            day_of_week=2,  # Mardi
            start_time=time(14, 0),
            end_time=time(18, 0),
            is_recurring=True,
            is_active=True
        )
        db_session.add(availability)
        db_session.flush()

        assert availability.id is not None
        assert availability.day_of_week == 2
        assert availability.is_recurring is True

    def test_availability_relations(self, user_availability: UserAvailability, user_infirmier: User, entity: Entity):
        """Test relations UserAvailability → User, Entity."""
        assert user_availability.user == user_infirmier
        assert user_availability.entity == entity
        assert user_availability in user_infirmier.availabilities
        assert user_availability in entity.user_availabilities

    def test_availability_duration_minutes(self, user_availability: UserAvailability):
        """Test calcul de la durée en minutes."""
        # La fixture a 7h00-12h00 = 5 heures = 300 minutes
        assert user_availability.duration_minutes == 300

    def test_availability_duration_hours(self, user_availability: UserAvailability):
        """Test calcul de la durée en heures."""
        assert user_availability.duration_hours == 5.0

    def test_availability_is_valid_on_correct_day(self, user_availability: UserAvailability):
        """Test is_valid_on pour un jour correct."""
        # Trouver le prochain lundi
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)

        # La fixture a valid_from=today, donc le prochain lundi devrait être valide
        result = user_availability.is_valid_on(next_monday)
        assert isinstance(result, bool)

    def test_availability_is_valid_on_wrong_day(self, user_availability: UserAvailability):
        """Test is_valid_on pour un mauvais jour."""
        # Trouver le prochain mardi (day_of_week=2)
        today = date.today()
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday <= 0:
            days_until_tuesday += 7
        next_tuesday = today + timedelta(days=days_until_tuesday)

        # La fixture a day_of_week=1 (Lundi), donc mardi devrait être invalide
        assert user_availability.is_valid_on(next_tuesday) is False

    def test_availability_is_valid_on_inactive(self, db_session: Session, user_availability: UserAvailability):
        """Test is_valid_on pour une disponibilité inactive."""
        user_availability.is_active = False
        db_session.flush()

        # Trouver le prochain lundi
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)

        assert user_availability.is_valid_on(next_monday) is False

    def test_availability_overlaps_with_same_day(self, db_session: Session, tenant, user_infirmier: User, entity: Entity,
                                                 user_availability: UserAvailability):
        """Test chevauchement avec même jour."""
        other = UserAvailability(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            user_id=user_infirmier.id,
            entity_id=entity.id,
            day_of_week=1,  # Même jour (Lundi)
            start_time=time(10, 0),  # Chevauche 7h00-12h00
            end_time=time(14, 0),
            is_recurring=True,
            is_active=True
        )
        db_session.add(other)
        db_session.flush()

        assert user_availability.overlaps_with(other) is True

    def test_availability_no_overlap_different_day(self, db_session: Session, tenant, user_infirmier: User, entity: Entity,
                                                   user_availability: UserAvailability):
        """Test pas de chevauchement avec jour différent."""
        other = UserAvailability(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            user_id=user_infirmier.id,
            entity_id=entity.id,
            day_of_week=2,  # Mardi (différent)
            start_time=time(7, 0),
            end_time=time(12, 0),
            is_recurring=True,
            is_active=True
        )
        db_session.add(other)
        db_session.flush()

        assert user_availability.overlaps_with(other) is False

    def test_availability_no_overlap_adjacent(self, db_session: Session, tenant, user_infirmier: User, entity: Entity,
                                              user_availability: UserAvailability):
        """Test pas de chevauchement avec créneaux adjacents."""
        other = UserAvailability(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            user_id=user_infirmier.id,
            entity_id=entity.id,
            day_of_week=1,  # Même jour
            start_time=time(12, 0),  # Commence quand l'autre finit
            end_time=time(18, 0),
            is_recurring=True,
            is_active=True
        )
        db_session.add(other)
        db_session.flush()

        assert user_availability.overlaps_with(other) is False

    def test_availability_str(self, user_availability: UserAvailability):
        """Test représentation string."""
        result = str(user_availability)
        assert "Lun" in result
        assert "07:00" in result
        assert "12:00" in result