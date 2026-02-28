## Commands to run before starting database containers:
```
# Create the directories
mkdir -p /home/nikos/home-telemetry/deploy/data/timescaledb
mkdir -p /home/nikos/home-telemetry/deploy/data/pgadmin

# Change folders permissions
sudo chown -R 70:70 /home/nikos/home-telemetry/deploy/data/timescaledb

sudo chown -R 5050:5050 /home/nikos/home-telemetry/deploy/data/pgadmin
```

### Start the containers:
```
docker compose up
```
