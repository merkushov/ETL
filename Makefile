dbshell:
	docker exec -it yandex_p_db psql -U postgres movie_catalog
.PHONY: dbshell