import httplib as http
from dataverse import Connection
from dataverse.exceptions import ConnectionError, UnauthorizedError

from framework.exceptions import HTTPError
from website.addons.dataverse import settings


def _connect(username, password, host=settings.HOST):
    try:
        return Connection(
            host=host,
            username=username,
            password=password,
        )
    except ConnectionError:
        return None


def connect_from_settings(user_settings):
    try:
        return _connect(
            user_settings.dataverse_username,
            user_settings.dataverse_password
        ) if user_settings else None
    except UnauthorizedError:
        return None


def connect_or_401(username, password, host=settings.HOST):
    try:
        return _connect(
            host=host,
            username=username,
            password=password,
        )
    except UnauthorizedError:
        raise HTTPError(http.UNAUTHORIZED)


def connect_from_settings_or_401(user_settings):
    return connect_or_401(
        user_settings.dataverse_username,
        user_settings.dataverse_password
    ) if user_settings else None


def delete_file(file):
    dataset = file.dataset
    dataset.delete_file(file)


def upload_file(dataset, filename, content):
    dataset.upload_file(filename, content)


def get_file(dataset, filename, published=False):
    return dataset.get_file(filename, published)


def get_file_by_id(dataset, file_id, published=False):
    return dataset.get_file_by_id(file_id, published)


def get_files(dataset, published=False):
    return dataset.get_files(published)


def publish_dataset(dataset):
    return dataset.publish()


def get_datasets(dataverse):
    if dataverse is None:
        return [], []
    accessible_datasets = []
    bad_datasets = []    # Currently none, but we may filter some out
    for ds in dataverse.get_datasets():
        accessible_datasets.append(ds)
    return accessible_datasets, bad_datasets


def get_dataset(dataverse, doi):
    if dataverse is None:
        return
    dataset = dataverse.get_dataset_by_doi(doi)
    try:
        if dataset.get_state() == 'DEACCESSIONED':
            raise HTTPError(http.GONE)
        return dataset
    except UnicodeDecodeError:
        raise HTTPError(http.NOT_ACCEPTABLE)


def get_dataverses(connection):
    if connection is None:
        return []
    dataverses = connection.get_dataverses()
    published_dataverses = [d for d in dataverses if d.is_published]
    return published_dataverses


def get_dataverse(connection, alias):
    if connection is None:
        return
    dataverse = connection.get_dataverse(alias)
    return dataverse if dataverse and dataverse.is_published else None
