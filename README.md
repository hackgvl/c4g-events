# slack-events-bot
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

A Slack bot that relays information from HackGreenville Labs' _Events API_ to
Slack channels!

## Repository

You can find the repository on
[Github](https://github.com/hackgvl/slack-events-bot).

To download this repo locally, clone it with `git clone
git@github.com:hackgvl/slack-events-bot.git`

## Docker Instructions

1. Download the `docker-compose.yml` file to your desired hosting location and
   navigate to it
1. Run `docker-compose pull` to pull the latest version of the container and
   it's dependencies.
1. Modify `docker-compose.yml` by replacing `BOT_TOKEN` and `SIGNING_SECRET`
   values with values for a [valid Slack App](https://api.slack.com/apps).
1. (Optional) By default, the app will create a sqlite database in the same
   directory as `docker-compose.yml`. To modify the database location, modify
   the `volumes:` binding like below:
```
    volumes:
      - ./my-new-database-subdirectory/slack-events-bot.db:/usr/src/app/slack-events-bot.db
```
1. Run `docker-compose pull` to pull the latest version of the container and
   it's dependencies.
1. Start the app by doing `docker-compose up` or `docker-compose up -d` to run in
   detached mode.  Run `docker ps` to verify the status.
1. If desired, [configure Docker to start automatically upon server reboot](https://docs.docker.com/engine/install/linux-postinstall/#configure-docker-to-start-on-boot-with-systemd).
1. To check the app's error log from within the Docker container, run `docker-compose logs -f`
1. Proxy a web server to the Docker container's port, as defined in the docker-composer.yml

### Autohealing
[willfarrell/autoheal](https://github.com/willfarrell/docker-autoheal) ([Docker Hub](https://hub.docker.com/r/willfarrell/autoheal/)) is used
to provide autohealing capabilities that will automatically restart containers that repeatedly fail healthchecks. This service is not required for
local development, and as a result it is set to not run by default. If you would like to spin up this container for local testing purposes then please
specify the `autohealing` profile whenever executing `docker-compose up`:

```bash
docker-compose --profile autohealing up
```

### Apache Example
The following needs to be included in an appropriate Apache .conf file, usually as part of an existing VirtualHost directive.

```
    # Proxy requests to /events/slack to the 'Slack Bolt' Docker container port
    ProxyPass /slack/events http://127.0.0.1:7331/slack/events
```

## Native (non-Docker) App Installation

1. Clone the repo using the instructions above and enter the new directory.
1. Install the python version in `.tool-versions`. I recommend that you use
   [asdf version manager](https://asdf-vm.com/), which will use the version in
   `.tool-versions`.
    1. To use asdf, first follow the [install
     instructions](https://asdf-vm.com/guide/getting-started.html#_1-install-dependencies).
    1. Then, install the python plugin with `asdf plugin-add python`
    1. Then, run `asdf install` and possibly `asdf reshim` to install.
1. Load the environment variables specified in `.envrc.example`. I recommend you
   use [direnv](https://direnv.net/) to keep this per-project.
    1. To use direnv, follow the [instruction
       examples](https://direnv.net/docs/installation.html).
    1. Then, create a slack app following the [Slack Bolt
       tutorial](https://slack.dev/bolt-python/tutorial/getting-started#create-an-app).
    1. Copy `.envrc.example` to `.envrc`, and fill in the private values from
       Slack into `.envrc`. Make sure to never put these values into the code
       directly!
    1. Run `direnv allow` to load the environment variables into your shell.
       This will need to be re-run if there are any changes to `.envrc`.
1. Create a virtual environment with `python -m venv env`.
1. Activate the venv with `source env/bin/activate`
    1. Use `deactivate` to exit the venv if needed.
1. Install project dependencies using `pip install .` or `pip install .[test]`
   to install development dependencies for testing
1. Run the app with `python src/server.py`!

1. Proxy a web server to the running app's port, as defined in the .envrc `PORT` value.

### Apache Example
The following needs to be included in an appropriate Apache .conf file, usually as part of an existing VirtualHost directive.

```
    # Proxy requests to /events/slack to the running 'Slack Bolt' app port
    ProxyPass /slack/events http://127.0.0.1:3000/slack/events
```

## Docker Build Instructions

1. Clone the repo using the instructions above and enter the new directory.
1. Modify `docker-compose.yml` by replacing `image: hackgvl/slack-events-bot` with the
   following:
```
    build:
      context: ./
```
1. Modify `docker-compose.yml` by replacing `BOT_TOKEN` and `SIGNING_SECRET`
   values with values for a [valid Slack App](https://api.slack.com/apps).
1. (Optional) By default, the app will create a sqlite database in the same
   directory as `docker-compose.yml`. To modify the database location, modify
   the `volumes:` binding like below:
```
    volumes:
      - ./my-new-database-subdirectory/slack-events-bot.db:/usr/src/app/slack-events-bot.db
```
1. Build and start the app with `docker-compose up --force-recreate --no-deps`
    1. You can just start the app by doing `docker-compose up` or
       `docker-compose -d` to run in detached mode once it's been built

## Development Tips

This project uses some handy tools to assist with development. It's also
recommended that you use a [python virtual
environment](https://docs.python.org/3/library/venv.html) to help separate this
project's dependencies from the rest of your system, and vice versa. Please feel
free to give recommendations for any more tools if there are any that would be a
good idea!

- [direnv](https://direnv.net/) suggestions with `.envrc.example` for an easy
  way to set environment variables per-directory.
  - Once you have direnv installed, copy `.envrc.example` to `.envrc` and
    replace with your slack dev application keys. Then, your slack application
    keys will only be available when you enter that directory!
- [asdf version manager](https://asdf-vm.com/) and
  [asdf-python](https://github.com/asdf-community/asdf-python) with
  `.tool-versions` for an easy way to use the right python version
  per-directory.
- [black](https://black.readthedocs.io/en/stable/) via `black src/` to format
  the source code in the `src/` folder.
- [pylint](https://pylint.readthedocs.io/en/stable/) via `pylint src/` to lint
  the source code in the `src/` folder. We want this to stay at 10/10!
- [isort](https://pycqa.github.io/isort/index.html) via `isort src/` to make
  sure that imports are in a standard order (black doesn't do this).
- [ssort](https://github.com/bwhmather/ssort) via `ssort src/` to better group
  code.
- `pip freeze` to figure out which versions of dependencies to use in
  `pyproject.toml`. This is only necessary if you're adding or removing a new
  dependency to the project.

## Handy commands

- `pip install .[test]`: Install test dependencies
- `python -m black src/`: Format source files
- `python -m isort --check src/`: sort imports with isort
- `python -m ssort --check src/`: sorts python code
- `python -m pylint src/`: Runs linter, try to get a 10/10 score!
- `python -m pytest tests/`: Runs tests

## License

This bot is licensed under the MIT license.

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://olivia.sculley.dev"><img src="https://avatars.githubusercontent.com/u/88074048?v=4?s=100" width="100px;" alt="Olivia Sculley"/><br /><sub><b>Olivia Sculley</b></sub></a><br /><a href="#ideas-oliviasculley" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/hackgvl/slack-events-bot/commits?author=oliviasculley" title="Code">💻</a> <a href="https://github.com/hackgvl/slack-events-bot/issues?q=author%3Aoliviasculley" title="Bug reports">🐛</a> <a href="#question-oliviasculley" title="Answering Questions">💬</a> <a href="https://github.com/hackgvl/slack-events-bot/commits?author=oliviasculley" title="Documentation">📖</a> <a href="#maintenance-oliviasculley" title="Maintenance">🚧</a> <a href="#infra-oliviasculley" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/allella"><img src="https://avatars.githubusercontent.com/u/1777776?v=4?s=100" width="100px;" alt="Jim Ciallella"/><br /><sub><b>Jim Ciallella</b></sub></a><br /><a href="#infra-allella" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#maintenance-allella" title="Maintenance">🚧</a> <a href="#projectManagement-allella" title="Project Management">📆</a> <a href="https://github.com/hackgvl/slack-events-bot/commits?author=allella" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ThorntonMatthewD"><img src="https://avatars.githubusercontent.com/u/44626690?v=4?s=100" width="100px;" alt="Matthew Thornton"/><br /><sub><b>Matthew Thornton</b></sub></a><br /><a href="https://github.com/hackgvl/slack-events-bot/commits?author=ThorntonMatthewD" title="Code">💻</a> <a href="#infra-ThorntonMatthewD" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/hackgvl/slack-events-bot/commits?author=ThorntonMatthewD" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/JakeBobAnderson"><img src="https://avatars.githubusercontent.com/u/89029029?v=4?s=100" width="100px;" alt="Jake Anderson"/><br /><sub><b>Jake Anderson</b></sub></a><br /><a href="https://github.com/hackgvl/slack-events-bot/commits?author=JakeBobAnderson" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
