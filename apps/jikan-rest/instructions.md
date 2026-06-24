# run this command in your terminal to generate the secrets for the database and redis

```bash
echo -n "jikan"        > secrets/db_username.txt
echo -n "jikanadmin"   > secrets/db_admin_username.txt
openssl rand -hex 24   > secrets/db_password.txt
openssl rand -hex 24   > secrets/db_admin_password.txt
openssl rand -hex 24   > secrets/redis_password.txt
openssl rand -hex 24   > secrets/typesense_api_key.txt
chmod 600 secrets/*.txt

# then start the container as normal `docker compose up -d jikan_rest`

run these commands to seed the index notice here i use the -d flag to run the command in the background so you can continue using your terminal. You can also remove the -d flag to see the output of the command in your terminal.

```bash
# Fast metadata
docker exec -d jikan_rest php artisan indexer:genres
docker exec -d jikan_rest php artisan indexer:producers
docker exec -d jikan_rest php artisan indexer:anime-current-season
docker exec -d jikan_rest php artisan indexer:anime-schedule

# Full catalog (~30k anime — runs for hours; --delay is seconds between requests, default 3)
# Using --delay=1 to speed up indexing (faster than default but still polite to upstream)
docker exec -d jikan_rest sh -c 'php artisan indexer:anime --delay=1 >> /tmp/indexer-anime.log 2>&1'

The bundled RoadRunner app server can accumulate CPU/memory over time. To recycle workers gracefully (no restart needed), mount a custom .rr.yaml over /app/.rr.yaml that adds lifecycle limits — give the queue worker queue:work --max-time=3600 --max-jobs=1000 --memory=256, set the HTTP pool supervisor.exec_ttl: 3600s, and cap num_workers. Add - ./rr.yaml:/app/.rr.yaml:ro to the jikan_rest volumes.

I have bundeled the rr.yaml file in apps/jikan-rest/rr.yaml that you can use. it should work out of the box, but you can also customize it to your needs.

# Once complete add `JIKAN_API_BASE=http://jikan_rest:8080/v4` to your AIOMetadata .env file and you should be good to go after force recreating the container.

# This information was pulled from: https://github.com/cedya77/aiometadata#4-self-hosted-jikan-api-optional--anime-source

# All credits go to Cedya and Din the Goats that brought us AIOMetadata (ft Andrew).

# Any issues please join the discord server: https://discord.gg/DdXgUY7e8z 