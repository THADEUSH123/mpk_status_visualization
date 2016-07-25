"""Persistant data storage.

Store persistent serialized data in text documents from python objects and vic
versa. Also provides helper functions to manage DeploymentFeature objects.
"""

from gis_feature import DeploymentFeature
from github3 import login, GitHubError
from geojson import Feature, FeatureCollection, loads, dumps
from os import makedirs, walk, path
from uuid import uuid4
import json


class Datastore(object):
    """
    Manage data from local files and online files in a pythonic way.

    The Datastore class manages persistent data storage and exposes the data in
    native python objects(DeploymentFeatures). The class can be extended to
    support various file types and repositories.

    """

    def __init__(self, config_file=None):
        """init DeploymentFeatures that are stored in the Datastore class."""
        self._data = {}
        try:
            with open(config_file, 'r') as f:
                self._settings = json.loads(f.read())
        except (IOError):
            self._settings = {}
            print('Unable to load settings file: File does not exsist.')
        except (TypeError):
            self._settings = {}
            pass

    def __setitem__(self, key, value):
        """Type checking before adding the value object to the store."""
        if not isinstance(value, DeploymentFeature):
            print('This is not a DeploymentFeature!\n{}'.format(value))
            raise TypeError
        self._data[key] = value

    def __getattr__(self, name):
        """Get attributes available in the Datastore class.

        Perform simple filtering of object types for easy manipultion.
        """
        if name is 'sites':
            return [f for f in self._data.values()
                    if f.subtype == 'site']
        elif name is 'mountpoints':
            return [f for f in self._data.values()
                    if f.subtype == 'mountpoint']
        elif name is 'observations':
            return [f for f in self._data.values()
                    if f.subtype == 'observation']
        elif name is 'all':
            return self._data.values()
        elif name is 'settings':
            return self._settings

    def add(self, feature):
        """Validate and add instance of DeploymentFeature to the Datastore set.

        :param feature: A feature to add
        :type feature: DeploymentFeature
        """
        try:
            identitifier = str(feature.get('id', uuid4()))
            properties = feature.get('properties')
            subtype = properties.get('subtype')

            while subtype is None:
                print('{} subtype not specified.'.format(identitifier))
                subtype = raw_input('Assign subtype [site]: ') or 'site'

            new_feature = DeploymentFeature(id=identitifier,
                                            geometry=feature['geometry'],
                                            subtype=subtype,
                                            properties=properties)

            self._data[identitifier] = new_feature

        except (OSError, TypeError):
            print('Failed to properly add/import {}'.format(identitifier))
        except (AttributeError):
            print('{} subtype not specified.'.format(identitifier))
            subtype = raw_input('Assign subtype [site]: ') or 'site'

    def load_folder(self, folder):
        """Load geojson files from a folder and store them in the Datastore."""
        for (dirpath, dirnames, filenames) in walk(folder):
            for filename in filenames:
                try:
                    file_path = path.join(dirpath, filename)
                    with open(file_path, 'r') as f:
                        feature = loads(f.read())
                        self.add(feature)
                except (IOError), error:
                    print(error)
                except:
                    print('Unable to load {}.'.format(filename))
        print('SUCCESS: files loaded!')

    def write_folder(self, folder):
        """Save all objects as multipe geojson local files."""
        FOLDERS = {
            'observation': 'observation-objects',
            'mountpoint': 'mountpoint-objects',
            'site': 'site-objects',
            'device': 'device-objects',
            'link': 'link-objects'
        }

        for feature in self.all:
            file_name = feature.id + '.json'
            sub_path = path.join(folder, FOLDERS[feature.subtype])
            full_path = path.join(sub_path, file_name)
            if not path.exists(sub_path):
                makedirs(sub_path)

            with open(full_path, 'w')as f:
                f.write(format_to_geojson(feature))

    def load_geojson_file(self, file_path):
        """Load features from single geojson document."""
        try:
            with open(file_path, 'r') as f:
                feature_collection = f.read()

            features = loads(feature_collection).features
            for feature in features:
                self.add(feature)
            print('SUCCESS: file loaded!')
        except (IOError), error:
            print(error)

    def write_geojson_file(self, file_path):
        """Save all objects as a single geojson collection in a local file."""
        with open(file_path, 'w') as f:
            f.write(format_to_geojson(self.all))

    def load_gist(self, github_user, github_psswd, gist_id):
        """Load a geojson collection from a gist repo."""
        try:
            github = login(github_user, password=github_psswd)
            display_gist = github.gist(gist_id)
            for file in display_gist.iter_files():
                feature_collection = file.content

            for feature in loads(feature_collection).features:
                self.add(feature)

            print('SUCCESS: gist id {} loaded!'.format(gist_id))
        except(GitHubError, AttributeError), error:
            print('ERROR: load failed due to {}'.format(error))

    def write_gist(self, github_user, github_psswd, gist_id):
        """Save all objects as a single geojson collection in a gist repo."""
        try:
            github = login(github_user, password=github_psswd)
            gist = github.gist(gist_id)
            collection = format_to_geojson(self.all)
            gist.edit(files={gist_id + '.geojson': {"content": collection}})
            print('SUCCESS: gist id {} saved!'.format(gist_id))
        except(GitHubError, AttributeError), error:
            print('ERROR: save failed due to {}'.format(error))

    def load_data(self, choice=1, folder=None, file_path=None, gh_gist_id=None,
                  gh_username=None, gh_password=None):
        """Load data into Datastore based on user supplied input."""
        PROMPT = ('\n============LOAD MENU================='
                  '\nLoad multiple data sets in the following ways:'
                  '\n1 => From a folder'
                  '\n2 => From a geojson file'
                  '\n3 => From a geojson file in a gist'
                  '\n4 => Do not load additional data'
                  '\nEnter menue choice[{}]: ')

        while True:
            try:
                choice = int(raw_input(PROMPT.format(choice)) or choice)
            except(ValueError):
                print('Invalid choice')

            if choice is 1:
                folder_prompt = 'Enter folder name[{}]: '.format(folder)
                folder = raw_input(folder_prompt) or folder
                self.load_folder(folder)

            if choice is 2:
                file_prompt = 'Enter file name[{}]: '.format(file_path)
                file_path = raw_input(file_prompt) or file_path
                self.load_geojson_file(file_path)

            if choice is 3:
                user_prompt = 'Enter username[{}]: '.format(gh_username)
                gh_username = raw_input(user_prompt) or gh_username
                password_prompt = 'Enter password[{}]: '.format(gh_password)
                gh_password = raw_input(password_prompt) or gh_password
                gist_prompt = 'Enter gist ID[{}]: '.format(gh_gist_id)
                gh_gist_id = raw_input(gist_prompt) or gh_gist_id
                self.load_gist(gh_username, gh_password, gh_gist_id)

            if choice is 4:
                break

            choice = 4

    def save_data(self, choice=1, folder=None, file_path=None, gh_gist_id=None,
                  gh_username=None, gh_password=None):
        """Save data into Datastore based on user supplied input."""
        PROMPT = ('\n============SAVE MENU================='
                  '\nSave current data set to multiple locations/formats:'
                  '\n1 => To a folder'
                  '\n2 => To a geojson file'
                  '\n3 => To a geojson file in a gist'
                  '\n4 => Do not save in additional formats/locations'
                  '\nEnter choice[{}]: ')

        while True:
            try:
                choice = int(raw_input(PROMPT.format(choice)) or choice)
            except(ValueError):
                print('Invalid choice')

            if choice is 1:
                folder_prompt = 'Enter folder name[{}]: '.format(folder)
                folder = raw_input(folder_prompt) or folder
                self.write_folder(folder)

            if choice is 2:
                file_prompt = 'Enter file name[{}]: '.format(file_path)
                file_path = raw_input(file_prompt) or file_path
                self.write_geojson_file(file_path)

            if choice is 3:
                user_prompt = 'Enter username[{}]: '.format(gh_username)
                gh_username = raw_input(user_prompt) or gh_username
                password_prompt = 'Enter password[{}]: '.format(gh_password)
                gh_password = raw_input(password_prompt) or gh_password
                gist_prompt = 'Enter gist ID[{}]: '.format(gh_gist_id)
                gh_gist_id = raw_input(gist_prompt) or gh_gist_id
                self.write_gist(gh_username, gh_password, gh_gist_id)

            if choice is 4:
                break

            choice = 4


def format_to_geojson(obj):
    """Convert DeploymentFeatures to an ordered geojson txt string."""
    if isinstance(obj, list):
        obj = [Feature(
            id=feature.id,
            geometry=feature.geometry,
            properties=feature.properties
            ) for feature in obj]

        obj.sort(lambda x, y: cmp(x['id'], y['id']))
        obj = FeatureCollection(obj)

    return dumps(obj, sort_keys=True,
                 indent=4, separators=(',', ': '))
