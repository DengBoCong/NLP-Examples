from configparser import ConfigParser


def get_config(config_file='seq2seq.ini'):
    parser = ConfigParser()
    parser.read(filenames=config_file, encoding='utf-8')
    # get the ints and strings
    _conf_ints = [(key, int(value)) for key, value in parser.items('ints')]
    _conf_strings = [(key, str(value)) for key, value in parser.items('strings')]
    return dict(_conf_ints + _conf_strings)