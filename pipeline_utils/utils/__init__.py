import yaml
import re
import json
from pathlib import Path
import platform
import subprocess
from types import SimpleNamespace
from typing import Dict, List, Union
from urllib.parse import urlparse
import os
import logging
import boto3

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
cpu_count = os.cpu_count() or 1
MAX_WORKERS = max(1, cpu_count - 4)



def check_gpu():
    # For NVIDIA GPUs on any platform
    try:
        nvidia_output = subprocess.check_output("nvidia-smi", shell=True).decode('utf-8')
        logging.info("NVIDIA GPU detected:")
        logging.info(nvidia_output)
        return True
    except:
        pass
    # For AMD GPUs on Linux
    try:
        if platform.system() == "Linux":
            amd_output = subprocess.check_output("rocm-smi", shell=True).decode('utf-8')
            logging.info("AMD GPU detected:")
            logging.info(amd_output)
            return True
    except:
        pass

    # For macOS
    try:
        if platform.system() == "Darwin":
            mac_gpu = subprocess.check_output("system_profiler SPDisplaysDataType | grep 'Chipset Model'",
                                              shell=True).decode('utf-8')
            logging.info("Mac GPU detected:")
            logging.info(mac_gpu)
            return True
    except:
        pass

    logging.error("No GPU detected using system commands")
    return False

# HAVE_GPU = check_gpu()

region = os.environ.get('AWS_REGION', 'us-east-2')
aws_session = boto3.Session(region_name=region)
TEXTRACT_CLIENT = aws_session.client('textract')


def load_config(config_path):
    """Load configuration from a JSON file."""
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config


## get the config file information
class IterableSimpleNamespace(SimpleNamespace):
    """Ultralytics IterableSimpleNamespace is an extension class of SimpleNamespace that adds iterable functionality and
    enables usage with dict() and for loops.
    """

    def __iter__(self):
        """Return an iterator of key-value pairs from the namespace's attributes."""
        return iter(vars(self).items())

    def __str__(self):
        """Return a human-readable string representation of the object."""
        return '\n'.join(f'{k}={v}' for k, v in vars(self).items())

    def __getattr__(self, attr):
        """Custom attribute access error message with helpful information."""
        name = self.__class__.__name__
        raise AttributeError(f"""
            '{name}' object has no attribute '{attr}'. This may be caused by a modified or out of date ultralytics
            'default.yaml' file.\nPlease update your code and if necessary replace the default.yaml file on your local path
            """)

    def get(self, key, default=None):
        """Return the value of the specified key if it exists; otherwise, return the default value."""
        return getattr(self, key, default)



def cfg2dict(cfg):
    """
    Convert a configuration object to a dictionary, whether it is a file path, a string, or a SimpleNamespace object.

    Args:
        cfg (str | Path | dict | SimpleNamespace): Configuration object to be converted to a dictionary.

    Returns:
        cfg (dict): Configuration object in dictionary format.
    """
    if isinstance(cfg, (str, Path)):
        cfg = yaml_load(cfg)  # load dict
    elif isinstance(cfg, SimpleNamespace):
        cfg = vars(cfg)  # convert to dict
    return cfg

def yaml_load(file='data.yaml', append_filename=False):
    """
    Load YAML data from a file.

    Args:
        file (str, optional): File name. Default is 'data.yaml'.
        append_filename (bool): Add the YAML filename to the YAML dictionary. Default is False.

    Returns:
        (dict): YAML data and file name.
    """
    assert Path(file).suffix in ('.yaml', '.yml'), f'Attempting to load non-YAML file {file} with yaml_load()'
    with open(file, errors='ignore', encoding='utf-8') as f:
        s = f.read()  # string

        # Remove special characters
        if not s.isprintable():
            s = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD\U00010000-\U0010ffff]+', '', s)

        # Add YAML filename to dict and return
        data = yaml.safe_load(s) or {}  # always return a dict (yaml.safe_load() may return None for empty files)
        if append_filename:
            data['yaml_file'] = str(file)
        return data



## default config information
DEFAULT_CFG_DICT = yaml_load(DEFAULT_CFG_PATH)
for k, v in DEFAULT_CFG_DICT.items():
    if isinstance(v, str) and v.lower() == 'none':
        DEFAULT_CFG_DICT[k] = None

DEFAULT_CFG_KEYS = DEFAULT_CFG_DICT.keys()
DEFAULT_CFG = IterableSimpleNamespace(**DEFAULT_CFG_DICT)



def check_dict_alignment(base: Dict, custom: Dict, e=None):
    """
    This function checks for any mismatched keys between a custom configuration list and a base configuration list. If
    any mismatched keys are found, the function prints out similar keys from the base list and exits the program.

    Args:
        custom (dict): a dictionary of custom configuration options
        base (dict): a dictionary of base configuration options
        e (Error, optional): An optional error that is passed by the calling function.
    """
    # custom = _handle_deprecation(custom)
    base_keys, custom_keys = (set(x.keys()) for x in (base, custom))
    mismatched = [k for k in custom_keys if k not in base_keys]
    if mismatched:
        from difflib import get_close_matches

        string = ''
        for x in mismatched:
            matches = get_close_matches(x, base_keys)  # key list
            matches = [f'{k}={base[k]}' if base.get(k) is not None else k for k in matches]
            match_str = f'Similar arguments are i.e. {matches}.' if matches else ''
            string += f"'{x}' is not a valid argument. {match_str}\n"
        raise SyntaxError(string) from e

## override the default config information 
def get_cfg(cfg: Union[str, Path, Dict, SimpleNamespace] = DEFAULT_CFG_DICT, overrides: Dict = None):
    """
    Load and merge configuration data from a file or dictionary.

    Args:
        cfg (str | Path | Dict | SimpleNamespace): Configuration data.
        overrides (str | Dict | optional): Overrides in the form of a file name or a dictionary. Default is None.

    Returns:
        (SimpleNamespace): Training arguments namespace.
    """
    cfg = cfg2dict(cfg)

    # Merge overrides
    if overrides:
        overrides = cfg2dict(overrides)
        if 'save_dir' not in cfg:
            overrides.pop('save_dir', None)  # special override keys to ignore
        check_dict_alignment(cfg, overrides)
        cfg = {**cfg, **overrides}  # merge cfg and overrides dicts (prefer overrides)


    # Return instance
    return IterableSimpleNamespace(**cfg)


## get file name
def is_url(path):
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except:
        return False

def extract_filename_without_suffix(url):
    if is_url(url):
        parsed_url = urlparse(url)
        path = parsed_url.path
        filename_with_extension = os.path.basename(path)
        filename_without_extension, _ = os.path.splitext(filename_with_extension)
    else:
        path=url
        filename_with_extension = os.path.basename(path)
        filename_without_extension, _ = os.path.splitext(filename_with_extension)

    return filename_without_extension

## save the label result
def label_save(**kwargs):
    i = kwargs.get('i')
    x1 = kwargs.get('x1')
    x2 = kwargs.get('x2')
    y1 = kwargs.get('y1')
    y2 = kwargs.get('y2')
    box_cls = kwargs.get('box_cls')
    box_conf = kwargs.get('box_conf')
    label = kwargs.get('label')
    original_width = kwargs.get('original_width')
    original_height = kwargs.get('original_height')
    scale = kwargs.get('scale', 1.0)  # Example of a default value
    format = kwargs.get('format',None)

    xmin= (x1 / scale)
    ymin= (y1 / scale)
    xmax= (x2 / scale)
    ymax= (y2 / scale)
        
    data = {"id":i,
            "minX":xmin,
            "maxX":xmax,
            "minY":ymin,
            "maxY":ymax,
            "score": box_conf,
            "class_id":box_cls,
            "label": label,
            "original_width":original_width,
            "original_height":original_height
            }
    return data 
        

