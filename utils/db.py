import json
import re

import asyncpg
from addict import Dict


class Database:
    def __init__(self, dsn, regex_filter):
        self.dsn = dsn
        self.conn = None
        self.regex_filter = (
            re.compile(regex_filter) if regex_filter is not None else None
        )

    async def _connect(self):
        if self.conn is None:
            self.conn = await asyncpg.create_pool(self.dsn, command_timeout=60)
            await self._initdb()

    async def get_latest(self):
        await self._connect()
        async with self.conn.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    name,
                    address,
                    image,
                    timestamp,
                    latitude,
                    longitude,
                    altitude,
                    raw->'location'->'horizontalAccuracy' as accuracy,
                    raw->'role'->'emoji' as emoji
                FROM log
                WHERE
                    log.timestamp IN (SELECT max(timestamp) FROM log AS b WHERE log.id = b.id)
            """
            )
            return self.filter([Dict(dict(row)) for row in rows])

    async def specific(self, deviceid):
        await self._connect()
        async with self.conn.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    name,
                    address,
                    image,
                    timestamp,
                    latitude,
                    longitude,
                    altitude
                FROM log
                WHERE
                    id = $1
                ORDER BY timestamp DESC
                """,
                deviceid,
            )
            rows = [Dict(dict(row)) for row in rows]
            return self.filter(rows)

    async def insert(self, data):
        await self._connect()
        async with self.conn.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO log
                    (id, name, address, image, timestamp, latitude, longitude, altitude, raw)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                data.id,
                data.name,
                data.address,
                data.image,
                data.timestamp,
                data.latitude,
                data.longitude,
                data.altitude,
                json.dumps(data.raw),
            )

    async def _initdb(self):
        await self._connect()
        async with self.conn.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS log (
                    id TEXT CHECK (id <> ''),
                    name TEXT CHECK (name <> ''),
                    address TEXT,
                    image TEXT,
                    timestamp BIGINT CHECK (timestamp > 0),
                    latitude FLOAT CHECK (latitude > -90 AND latitude < 90),
                    longitude FLOAT CHECK (longitude > -180 AND longitude < 180),
                    altitude FLOAT,
                    raw JSONB,
                    UNIQUE (id, latitude, longitude, altitude, timestamp)
                );
                ALTER TABLE log ADD CONSTRAINT log_id_timestamp UNIQUE (id, timestamp);
            """
            )

    def filter(self, data):
        if self.regex_filter is None:
            return data
        return [i for i in data if re.match(self.regex_filter, i.name)]
