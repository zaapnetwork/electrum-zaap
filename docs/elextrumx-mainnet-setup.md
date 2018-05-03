# Setup electrumx server with docker

## 1. Setup zaapd node with docker

Used docker zaapd image has `txindex=1` setting in zaap.conf,
which is need by electrumx server.

Create network to link with electrumx server.

```
docker network create zaap-mainnet
```

Create volume to store zaapd data and settings.

```
docker volume create zaapd-data
```

Start zaapd container.

```
docker run --restart=always -v zaapd-data:/zaap \
    --name=zaapd-node --net zaap-mainnet -d \
    -p 24126:24126 -p 127.0.0.1:9998:9998 zebralucky/zaapd
```

**Notes**:
 - port 24126 is published without bind to localhost and can be
 accessible from out world even with firewall setup:
 https://github.com/moby/moby/issues/22054

Copy or change RPC password. Random password generated
on first container startup.

```
docker exec -it zaapd-node bash -l

# ... login to container

cat .zaapcore/zaap.conf | grep rpcpassword
```

See log of zaapd.

```
docker logs zaapd-node
```

## 2. Setup electrumx server with docker

Create volume to store elextrumx server data and settings.

```
docker volume create electrumx-zaap-data
```

Start elextrumx container.

```
docker run --restart=always -v electrumx-zaap-data:/data \
    --name electrumx-zaap --net zaap-mainnet -d \
    -p 50001:50001 -p 50002:50002 zebralucky/electrumx-zaap:mainnet
```

Change DAEMON_URL `rpcpasswd` to password from zaapd and creaate SSL cert.

**Notes**:
 - DAEMON_URL as each URL can not contain some symbols.
 - ports 50001, 50002 is published without bind to localhost and can be
 accessible from out world even with firewall setup:
 https://github.com/moby/moby/issues/22054

```
docker exec -it electrumx-zaap bash -l

# ... login to container

cd /data/

# Edit and save env/DAEMON_URL
nano env/DAEMON_URL

# Create SSL self signed certificate

openssl genrsa -des3 -passout pass:x -out server.pass.key 2048 && \
openssl rsa -passin pass:x -in server.pass.key -out server.key && \
rm server.pass.key && \
openssl req -new -key server.key -out server.csr

openssl x509 -req -days 730 -in server.csr -signkey server.key \
  -out server.crt && rm server.csr


exit
# ... logout from container

# Restart electrumx container to switch on new RPC password

docker restart electrumx-zaap
```

See log of electrumx server.

```
docker exec -it electrumx-zaap bash -l

# ... login to container

tail /data/log/current

# or less /data/log/current
```

Wait some time, when electrumx sync with zaapd and
starts listen on client ports. It can be seen on `/data/log/current`.
