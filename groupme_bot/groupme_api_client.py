from datetime import datetime
import logging
import json
import os
import requests

BASE_URL = 'https://api.groupme.com/v3/'

logger = logging.getLogger(__name__)


def _get_groupme(uri, params={}):
    default_params = {'token': os.environ['GROUPME_TOKEN']}
    params.update(default_params)

    response = requests.get(BASE_URL + uri, params=params)

    return json.loads(response.text)


def _post_groupme(uri, data):
    return requests.post(BASE_URL + uri, data=data)


def _get_group_id():
    response_data = _get_groupme('groups')
    for group in response_data['response']:
        if group['name'] == os.environ['GROUPME_GROUP_NAME']:
            return group['id']

    raise Exception('group could not be found')


def get_messages(cutoff):
    group_id = _get_group_id()
    earliest_created_time = None
    earliest_created_id = None
    counter = 0
    messages = dict()
    user_names = dict()
    while True:
        params = {'limit': 100}
        if earliest_created_id:
            params['before_id'] = earliest_created_id

        response_data = _get_groupme(
            'groups/{}/messages'.format(group_id),
            params=params,
        )

        if not response_data:
            break

        for message in response_data['response']['messages']:
            if message['system']:
                continue

            if message['sender_id'] == os.environ.get('USER_TO_REPEAT'):
                message['name'] = os.environ.get('USER_TO_REPEAT_NEW_NAME')

            user_names[message['sender_id']] = message['name']
            message_created = datetime.fromtimestamp(message['created_at'])
            messages[message['id']] = {
                'user': message['sender_id'],
                'text': message['text'],
                'created': message_created,
                'likers': message['favorited_by'],
                'attachments': message['attachments'],
            }
            if (
                not earliest_created_time or
                message_created < earliest_created_time
            ):
                earliest_created_id = message['id']
                earliest_created_time = message_created

            if earliest_created_time < cutoff:
                break

        if earliest_created_time < cutoff:
            break

        counter += 1

    return messages, user_names


def _is_bot_enabled():
    return os.environ['GROUPME_BOT_ENABLED'] == '1'


def post_as_bot(text):
    if not _is_bot_enabled():
        logger.info(text)
        return

    return _post_groupme(
        'bots/post',
        data={
            'bot_id': os.environ['GROUPME_BOT_ID'],
            'text': text,
        },
    )
