import os
import subprocess
from os.path import expanduser
import re
import locale
import shutil 

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent, PreferencesEvent, PreferencesUpdateEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction


SPECIAL_CHARS_PATTERN = re.compile(r"([\[\]\$&`|;<>\"'\\ ])")



def escape_special_chars(password):
  """
  Escape shell-special characters by prefixing them with a backslash.  
  """
  return SPECIAL_CHARS_PATTERN.sub(r'\\\1', password)



def load_translations(language):
  translations = {
    "en": {
      "loading": "Loading SSH hosts...",
      "connect_to": "Connect to {host} ({n} tab)",
      "missing_deps_label": "Missing one or more dependencies",
      "missing_deps": "The following dependencies are missing: {missing}"
    },
    "it": {
      "loading": "Caricamento host SSH...",
      "connect_to": "Connetti a {host} ({n} tab)",
      "missing_deps_label": "Mancano una o più dipendenze",
      "missing_deps": "Dipendenze mancanti: {missing}"
    },
    "es": {
        "loading": "Cargando hosts SSH...",
        "connect_to": "Conectar a {host} ({n} pestaña)",
        "missing_deps_label": "Falta una o más dependencias",
        "missing_deps": "Faltan las siguientes dependencias: {missing}"
    },
    "fr": {
        "loading": "Chargement des hôtes SSH...",
        "connect_to": "Se connecter à {host} ({n} onglet)",
        "missing_deps_label": "Une ou plusieurs dépendances manquantes",
        "missing_deps": "Les dépendances suivantes sont manquantes : {missing}"
    },
    "de": {
        "loading": "Lade SSH-Hosts...",
        "connect_to": "Verbinden mit {host} ({n} Tab)",
        "missing_deps_label": "Eine oder mehrere Abhängigkeiten fehlen",
        "missing_deps": "Folgende Abhängigkeiten fehlen: {missing}"
    },
    "pt": {
        "loading": "Carregando hosts SSH...",
        "connect_to": "Conectar a {host} ({n} aba)",
        "missing_deps_label": "Uma ou mais dependências ausentes",
        "missing_deps": "As seguintes dependências estão ausentes: {missing}"
    },
    "zh": {
        "loading": "正在加载 SSH 主机...",
        "connect_to": "连接到 {host}（{n} 个标签页）",
        "missing_deps_label": "缺少一个或多个依赖项",
        "missing_deps": "缺少以下依赖项：{missing}"
    },
    "ru": {
        "loading": "Загрузка SSH-хостов...",
        "connect_to": "Подключиться к {host} ({n} вкладка)",
        "missing_deps_label": "Отсутствует одна или несколько зависимостей",
        "missing_deps": "Отсутствуют следующие зависимости: {missing}"
    },
    "pl": {
        "loading": "Ładowanie hostów SSH...",
        "connect_to": "Połącz z {host} ({n} karta)",
        "missing_deps_label": "Brakuje jednej lub więcej zależności",
        "missing_deps": "Brakuje następujących zależności: {missing}"
    },
    "uk": {
        "loading": "Завантаження SSH-хостів...",
        "connect_to": "Підключення до {host} ({n} вкладка)",
        "missing_deps_label": "Відсутня одна або кілька залежностей",
        "missing_deps": "Відсутні наступні залежності: {missing}"
    },
    "ja": {
        "loading": "SSHホストを読み込んでいます...",
        "connect_to": "{host} に接続 ({n} タブ)",
        "missing_deps_label": "1つ以上の依存関係が見つかりません",
        "missing_deps": "次の依存関係が見つかりません: {missing}"
    },
    "hi": {
        "loading": "SSH होस्ट लोड हो रहे हैं...",
        "connect_to": "{host} से कनेक्ट करें ({n} टैब)",
        "missing_deps_label": "एक या अधिक निर्भरताएँ गायब हैं",
        "missing_deps": "निम्नलिखित निर्भरताएँ गायब हैं: {missing}"
    },
    "ar": {
        "loading": "جارٍ تحميل مضيفي SSH...",
        "connect_to": "الاتصال بـ {host} ({n} تبويب)",
        "missing_deps_label": "يوجد نقص في اعتماد واحد أو أكثر",
        "missing_deps": "الاعتمادات التالية مفقودة: {missing}"
    }
  }
  return translations.get(language, translations["en"])
    
    

class SshMultiplexExtension(Extension):
  def __init__(self):
    super(SshMultiplexExtension, self).__init__()
    self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
    self.subscribe(ItemEnterEvent, ItemEnterListener())
    self.subscribe(PreferencesEvent, PreferencesListener())
    self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
    
    # Default settings
    self.terminal_command = "xfce4-terminal"
    self.tab_option = "--tab"
    self.command_option = "--command"
    self.max_tabs = "10"
    self.ssh_command_template = "bash -c 'export SSHPASS={password}; sshpass -e ssh {host}; exec bash'" 
    self.ssh_command_template_no_pw = "bash -c 'ssh {host}; exec bash'"
    
    locale.setlocale(locale.LC_ALL, '')
    lang = locale.getlocale()[0]
    self.language = lang.split('_')[0] if lang else 'en'
    self.translations = load_translations(self.language) 
    
    self.missing_deps = []
    for dep in ["zenity", "sshpass"]:
      if shutil.which(dep) is None:
        self.missing_deps.append(dep)
    

  def parse_ssh_config(self):
    hosts = []
    path = expanduser("~/.ssh/config")
    if os.path.isfile(path):
      current_host = None
      
      with open(path) as f:
        for line in f:
          stripped = line.strip()
          if stripped.lower().startswith("host ") and "*" not in stripped:
            host = stripped.split()[1]
            
            hosts.append({
              "host": host,
              "has_identity_file": False
            })
          elif stripped.lower().startswith("identityfile"):
            hosts[-1]["has_identity_file"] = True
            
    return sorted(hosts, key=lambda x: x["host"])




class PreferencesUpdateEventListener(EventListener):

  def on_event(self, event, extension):
    
    fields = {
      "terminal_command",
      "tab_option",
      "command_option",
      "ssh_command_template",
      "ssh_command_template_no_pw"
    }

    if event.id in fields:
      setattr(extension, event.id, event.new_value)

    if event.id == "max_tabs":
      try:
        extension.max_tabs = int(event.new_value)    
      except ValueError:
        extension.max_tabs = 10 
        
    elif event.id == "language":
      extension.language = event.new_value
      if extension.language:
        extension.translations = load_translations(extension.language)
      else:
        lang = locale.getlocale()[0]
        extension.language = lang.split('_')[0] if lang else 'en'
        extension.translations = load_translations(extension.language)
        
        
        

class PreferencesListener(EventListener):
  def on_event(self, event, extension):

    extension.terminal_command = event.preferences.get("terminal_command", extension.terminal_command)
    extension.tab_option = event.preferences.get("tab_option", extension.tab_option)
    extension.command_option = event.preferences.get("command_option", extension.command_option)
    
    try:
      extension.max_tabs = int(event.preferences.get("max_tabs", extension.max_tabs))    
    except ValueError:
      extension.max_tabs = 10 
    
    extension.ssh_command_template = event.preferences.get("ssh_command_template", extension.ssh_command_template)
    extension.ssh_command_template_no_pw = event.preferences.get("ssh_command_template_no_pw", extension.ssh_command_template_no_pw)
    extension.language = event.preferences.get("language", extension.language)

    if extension.language:
      extension.translations = load_translations(extension.language)
    else:
      lang = locale.getlocale()[0]
      extension.language = lang.split('_')[0] if lang else 'en'
      extension.translations = load_translations(extension.language)
    
            
class KeywordQueryEventListener(EventListener):
  def on_event(self, event, extension):
    query = event.get_argument() or ""
    parts = query.split()
    icon = "images/icon.svg"
    items = []
    
    
    if len(extension.missing_deps) > 0:
      items.append(ExtensionResultItem(
          icon=icon,
          name=extension.translations["missing_deps_label"],          
          description=extension.translations["missing_deps"].format(missing=','.join(extension.missing_deps))          
        ))
      return RenderResultListAction(items)
      
    
    all_hosts = extension.parse_ssh_config()

    if not parts:      
      for host_info in all_hosts:
        items.append(ExtensionResultItem(
          icon=icon,
          name=host_info["host"],          
          description=extension.translations["connect_to"].format(host=host_info["host"], n=1),
          on_enter=ExtensionCustomAction({"n": 1, "host": host_info["host"], "has_identity_file": host_info["has_identity_file"]}, keep_app_open=False)
        ))
      return RenderResultListAction(items)

    if parts[0].isdigit():
      n = int(parts[0])
      prefix = parts[1] if len(parts) > 1 else ''
    else:
      n = 1
      prefix = parts[0]
      
      
    if n > extension.max_tabs:
      n = extension.max_tabs

    prefix_lower = prefix.lower()
    matches = [{"host": h["host"], "has_identity_file": h["has_identity_file"]} for h in all_hosts if prefix_lower in h["host"].lower()]
    matches.sort(key=lambda h: (not h["host"].lower().startswith(prefix_lower), h["host"]))

    if not matches:
      items.append(ExtensionResultItem(
        icon=icon,
        name=prefix,
        description=extension.translations["connect_to"].format(host=prefix, n=n),
        on_enter=ExtensionCustomAction({"n": n, "host": prefix}, keep_app_open=False)
      ))
    else:
      for host_info in matches:
        items.append(ExtensionResultItem(
          icon=icon,
          name=host_info["host"],
          description=extension.translations["connect_to"].format(host=host_info["host"], n=n),
          on_enter=ExtensionCustomAction({"n": n, "host": host_info["host"], "has_identity_file": host_info["has_identity_file"]}, keep_app_open=False)
        ))

    return RenderResultListAction(items)

class ItemEnterListener(EventListener):
  def on_event(self, event, extension):
    data = event.get_data() or {}
    n = data.get("n", 1)
    host = data.get("host")
    has_identity_file = data.get("has_identity_file")
    if not host:
      return


    if n > extension.max_tabs:
      n = extension.max_tabs
    
    env = os.environ.copy()
    ssh_cmd_layout = None
    
    if has_identity_file != True:
      try:
        zen_env = os.environ.copy()
        #zen_env.setdefault("DISPLAY", ":0")
        home = expanduser("~")
        zen_env.setdefault("XAUTHORITY", os.path.join(home, ".Xauthority"))
        proc = subprocess.run(
          ["zenity", "--password", "--title=SSH Password"],
          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=zen_env
        )
        if proc.returncode != 0 or not proc.stdout:
          return
        password = proc.stdout.strip()
      except Exception:
        return

      
      env["SSHPASS"] = password
      ssh_cmd_layout = extension.ssh_command_template.format(password=escape_special_chars(password), host=host)

    else:
      ssh_cmd_layout = extension.ssh_command_template_no_pw.format(host=host)      


    cmd = [extension.terminal_command, "--disable-server"]

    # Apriamo n tab SSH
    for i in range(n):
      #ssh_cmd = extension.ssh_command_template.format(password=password, host=host)
      ssh_cmd = ssh_cmd_layout
      
      if i > 0:
        cmd += [extension.tab_option]
      
      cmd += [        
        f"--title={i + 1}-{host}",
        extension.command_option,
        ssh_cmd
      ]

    # Eseguiamo il comando per aprire i tab
    subprocess.Popen(cmd, env=env)

if __name__ == '__main__':
  SshMultiplexExtension().run()
