"""Simpe utilities to manipulate geospatial data."""

from math import radians, cos, sin, atan2, sqrt
from time import sleep
from urllib import urlencode, urlopen
from simplejson import load


def get_altitude(lattitude, longitude, offset=0.0):
    """
    Convert a latitude and longitude into a list of x, y, z coordinates.

    NOTE: the geojson spec of x, y, z order (easting, northing,
    altitude for coordinates) and not lat, lng, alt.
    """
    coordinates = '{},{}'.format(lattitude, longitude)
    BASE_URL = 'http://maps.google.com/maps/api/elevation/json'
    url = BASE_URL + '?' + urlencode({'locations': coordinates})
    response = load(urlopen(url))['results'][0]['elevation']
    print('At {}, the altitude is {}'.format(coordinates, response))
    sleep(1)  # Play nice with the api and wait
    return float('{:.1f}'.format(offset + float(response)))


def distance(coordinates1, coordinates2):
    """
    Return the distance in meters between two points.

    Accept coordinates in [x, y, z] or [lng, lat, alt]. Ignore altitude due to
    common accuracy issues.
    """
    (lat1, long1) = (float(x) for x in coordinates1[0:2])
    (lat2, long2) = (float(x) for x in coordinates2[0:2])
    radius = 6371 * 1000  # radius of earth in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(long2 - long1)
    a = sin(dlat / 2) * sin(dlat / 2) \
        + cos(radians(lat1)) * cos(radians(lat2)) \
        * sin(dlon / 2) * sin(dlon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    d = radius * c
    return float('{:.1f}'.format(d))


def calc_azimuth_elevation(origin, destination):
    """Calculate the magnetic azimuth between two points."""
    pass
