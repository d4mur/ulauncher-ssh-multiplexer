import os
import subprocess
import shutil
import json
import locale
import shlex
import glob
from os.path import expanduser, join, dirname, isfile, isabs, abspath

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent, PreferencesEvent, PreferencesUpdateEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

class SshMultiplexExtension(Extension):
    def __init__(self):
        super(SshMultiplexExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterListener())
        self.subscribe(PreferencesEvent, PreferencesListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        
        self.terminal_command = "xfce4-terminal"
        self.tab_option = "--tab"
        self.command_option = "--command"
        self.max_tabs = 10
        self.ssh_command_template = ""
        self.ssh_command_template_no_pw = ""
        self.language = "en"
        self.translations = {}
        
        self._load_translations_file()
        self.missing_deps = [d for d in ["zenity", "sshpass"] if shutil.which(d) is None]

    def _load_translations_file(self):
        try:
            with open(join(dirname(__file__), 'translations.json'), 'r') as f:
                self.all_translations = json.load(f)
        except:
            self.all_translations = {"en": {"tab_forms": ["tab", "tabs"], "connect_to": "Connect to {host} ({n} {tab_label})"}}

    def set_language(self, lang_code=None):
        if not lang_code:
            try:
                lang = locale.getlocale()[0]
                lang_code = lang.split('_')[0] if lang else 'en'
            except:
                lang_code = 'en'
        self.language = lang_code
        self.translations = self.all_translations.get(lang_code, self.all_translations.get("en"))

    def get_tab_label(self, n):
        """Plural logic for various language groups (Slavic, Arabic, French, CJK)"""
        forms = self.translations.get("tab_forms", ["tab", "tabs"])
        num_forms = len(forms)
        if num_forms == 1: return forms[0]

        # Arabic (Dual and Plural forms for technical tools)
        if self.language == 'ar' and num_forms >= 3:
            if n == 1: return forms[0]
            if n == 2: return forms[1]
            return forms[2] # Plural for 0 and 3-10+

        # Slavic languages (RU, UK, PL)
        if self.language in ['ru', 'uk', 'pl'] and num_forms >= 3:
            if self.language == 'pl':
                if n == 1: return forms[0]
                if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20): return forms[1]
                return forms[2]
            else: # RU, UK
                if n % 10 == 1 and n % 100 != 11: return forms[0]
                if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20): return forms[1]
                return forms[2]
        
        # French and Portuguese (0 is singular)
        if self.language in ['fr', 'pt-br']:
            return forms[0] if n < 2 else forms[1]
        
        # Default (EN, IT, etc. where 0 is plural "0 tabs")
        return forms[0] if n == 1 else forms[1]

    def update_preference(self, pref_id, value):
        if pref_id == "max_tabs":
            try: self.max_tabs = int(value)
            except: self.max_tabs = 10
        elif pref_id == "language":
            self.set_language(value)
        elif pref_id == "ssh_command_template":
            old_insecure = "bash -c 'export SSHPASS={password}; sshpass -e ssh {host}; exec bash'"
            new_secure = "bash -c 'sshpass -e ssh {host}; exec bash'"
            self.ssh_command_template = new_secure if value.strip() == old_insecure else value
        elif pref_id == "ssh_command_template_no_pw":
            self.ssh_command_template_no_pw = value
        else:
            setattr(self, pref_id, value)

    def parse_ssh_config(self, config_path=None, visited=None):
        if config_path is None: config_path = expanduser("~/.ssh/config")
        if visited is None: visited = set()
        config_path = abspath(config_path)
        if config_path in visited or not isfile(config_path): return []
        visited.add(config_path)
        hosts = []
        ssh_dir = expanduser("~/.ssh/")
        try:
            with open(config_path) as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith('#'): continue
                    l = s.lower()
                    if l.startswith("include "):
                        include_pattern = s.split(None, 1)[1]
                        full_pattern = expanduser(include_pattern)
                        if not isabs(full_pattern): full_pattern = join(ssh_dir, include_pattern)
                        for matched_file in glob.glob(full_pattern):
                            hosts.extend(self.parse_ssh_config(matched_file, visited))
                    elif l.startswith("host ") and "*" not in l:
                        try:
                            host_name = s.split()[1]
                            hosts.append({"host": host_name, "has_id": False})
                        except: continue
                    elif l.startswith("identityfile") and hosts:
                        hosts[-1]["has_id"] = True
        except: pass
        if config_path == abspath(expanduser("~/.ssh/config")):
            return sorted(hosts, key=lambda x: x["host"])
        return hosts

class PreferencesListener(EventListener):
    def on_event(self, event, extension):
        for k, v in event.preferences.items():
            extension.update_preference(k, v)

class PreferencesUpdateEventListener(EventListener):
    def on_event(self, event, extension):
        extension.update_preference(event.id, event.new_value)

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_argument() or ""
        parts = query.split()
        icon = "images/icon.svg"
        
        if extension.missing_deps:
            return RenderResultListAction([ExtensionResultItem(
                icon=icon, name=extension.translations.get("missing_deps_label", "Error"),
                description=extension.translations.get("missing_deps", "").format(missing=', '.join(extension.missing_deps))
            )])

        all_hosts = extension.parse_ssh_config()
        n, prefix = 1, ""
        if parts:
            if parts[0].isdigit():
                n = min(int(parts[0]), extension.max_tabs)
                prefix = parts[1] if len(parts) > 1 else ""
            else:
                prefix = parts[0]

        matches = [h for h in all_hosts if prefix.lower() in h["host"].lower()]
        if not matches and prefix: matches = [{"host": prefix, "has_id": False}]
        
        items = []
        display = matches if prefix or parts else all_hosts
        tab_label = extension.get_tab_label(n)
        
        for h in display:
            items.append(ExtensionResultItem(
                icon=icon, name=h["host"],
                description=extension.translations["connect_to"].format(host=h["host"], n=n, tab_label=tab_label),
                on_enter=ExtensionCustomAction({"n": n, "host": h["host"], "has_id": h.get("has_id", False)}, keep_app_open=False)
            ))
        return RenderResultListAction(items)

class ItemEnterListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        n, host, has_id = data["n"], data["host"], data["has_id"]
        env = os.environ.copy()
        safe_host = shlex.quote(host)
        
        if not has_id:
            zen_env = env.copy()
            zen_env.setdefault("XAUTHORITY", join(expanduser("~"), ".Xauthority"))
            proc = subprocess.run(
                ["zenity", "--password", "--title=" + extension.translations["password"]],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=zen_env
            )
            if proc.returncode != 0 or not proc.stdout: return
            password = proc.stdout.strip()
            env["SSHPASS"] = password
            cmd_layout = extension.ssh_command_template.replace("{host}", safe_host).replace("{password}", password)
        else:
            cmd_layout = extension.ssh_command_template_no_pw.replace("{host}", safe_host)

        full_cmd = [extension.terminal_command, "--disable-server"]
        for i in range(n):
            if i > 0: full_cmd.append(extension.tab_option)
            full_cmd.extend([f"--title={i+1}-{host}", extension.command_option, cmd_layout])

        subprocess.Popen(full_cmd, env=env)

if __name__ == '__main__':
    SshMultiplexExtension().run()
