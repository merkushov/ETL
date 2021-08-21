from django.urls import path

from movies.api.v1 import views

urlpatterns = [
    path('movies/', views.Movies.as_view()),
    path('movies/<uuid:pk>/', views.MoviesDetailApi.as_view()),
]
