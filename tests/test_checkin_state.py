import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import checkin
from checkin import check_in_account, generate_balance_hash
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
		sign_in_path=None,
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
