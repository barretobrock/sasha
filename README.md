# sasha
Home automation robot that interfaces with Slack 

## Info
This is really something I built for personal use. There are credential collection methods that rely on prebuilt routines that might prove specific to only my use case. Should anyone discover this and wish to use it, feel free to contact me and I'll work on adapting this to wider use cases.

## App Info

### Slack Scopes
#### Bot
 - channels.history
 - channels.read
 - chat.write
 - emoji.read
 - files.write
 - groups.history
 - groups.read
 - im.history
 - im.read
 - im.write
 - mpim.read
 - reactions.read
 - reactions.write
 - users.read
#### User
 - search.read

## Installation
```bash
pip3 install git+https://github.com/barretobrock/sasha.git#egg=sasha
```

## Upgrade
```bash
pip3 install git+https://github.com/barretobrock/sasha.git#egg=sasha --upgrade
```

## Run
```bash
python3 run.py
```

## Debug
```bash
python3 run_debug.py
```

