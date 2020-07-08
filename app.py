import json
import redis
import sys
import httpx
from datetime import timedelta
from fastapi import FastAPI

'''
To check whether a Redis client is running: redis-cli ping
To shut down the redis process: redis-cli shutdown 
'''

def redis_connect() -> redis.client.Redis:
    try:
        client = redis.Redis(
        host="localhost",
        port=6379,
        password="ubuntu",
        db=0,
        socket_timeout=5,
        )
        ping = client.ping()
        if ping is True:
            return client
    except redis.AuthenticationError:
            print("AuthenticationError")
            sys.exit(1)
        
client = redis_connect()

def get_routes_from_api(coordinates: str) -> dict:
    '''Data from mapbox api'''

    with httpx.Client() as client:
        base_url = "https://api.mapbox.com/optimized-trips/v1/mapbox/driving"
        geometries = "geojson"
        access_token = "pk.eyJ1IjoicGFyaXRvc2gtamFkaGF2IiwiYSI6ImNqMmJub2pzajAwMHMyd256cjAya2Z4dHAifQ.dVBv-QkoR0PbZwspq_TlHQ"

        url = f"{base_url}/{coordinates}?geometries={geometries}&access_token={access_token}"

        response = client.get(url)
        return response.json()

def get_routes_from_cache(key: str) -> str:
    '''Get data from Redis database'''

    val = client.get(key)
    return val

def set_routes_to_cache(key: str, value: str) -> str:
    '''Set data to Redis database'''

    state = client.setex(key, timedelta(seconds = 3600), value = value) 
    '''
    In setex: Set key to hold the string value and set key to timeout after a given number of seconds. 
    This command is equivalent to executing the following commands:

    SET mykey value
    EXPIRE mykey seconds
    '''

    return state 


def route_optima(coordinates: str) -> dict:
    #First look for data in Redis database
    
    #The key is the coordinates, which is basically a string of coordinate values. Thus 'data' variable is also a string.
    data = get_routes_from_cache(key = coordinates)

    #If data is in the cache, data is served

    if data is not None:
        data = json.loads(data)     #loads returns an object from a string(data) representing a JSON object
        data["cache"] = True        #that is the coordinates, since they are objects with lat,long as keys and their values as items.
        return data

    else:
        #If cache is not found, it sends the request to the MapBox API
        data = get_routes_from_api(coordinates) #look up in the function, the return value is a dict, an object representing a JSON object

        #Here we save the response to Redis db cache and then serve it directly
        if["code"] == "Ok":
            data["cache"] = False
            data = json.dumps(data)  #json.dumps returns a string from an object representing a JSON object. Now data is a string.
            state = set_routes_to_cache(key = coordinates, value = data)

            if state is True:
                return json.loads(data) #json.loads returns an object from a string representing a JSON object.
            return data

app = FastAPI

@app.get("/route-optima/{coordinates}")
def view(coordinates: str) -> dict:
    """This will wrap our original route optimization API and
    incorporate Redis Caching. You'll only expose this API to
    the end user. """

    #coordinates = "90.3866,23.7182;90.3742,23.7461" 

    return route_optima(coordinates)

'''https://stackoverflow.com/questions/32947076/redis-server-in-ubuntu14-04-bind-address-already-in-use'''