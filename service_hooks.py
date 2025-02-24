#!/usr/bin/env python
import argparse
import logging
import os
import sys
from concurrent import futures
from itertools import product

import requests
from requests.adapters import HTTPAdapter, Retry


logger = logging.getLogger(__name__)


AZURE_API_HOST = os.getenv('AZURE_API_HOST', 'dev.azure.com')
AZURE_API_ROOT = 'https://' + AZURE_API_HOST
AZURE_EXTENSION_API_ROOT = 'https://extmgmt.dev.azure.com'
_MAX_RETRIES = Retry(total=5, backoff_factor=0.1)


EXTENSION_PUBLISHER = 'Datadog'
EXTENSION_NAME = 'ci-visibility'
EXTENSION_ID = '/'.join((EXTENSION_PUBLISHER, EXTENSION_NAME))
CONSUMER_ID = '.'.join((EXTENSION_PUBLISHER, EXTENSION_NAME, 'consumer'))


WEBHOOK_EVENTS = (
    'ms.vss-pipelines.run-state-changed-event',
    'ms.vss-pipelines.stage-state-changed-event',
    'ms.vss-pipelines.job-state-changed-event',
    "ms.vss-pipelinechecks-events.approval-pending",
    "ms.vss-pipelinechecks-events.approval-completed",
    "build.complete"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Install service hooks for Datadog CI Visibility on your Azure Devops organization')

    def validate_api_key(name):
        if len(name) < 32:
            raise ValueError('Datadog API Key must be at least 32 characters long')
        return name

    dd_args = parser.add_argument_group('Datadog')
    dd_args.add_argument('--dd-api-key', type=validate_api_key, help='Datadog API Key')
    dd_args.add_argument('--dd-site', help='Datadog Site (default: datadoghq.com)')

    az_args = parser.add_argument_group('Azure DevOps')
    az_args.add_argument('-u', '--az-user', help='Azure DevOps username')
    az_args.add_argument('-t', '--az-token', help='Azure DevOps API Token')
    az_args.add_argument('-o', '--az-org', help='Azure DevOps Organization name')

    parser.add_argument('projects', nargs='*', help='Space separated list of Azure DevOps project names')
    parser.add_argument('--uninstall', action='store_true', help='Uninstall Datadog Service Hooks')
    parser.add_argument('--threads', type=int, default=1, help='Number of threads for concurrency on the Azure DevOps projects (default: 1)')
    parser.add_argument('--log-level', default='INFO', help='Logging level (default: INFO)')

    parser.set_defaults(
        dd_api_key=os.getenv('DD_API_KEY'),
        dd_site=os.getenv('DD_SITE', 'datadoghq.com'),
        az_user=os.getenv('AZURE_USERNAME'),
        az_token=os.getenv('AZURE_TOKEN'),
        az_org=os.getenv('AZURE_ORGANIZATION'),
    )

    args = parser.parse_args()

    if not args.dd_api_key:
        parser.error('the following arguments are required: --dd-api-key')
    if not all((args.az_user, args.az_token, args.az_org)):
        parser.error('the following arguments are required: -u/--az-user, -t/--az-token, -o/--az-org')
    return args


def create_http_session(auth):
    _adapter = HTTPAdapter(
        max_retries=_MAX_RETRIES, pool_maxsize=5, pool_block=True
    )
    session = requests.Session()
    session.mount(AZURE_API_ROOT, _adapter)
    session.mount(AZURE_EXTENSION_API_ROOT, _adapter)
    session.auth = auth
    session.headers.update({
        'Accept': 'application/json;api-version=7.0'
    })
    return session


class AzureClient:
    def __init__(self, session, org, dd_site, dd_api_key):
        self.session = session
        self.org = org
        self.consumer_inputs = {
            'datadog_site': dd_site,
            'api_key': dd_api_key,
        }

    def list_projects(self, project_names, continuation_token=None):
        params = {}
        if continuation_token:
            params = {'continuationToken': continuation_token}

        response = self.session.get(AZURE_API_ROOT + f'/{self.org}/_apis/projects', params=params)
        response.raise_for_status()
        data = response.json()

        if not project_names:
            projects = data['value']
        else:
            projects = [
                project for project in data['value']
                if project['name'] in set(project_names)
            ]

        continuation_token = data.get('continuation_token')
        if continuation_token:
            projects += self.list_projects(project_names, continuation_token)

        return projects

    def list_subscriptions(self, event_type, project_ids):
        params = {'consumerId': CONSUMER_ID, 'eventType': event_type}
        response = self.session.get(AZURE_API_ROOT + f'/{self.org}/_apis/hooks/subscriptions', params=params)
        response.raise_for_status()
        subscriptions = {
            subscription['publisherInputs']['projectId']: subscription
            for subscription in response.json()['value']
            if subscription['publisherInputs']['projectId'] in project_ids
        }
        return subscriptions

    def create_subscription(self, project, event_type):
        data = {
            'publisherId': 'pipelines',
            'eventType': event_type,
            # 'resourceVersion': '1.0-preview.1',
            'consumerId': CONSUMER_ID,
            'consumerActionId': 'performAction',
            'publisherInputs': {
                'projectId': project['id'],
            },
            'consumerInputs': self.consumer_inputs
        }
        response = self.session.post(AZURE_API_ROOT + f'/{self.org}/_apis/hooks/subscriptions', json=data,
            params={'api-version': '7.0'}
        )
        response.raise_for_status()
        return response.json()

    def replace_subscription(self, project, event_type, subscription_id):
        params = {'subscriptionId': subscription_id}
        data = {
            'publisherId': 'pipelines',
            'eventType': event_type,
            # 'resourceVersion': '1.0-preview.1',
            'consumerId': CONSUMER_ID,
            'consumerActionId': 'performAction',
            'publisherInputs': {
                'projectId': project['id'],
            },
            'consumerInputs': self.consumer_inputs
        }
        response = self.session.put(AZURE_API_ROOT + f'/{self.org}/_apis/hooks/subscriptions', params=params, json=data)
        response.raise_for_status()

    def delete_subscription(self, subscription_id):
        params = {'subscriptionId': subscription_id}
        response = self.session.delete(AZURE_API_ROOT + f'/{self.org}/_apis/hooks/subscriptions', params=params)
        response.raise_for_status()

    def get_extension(self):
        response = self.session.get(
            AZURE_EXTENSION_API_ROOT + f'/{self.org}/_apis/extensionmanagement/installedextensionsbyname/{EXTENSION_ID}',
            params={'api-version': '7.0-preview.1'}
        )
        if response.status_code == 404:
            return
        response.raise_for_status()
        return response.json()

    def install_extension(self):
        response = self.session.post(
            AZURE_EXTENSION_API_ROOT + f'/{self.org}/_apis/extensionmanagement/installedextensionsbyname/{EXTENSION_ID}',
            params={'api-version': '7.0-preview.1'}
        )
        response.raise_for_status()
        return response.json()


if __name__ == '__main__':
    args = parse_args()

    logging.basicConfig(
        level=args.log_level,
        format='[%(levelname)s - %(asctime)s - %(threadName)s]:  %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    session = create_http_session((args.az_user, args.az_token))
    client = AzureClient(session, args.az_org, args.dd_site, args.dd_api_key)

    extension = client.get_extension()
    if not extension:
        do_install = input(f'The extension {EXTENSION_ID} is not installed. Install it now? (Y/N)')
        if do_install.upper() == 'Y':
            client.install_extension()
            logger.info("Extension installed")
        else:
            exit(0)

    action = 'Installing' if not args.uninstall else 'Uninstalling'
    if args.projects:
        logger.info('%s hooks for projects %s', action, args.projects)
    else:
        logger.info('%s hooks for all projects in %s', action, args.az_org)

    projects = client.list_projects(args.projects)
    project_ids = {project['id'] for project in projects}
    subscriptions = {event: client.list_subscriptions(event, project_ids) for event in WEBHOOK_EVENTS}

    def handle_subscription(project, event):
        current_subscription = subscriptions[event].get(project['id'])
        if args.uninstall and current_subscription:
            client.delete_subscription(current_subscription['id'])
            logger.debug('Hook %s for project %s deleted', event, project['name'])
        else:
            if not current_subscription:
                client.create_subscription(project, event)
                logger.debug('Hook %s for project %s created', event, project['name'])
            else:
                client.replace_subscription(project, event, current_subscription['id'])
                logger.debug('Hook %s for project %s updated', event, project['name'])
        logger.info('%s hook: %s installed', project['name'], event)

    with futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        list(executor.map(lambda p: handle_subscription(*p), product(projects, WEBHOOK_EVENTS)))

    logger.info('Finished!')
