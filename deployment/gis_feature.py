"""Atomic object within a deployment environment.

There are 3 types of DeploymentFeatures: sites, mountpoints, and observations.
Sites and mountpoints are physical locations. Sites represent various objects
within a cityscape: streetlamps, buildings, traffic lights, etc. A mountpoint
generally represents a 1m X 1m X 1m sublocation on an site. An "observation" is
an observation of a characteristic of a physical object. Or an observation
between two objects, such as two mountpoints.

Observations can be made by any entity: surveys by people, automated analysis,
LIDAR, etc.

"""

from geojson import Feature, Point, LineString
from gis_utilities import distance, get_altitude


class DeploymentFeature(Feature):
    """A simple, Atom-ish, single geometry (WGS84) GIS feature.

    Used for analysis and tracking of deployment data.

    """

    def __init__(self, id, geometry, subtype, properties):
        """Initialise a DeploymentFeature with the given parameters.

        :param id: Identifier assigned to the object.
        :type id: int, str
        :param geometry: The geometry on which the object is based.
        :type geometry: Geometry
        :param subtype: Name of the object
        :type subtype: str
        :param desc: Short description associated with the object.
        :type desc: str
        :return: A DeploymentFeature object
        :rtype: DeploymentFeature
        """
        super(DeploymentFeature, self).__init__(id, geometry, properties)
        self['type'] = 'Feature'
        self.normalize_precision()

    @property
    def subtype(self):
        """Return type of object: 'site','mountpoint', or 'observation'."""
        return self.properties.get('subtype', None)

    @subtype.setter
    def subtype(self, value):
        """Set type of object: 'site','mountpoint', or 'observation'."""
        if value not in ['site', 'mountpoint', 'observation']:
            raise AttributeError()
        self.properties['subtype'] = value

    @property
    def coordinates(self):
        """The coordinates of the object."""
        return self.geometry['coordinates']

    @property
    def length(self):
        """The length of the object."""
        if isinstance(self.geometry, LineString):
            coords1, coords2 = self.coordinates
            return distance(coords1, coords2)
        else:
            return 0.0

    def normalize_precision(self):
        """Update a feature precision to avoid excessive decimals."""
        def nomalized_precision(coordinates):
            """Normalize coordinates [x, y, z] to 10 to11 cm of precision."""
            if len(coordinates) is 2:
                return [float('{:.6f}'.format(float(coordinates[0]))),
                        float('{:.6f}'.format(float(coordinates[1])))]

            elif len(coordinates) is 3:
                return [float('{:.6f}'.format(float(coordinates[0]))),
                        float('{:.6f}'.format(float(coordinates[1]))),
                        float('{:.1f}'.format(float(coordinates[2])))]

        try:
            if isinstance(self.geometry, Point):
                coordinates = nomalized_precision(self.coordinates)
                self.geometry['coordinates'] = coordinates

            elif isinstance(self.geometry, LineString):
                # Transform the first coordinate set in the line.
                coordinates0 = nomalized_precision(self.coordinates[0])
                self.geometry['coordinates'][0] = coordinates0

                # Transform the second coordinate set in the line.
                coordinates1 = nomalized_precision(self.coordinates[1])
                self.geometry['coordinates'][1] = coordinates1
        except (KeyError, TypeError):
            print 'failed precision checking'

        return self

    def remove_unused_properties(self):
        """Strip unused properties from the DeploymentFeature."""
        unused_props = [n for n, v in self.properties.iteritems() if v == '']
        for p_name in unused_props:
            print('{}=>DELETED for ({})'.format(p_name, self.id))
            del self.properties[p_name]

    def update_properties(self, properties):
        """Update the DeploymentFeatures properties.

        Default behavior is to overwrite existing properties if provided.
        """
        self.properties.update(properties)

    def update_icon(self, color='white', size='small'):
        """Update leaflet.js display properties using human readable input.

        This could be done with the update_properties method, but is intended
        to be more user friendly.
        """
        COLOR_MAP = {
            'red': "#ff2600",
            'green': "#00f900",
            'yellow': "#fffb00",
            'white': "#ffffff",
            'black': "#000000"
        }

        SIZE_MAP = {
            'small': 1,
            'medium': 3,
            'large': 5
        }

        if isinstance(self.geometry, Point):
            self.update_properties({
                'marker-color': COLOR_MAP[color],
                'marker-size': size})

        if isinstance(self.geometry, LineString):
            self.update_properties({
                'stroke': color,
                'stroke-width': SIZE_MAP[size],
                'stroke-opacity': 1})

    def infer_altitude(self, height_offset=0.0):
        """Add elevation/altitude data to the mountpount or site.

        Optionally add an additional offset for elevations that are above
        ground elevation(such as most/all mountpoints).
        """
        if isinstance(self.geometry, Point):
            lng, lat = self.coordinates[0:2]
            try:
                alt = get_altitude(lat, lng, height_offset)
                self.geometry['coordinates'] = [lng, lat, alt]
            except:
                print 'ERROR: Requesting altitude data'
