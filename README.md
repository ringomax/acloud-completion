# acloud completion

Fig-format command completion for the Arc Cloud Platform CLI, including nested commands, flags, positional arguments and enumerated values. Compatible with Figxit 0.5.0.

The checked-in definition covers 119 commands documented by acloud `v2026.10.12-45c6247`. Suggestions come from the CLI's offline documentation. Completion does not sign in, call the Platform API, or list account resources.

## Install in Figxit

Requires Python 3 and an installed Figxit application:

```sh
git clone https://github.com/ringomax/acloud-completion.git
cd acloud-completion
python3 scripts/install-figxit.py --activate
```

The installer creates an overlay under `~/Library/Application Support/figxit-custom`. It retains the app's bundled specs, including git and pnpm, and adds acloud. It does not modify the signed application bundle. Existing additional specs in this overlay are retained when the installer runs again.

`--activate` restarts Figxit and installs a macOS LaunchAgent that opens Figxit with `FIGXIT_SPECS` set at login. Use this launch agent instead of Figxit's built-in **Launch at Login** setting to avoid starting an app instance without the custom environment. The launch agent has no background polling or keep-alive process. Open a new terminal if an existing terminal has not reconnected after the restart.

For a different application path, pass `--app /path/to/Figxit.app`. For additional compiled Fig specs, pass `--extra-specs /path/to/specs`. The additional directory should contain command `.js` files and any nested spec directories; its `index.js` is not required. Custom files with the same command name take precedence.

Run the installer again after a Figxit upgrade so newly bundled command files are linked into the overlay.

## Update the definition

```sh
python3 scripts/generate.py
python3 -m unittest discover -s tests
node --test
```

Generation uses only `acloud --help`, `acloud cli search` and `acloud cli describe`. It stops if a command group hits the search result limit. Review `catalog.json` and the generated `acloud.js` after upgrading acloud. `index.js` and `acloud.js` can also be used by other tools that support Fig specs.

## Remove the Figxit configuration

```sh
launchctl bootout "gui/$(id -u)/local.figxit.custom-specs"
rm ~/Library/LaunchAgents/local.figxit.custom-specs.plist
launchctl unsetenv FIGXIT_SPECS
/Applications/Figxit.app/Contents/MacOS/figxit-engine stop
open -g -a Figxit
```

This restores bundled completion on the next Figxit launch. The overlay files are kept; remove `~/Library/Application Support/figxit-custom` separately if no longer needed. Re-enable Figxit's built-in Launch at Login if desired.

## License

MIT.
