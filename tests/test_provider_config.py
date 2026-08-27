import json

from utils.config import AppConfig, ProviderConfig, load_accounts_config


def test_builtin_provider_profile_persistence_defaults(monkeypatch):
	monkeypatch.delenv('PROVIDERS', raising=False)

	config = AppConfig.load_from_env()

	assert config.providers['anyrouter'].persist_profile is True
	assert config.providers['agentrouter'].persist_profile is False
	assert config.providers['agentrouter'].domain == 'https://agentrouter.org'
	assert config.providers['agentrouter'].use_proxy is False
	assert config.providers['agentrouter'].bypass_method == 'waf_cookies'
	assert config.providers['agentrouter'].waf_cookie_names == ['acw_tc']


def test_provider_profile_persistence_can_override_builtin(monkeypatch):
	monkeypatch.setenv(
		'PROVIDERS',
		json.dumps(
			{
				'anyrouter': {'domain': 'https://anyrouter.top', 'persist_profile': False},
				'agentrouter': {'domain': 'https://agentrouter.org', 'persist_profile': True},
			}
		),
	)

	config = AppConfig.load_from_env()

	assert config.providers['anyrouter'].persist_profile is False
	assert config.providers['agentrouter'].persist_profile is True


def test_custom_provider_profile_persistence_defaults_to_false(monkeypatch):
	monkeypatch.setenv('PROVIDERS', json.dumps({'custom': {'domain': 'https://custom.example.com'}}))

	config = AppConfig.load_from_env()

	assert config.providers['custom'].persist_profile is False


def test_provider_from_dict_inherits_profile_persistence_from_defaults():
	defaults = ProviderConfig(name='custom', domain='https://old.example.com', persist_profile=True)

	provider = ProviderConfig.from_dict(
		'custom',
		{'domain': 'https://new.example.com'},
		defaults=defaults,
	)

	assert provider.persist_profile is True


def test_access_token_account_does_not_require_cookies_or_api_user(monkeypatch):
	monkeypatch.setenv(
		'ANYROUTER_ACCOUNTS',
		json.dumps(
			[
				{
					'name': 'Token account',
					'provider': 'anyrouter',
					'access_token': 'account-access-token',
				}
			]
		),
	)

	accounts = load_accounts_config()

	assert accounts is not None
	assert len(accounts) == 1
	assert accounts[0].has_access_token() is True
	assert accounts[0].access_token == 'account-access-token'


def test_provider_access_token_secret_overrides_existing_account_auth(monkeypatch):
	monkeypatch.setenv(
		'ANYROUTER_ACCOUNTS',
		json.dumps(
			[
				{
					'name': 'AgentRouter account',
					'provider': 'agentrouter',
					'cookies': {'session': 'expired-session'},
					'api_user': '152183',
				}
			]
		),
	)
	monkeypatch.setenv('AGENTROUTER_ACCESS_TOKEN', 'rotated-agentrouter-token')

	accounts = load_accounts_config()

	assert accounts is not None
	assert accounts[0].access_token == 'rotated-agentrouter-token'
	assert accounts[0].has_access_token() is True


def test_provider_access_token_secret_can_supply_missing_account_auth(monkeypatch):
	monkeypatch.setenv(
		'ANYROUTER_ACCOUNTS',
		json.dumps([{'name': 'AnyRouter account', 'provider': 'anyrouter'}]),
	)
	monkeypatch.setenv('ANYROUTER_ACCESS_TOKEN', 'rotated-anyrouter-token')

	accounts = load_accounts_config()

	assert accounts is not None
	assert accounts[0].access_token == 'rotated-anyrouter-token'
	assert accounts[0].has_access_token() is True
