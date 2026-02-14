## Commands to run before starting database containers:
```
# Create the directories
mkdir -p data/timescaledb
mkdir -p data/pgadmin

# Change folders permissions
sudo chown -R 70:70 data/timescaledb

sudo chown -R 5050:5050 data/pgadmin
```

### Start the containers:
```
docker compose up
```
