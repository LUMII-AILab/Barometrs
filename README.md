# Setup for development build
1. Create `.env` file according to `.env.example`.
2. Run `docker-compose -f docker-compose.dev.yml up --build -d` to build and start development containers.
3. (optional) [Pycharm] Set up remote interpreter:
   - Go to `File -> Settings -> Project -> Python Interpreter`.
   - Click `Add interpreter -> On SSH...`.
   - Fill in the fields (double-check the values in `docker-compose.dev.yml`):
     - Host: `localhost`.
     - Port: `2222`.
     - Username: `root`.
     - Password: no password.
     - Use System installed interpreter: `selected`.
     - Automatically sync project files: `checked`.
     - Path mappings: `<Project root> → /app`
   - Click `OK`.
   - Local project files might get [wiped out](https://youtrack.jetbrains.com/issue/WI-5900/problem-with-automatic-upload-local-deletions-are-applied-to-server), just don't commit them and unstage changes.
   - To connect to SSH via terminal run `ssh root@localhost -p 2222`.
4. Create volume for language models:
   ```
   docker volume create barometrs-language_models_volume
   ```
5. Run `download_models.py` to download language models from HuggingFace inside `web` container:
   ```
   docker exec -it web bash -c "python3 /app/download_models.py"
   ```
6. TBD

# Database export
Create database dump in plain-text format:
```
docker exec barometrs-db pg_dump -U emotion_classification -d emotion_classification -f /tmp/emotion_classification.sql
docker cp barometrs-db:/tmp/emotion_classification.sql ./emotion_classification.sql
```

Create database dump in directory-format:
```
docker exec barometrs-db pg_dump -U emotion_classification -d emotion_classification -Fc -Z 9 -f /tmp/emotion_classification.dump
docker cp barometrs-db:/tmp/emotion_classification.dump ./emotion_classification.dump
```

# Database import
1. Wipe out database:
```
docker exec -u root barometrs-db bash -c "rm -rf /var/lib/postgresql/data/*"
```
2. Copy data:
```
docker cp path_to/var/lib/postgresql/data/. barometrs-db:/var/lib/postgresql/data
```