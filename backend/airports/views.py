from __future__ import annotations

from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework import generics

from .models import Airport
from .serializers import AirportSerializer

MAX_LIMIT = 50
DEFAULT_LIMIT = 20


class AirportSearchView(generics.ListAPIView):
    serializer_class = AirportSerializer

    def get_queryset(self):
        q = (self.request.query_params.get("q") or "").strip()
        if not q:
            return Airport.objects.none()

        try:
            limit = int(self.request.query_params.get("limit", DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT
        limit = max(1, min(limit, MAX_LIMIT))

        q_upper = q.upper()
        qs = Airport.objects.filter(
            Q(iata__iexact=q) | Q(name__icontains=q) | Q(city__icontains=q)
        )
        qs = qs.annotate(
            is_iata_exact=Case(
                When(iata=q_upper, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("is_iata_exact", "name")
        return qs[:limit]
