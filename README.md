# Ataka

Runs exploits, fast.

> See `.env` variable for ctf selection. See ataka/ctfconfig/ for ctf config code. This directory is mounted into the docker container, not copied. Edits can be applied via hot-reload.

# Server

1. Edit `.env` file to set:
    - **DATA_STORE**: **Absolute** path to a folder to store player exploit related files.
    - **USERID**: The user that has access to the data directory and has access to the docker socket.
    - **CTF**: The name of the ctfconfig to use.
2. Edit the ctfconfig in `ataka/ctfconfig/`
3. Run `docker-compose up -d --build`

> When editing the config while ataka is running, run `./ataka-cli reload` to hot-reload the ctfconfig.

# Player-CLI

The player-cli is a tool written in python to help players interact with *ataka* and create, upload and manage exploits and targets.

## Setup

The player-cli is a `.pyz` file (Python Zipped Executable).

> This only needs to be done once.

- Download the ataka-player-cli through a get request to port 8000 of the api container.
- Save that in a known location (`~/.local/bin/atk`).
- Mark as excecutable

## Reloading Player-CLI

When the ctfconfig is modified and `./ataka-cli reload` is run, the local offline copy of the ctfconfig needs to also be reloaded. For that run:

```bash
$ atk service reload
Writing player-cli at <player-cli-location>
```

This overwrites the old player-cli with the new one.

## How to write an exploit

An exploit can be any executable or script.

It will receive two environment variables:
- `TARGET_IP`: the IP to attack;
- `TARGET_EXTRA`: a JSON string containing extra information on the target, such as flag IDs.

Your exploit should print the captured flags.
They will be matched by a regular expression, so the output doesn't have to be clean.

## Local exploits

### Testing a local exploit

Get the name of your service:

```
$ atk service ls
buffalo
gopher_coin
kyc
oly_consensus
swiss_keys
to_the_moon
wall.eth
```

Run the exploit:

```
$ atk exploit runlocal exploit.py SERVICE EXPLOIT_ID
```

Where:
- `exploit.py` is your exploit (must be executable);
- `SERVICE` is the target service name;
- `EXPLOIT_ID` is a unique identifier for your exploit (you can check with `atk exploit ls` to avoid colliding with an existing one). *This is actually ignored in the current version, you can pass whatever.*

This will test the exploit against the NOP team: `exploit runlocal` is supposed to be used for testing, not for actual attacks, which should be centralized to allow the captain to manage them.

By default, only the first 100 characters of the exploit output will be shown.
You can use `-l/--limit` to control this; `-l -1` shows the whole output.

If you only want to run a fixed number of attack rounds, you can use `-c/--count` (e.g., `-c 1` is a one-shot attack).
By default, the command attacks forever until manually terminated.

Instead of an executable, you can also specify a directory containing a Dockerfile.
The runner will try to execute the command from the Dockerfile (locally, outside Docker), with the specified directory as the working directory.
This is useful in combination with `exploit download`, described in the next section.

The local runner can run exploits against the real targets (`--all-targets`, or subsets via `-T/-N`).

## Centralized exploits

### Deploying a centralized exploit

To run on the centralized attacker, exploits must be wrapped in a Docker container and uploaded to the server.

The CLI provides templates for common containers.
For example, to get a Python (latest version) container, use:

```
$ atk exploit template python DIR_NAME
```

Where `DIR_NAME` is the name of the directory that will be created.

At the moment, we have templates for `python` (Python plus some common dependencies, such as pwntools, you can add more in `requirements.txt`) and `ubuntu` (Ubuntu with a bash exploit).
You can also specify Docker tags for specific versions (e.g., `python:3.9-slim`, `ubuntu:18.04`, and so forth).

Now you need to create an "exploit history", i.e., the collection which will contain all the versions of your exploit:

```
$ atk exploit create NAME SERVICE
```

Where `NAME` is the name of your exploit, and `SERVICE` is the target service (you can list them with `atk service ls`).

Finally, upload your exploit directory:

```
$ atk exploit upload NAME AUTHOR DIR_NAME
```

Where `NAME` is the one you chose earlier, `AUTHOR` is your nickname, and `DIR_NAME` is the exploit directory.

This will take care of uploading the exploit.
You can check it with `atk exploit ls`.

Whenever you want to update your exploit to a new version, just issue the `exploit upload` command again.
The attacker will assign progressive numbers to the versions, such as `NAME-1`, `NAME-2`, and so forth.

**New exploits will NOT be activated by default**.
When you upload a new version of an already active exploit, the CLI will deactivate the old version and activate the new version automatically (if that's not what you want, pass `--no-switch-if-active` to avoid it).

Uploaded exploits can be downloaded by anyone with `atk exploit download EXPLOIT_ID OUTPUT_DIR`.


### (De)activating exploits

You can use `atk exploit activate/deactivate` to activate/deactivate an exploit.
The commands accepts a history ID or an exploit ID.
Generally, you should use them with history IDs, and use `exploit switch` (see next section) for switching between different versions.

When `exploit activate` gets a history ID, it activates the most recent exploit version in the history.
If an exploit is already active, it does nothing.

When `exploit deactivate` gets a history ID, it deactivates all the exploits in the history.


### Switching exploit versions

List the exploits to find the exploit ID:

```
$ atk exploit ls
...
cool-pwn (buffalo)
    2022-06-04 14:59:11        nickname cool-pwn-1
    2022-06-04 18:15:29        nickname cool-pwn-2
    2022-06-04 18:15:31 ACTIVE nickname cool-pwn-3
...
```

Now switch to the desired version:

```
$ atk exploit switch cool-pwn-1
Deactivate cool-pwn-3
Activate cool-pwn-1
```

We can confirm it worked:

```
$ atk exploit ls
...
cool-pwn (buffalo)
    2022-06-04 14:59:11 ACTIVE nickname cool-pwn-1
    2022-06-04 18:15:29        nickname cool-pwn-2
    2022-06-04 18:15:31        nickname cool-pwn-3
...
```


### Checking exploit logs

You can check logs (including stdout/stderr) for a centralized exploit using `atk exploit logs NAME`, where `NAME` is a history or exploit ID.
If you pass an exploit ID, it will show logs for that specific version.
If you pass a history ID, it will show logs for active exploits in the history.
You can pass more than one ID and mix exploit and history IDs.

By default, it will show logs from the current round.
You can show logs from the last NUM rounds by passing `-n NUM`.


### Target management

Ataka supports per-history target control.
By default, all targets are enabled.

To see which targets are enabled for a history, use `atk exploit target ls`.
You can enable/disable targets for a history with `atk exploit target on/off` (they both support `--all` to mean "all known targets").

## Manual flag submission

You can manually submit flags:

```
$ atk flag submit 'FLAG{foo}' 'FLAG{bar}' ...
```

The flags can be dirty, they will be matched using the flag regex.

If you don't specify flags, `flag submit` will read from stdin until EOF and then submit (i.e., **it is not streaming**):

```
$ echo 'dirtyFLAG{foo}dirtyFLAG{bar}dirty' | atk flag submit
```

## Emergency mode

Invoking the CLI as `atk -b/--bypass-tools ...` will bypass the centralized Ataka service and connect directly to the gameserver to get attack targets, flag IDs and to submit flags.
In this mode, only `exploit runlocal` and `flag submit` are guaranteed to work.

A typical emergency scenario will involve running exploits locally with `exploit runlocal --all-targets` (and/or `-N/-T` if finer target control is required).
