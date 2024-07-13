docker build -t news-comments-app .
docker run -d --name news-comments-app-container -p 8000:8000 -v %cd%:/app news-comments-app
docker stop news-comments-app-container

docker-compose -f docker-compose.prod.yml up --build -d # Build and start containers (prod)
docker-compose -f docker-compose.dev.yml up --build -d # Build and start containers (dev)
docker-compose down # Stop and remove containers

docker volume create barometrs-language_models_volume
docker run --rm -v %cd%/models:/source -v barometrs-language_models_volume:/target ubuntu cp -a /source/. /target/
docker volume rm barometrs-language_models_volume


Create database dump:
1. docker exec barometrs-db pg_dump -U emotion_classification -d emotion_classification -f /tmp/emotion_classification.sql
2. docker cp barometrs-db:/tmp/emotion_classification.sql ./emotion_classification.sql

Create database dump in directory-format:
1. docker exec barometrs-db pg_dump -U emotion_classification -d emotion_classification -Fc -Z 9 -f /tmp/emotion_classification.dump
2. docker cp barometrs-db:/tmp/emotion_classification.dump ./emotion_classification.dump