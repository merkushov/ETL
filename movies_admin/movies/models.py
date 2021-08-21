from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
import uuid


class BaseModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseLinkedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(
        _('date of creation'),
        auto_now_add=True,
        blank=True
    )

    class Meta:
        abstract = True


class Certificate(BaseModel):
    name = models.CharField(_('name'), max_length=60)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('age qualification')
        verbose_name_plural = _('age qualifications')
        db_table = 'content\".\"certificates'
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='certificates_name_uidx',
            )
        ]

    def __str__(self):
        return self.name


class Genre(BaseModel):
    name = models.CharField(_('name'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    movies = models.ManyToManyField(
        'Movie',
        verbose_name=_('genre film'),
        through='MovieGenre',
        blank=True,
    )

    class Meta:
        verbose_name = _('genre')
        verbose_name_plural = _('genres')
        db_table = 'content\".\"genres'
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='genres_name_uidx'
            )
        ]

    def __str__(self):
        return self.name


class Gender(models.TextChoices):
    MALE = 'male', _('male gender ')
    FEMALE = 'female', _('female gender ')


class Person(BaseModel):
    full_name = models.CharField(_('full name'), max_length=255)
    birth_date = models.DateField(_('date of birth '), blank=True, null=True)
    gender = models.TextField(_('gender'), choices=Gender.choices, null=True)
    movies = models.ManyToManyField(
        'Movie',
        verbose_name=_('person film'),
        through='MoviePersonRole',
        blank=True,
    )

    class Meta:
        verbose_name = _('person')
        verbose_name_plural = _('persons')
        db_table = 'content\".\"persons'

    def __str__(self):
        return self.full_name


class MovieType(BaseModel):
    name = models.CharField(_('name'), max_length=255)

    class Meta:
        verbose_name = _('type of film')
        verbose_name_plural = _('types of film')
        db_table = 'content\".\"movie_types'
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='movie_types_name_uidx'
            )
        ]

    def __str__(self):
        return self.name


class Movie(BaseModel):
    title = models.CharField(_('name'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    imdb_identifier = models.CharField(
        _('IMDB identifier'),
        max_length=255,
        blank=True
    )
    creation_date = models.DateField(
        _('movie creation date '),
        blank=True,
        null=True
    )
    file_path = models.FileField(
        _('file'),
        upload_to='movies/',
        blank=True
    )
    rating = models.FloatField(
        _('rating'),
        validators=[MinValueValidator(0)],
        blank=True,
        default=0
    )
    type = models.ForeignKey(
        MovieType,
        verbose_name=_('type of film'),
        related_name='movies',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    certificate = models.ForeignKey(
        Certificate,
        verbose_name=_('age qualification'),
        related_name='movies',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    genres = models.ManyToManyField(
        Genre,
        through='MovieGenre',
    )
    persons = models.ManyToManyField(
        Person,
        verbose_name=_('film person'),
        through='MoviePersonRole',
        blank=True,
    )
    person_roles = models.ManyToManyField(
        'PersonRole',
        through='MoviePersonRole'
    )

    class Meta:
        verbose_name = _('film work')
        verbose_name_plural = _('film works')
        db_table = 'content\".\"movies'

    def __str__(self):
        return self.title


class MovieGenre(BaseLinkedModel):
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
    )
    genre = models.ForeignKey(
        Genre,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _('film genre')
        verbose_name_plural = _('film genres')
        db_table = 'content\".\"movie_genre'
        constraints = [
            models.UniqueConstraint(
                fields=['movie_id', 'genre_id'],
                name='movie_genre_main_uidx'
            )
        ]


class PersonRole(BaseModel):
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('role')
        verbose_name_plural = _('roles')
        db_table = 'content\".\"person_roles'
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='person_roles_name_uidx',
            )
        ]

    def __str__(self):
        return self.name


class MoviePersonRole(BaseLinkedModel):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    person_role = models.ForeignKey(PersonRole, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('film person')
        verbose_name_plural = _('film persons')
        db_table = 'content\".\"movie_person_role'
        constraints = [
            models.UniqueConstraint(
                fields=['movie_id', 'person_id', 'person_role_id'],
                name='movie_person_role_main_uidx'
            )
        ]
