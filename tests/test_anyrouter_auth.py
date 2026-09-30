import json

import httpx
import pytest

import checkin
from utils.config import AccountConfig, ProviderConfig, load_accounts_config


@pytest.mark.parametrize(
	('body', 'label'),
	[
		({'message': '无权进行此操作，用户 ID 不匹配'}, 'AUTH_USER_ID_MISMATCH'),
		({'message': '无权进行此操作，未登录且未提供 access token'}, 'AUTH_SESSION_NOT_ACCEPTED'),
		({'code': 'AUTH_SESSION_REVOKED', 'message': 'private response'}, 'AUTH_SESSION_REVOKED'),
		({'message': 'private-session-value'}, 'AUTH_RESPONSE_UNCLASSIFIED'),
		({'message': {'secret': 'private-session-value'}}, 'AUTH_RESPONSE_UNCLASSIFIED'),
		([], 'AUTH_RESPONSE_UNCLASSIFIED'),
	],
)
def test_auth_error_classification_never_returns_response_values(body, label):
	response = httpx.Response(401, json=body)
	assert checkin.classify_auth_error(response) == label


def test_non_json_auth_error_does_not_log_body():
	assert checkin.classify_auth_error(httpx.Response(401, text='private-session-value')) == 'AUTH_RESPONSE_NOT_JSON'


def test_anyrouter_unauthorized_request_never_attempts_check_in(monkeypatch, capsys):
	requests = []

	def respond(request):
		requests.append(request)
		return httpx.Response(401, json={'message': '用户 ID 不匹配 private-session-value'})

	original_client = httpx.Client
	monkeypatch.setattr(
		checkin.httpx, 'Client', lambda **kw: original_client(transport=httpx.MockTransport(respond), **kw)
	)
	cookies = {'session': 'test-session'}
	account = AccountConfig(cookies=cookies, api_user='16', provider='anyrouter')
	provider = ProviderConfig(name='anyrouter', domain='https://example.test')
	success, before, after = checkin.run_check_in_requests(cookies, account, 'AnyRouter test', provider)
	assert not success
	assert before is not None
	assert before == after
	assert [request.method for request in requests] == ['GET']
	assert 'AUTH_USER_ID_MISMATCH' in capsys.readouterr().out
	assert 'private-session-value' not in before['error']


def test_manual_provider_filter_skips_other_account_configuration(monkeypatch):
	monkeypatch.setenv('CHECKIN_PROVIDER', 'anyrouter')
	monkeypatch.setenv('ANYROUTER_SESSION_COOKIE', 'test-session')
	monkeypatch.setenv(
		'ANYROUTER_ACCOUNTS',
		json.dumps(
			[
				{'provider': 'anyrouter', 'api_user': '16'},
				{'provider': 'unrelated'},
			]
		),
	)
	accounts = load_accounts_config()
	assert accounts is not None
	assert len(accounts) == 1
	assert accounts[0].provider == 'anyrouter'
