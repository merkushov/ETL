from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.http import JsonResponse
from django.views.generic.dates import BaseDetailView
from django.views.generic.list import BaseListView
from movies.models import Movie


class MoviesApiMixin:
    model = Movie
    http_method_names = ['get']

    def get_queryset(self):
        return Movie.objects.select_related(
            'type'
        ).prefetch_related(
            'genres'
        ).annotate(
            actors=ArrayAgg('persons__full_name', filter=Q(person_roles__name='актёр'))
        ).annotate(
            directors=ArrayAgg('persons__full_name', filter=Q(person_roles__name='режисёр'))
        ).annotate(
            writers=ArrayAgg('persons__full_name', filter=Q(person_roles__name='сценарист'))
        )

    def render_to_response(self, context):
        return JsonResponse(context)

    def movie_serialize(self, movie):
        movie_genres = [genre.name for genre in movie.genres.all()]

        return {
            "id": movie.id,
            "title": movie.title,
            "description": movie.description,
            "creation_date": movie.creation_date.strftime("%Y-%m-%d"),
            "rating": movie.rating,
            "type": movie.type.name,
            "genres": movie_genres,
            "actors": movie.actors,
            "directors": movie.directors,
            "writers": movie.writers,
        }


class Movies(MoviesApiMixin, BaseListView):
    paginate_by = 50

    def get_context_data(self, *args, **kwargs):
        queryset = self.get_queryset()
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset,
            self.paginate_by
        )

        context = {
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "prev": None,
            "next": None,
            'results': []
        }

        if page.has_previous():
            context["prev"] = page.previous_page_number()

        if page.has_next():
            context["next"] = page.next_page_number()

        context["results"] = [self.movie_serialize(movie) for movie in queryset.all()]

        return context


class MoviesDetailApi(MoviesApiMixin, BaseDetailView):
    def get_context_data(self, *args, **kwargs):
        return self.movie_serialize(self.object)
