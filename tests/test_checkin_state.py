import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import checkin
from checkin import check_in_account, generate_balance_hash, get_check_in_exit_code
from utils.config import AccountConfig, AppConfig, ProviderConfig


def test_balance_hash_changes_when_quota_changes():
	before = {'account_1': {'quota': 100.0, 'used': 20.0}}
	after = {'account_1': {'quota': 125.0, 'used': 20.0}}

	assert generate_balance_hash(before) != generate_balance_hash(after)


def test_balance_hash_changes_when_used_quota_changes():
	before = {'account_1': {'quota': 100.0, 'used': 20.0}}
	after = {'account_1': {'quota': 100.0, 'used': 21.0}}

	assert generate_balance_hash(before) != generate_balance_hash(after)


def test_balance_hash_is_stable_for_equivalent_balances():
	left = {
		'account_2': {'quota': 50.0, 'used': 1.0},
		'account_1': {'quota': 100.0, 'used': 20.0},
	}
	right = {
		'account_1': {'used': 20.0, 'quota': 100.0},
		'account_2': {'used': 1.0, 'quota': 50.0},
	}

	assert generate_balance_hash(left) == generate_balance_hash(right)


@pytest.mark.parametrize(
	('success_count', 'total_count', 'expected'),
	[
		(2, 2, 0),
		(1, 2, 1),
		(0, 2, 1),
		(0, 0, 1),
	],
)
def test_check_in_exit_code_requires_every_account_to_succeed(success_count, total_count, expected):
	assert get_check_in_exit_code(success_count, total_count) == expected


@pytest.mark.asyncio
async def test_access_token_auth_allows_empty_cookie_jar(monkeypatch):
	account = AccountConfig(
		cookies=None,
		provider='agentrouter',
		name='AgentRouter account',
		access_token='account-access-token',
	)
	provider = ProviderConfig(
		name='agentrouter',
		domain='https://ps.air-outer.com',
		sign_in_path='/api/user/sign_in',
	)
	app_config = AppConfig(providers={'agentrouter': provider})
	captured = {}

	def fake_run_check_in_requests(all_cookies, *args, **kwargs):
		captured['cookies'] = all_cookies
		captured['access_token'] = kwargs['access_token_override']
		return True, None, None

	monkeypatch.setattr(checkin, 'run_check_in_requests', fake_run_check_in_requests)

	result = await check_in_account(account, 0, app_config)

	assert result == (True, None, None)
	assert captured == {'cookies': {}, 'access_token': 'account-access-token'}


@pytest.mark.asyncio
async def test_proxy_enabled_provider_falls_back_to_direct_connection(monkeypatch):
	monkeypatch.delenv('CHECKIN_PROXY_URL', raising=False)
	account = AccountConfig(
		cookies=None,
		provider='agentrouter',
		name='AgentRouter account',
		access_token='account-access-token',
	)
	provider = ProviderConfig(
		name='agentrouter',
		domain='https://agentrouter.org',
		sign_in_path='/api/user/sign_in',
		use_proxy=True,
	)
	app_config = AppConfig(providers={'agentrouter': provider})
	captured = {}

	async def fake_prepare_cookies(*args, **kwargs):
		return {}

	def fake_run_check_in_requests(all_cookies, *args, **kwargs):
		captured['cookies'] = all_cookies
		captured['use_proxy'] = kwargs['use_proxy']
		return True, None, None

	monkeypatch.setattr(checkin, 'prepare_cookies', fake_prepare_cookies)
	monkeypatch.setattr(checkin, 'run_check_in_requests', fake_run_check_in_requests)

	result = await check_in_account(account, 0, app_config)

	assert result == (True, None, None)
	assert captured == {'cookies': {}, 'use_proxy': True}


@pytest.mark.asyncio
async def test_login_triggered_provider_rejects_token_only_authentication():
	account = AccountConfig(
		cookies=None,
		provider='agentrouter',
		name='AgentRouter account',
		access_token='account-access-token',
	)
	provider = ProviderConfig(
		name='agentrouter',
		domain='https://agentrouter.org',
		sign_in_path=None,
	)
	app_config = AppConfig(providers={'agentrouter': provider})

	result = await check_in_account(account, 0, app_config)

	assert result == (False, None, None)


@pytest.mark.asyncio
async def test_login_triggered_provider_uses_fresh_credentials(monkeypatch):
	account = AccountConfig(
		cookies=None,
		provider='agentrouter',
		name='AgentRouter account',
		email='github_152183',
		password='dedicated-agentrouter-password',
		access_token='account-access-token',
	)
	provider = ProviderConfig(
		name='agentrouter',
		domain='https://agentrouter.org',
		sign_in_path=None,
	)
	app_config = AppConfig(providers={'agentrouter': provider})
	captured = {}

	async def fake_login(*args, **kwargs):
		return checkin.BrowserLoginResult(cookies={'session': 'fresh-session'}, api_user='152183')

	def fake_run_check_in_requests(all_cookies, *args, **kwargs):
		captured['cookies'] = all_cookies
		captured['login_check_in_completed'] = kwargs['login_check_in_completed']
		captured['access_token'] = kwargs['access_token_override']
		return True, None, None

	monkeypatch.setattr(checkin, 'login_with_credentials', fake_login)
	monkeypatch.setattr(checkin, 'run_check_in_requests', fake_run_check_in_requests)

	result = await check_in_account(account, 0, app_config)

	assert result == (True, None, None)
	assert captured == {
		'cookies': {'session': 'fresh-session'},
		'login_check_in_completed': True,
		'access_token': None,
	}
