"""Define a network device that is deployed."""

import os


class SectorDevice(object):
    """A deployed sector."""

    def __init__(self, id, mount_point_id=None, mount_point_name=None):
        """Initialize the device and associate it with a location.

        A SectorDevice has various statuses for different tests. Each of
        these tests is independent of all other tests.
        """
        self.id = id
        self.radio_link_id = None
        self.status_ping = 'unknown'
        self.status_login = 'unknown'
        self.status_radio_link = 'unknown'
        self.hostname = None
        self.oob_ip_address = '127.0.0.1'  # For testing only
        self.mount_point_name = mount_point_name
        self.mount_point_id = mount_point_id
        self.username = 'root'
        self.password = ''

    def test_ping(self):
        """Test if an IP is pingable from the script endpoint."""
        response = os.system("ping6 -c 1 {}".format(self.oob_ip_address))
        if response is 0:
            self.status_ping = 'up'
        else:
            self.status_ping = 'down'

    def test_login(self):
        """Test if IP address is ssh-able from script endpoint."""
        self.status_login = 'unknown'  # Need to implement.

    def test_radio_link(self):
        """Test if a devices radio is functional."""
        self.status_radio_link = 'unknown'  # Need to implement.
