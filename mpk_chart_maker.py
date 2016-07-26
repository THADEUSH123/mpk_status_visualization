"""Generate a chart for the MPK deployment.

The chart is in the form of an html document with embedded javascript.
"""

from collections import defaultdict
from deployment.datastore import Datastore
from deployment.device import SectorDevice
import folium
import json
import quip
import time
from selenium import webdriver

STATUS = {
    'down': {
        'color': 'red',
        'color-value': '#ff2600',
        'status-code': 0},
    'up': {
        'color': 'green',
        'color-value': '#00f900',
        'status-code': 1},
    'partial-up': {
        'color': 'yellow',
        'color-value': '#fffb00',
        'status-code': 2},
    'unknown': {
        'color': 'white',
        'color-value': '#ffffff',
        'status-code': 3},
    'testing': {
        'color': 'black',
        'color-value': '#000000',
        'status-code': 4}
}


def get_install_data(api_key, thread_id):
    """Pull data config data from the quip doc."""
    def is_installed_sector(row):
        """Return if is a configured sector device."""
        return all(
            [(row.get('device_type').lower() == 'sector'),
             (row.get('physical_install_status').lower() == 'installed'),
             (row.get('ipv6_admin_address').lower() != '')])

    quip_data = quip.dictReader(access_token=api_key,
                                thread_id=thread_id)

    return filter(is_installed_sector, quip_data)


def infer_devices_to_nodes(install_data):
    """Return a device map in adjacency list form.

    Format is in common human readable format of location description
    to list of installed device hostnames.
    """
    device_map = defaultdict(list)
    for row in install_data:
        device_map[row['location_description']].append(row['hostname'])
    return dict(device_map)


def infer_devices_to_links(install_data):
    """Return a device map in adjacency list form.

    Format is in common human readable format of location description
    to list of installed device hostnames.
    """
    device_map = defaultdict(list)
    for row in install_data:
        device_map[row['associated_link']].append(row['hostname'])
    return dict(device_map)


def apply_spacial_map(geojson_data, device_map):
    """Transform a mapping to use ids instead of 'common names' as keys.

    Keep the same values but convert the keys to uids of the known objects.
    This makes working with the mapping more efficient.
    """
    try:
        name_map = {f.properties['desc']: f['id'] for f in geojson_data}
    except:
        print [f.properties['desc'] for f in geojson_data if 'id' not in f]

    for key, values in device_map.items():
        description = name_map[key]
        device_map[description] = values
        del device_map[key]
    return device_map


def create_node_level_graph(nodes, edges):
    """Create a graph data structure of the deployment based on the mapping.

    This is implemented as a sparsely connected graph and uses an adjacency
    list of features(nodes and observations) to store relationships.
    """
    graph = defaultdict(list)
    for node_id, node_devices in nodes.iteritems():
        for link_id, link_devices in edges.iteritems():
            if not set(link_devices).isdisjoint(set(node_devices)):
                graph[node_id].append(link_id)
    return dict(graph)


def generate_device_status(node_map, edge_map, install_data):
    """Create a list of all devices for tracking status.

    This may better be called, associate with geospacial data id.
    """
    devices = {}
    for node_id, unique_device_ids in node_map.iteritems():
        for hostname in unique_device_ids:
            devices[hostname] = SectorDevice(id=hostname,
                                             mount_point_id=node_id)

    for link_id, unique_device_ids in edge_map.iteritems():
        for unique_device_id in unique_device_ids:
            try:
                devices[unique_device_id].radio_link_id = link_id
            except(KeyError):
                print('Please check the mapping. {} is referenced as a '
                      'device, but its location is not known.'
                      ''.format(unique_device_id))

    # Assign some other data to the devices based on configurations.
    for device_config in install_data:
        hostname = device_config.get('hostname', 'Unknown')
        devices[hostname].oob_ip_address = device_config['ipv6_admin_address']
        devices[hostname].hostname = device_config['hostname']

    return devices.values()


def update_nodes(geojson_data, devices):
    """Update nodes based on device status.

    This can be modified to display specific colors based on custom
    criteria.
    """
    def pretty_status(results):
        """Convert a results dict into a pretty status string."""
        if not results:
            return 'No known devices installed'
        else:
            return ' '.join(list('{} is {}\n'.format(name, status)
                            for name, status in results.iteritems()))

    for feature in geojson_data:
        ping_results = {device.id: device.status_ping
                        for device in devices
                        if device.mount_point_id == feature['id']}

        login_results = {device.id: device.status_login
                         for device in devices
                         if device.mount_point_id == feature['id']}

        radio_link_results = {device.id: device.status_radio_link
                              for device in devices
                              if device.mount_point_id == feature['id']}

        feature.properties['Ping Status'] = pretty_status(ping_results)
        feature.properties['Login Status'] = pretty_status(login_results)
        feature.properties['Radio Status'] = pretty_status(radio_link_results)

        if not ping_results:
            feature.properties['Overall Status'] = 'unknown'
        elif all(map(lambda x: x is 'down', ping_results.values())):
            feature.properties['Overall Status'] = 'down'
        elif all(map(lambda x: x is 'up', ping_results.values())):
            feature.properties['Overall Status'] = 'up'
        elif any(map(lambda x: x is 'up', ping_results.values())):
            feature.properties['Overall Status'] = 'partial-up'
        else:
            pass
    return geojson_data


def render_mpk_chart(features):
    """Construct an html file to display the status of the mpk deployment.

    Input is a list of features in python dict format.Output is a html file.
    """
    TABLE_OUTER = ('<center><h2>{title}</h2></center>'
                   '<table border="1" style="width:100%">'
                   '{table_rows}'
                   '</table>')

    TABLE_ROW = '<tr><td>{title}</td><td>{value}</td></tr>'

    mpk_chart = folium.Map(location=[37.484511, -122.14710], zoom_start=18)

    for feature in features:
        rows = ''.join([TABLE_ROW.format(title=name.replace('\n', '<br>'),
                                         value=value.replace('\n', '<br>'))
                        for (name, value) in feature.properties.items()])

        popup_html = TABLE_OUTER.format(title=feature.properties['desc'],
                                        table_rows=rows)

        popup = folium.Popup(folium.element.IFrame(html=popup_html,
                                                   width=350,
                                                   height=350),
                             max_width=350)

        status = feature.properties['Overall Status']
        if feature.geometry['type'] == 'LineString':
            ((lng1, lat1), (lng2, lat2)) = feature.geometry['coordinates']
            folium.PolyLine(locations=[(lat1, lng1), (lat2, lng2)],
                            color=STATUS[status]['color'],
                            popup=popup).add_to(mpk_chart)

        elif feature.geometry['type'] == 'Point':
            (lng1, lat1) = feature.geometry['coordinates'][0:2]
            icon = folium.Icon(color='white',
                               icon_color=STATUS[status]['color'])

            folium.Marker(location=[lat1, lng1],
                          popup=popup,
                          icon=icon).add_to(mpk_chart)

    mpk_chart.save('mpk_chart.html')


if __name__ == '__main__':
    with open('config_settings.json', 'r') as f:
        settings = json.loads(f.read())

    geospacial_data = Datastore()
    browser = webdriver.Firefox()

    geospacial_data.load_data(choice=settings['default_load_choice'],
                              file_path=settings['default_load_file'])

    while True:
        device_data = get_install_data(api_key=settings['quip_api_key'],
                                       thread_id=settings['thread_id'])

        device_map = infer_devices_to_nodes(device_data)
        link_map = infer_devices_to_links(device_data)

        device_map = apply_spacial_map(geojson_data=geospacial_data.all,
                                       device_map=device_map)

        link_map = apply_spacial_map(geojson_data=geospacial_data.all,
                                     device_map=link_map)

        mpk_device_status = generate_device_status(node_map=device_map,
                                                   edge_map=link_map,
                                                   install_data=device_data)

        for device in mpk_device_status:
            device.test_ping()
            device.test_login()
            device.test_radio_link()

        print('\nBuilding Map Now...')
        current_status = update_nodes(geospacial_data.all, mpk_device_status)
        render_mpk_chart(current_status)

        # f = '<path to file> /mpk_chart.html'
        # browser.get(f)
        time.sleep(10)
        print('Sleeping for 30 seconds...')
