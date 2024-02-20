# aiohttp server
import asyncio
import datetime as dt
import traceback

import asyncpg
from ago import human
from aiohttp import web

from utils.config import DATABASE_DSN, PATH, PORT
from utils.db import Database
from utils.find_my import FindMyDevices, FindMyItems

routes = web.RouteTableDef()


@routes.get("/")
async def track(request):
    return web.FileResponse("static/index.html")


@routes.get("/api/local/devices")
async def api_local_get_devices(request):
    return web.json_response(await app["devices"].get())


@routes.get("/api/local/items")
async def api_local_get_items(request):
    return web.json_response(await app["items"].get())


@routes.get("/api/db/latest")
async def api_db_get_latest(request):
    res = await app["db"].get_latest()
    for row in res:
        row["ago"] = human(dt.datetime.fromtimestamp(row["timestamp"]), precision=2)
        row["timestamp_human"] = dt.datetime.fromtimestamp(row["timestamp"]).isoformat()
    return web.json_response(res)


@routes.get("/api/db/trail/{did}")
async def api_db_get_trail(request):
    res = await app["db"].specific(request.match_info["did"])
    for row in res:
        row["ago"] = human(dt.datetime.fromtimestamp(row["timestamp"]), precision=2)
        row["timestamp_human"] = dt.datetime.fromtimestamp(row["timestamp"]).isoformat()

    return web.json_response(res)


async def update_database(app):
    try:
        while True:
            await asyncio.sleep(10)
            feed = await app["items"].get() + await app["devices"].get()
            for item in feed:
                try:
                    await app["db"].insert(item)
                    print(f"Inserted {item['id']} {item['timestamp']}")
                except asyncpg.exceptions.UniqueViolationError:
                    print("Duplicate", item["id"], item["timestamp"])
                    pass
                except:
                    traceback.print_exc()
    except asyncio.CancelledError:
        print("Background task cancelled")


async def background_tasks(app):
    app["update_database"] = asyncio.create_task(update_database(app))

    yield

    app["update_database"].cancel()
    await app["update_database"]


app = web.Application()
app.add_routes(routes)
app.add_routes([web.static("/static", "static")])
# add background tasks
app.cleanup_ctx.append(background_tasks)

app["db"] = Database(DATABASE_DSN)
app["items"] = FindMyItems(path=PATH)
app["devices"] = FindMyDevices(path=PATH)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
