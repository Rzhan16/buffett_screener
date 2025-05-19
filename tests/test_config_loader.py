import pytest
from src.utils.config_loader import load_config, ConfigLoaderError


def test_load_long_term_config():
    config = load_config('configs/long_term.yml')
    assert isinstance(config, dict)
    assert config['strategy'] == 'long_term'
    assert 'filters' in config
    assert config['filters']['f_score'] == 7
    assert config['filters']['sma_200'] is True

def test_load_swing_config():
    config = load_config('configs/swing.yml')
    assert isinstance(config, dict)
    assert config['strategy'] == 'swing'
    assert 'filters' in config
    assert config['filters']['rsi'] == [30, 70]
    assert config['filters']['sma_50'] is True

def test_non_dict_yaml(tmp_path):
    # Write a YAML file that is a list, not a dict
    bad_yaml = tmp_path / 'bad.yml'
    bad_yaml.write_text('- a\n- b\n- c\n')
    with pytest.raises(ConfigLoaderError):
        load_config(str(bad_yaml)) 