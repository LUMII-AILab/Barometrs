docker build -t news-comments-app .
docker run -d --name news-comments-app-container -p 8000:8000 -v %cd%:/app news-comments-app
docker stop news-comments-app-container

docker-compose -f docker-compose.prod.yml up --build -d # Build and start containers (prod)
docker-compose -f docker-compose.dev.yml up --build -d # Build and start containers (dev)
docker-compose down # Stop and remove containers

docker volume create barometrs-language_models_volume
docker run --rm -v %cd%/models:/source -v barometrs-language_models_volume:/target ubuntu cp -a /source/. /target/
docker volume rm barometrs-language_models_volume