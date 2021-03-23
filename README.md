# mining_control

## Requirements

### Python modules
You can just run the installer to get them install or `pip install -r requirements.txt`
- click
- click_config_file
- requests

### NiceHash account
- You need an account in [NiceHash](https://www.nicehash.com/my/register)
- You need to create an API key and secret pair in [NiceHash](https://www.nicehash.com/docs/)
- You need also a computer with a decent GPU (Nvidia are the best supported but others work too) with NiceHash software installed. But this script can run somewhere else.

## Installation

### Linux

  `sudo python3 setup.py install`

### Windows (from PowerShell)

  `& $(where.exe python).split()[0] setup.py install`

## Usage

  ```
Usage: mining_control.py [OPTIONS]

Options:
  -d, --debug-level [CRITICAL|ERROR|WARNING|INFO|DEBUG|NOTSET]
                                  Set the debug level for the standard output.
  -l, --log-file TEXT             File to store all debug messages.
  -p, --price-limit INTEGER       Price limit of electricity before stopping
                                  rig from mining.
  -k, --api-key TEXT              Your NiceHash API key.
  -s, --api-secret TEXT           You NiceHash API secret. Preferebly use a
                                  configuration file for this option.
  -o, --organization-id TEXT      Your NiceHash organization ID.
  -i, --rig-id TEXT               Your NiceHash Righ ID.
  --config FILE                   Read configuration from FILE.
  --help                          Show this message and exit.
```

## Credits
To the contributors of [NiceHash's rest-clients-demos](https://github.com/nicehash/rest-clients-demo/graphs/contributors) for the API class.
And to [Iisakki Uusimäki](https://www.linkedin.com/in/iisakkiuusimaki/) for the information about Sahko.