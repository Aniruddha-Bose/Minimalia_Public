import base64
import json
import os
import sys
from PyQt6.QtCore import QUrl, Qt, QEvent
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit,
    QTabWidget, QVBoxLayout, QHBoxLayout, QStatusBar,
    QDialog, QRadioButton, QButtonGroup, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QWidget,
    QMessageBox, QSplitter, QCheckBox, QComboBox,
)
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor
from PyQt6.QtWebEngineWidgets import QWebEngineView

import urllib.request

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

if sys.platform == "win32":
    DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Minimalia")
elif sys.platform == "darwin":
    DATA_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Minimalia")
else:
    DATA_DIR = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share")), "Minimalia")
os.makedirs(DATA_DIR, exist_ok=True)

SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
LOGO_PATH = os.path.join(BUNDLE_DIR, "assets", "ui", "minimalia_logo.png")

EASYLIST_URL = "https://easylist.to/easylist/easylist.txt"
EASYLIST_PATH = os.path.join(DATA_DIR, "easylist.txt")


def _download_easylist():
    """Download EasyList if not already cached (re-downloads every 7 days)."""
    import time
    if os.path.exists(EASYLIST_PATH):
        age = time.time() - os.path.getmtime(EASYLIST_PATH)
        if age < 7 * 86400:
            return
    try:
        req = urllib.request.Request(EASYLIST_URL, headers={"User-Agent": "Minimalia/1.0"})
        with urllib.request.urlopen(req) as resp:
            with open(EASYLIST_PATH, "wb") as f:
                f.write(resp.read())
    except Exception:
        pass


def _load_adblock_engine():
    """Load adblock engine from cached EasyList filters."""
    import adblock
    _download_easylist()
    if not os.path.exists(EASYLIST_PATH):
        return None
    engine = adblock.Engine(adblock.FilterSet())
    fs = adblock.FilterSet()
    with open(EASYLIST_PATH, "r", encoding="utf-8") as f:
        fs.add_filter_list(f.read())
    engine = adblock.Engine(fs)
    return engine


class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    RESOURCE_TYPE_MAP = {
        0: "other",           # NavigationTypeLink
        1: "other",           # NavigationTypeTyped
        2: "other",           # NavigationTypeFormSubmitted
        3: "other",           # NavigationTypeBackForward
        4: "other",           # NavigationTypeReload
        5: "other",           # NavigationTypeOther
    }

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        first_party = info.firstPartyUrl().toString()
        result = self._engine.check_network_urls(url, first_party, "other")
        if result.matched:
            info.block(True)


BG_JS = """
    (function() {
        var dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        var bg = dark ? '#1e1e1e' : '#ffffff';
        var fg = dark ? '#e0e0e0' : '#202124';
        var s = document.createElement('style');
        s.textContent =
            'html, body, .hp_body, .hp_top_cover, .hp_top_cover_container, ' +
            '.hp_top_cover_dim, .hp_media_container, .hp_media_container_gradient, ' +
            '.hp_cont, .topLeft, .topRight, .bottom, #hp_top_cover, ' +
            '#bgDiv, #preloadBg, .vs_cover, .hp_sw_hdr { ' +
            '  background: ' + bg + ' !important; ' +
            '  background-image: none !important; ' +
            '} ' +
            '.hp_media_container, #preloadBg, #bgDiv { ' +
            '  visibility: hidden !important; ' +
            '} ' +
            '.bottom, .infopane, .river, .feed_layout, ' +
            '#feed_col, .todaystripe, .hp_sw_tc, ' +
            '.bnc-container, #crs_pane, #carousel, .carousel, ' +
            '.feed_bg, .module.feed_bg, #widget_container, ' +
            '.peregrine-widgets, .feed_header, ' +
            '.bottom_row, .msnpeek, .vs_cont, .mc_caro, ' +
            '#scroll_cont, #sb_feedback, .vs, .sw_lang, ' +
            '.hp_bottom_cover_container { ' +
            '  display: none !important; ' +
            '} ' +
            'html, body { color: ' + fg + ' !important; }';
        document.head.appendChild(s);
    })();
"""

DISABLE_AI_JS = {
    "Google Search": """
        (function() {
            var s = document.createElement('style');
            s.textContent = 'a[href*="udm=50"], button.plR5qb { display: none !important; }';
            (document.head || document.documentElement).appendChild(s);
            function removeAI() {
                document.querySelectorAll(
                    '[data-attrid="AIOverview"], .kno-fb-ctx, .M8OgIe, .LuVEUc, ' +
                    '.aisoOverviewLinkCardGroup, [jsname="Ol3kkd"], .Wt5Tfe, ' +
                    '.GVkMFc, [data-content-feature="1"], .GBLmjf'
                ).forEach(function(el) { el.remove(); });
                document.querySelectorAll('div, span, h2').forEach(function(el) {
                    if (el.textContent.trim() === 'AI Overview') {
                        var block = el.closest('[data-hveid], [jscontroller], .g') || el.parentElement;
                        if (block) block.remove();
                    }
                });
            }
            removeAI();
            var obs = new MutationObserver(function() { removeAI(); });
            obs.observe(document.body, {childList: true, subtree: true});
        })();
    """,
    "Microsoft Bing (Experimental)": """
        (function() {
            function removeAI() {
                document.querySelectorAll(
                    '#codex, [id="codex"], ' +
                    'li:has(> a[href*="/chat"]), ' +
                    'a[href*="/images/create"], a[href*="/videos/create"], ' +
                    '.ic_bk, .vc_bk, ' +
                    '.b-scopeListItem-conv, ' +
                    '.cdxCopilotIconBg, .cdxCopilotIcon, ' +
                    '.gs_h, .gs_caphead, .gs_temp_content, ' +
                    '.gs_card, .gs_card_ans, .gs_heroTextHeader, ' +
                    '[class*="gs_caphead"], ' +
                    'a[href*="/copilotsearch"], a[href*="CSSCOP"], ' +
                    '#b_bop_cs_sb_place, .b_bop_cs_sb_l, .composer_container, ' +
                    '.suggestion_container, .b_copilot_composer, .b_copilot_icon'
                ).forEach(function(el) { el.remove(); });
                document.querySelectorAll('.scopes li, .scope').forEach(function(el) {
                    var a = el.querySelector('a');
                    if (a) {
                        var text = a.textContent.trim().toLowerCase();
                        if (text === 'copilot' || text === 'image creator' || text === 'video creator') {
                            el.remove();
                        }
                    }
                });
            }
            removeAI();
            var obs = new MutationObserver(function() { removeAI(); });
            obs.observe(document.body, {childList: true, subtree: true});
        })();
    """,
    "DuckDuckGo": """
        (function() {
            var s = document.createElement('style');
            s.textContent = '[data-testid="ai-toggle-integrated"], [data-ssg-id="mode-toggle-switch"], [data-testid="aichat-button"], a[href*="duck.ai"], a[href*="assist=true"], a[href*="ia=chat"] { display: none !important; }';
            (document.head || document.documentElement).appendChild(s);
        })();
    """,
}

SEARCH_RESULTS_LOGO_JS = {
    "Google Search": "",
    "Microsoft Bing (Experimental)": """
        (function() {
            function hideRewardsIfNotSignedIn() {
                var signInBtn = document.querySelector('#id_s, #id_a, a[href*="login.live"], a[href*="login.microsoftonline"]');
                if (signInBtn) {
                    document.querySelectorAll('#id_rh_w, [data-rewards-widget], .serp.kumo_rewards, .medal, .points-container').forEach(function(el) { el.remove(); });
                }
            }
            hideRewardsIfNotSignedIn();
            var obs = new MutationObserver(function() { hideRewardsIfNotSignedIn(); });
            obs.observe(document.body, {childList: true, subtree: true});
        })();
    """,
    "DuckDuckGo": """
        (function() {
            function replaceSearchLogo() {
                var el = document.querySelector('[class*="header_logoImg"] img, [class*="header_logoHorizontal"] img, a[title*="DuckDuckGo"] img');
                if (!el) document.querySelectorAll('a img').forEach(function(i) { if (i.src && i.src.includes('svg+xml') && i.closest('header,a[href*="about"]')) el = i; });
                if (el && !el.dataset.jbReplaced) {
                    el.dataset.jbReplaced = '1';
                    el.src = '%LOGO%';
                    el.style.height = '30px';
                    el.style.width = 'auto';
                    return true;
                }
                return false;
            }
            replaceSearchLogo();
            var obs = new MutationObserver(function() { replaceSearchLogo(); });
            obs.observe(document.body, {childList: true, subtree: true});
        })();
    """,
}

SEARCH_ENGINES = {
    "Google Search": {
        "search_url": "https://www.google.com/search?q={}",
        "home_url": "https://www.google.com",
        "logo_js": """
            function removeChromeBanner() {
                document.querySelectorAll('g-bottom-sheet, [aria-describedby="promo_desc_id"], [aria-labelledby="promo_label_id"], .ky4hfd, .lgo9kc').forEach(function(el) { el.remove(); });
            }
            function fixFooter() {
                if (!document.getElementById('__jb_footer_fix')) {
                    var s = document.createElement('style');
                    s.id = '__jb_footer_fix';
                    s.textContent = '#SIvCob, .uU7dJb { display: none !important; } #footcnt, .o3j99.qarstb { margin-top: 0 !important; padding-top: 0 !important; } a.MV3Tnb[href*="about.google"], a.MV3Tnb[href*="store.google"] { display: none !important; }';
                    document.head.appendChild(s);
                }
            }
            removeChromeBanner(); fixFooter();
            var obs = new MutationObserver(function() { removeChromeBanner(); });
            obs.observe(document.body, {childList: true, subtree: true});
        """,
    },
    "DuckDuckGo": {
        "search_url": "https://duckduckgo.com/?q={}",
        "home_url": "https://duckduckgo.com",
        "logo_js": "",
    },
    "Microsoft Bing (Experimental)": {
        "search_url": "https://www.bing.com/search?q={}",
        "home_url": "https://www.bing.com",
        "logo_js": """
            if (!document.getElementById('__jb_hdr_fix')) {
                var s = document.createElement('style');
                s.id = '__jb_hdr_fix';
                s.textContent = '.head_cont, #headCont { display: flex !important; width: 100% !important; } .scope_cont { display: none !important; } #id_h { margin-left: auto !important; white-space: nowrap !important; } #id_mob, .id_mob, a[href*="aka.ms/AAbig39"], .mobile { display: none !important; }';
                document.head.appendChild(s);
            }
        """,
    },
}


def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    return None


def save_settings(settings):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


_logo_cache = None

def get_logo_data_uri():
    global _logo_cache
    if _logo_cache is None:
        with open(LOGO_PATH, "rb") as f:
            _logo_cache = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return _logo_cache


def build_home_html(search_url, logo_b64, engine_name):
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Minimalia</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; height: 100vh;
  }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #1e1e1e; color: #e0e0e0; }}
    input[type="text"] {{ background: #2d2d2d; color: #e0e0e0; border-color: #444; }}
    input[type="text"]:focus {{ box-shadow: 0 1px 6px rgba(255,255,255,0.1); }}
  }}
  @media (prefers-color-scheme: light) {{
    body {{ background: #fff; color: #202124; }}
  }}
  img.logo {{ width: 292px; margin-bottom: 28px; }}
  form {{ display: flex; align-items: center; }}
  input[type="text"] {{
    width: 480px; padding: 12px 20px; font-size: 16px;
    border: 1px solid #dfe1e5; border-radius: 24px;
    outline: none; transition: box-shadow 0.2s;
  }}
  input[type="text"]:focus {{
    box-shadow: 0 1px 6px rgba(32,33,36,0.28);
    border-color: transparent;
  }}
  .powered {{ margin-top: 18px; font-size: 13px; color: #9aa0a6; }}
</style>
</head>
<body>
  <img class="logo" src="data:image/png;base64,{logo_b64}" alt="Minimalia">
  <form action="javascript:void(0)" onsubmit="search()">
    <input type="text" id="q" autofocus placeholder="Search the web...">
  </form>
  <div class="powered">Powered by {engine_name}</div>
  <script>
    function search() {{
      var q = document.getElementById('q').value.trim();
      if (q) window.location.href = '{search_url}'.replace('{{}}', encodeURIComponent(q));
    }}
  </script>
</body>
</html>"""


class SearchEngineDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Minimalia")
        self.setFixedSize(350, 230)
        self.chosen = None
        self.custom_url = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose your default search engine:"))

        self.group = QButtonGroup(self)
        names = list(SEARCH_ENGINES.keys())
        for i, name in enumerate(names):
            radio = QRadioButton(name)
            if i == 0:
                radio.setChecked(True)
            self.group.addButton(radio, i)
            layout.addWidget(radio)

        self._custom_radio = QRadioButton("Custom URL")
        self.group.addButton(self._custom_radio, len(names))
        layout.addWidget(self._custom_radio)

        ok_btn = QPushButton("Next")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        from PyQt6.QtWidgets import QMessageBox
        names = list(SEARCH_ENGINES.keys())
        idx = self.group.checkedId()
        if idx < len(names):
            self.chosen = names[idx]
        else:
            self.chosen = "__custom__"
        if self.chosen and "Experimental" in self.chosen:
            msg = QMessageBox(self)
            msg.setWindowTitle("Warning")
            msg.setText("Warning! This is in an experimental stage and may not work with full functionality.")
            msg.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok)
            msg.button(QMessageBox.StandardButton.Ok).setText("Continue")
            if msg.exec() != QMessageBox.StandardButton.Ok:
                return
        super().accept()


class CustomURLDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Search Engine")
        self.setFixedSize(420, 150)
        self.url = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter the homepage URL of your search engine:"))

        self._input = QLineEdit()
        self._input.setPlaceholderText("https://example.com")
        layout.addWidget(self._input)

        lbl = QLabel("  e.g. https://duckduckgo.com, https://search.brave.com")
        lbl.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(lbl)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        text = self._input.text().strip()
        if not text.startswith(("http://", "https://")):
            text = "https://" + text
        self.url = text
        super().accept()


class ExperienceDialog(QDialog):
    def __init__(self, engine_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Experience")
        self.setFixedSize(420, 280)
        self.chosen = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose your experience:"))

        self.group = QButtonGroup(self)

        options = [
            ("Minimalia", "Just the web, nothing else."),
            (f"{engine_name} with cleanups", f"The search engine you know and love, just without the clutter."),
            (f"Default ({engine_name})", f"The default {engine_name}, no changes made."),
        ]
        keys = ["minimalia", "cleanups", "default"]

        for i, (name, caption) in enumerate(options):
            radio = QRadioButton(name)
            if i == 0:
                radio.setChecked(True)
            self.group.addButton(radio, i)
            layout.addWidget(radio)
            lbl = QLabel(f"  {caption}")
            lbl.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
            layout.addWidget(lbl)

        self._keys = keys

        ok_btn = QPushButton("Next")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        self.chosen = self._keys[self.group.checkedId()]
        super().accept()


class DisableAIDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Features")
        self.setFixedSize(400, 180)
        self.chosen = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Disable AI features?"))

        self.group = QButtonGroup(self)

        radio_yes = QRadioButton("Disable AI Features")
        radio_no = QRadioButton("Keep AI Features")
        radio_no.setChecked(True)
        self.group.addButton(radio_yes, 0)
        self.group.addButton(radio_no, 1)

        layout.addWidget(radio_yes)
        lbl_yes = QLabel("  Removes Copilot, Image/Video Creator from Bing and AI overview from Google.")
        lbl_yes.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        lbl_yes.setWordWrap(True)
        layout.addWidget(lbl_yes)

        layout.addWidget(radio_no)
        lbl_no = QLabel("  Keep all AI features as they are.")
        lbl_no.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        layout.addWidget(lbl_no)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        self.chosen = self.group.checkedId() == 0
        super().accept()


class BlockPromotionsDialog(QDialog):
    def __init__(self, engine_name="Microsoft Bing (Experimental)", parent=None):
        super().__init__(parent)
        short_name = engine_name.replace("Microsoft ", "")
        self.setWindowTitle(f"{short_name} Promotions")
        self.setFixedSize(400, 180)
        self.chosen = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Block {short_name} promotions?"))

        self.group = QButtonGroup(self)

        radio_yes = QRadioButton("Block Promotions")
        radio_no = QRadioButton("Keep Promotions")
        radio_no.setChecked(True)
        self.group.addButton(radio_yes, 0)
        self.group.addButton(radio_no, 1)

        layout.addWidget(radio_yes)
        lbl_yes = QLabel(f'  Blocks all promotional cards from {short_name} search results.')
        lbl_yes.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        lbl_yes.setWordWrap(True)
        layout.addWidget(lbl_yes)

        layout.addWidget(radio_no)
        lbl_no = QLabel(f"  Keep {short_name} promotional content as-is.")
        lbl_no.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        layout.addWidget(lbl_no)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        self.chosen = self.group.checkedId() == 0
        super().accept()


class AdBlockDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ad Blocker")
        self.setFixedSize(400, 180)
        self.chosen = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enable ad blocker?"))

        self.group = QButtonGroup(self)

        radio_yes = QRadioButton("Enable Ad Blocker")
        radio_no = QRadioButton("No Ad Blocker")
        radio_no.setChecked(True)
        self.group.addButton(radio_yes, 0)
        self.group.addButton(radio_no, 1)

        layout.addWidget(radio_yes)
        lbl_yes = QLabel("  Blocks ads and trackers across all websites using EasyList filters.")
        lbl_yes.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        lbl_yes.setWordWrap(True)
        layout.addWidget(lbl_yes)

        layout.addWidget(radio_no)
        lbl_no = QLabel("  Browse without ad blocking.")
        lbl_no.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        layout.addWidget(lbl_no)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        self.chosen = self.group.checkedId() == 0
        super().accept()


class SearchHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search History")
        self.setFixedSize(400, 180)
        self.chosen = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enable search history?"))

        self.group = QButtonGroup(self)

        radio_yes = QRadioButton("Enable Search History")
        radio_no = QRadioButton("No Search History")
        radio_no.setChecked(True)
        self.group.addButton(radio_yes, 0)
        self.group.addButton(radio_no, 1)

        layout.addWidget(radio_yes)
        lbl_yes = QLabel("  Saves browsing history and keeps cookies between sessions.")
        lbl_yes.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        lbl_yes.setWordWrap(True)
        layout.addWidget(lbl_yes)

        layout.addWidget(radio_no)
        lbl_no = QLabel("  No history is saved and cookies are cleared on exit.")
        lbl_no.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        layout.addWidget(lbl_no)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        self.chosen = self.group.checkedId() == 0
        super().accept()


class SaveCookiesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cookies")
        self.setFixedSize(400, 180)
        self.chosen = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Save cookies between sessions?"))

        self.group = QButtonGroup(self)

        radio_yes = QRadioButton("Save Cookies")
        radio_no = QRadioButton("Clear Cookies on Exit")
        radio_no.setChecked(True)
        self.group.addButton(radio_yes, 0)
        self.group.addButton(radio_no, 1)

        layout.addWidget(radio_yes)
        lbl_yes = QLabel("  Keeps you logged in and remembers site preferences between sessions.")
        lbl_yes.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        lbl_yes.setWordWrap(True)
        layout.addWidget(lbl_yes)

        layout.addWidget(radio_no)
        lbl_no = QLabel("  All cookies are cleared when you close the browser.")
        lbl_no.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 6px;")
        layout.addWidget(lbl_no)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        self.chosen = self.group.checkedId() == 0
        super().accept()


class SettingsDialog(QDialog):
    def __init__(self, current_settings, parent=None, first_run=False):
        super().__init__(parent)
        self.setWindowTitle("Minimalia Settings" if first_run else "Settings")
        self.setFixedSize(420, 380 if first_run else 460)
        self._settings = current_settings.copy()

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(12, 12, 12, 12)

        self.setStyleSheet("QComboBox { max-height: 24px; min-height: 24px; margin-top: 4px; }")

        # Search engine
        lbl_engine = QLabel("Search Engine")
        layout.addWidget(lbl_engine)
        self.engine_combo = QComboBox()
        engines = list(SEARCH_ENGINES.keys()) + ["Custom URL"]
        self.engine_combo.addItems(engines)
        current_engine = current_settings.get("search_engine", "Google Search")
        if current_engine == "__custom__":
            self.engine_combo.setCurrentText("Custom URL")
        else:
            self.engine_combo.setCurrentText(current_engine)
        layout.addWidget(self.engine_combo)

        self.custom_url_input = QLineEdit()
        self.custom_url_input.setStyleSheet("margin-top: 6px;")
        self.custom_url_input.setPlaceholderText("Enter custom URL…")
        self.custom_url_input.setText(current_settings.get("custom_url", "") or "")
        self.custom_url_input.setVisible(current_engine == "__custom__")
        layout.addWidget(self.custom_url_input)

        self.engine_combo.currentTextChanged.connect(self._on_engine_changed)

        layout.addSpacing(10)

        # Experience
        layout.addWidget(QLabel("Experience"))
        self.exp_combo = QComboBox()
        self.exp_combo.addItems(["minimalia", "cleanups", "default"])
        self.exp_combo.setCurrentText(current_settings.get("experience", "default"))
        layout.addWidget(self.exp_combo)

        layout.addSpacing(10)

        # Toggles
        self.disable_ai_cb = QCheckBox("Disable AI features")
        self.disable_ai_cb.setChecked(current_settings.get("disable_ai", False))
        layout.addWidget(self.disable_ai_cb)

        self.block_promos_cb = QCheckBox("Block promotions")
        self.block_promos_cb.setChecked(current_settings.get("block_promos", False))
        layout.addWidget(self.block_promos_cb)

        self.adblock_cb = QCheckBox("Enable ad blocker")
        self.adblock_cb.setChecked(current_settings.get("enable_adblock", False))
        layout.addWidget(self.adblock_cb)

        self.history_cb = QCheckBox("Enable search history")
        self.history_cb.setChecked(current_settings.get("enable_history", False))
        layout.addWidget(self.history_cb)

        self.cookies_cb = QCheckBox("Save cookies between sessions")
        self.cookies_cb.setChecked(current_settings.get("save_cookies", False))
        layout.addWidget(self.cookies_cb)

        self.exp_combo.currentTextChanged.connect(self._on_experience_changed)
        self._on_experience_changed(self.exp_combo.currentText())

        # Buttons
        layout.addStretch()
        btn_layout = QHBoxLayout()
        if first_run:
            save_btn = QPushButton("Use selected settings")
            save_btn.clicked.connect(self.accept)
            btn_layout.addStretch()
            btn_layout.addWidget(save_btn)
        else:
            save_btn = QPushButton("Save and Restart")
            save_btn.clicked.connect(self.accept)
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addStretch()
            btn_layout.addWidget(cancel_btn)
            btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        if not first_run:
            layout.addStretch()
            reset_btn = QPushButton("Reset Profile")
            reset_btn.setStyleSheet("color: #d32f2f; border: 1px solid #d32f2f; padding: 6px;")
            reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reset_btn.clicked.connect(self._reset_profile)
            layout.addWidget(reset_btn)

    def _reset_profile(self):
        import shutil
        msg = QMessageBox(self)
        msg.setWindowTitle("Reset Profile")
        msg.setText("Are you sure you want to reset your profile?")
        msg.setInformativeText("This will delete all your browsing history, cookies and settings!")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        result = msg.exec()
        if result == QMessageBox.StandardButton.Yes:
            for path in [SETTINGS_PATH, HISTORY_PATH, BOOKMARKS_PATH]:
                if os.path.exists(path):
                    os.remove(path)
            for folder in ["browser_cache", "browser_data"]:
                p = os.path.join(DATA_DIR, folder)
                if os.path.exists(p):
                    shutil.rmtree(p, ignore_errors=True)
            QMessageBox.information(self, "Profile Reset", "Profile has been reset. Minimalia will now close.")
            self.reject()
            QApplication.instance().quit()

    def _on_engine_changed(self, engine):
        is_custom = engine == "Custom URL"
        self.custom_url_input.setVisible(is_custom)
        self.exp_combo.setEnabled(not is_custom)
        if is_custom:
            self.exp_combo.setCurrentText("default")

    def _on_experience_changed(self, exp):
        is_default = exp == "default"
        self.disable_ai_cb.setEnabled(not is_default)
        self.block_promos_cb.setEnabled(not is_default)
        if is_default:
            self.disable_ai_cb.setChecked(False)
            self.block_promos_cb.setChecked(False)

    def get_settings(self):
        engine = self.engine_combo.currentText()
        if engine == "Custom URL":
            engine = "__custom__"
        return {
            "search_engine": engine,
            "experience": self.exp_combo.currentText(),
            "disable_ai": self.disable_ai_cb.isChecked(),
            "block_promos": self.block_promos_cb.isChecked(),
            "enable_adblock": self.adblock_cb.isChecked(),
            "enable_history": self.history_cb.isChecked(),
            "save_cookies": self.cookies_cb.isChecked(),
            "custom_url": self.custom_url_input.text().strip() if engine == "__custom__" else self._settings.get("custom_url", None),
        }


HISTORY_PATH = os.path.join(DATA_DIR, "history.json")


def _load_history():
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_history(history):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def _add_history_entry(url, title):
    from datetime import datetime
    history = _load_history()
    history.append({"url": url, "title": title, "time": datetime.now().isoformat()})
    _save_history(history)


BOOKMARKS_PATH = os.path.join(DATA_DIR, "bookmarks.json")


def _load_bookmarks():
    if os.path.exists(BOOKMARKS_PATH):
        with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_bookmarks(bookmarks):
    with open(BOOKMARKS_PATH, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, ensure_ascii=False, indent=2)


def _add_bookmark(url, title):
    bookmarks = _load_bookmarks()
    for b in bookmarks:
        if b.get("url") == url:
            return
    bookmarks.append({"url": url, "title": title})
    _save_bookmarks(bookmarks)


BLOCK_PROMOS_JS = """
    (function() {
        function removePromos() {
            // Bing promos
            document.querySelectorAll(
                '.ad_sc, .b_ad, .b_adSlug, [data-ad-module], ' +
                '.promoSlug, .b_pPromote, .b_promote, ' +
                '[class*="promoted"], [data-prom]'
            ).forEach(function(el) { el.remove(); });
            document.querySelectorAll('*').forEach(function(el) {
                if (el.textContent.trim() === 'Promoted by Microsoft' ||
                    el.textContent.trim() === 'Ad' ||
                    el.textContent.trim() === 'Promoted') {
                    var block = el.closest('.b_algo, .b_ans, li, [data-tag]') || el.parentElement;
                    if (block) block.remove();
                }
            });
            // DuckDuckGo promos - CSS hide (immediate) + DOM remove (backup)
            if (window.location.hostname.includes('duckduckgo')) {
                if (!document.getElementById('__jb_ddg_promo')) {
                    var ddgStyle = document.createElement('style');
                    ddgStyle.id = '__jb_ddg_promo';
                    ddgStyle.textContent = '[data-testid*="desktopssg"], [class*="cta-cards"], [class*="homepage-cta-section"], [class*="desktop-homepage_heroContent"], [class*="desktop-homepage_ctaCards"], [class*="home-btf-hero"], [class*="download-options"], [class*="app-hero-download-button"], [class*="sidemenu-browser-promo"] { display: none !important; }';
                    (document.head || document.documentElement).appendChild(ddgStyle);
                }
                document.querySelectorAll(
                    '[data-testid*="desktopssg"], ' +
                    '[class*="cta-cards_cards"], [class*="cta-cards_card"], ' +
                    '[id="desktopssg:download"], [class*="desktop-homepage_ctaCards"], ' +
                    '[class*="homepage-cta-section"], [class*="desktop-homepage_heroContent"], ' +
                    '[class*="home-btf-hero"], [class*="download-options"], ' +
                    '[class*="app-hero-download-button"], ' +
                    '[class*="sidemenu-browser-promo"], ' +
                '[data-testid="belowTheFold"]'
                ).forEach(function(el) { el.remove(); });
                // Remove DDG browser promo cards on search results
                document.querySelectorAll('a[href*="funnel_browser"]').forEach(function(el) {
                    var section = el.closest('section');
                    if (section) { section.remove(); return; }
                    var div = el.parentElement;
                    if (div) div.remove();
                });
                // Center DDG search bar after removing promos
                if (window.location.hostname.includes('duckduckgo') && !document.getElementById('__jb_ddg_center')) {
                    var cs = document.createElement('style');
                    cs.id = '__jb_ddg_center';
                    cs.textContent = '[class*="desktop-homepage_hero"] { min-height: 100vh !important; } [class*="header_headerCenter"], [class*="ai-searchbox_formWrapper"] { margin-top: 20vh !important; }';
                    document.head.appendChild(cs);
                }
            }
        }
        removePromos();
        var obs = new MutationObserver(function() { removePromos(); });
        obs.observe(document.body, {childList: true, subtree: true});
    })();
"""


class BrowserTab(QWebEngineView):
    def __init__(self, experience, logo_js, disable_ai_js, search_results_logo_js, block_promos=False, profile=None, parent=None):
        super().__init__(parent)
        if profile:
            page = QWebEnginePage(profile, self)
            self.setPage(page)
        self.experience = experience
        self.logo_js = logo_js
        self.disable_ai_js = disable_ai_js
        self.search_results_logo_js = search_results_logo_js
        self.block_promos = block_promos

        self.loadFinished.connect(self._inject)
        if self.disable_ai_js:
            self.urlChanged.connect(self._block_ai_url)

    def _open_in_new_tab(self, qurl):
        browser = self.window()
        if isinstance(browser, Browser):
            browser.add_tab(qurl)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        hit = self.lastContextMenuRequest()
        image_url = hit.mediaUrl() if hit else QUrl()
        if image_url.isValid() and hit.mediaType() == hit.MediaType.MediaTypeImage:
            save_as_action = QAction("Save Image As…", menu)
            save_as_action.triggered.connect(lambda: self._save_image_as(image_url))
            # Insert after existing "Save image" action
            actions = menu.actions()
            inserted = False
            for i, a in enumerate(actions):
                if a.text() and "save image" in a.text().lower().replace("&", ""):
                    menu.insertAction(actions[i + 1] if i + 1 < len(actions) else None, save_as_action)
                    inserted = True
                    break
            if not inserted:
                menu.addAction(save_as_action)
        menu.addSeparator()
        url = self.url().toString()
        is_bookmarked = any(b.get("url") == url for b in _load_bookmarks())
        if is_bookmarked:
            bookmark_action = menu.addAction("Unbookmark")
            bookmark_action.triggered.connect(self._unbookmark_tab)
        else:
            bookmark_action = menu.addAction("Bookmark")
            bookmark_action.triggered.connect(self._bookmark_tab)
        if not (hasattr(self, '_devtools') and self._devtools is not None):
            menu.addSeparator()
            inspect_action = menu.addAction("Inspect")
            inspect_action.triggered.connect(self._open_inspect)
        menu.exec(event.globalPos())

    def _bookmark_tab(self):
        browser = self.window()
        if isinstance(browser, Browser):
            browser._bookmark_current_tab()

    def _unbookmark_tab(self):
        browser = self.window()
        if isinstance(browser, Browser):
            browser._unbookmark_current_tab()

    def _save_image_as(self, image_url):
        from PyQt6.QtWidgets import QFileDialog
        url_path = image_url.path()
        filename = url_path.split("/")[-1] if "/" in url_path else "image"
        path, _ = QFileDialog.getSaveFileName(self, "Save Image As", filename, "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;All Files (*)")
        if path:
            app = QApplication.instance()
            app._pending_save_path = path
            self.page().download(image_url, "")

    def _open_inspect(self):
        browser = self.window()
        if hasattr(browser, '_toggle_devtools'):
            browser._toggle_devtools()

    def _block_ai_url(self, qurl):
        url = qurl.toString()
        if 'udm=50' in url or 'google.com/search/ai' in url:
            import re
            clean = re.sub(r'[&?]udm=50', '', url)
            clean = re.sub(r'[&?]ntc=\d+', '', clean)
            if clean != url:
                self.setUrl(QUrl(clean))
        elif 'bing.com/chat' in url or 'bing.com/search?showconv' in url or 'bing.com/copilotsearch' in url:
            import re
            q = re.search(r'[?&]q=([^&]*)', url)
            if q:
                self.setUrl(QUrl(f"https://www.bing.com/search?q={q.group(1)}"))
            else:
                self.setUrl(QUrl("https://www.bing.com"))

    def _inject(self, ok):
        if not ok:
            return
        if self.experience == "cleanups":
            if self.logo_js:
                self.page().runJavaScript(self.logo_js)
            url = self.url().toString()
            if url.rstrip('/') in ('https://www.bing.com', 'https://bing.com', 'https://www.google.com', 'https://google.com', 'https://duckduckgo.com', 'https://www.duckduckgo.com'):
                self.page().runJavaScript(BG_JS)
            if self.disable_ai_js:
                self.page().runJavaScript(self.disable_ai_js)
            if self.search_results_logo_js:
                self.page().runJavaScript(self.search_results_logo_js)
        elif self.experience == "minimalia":
            if self.disable_ai_js:
                self.page().runJavaScript(self.disable_ai_js)
            if self.search_results_logo_js:
                self.page().runJavaScript(self.search_results_logo_js)
        if self.block_promos:
            self.page().runJavaScript(BLOCK_PROMOS_JS)
        self.page().runJavaScript(CTRL_CLICK_JS)

    def createWindow(self, window_type):
        browser = self.parent()
        while browser and not isinstance(browser, Browser):
            browser = browser.parent()
        if browser:
            return browser.add_tab(skip_home=True)
        return super().createWindow(window_type)


STATIC_SITES = [
    # Search engines
    "google.com", "bing.com", "duckduckgo.com", "search.brave.com",
    "yahoo.com", "baidu.com", "yandex.com", "ecosia.org", "startpage.com",
    # News
    "bbc.com", "bbc.co.uk", "cnn.com", "nytimes.com", "theguardian.com",
    "reuters.com", "apnews.com", "aljazeera.com", "washingtonpost.com",
    "forbes.com", "bloomberg.com", "cnbc.com", "foxnews.com", "nbcnews.com",
    "abcnews.go.com", "cbsnews.com", "usatoday.com", "latimes.com",
    "nypost.com", "dailymail.co.uk", "independent.co.uk", "telegraph.co.uk",
    "mirror.co.uk", "metro.co.uk", "sky.com", "euronews.com",
    "france24.com", "dw.com", "rt.com", "scmp.com", "straitstimes.com",
    "channelnewsasia.com", "thehindu.com", "timesofindia.indiatimes.com",
    "ndtv.com", "hindustantimes.com", "japantimes.co.jp",
    "smh.com.au", "abc.net.au", "stuff.co.nz", "globalnews.ca",
    "cbc.ca", "thestar.com", "politico.com", "thehill.com",
    "axios.com", "vox.com", "slate.com", "salon.com", "thedailybeast.com",
    "huffpost.com", "buzzfeed.com", "vice.com", "theatlantic.com",
    "newyorker.com", "economist.com", "ft.com", "wsj.com",
    "businessinsider.com", "techcrunch.com", "wired.com", "arstechnica.com",
    "theverge.com", "engadget.com", "gizmodo.com", "mashable.com",
    "zdnet.com", "cnet.com", "tomshardware.com", "anandtech.com",
    "pcmag.com", "tomsguide.com", "howtogeek.com", "lifehacker.com",
    "macrumors.com", "9to5mac.com", "9to5google.com", "androidcentral.com",
    "windowscentral.com", "xda-developers.com",
    # Social / forums
    "reddit.com", "quora.com", "medium.com", "substack.com",
    "tumblr.com", "deviantart.com", "imgur.com", "flickr.com",
    "pinterest.com", "linkedin.com",
    # Reference / education
    "wikipedia.org", "wikimedia.org", "wiktionary.org", "wikihow.com",
    "britannica.com", "dictionary.com", "thesaurus.com", "merriam-webster.com",
    "archive.org", "gutenberg.org", "jstor.org", "scholar.google.com",
    "khanacademy.org", "coursera.org", "edx.org", "udemy.com",
    "duolingo.com", "quizlet.com", "chegg.com", "sparknotes.com",
    # Developer / docs
    "stackoverflow.com", "stackexchange.com", "github.com", "gitlab.com",
    "bitbucket.org", "docs.python.org", "developer.mozilla.org",
    "w3schools.com", "css-tricks.com", "smashingmagazine.com",
    "digitalocean.com", "readthedocs.io", "docs.microsoft.com",
    "learn.microsoft.com", "developer.apple.com", "developers.google.com",
    "npmjs.com", "pypi.org", "crates.io", "packagist.org",
    "rubygems.org", "maven.apache.org", "hub.docker.com",
    # Entertainment / media
    "imdb.com", "rottentomatoes.com", "metacritic.com", "letterboxd.com",
    "tvtropes.org", "fandom.com", "myanimelist.net", "anilist.co",
    "goodreads.com", "audible.com", "last.fm", "genius.com",
    "songlyrics.com", "azlyrics.com",
    # Shopping / reviews
    "amazon.com", "amazon.co.uk", "amazon.de", "amazon.co.jp",
    "ebay.com", "etsy.com", "walmart.com", "target.com", "bestbuy.com",
    "aliexpress.com", "wish.com", "newegg.com", "costco.com",
    "ikea.com", "wayfair.com", "zappos.com", "shein.com",
    "yelp.com", "trustpilot.com", "glassdoor.com",
    # Travel / maps
    "tripadvisor.com", "booking.com", "airbnb.com", "expedia.com",
    "kayak.com", "skyscanner.com", "hotels.com", "agoda.com",
    "lonelyplanet.com", "google.com/maps", "maps.google.com",
    # Weather
    "weather.com", "accuweather.com", "wunderground.com", "weather.gov",
    "windy.com",
    # Finance
    "finance.yahoo.com", "marketwatch.com", "investopedia.com",
    "seekingalpha.com", "morningstar.com", "coinmarketcap.com",
    "coingecko.com", "tradingview.com",
    # Sports
    "espn.com", "sports.yahoo.com", "bleacherreport.com",
    "skysports.com", "goal.com", "transfermarkt.com",
    "nba.com", "nfl.com", "mlb.com", "nhl.com", "fifa.com",
    "uefa.com", "cricbuzz.com", "espncricinfo.com",
    # Government / org
    "who.int", "un.org", "nasa.gov", "nih.gov", "cdc.gov",
    "fda.gov", "irs.gov", "usa.gov", "gov.uk", "europa.eu",
    # Utilities / tools (read-only)
    "speedtest.net", "fast.com", "whatismyipaddress.com",
    "timeanddate.com", "worldtimebuddy.com", "xe.com",
    "wolframalpha.com", "desmos.com", "symbolab.com",
    "virustotal.com", "haveibeenpwned.com",
    "web.archive.org", "downdetector.com", "isitdownrightnow.com",
    # Misc popular
    "craigslist.org", "nextdoor.com", "meetup.com",
    "eventbrite.com", "change.org", "gofundme.com",
    "patreon.com", "ko-fi.com", "buymeacoffee.com",
    "producthunt.com", "alternativeto.net", "slashdot.org",
    "digg.com", "hackernews.com", "news.ycombinator.com",
    "lobste.rs", "lemmy.world", "mastodon.social",
]
_STATIC_SET = frozenset(STATIC_SITES)


MEDIA_SITES = [
    "youtube.com", "youtu.be", "instagram.com", "facebook.com", "fb.com",
    "tiktok.com", "twitter.com", "x.com", "twitch.tv", "vimeo.com",
    "dailymotion.com", "soundcloud.com", "spotify.com", "music.youtube.com",
    "music.apple.com", "pandora.com", "deezer.com", "tidal.com",
    "netflix.com", "hulu.com", "disneyplus.com", "hbomax.com",
    "primevideo.com", "peacocktv.com", "paramountplus.com",
    "crunchyroll.com", "funimation.com", "bilibili.com",
    "ted.com", "rumble.com", "odysee.com", "bitchute.com",
]
_MEDIA_SET = frozenset(MEDIA_SITES)


def _host_matches(host, site_set):
    """Fast suffix check against a frozenset of domains."""
    parts = host.split(".")
    for i in range(len(parts)):
        if ".".join(parts[i:]) in site_set:
            return True
    return False


CTRL_CLICK_JS = """
    (function() {
        if (window.__minimalia_ctrl_click) return;
        window.__minimalia_ctrl_click = true;
        document.addEventListener('click', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.button === 0) {
                var a = e.target.closest('a');
                if (a && a.href) {
                    e.preventDefault();
                    e.stopPropagation();
                    window.open(a.href, '_blank');
                }
            }
        }, true);
    })();
"""

PAUSE_MEDIA_JS = """
    (function() {
        document.querySelectorAll('video, audio').forEach(function(el) {
            el.pause();
        });
        var iframes = document.querySelectorAll('iframe');
        iframes.forEach(function(f) {
            try { f.contentDocument.querySelectorAll('video, audio').forEach(function(el) { el.pause(); }); } catch(e) {}
        });
    })();
"""


class Browser(QMainWindow):
    def __init__(self, search_engine, experience, disable_ai=False, block_promos=False, custom_url=None, profile=None, enable_history=False):
        super().__init__()
        self.setWindowTitle("Minimalia")
        self.resize(1200, 800)

        self.experience = experience
        self.block_promos = block_promos
        self.profile = profile
        self.enable_history = enable_history

        if search_engine == "__custom__" and custom_url:
            self.search_url = custom_url
            self.home_url = custom_url
            self.logo_js = None
            self.search_results_logo_js = None
            self.disable_ai_js = None
        else:
            engine = SEARCH_ENGINES[search_engine]
            self.search_url = engine["search_url"]
            self.home_url = engine["home_url"]
            logo_uri = get_logo_data_uri()
            self.logo_js = engine["logo_js"].replace("%LOGO%", logo_uri)
            sr_logo = SEARCH_RESULTS_LOGO_JS.get(search_engine, "")
            self.search_results_logo_js = sr_logo.replace("%LOGO%", logo_uri) if sr_logo else None
            if disable_ai:
                self.disable_ai_js = DISABLE_AI_JS.get(search_engine, "")
            else:
                self.disable_ai_js = None

        if experience == "minimalia":
            with open(LOGO_PATH, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            self.home_html = build_home_html(self.search_url, logo_b64, search_engine)

        # --- Tabs ---
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # --- History panel ---
        self._history_panel = QWidget()
        self._history_panel.setFixedWidth(320)
        self._history_panel.setVisible(False)
        hp_layout = QVBoxLayout(self._history_panel)
        hp_layout.setContentsMargins(0, 0, 0, 0)
        hp_layout.setSpacing(0)

        hp_header = QHBoxLayout()
        hp_title = QLabel("  Search History")
        hp_title.setStyleSheet("font-size: 15px; font-weight: bold; padding: 8px 0;")
        hp_header.addWidget(hp_title)
        hp_header.addStretch()
        delete_all_btn = QPushButton("Delete All")
        delete_all_btn.setStyleSheet("color: #d32f2f; border: 1px solid #d32f2f; font-size: 12px; padding: 4px 12px;")
        delete_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_all_btn.clicked.connect(self._confirm_delete_all_history)
        hp_header.addWidget(delete_all_btn)
        hp_layout.addLayout(hp_header)

        self._history_list = QListWidget()
        self._history_list.setStyleSheet(
            "QListWidget { border: none; font-size: 13px; }"
            "QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #e0e0e0; }"
            "QListWidget::item:hover { background: #f0f0f0; }"
        )
        self._history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._history_list.itemClicked.connect(self._on_history_item_clicked)
        hp_layout.addWidget(self._history_list)

        # --- Bookmarks panel ---
        self._bookmarks_panel = QWidget()
        self._bookmarks_panel.setFixedWidth(320)
        self._bookmarks_panel.setVisible(False)
        bp_layout = QVBoxLayout(self._bookmarks_panel)
        bp_layout.setContentsMargins(0, 0, 0, 0)
        bp_layout.setSpacing(0)

        bp_header = QHBoxLayout()
        bp_title = QLabel("  Bookmarks")
        bp_title.setStyleSheet("font-size: 15px; font-weight: bold; padding: 8px 0;")
        bp_header.addWidget(bp_title)
        bp_header.addStretch()
        delete_all_bm_btn = QPushButton("Delete All")
        delete_all_bm_btn.setStyleSheet("color: #d32f2f; border: 1px solid #d32f2f; font-size: 12px; padding: 4px 12px;")
        delete_all_bm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_all_bm_btn.clicked.connect(self._confirm_delete_all_bookmarks)
        bp_header.addWidget(delete_all_bm_btn)
        bp_layout.addLayout(bp_header)

        self._bookmarks_list = QListWidget()
        self._bookmarks_list.setStyleSheet(
            "QListWidget { border: none; font-size: 13px; }"
            "QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #e0e0e0; }"
            "QListWidget::item:hover { background: #f0f0f0; }"
        )
        self._bookmarks_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._bookmarks_list.itemClicked.connect(self._on_bookmark_clicked)
        bp_layout.addWidget(self._bookmarks_list)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._history_panel)
        splitter.addWidget(self._bookmarks_panel)
        splitter.setHandleWidth(0)
        splitter.setChildrenCollapsible(False)

        # --- Navigation toolbar ---
        nav = QToolBar("Navigation")
        nav.setMovable(False)

        back_btn = QAction("←", self)
        back_btn.setToolTip("Back (Alt+Left)")
        back_btn.triggered.connect(lambda: self.current_view().back())
        nav.addAction(back_btn)

        forward_btn = QAction("→", self)
        forward_btn.setToolTip("Forward (Alt+Right)")
        forward_btn.triggered.connect(lambda: self.current_view().forward())
        nav.addAction(forward_btn)

        reload_btn = QAction("⟳", self)
        reload_btn.setToolTip("Reload (Ctrl+R / F5)")
        reload_btn.triggered.connect(lambda: self.current_view().reload())
        nav.addAction(reload_btn)

        home_btn = QAction("⌂", self)
        home_btn.setToolTip("Home")
        home_btn.triggered.connect(self.go_home)
        nav.addAction(home_btn)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL…")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        nav.addWidget(self.url_bar)

        new_tab_btn = QAction("+", self)
        new_tab_btn.setToolTip("New Tab (Ctrl+T)")
        new_tab_btn.triggered.connect(lambda: self.add_tab())
        nav.addAction(new_tab_btn)

        private_btn = QAction("\U0001F512\uFE0E", self)
        private_btn.setToolTip("New Private Tab (Ctrl+Shift+N)")
        private_btn.triggered.connect(self._add_private_tab)
        nav.addAction(private_btn)

        zoom_out_btn = QAction("−", self)
        zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        zoom_out_btn.triggered.connect(self._zoom_out)
        nav.addAction(zoom_out_btn)

        self.zoom_label = QAction("100%", self)
        self.zoom_label.setToolTip("Reset Zoom (Ctrl+0)")
        self.zoom_label.triggered.connect(self._zoom_reset)
        nav.addAction(self.zoom_label)

        zoom_in_btn = QAction("+\u200A", self)
        zoom_in_btn.setToolTip("Zoom In (Ctrl+=)")
        zoom_in_btn.triggered.connect(self._zoom_in)
        nav.addAction(zoom_in_btn)

        if self.enable_history:
            history_btn = QAction("\u29D6", self)
            history_btn.setToolTip("Search History (Ctrl+H)")
            history_btn.triggered.connect(self._toggle_history_panel)
            nav.addAction(history_btn)

        bookmarks_btn = QAction("\u2606", self)
        bookmarks_btn.setToolTip("Bookmarks (Ctrl+B)")
        bookmarks_btn.triggered.connect(self._toggle_bookmarks_panel)
        nav.addAction(bookmarks_btn)

        settings_btn = QAction("\u2699", self)
        settings_btn.setToolTip("Settings")
        settings_btn.triggered.connect(self._open_settings)
        nav.addAction(settings_btn)

        # --- Find bar ---
        self._find_bar = QWidget()
        self._find_bar.setVisible(False)
        self._find_bar.setStyleSheet("background: #2d2d2d; border-bottom: 1px solid #555;")
        fb_layout = QHBoxLayout(self._find_bar)
        fb_layout.setContentsMargins(10, 4, 10, 4)
        fb_layout.setSpacing(6)

        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("Find in page…")
        self._find_input.setFixedWidth(250)
        self._find_input.setStyleSheet("padding: 3px 8px;")
        self._find_input.textChanged.connect(self._find_text)
        self._find_input.returnPressed.connect(self._find_next)
        fb_layout.addWidget(self._find_input)

        prev_btn = QPushButton("▲")
        prev_btn.setFixedSize(28, 28)
        prev_btn.setToolTip("Previous (Shift+Enter)")
        prev_btn.clicked.connect(self._find_prev)
        fb_layout.addWidget(prev_btn)

        next_btn = QPushButton("▼")
        next_btn.setFixedSize(28, 28)
        next_btn.setToolTip("Next (Enter)")
        next_btn.clicked.connect(self._find_next)
        fb_layout.addWidget(next_btn)

        close_find_btn = QPushButton("✕")
        close_find_btn.setFixedSize(28, 28)
        close_find_btn.setStyleSheet("border: none; color: #999;")
        close_find_btn.clicked.connect(self._close_find)
        fb_layout.addWidget(close_find_btn)

        fb_layout.addStretch()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, nav)
        # Insert find bar between toolbar and content
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._find_bar)
        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

        # --- Status bar ---
        self.setStatusBar(QStatusBar())

        # --- Keyboard shortcuts ---
        self._closed_tabs = []

        QShortcut(QKeySequence("Ctrl+T"), self, lambda: self.add_tab())
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+L"), self, self.url_bar.setFocus)
        QShortcut(QKeySequence("Ctrl+R"), self, lambda: self.current_view().reload())
        QShortcut(QKeySequence("F5"), self, lambda: self.current_view().reload())
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, self._reopen_closed_tab)
        QShortcut(QKeySequence("Alt+Left"), self, lambda: self.current_view().back())
        QShortcut(QKeySequence("Alt+Right"), self, lambda: self.current_view().forward())
        QShortcut(QKeySequence("Ctrl+Tab"), self, lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count()))
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % self.tabs.count()))
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, self._add_private_tab)
        QShortcut(QKeySequence("F12"), self, self._toggle_devtools)
        QShortcut(QKeySequence("Ctrl+="), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self._zoom_reset)
        if self.enable_history:
            QShortcut(QKeySequence("Ctrl+H"), self, self._toggle_history_panel)
        QShortcut(QKeySequence("Ctrl+B"), self, self._toggle_bookmarks_panel)
        QShortcut(QKeySequence("Ctrl+F"), self, self._open_find)
        QShortcut(QKeySequence("Escape"), self, self._close_find)
        QShortcut(QKeySequence("Ctrl+P"), self, self._print_page)

        # --- Open first tab ---
        self.add_tab()

    # ---- History ----

    def _toggle_history_panel(self):
        visible = self._history_panel.isVisible()
        if not visible:
            self._refresh_history_panel()
            self._bookmarks_panel.setVisible(False)
        self._history_panel.setVisible(not visible)

    def _refresh_history_panel(self):
        self._history_list.clear()
        history = _load_history()
        seen = set()
        for entry in reversed(history):
            url = entry.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            title = entry.get("title", "")
            display = title if title else url

            from PyQt6.QtCore import QSize
            item_widget = QWidget()
            row = QHBoxLayout(item_widget)
            row.setContentsMargins(10, 6, 6, 6)

            text_label = QLabel(f"<b>{display}</b><br><span style='color:gray;font-size:11px;'>{url}</span>")
            text_label.setWordWrap(True)
            text_label.setTextFormat(Qt.TextFormat.RichText)
            row.addWidget(text_label, 1)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("border: none; color: #999; font-size: 14px;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, u=url: self._delete_history_entry(u))
            row.addWidget(del_btn)

            item = QListWidgetItem()
            item.setSizeHint(QSize(300, 60))
            item.setData(Qt.ItemDataRole.UserRole, url)
            self._history_list.addItem(item)
            self._history_list.setItemWidget(item, item_widget)

    def _on_history_item_clicked(self, item):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.url_bar.setText(url)
            self.navigate_to_url()

    def _delete_history_entry(self, url):
        history = _load_history()
        history = [e for e in history if e.get("url") != url]
        _save_history(history)
        self._refresh_history_panel()

    def _confirm_delete_all_history(self):
        result = QMessageBox.question(
            self, "Delete All History",
            "Are you sure you want to delete your entire search history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            _save_history([])
            self._refresh_history_panel()

    def _record_history(self, view, qurl):
        if getattr(view, '_is_private', False):
            return
        url = qurl.toString()
        if url and url not in ("", "about:blank", "about:home"):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, lambda: _add_history_entry(url, view.title()))

    # ---- Bookmarks ----

    def _toggle_bookmarks_panel(self):
        visible = self._bookmarks_panel.isVisible()
        if not visible:
            self._refresh_bookmarks_panel()
            self._history_panel.setVisible(False)
        self._bookmarks_panel.setVisible(not visible)

    def _refresh_bookmarks_panel(self):
        self._bookmarks_list.clear()
        bookmarks = _load_bookmarks()
        for entry in bookmarks:
            from PyQt6.QtCore import QSize
            url = entry.get("url", "")
            title = entry.get("title", "")
            display = title if title else url

            item_widget = QWidget()
            row = QHBoxLayout(item_widget)
            row.setContentsMargins(10, 6, 6, 6)

            text_label = QLabel(f"<b>{display}</b><br><span style='color:gray;font-size:11px;'>{url}</span>")
            text_label.setWordWrap(True)
            text_label.setTextFormat(Qt.TextFormat.RichText)
            row.addWidget(text_label, 1)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("border: none; color: #999; font-size: 14px;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, u=url: self._delete_bookmark(u))
            row.addWidget(del_btn)

            item = QListWidgetItem()
            item.setSizeHint(QSize(300, 60))
            item.setData(Qt.ItemDataRole.UserRole, url)
            self._bookmarks_list.addItem(item)
            self._bookmarks_list.setItemWidget(item, item_widget)

    def _on_bookmark_clicked(self, item):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.url_bar.setText(url)
            self.navigate_to_url()

    def _delete_bookmark(self, url):
        bookmarks = _load_bookmarks()
        bookmarks = [b for b in bookmarks if b.get("url") != url]
        _save_bookmarks(bookmarks)
        self._refresh_bookmarks_panel()

    def _confirm_delete_all_bookmarks(self):
        result = QMessageBox.question(
            self, "Delete All Bookmarks",
            "Are you sure you want to delete all your bookmarks?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            _save_bookmarks([])
            self._refresh_bookmarks_panel()

    def _bookmark_current_tab(self):
        view = self.current_view()
        url = view.url().toString()
        title = view.title()
        if url and url not in ("", "about:blank", "about:home"):
            _add_bookmark(url, title)
            self.statusBar().showMessage(f"Bookmarked: {title}", 3000)

    def _unbookmark_current_tab(self):
        view = self.current_view()
        url = view.url().toString()
        bookmarks = _load_bookmarks()
        bookmarks = [b for b in bookmarks if b.get("url") != url]
        _save_bookmarks(bookmarks)
        self.statusBar().showMessage("Bookmark removed", 3000)

    # ---- Print ----

    def _print_page(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save as PDF", "", "PDF Files (*.pdf)")
        if path:
            self._pdf_save_path = path
            self.statusBar().showMessage("Generating PDF...")
            self.current_view().page().printToPdf(self._handle_print_pdf)

    def _handle_print_pdf(self, pdf_data):
        path = getattr(self, '_pdf_save_path', None)
        if path and pdf_data:
            with open(path, "wb") as f:
                f.write(pdf_data)
            self.statusBar().showMessage("PDF saved successfully.", 3000)
        else:
            self.statusBar().showMessage("Failed to generate PDF.", 3000)

    # ---- Find in page ----

    def _open_find(self):
        self._find_bar.setVisible(True)
        self._find_input.setFocus()
        self._find_input.selectAll()

    def _close_find(self):
        self._find_bar.setVisible(False)
        self.current_view().findText("")

    def _find_text(self, text):
        self.current_view().findText(text)

    def _find_next(self):
        self.current_view().findText(self._find_input.text())

    def _find_prev(self):
        self.current_view().findText(self._find_input.text(), QWebEnginePage.FindFlag.FindBackward)

    # ---- Settings ----

    def _open_settings(self):
        current = load_settings() or {}
        dlg = SettingsDialog(current, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_settings = dlg.get_settings()
            save_settings(new_settings)
            msg = QMessageBox(self)
            msg.setWindowTitle("Restart Required")
            msg.setText("Settings saved. Restart Minimalia for changes to take effect.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

    # ---- Dev Tools ----

    def _toggle_devtools(self):
        view = self.current_view()
        if hasattr(view, '_devtools') and view._devtools is not None:
            view._devtools.close()
            view._devtools = None
            return
        devtools = QWebEngineView()
        devtools.setWindowTitle("DevTools — Minimalia")
        devtools.resize(900, 600)
        view.page().setDevToolsPage(devtools.page())
        devtools.show()
        view._devtools = devtools

    # ---- Zoom ----

    def _zoom_in(self):
        view = self.current_view()
        view.setZoomFactor(min(view.zoomFactor() + 0.1, 5.0))
        self._update_zoom_label()

    def _zoom_out(self):
        view = self.current_view()
        view.setZoomFactor(max(view.zoomFactor() - 0.1, 0.25))
        self._update_zoom_label()

    def _zoom_reset(self):
        self.current_view().setZoomFactor(1.0)
        self._update_zoom_label()

    def _update_zoom_label(self):
        zoom = self.current_view().zoomFactor()
        self.zoom_label.setText(f"{round(zoom * 100)}%")

    # ---- Tab management ----

    def _load_home(self, view):
        if self.experience == "minimalia":
            view.setHtml(self.home_html, QUrl("about:home"))
        else:
            view.setUrl(QUrl(self.home_url))

    def _add_private_tab(self):
        private_profile = QWebEngineProfile(self)
        view = BrowserTab(self.experience, self.logo_js, self.disable_ai_js, self.search_results_logo_js, self.block_promos, private_profile, self)
        view._is_private = True
        view.setUrl(QUrl(self.home_url))
        view.titleChanged.connect(lambda title, v=view: self.update_tab_title(v, title))
        view.urlChanged.connect(lambda qurl, v=view: self.update_url_bar(v, qurl))
        view.loadProgress.connect(lambda p: self.statusBar().showMessage(f"Loading… {p}%") if p < 100 else self.statusBar().clearMessage())
        view.iconChanged.connect(lambda icon, v=view: self._update_tab_icon(v, icon))
        index = self.tabs.addTab(view, "\U0001F512 Private Tab")
        self.tabs.setCurrentIndex(index)

    def add_tab(self, url=None, skip_home=False):
        view = BrowserTab(self.experience, self.logo_js, self.disable_ai_js, self.search_results_logo_js, self.block_promos, self.profile, self)
        if url:
            view.setUrl(url)
        elif not skip_home:
            self._load_home(view)
        view.titleChanged.connect(lambda title, v=view: self.update_tab_title(v, title))
        view.urlChanged.connect(lambda qurl, v=view: self.update_url_bar(v, qurl))
        view.loadProgress.connect(lambda p: self.statusBar().showMessage(f"Loading… {p}%") if p < 100 else self.statusBar().clearMessage())
        view.iconChanged.connect(lambda icon, v=view: self._update_tab_icon(v, icon))
        if self.enable_history:
            view.urlChanged.connect(lambda qurl, v=view: self._record_history(v, qurl))

        index = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(index)
        return view

    def close_tab(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            url = widget.url()
            if url.isValid() and url.toString() not in ("", "about:blank", "about:home"):
                self._closed_tabs.append(url)
            self.tabs.removeTab(index)
            widget.deleteLater()
        else:
            self.close()

    def _close_current_tab(self):
        self.close_tab(self.tabs.currentIndex())

    def _reopen_closed_tab(self):
        if self._closed_tabs:
            url = self._closed_tabs.pop()
            self.add_tab(url)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def current_view(self):
        return self.tabs.currentWidget()

    def _is_static_site(self, view):
        return _host_matches(view.url().host().lower(), _STATIC_SET)

    def _is_media_site(self, view):
        return _host_matches(view.url().host().lower(), _MEDIA_SET)

    def _pause_and_freeze(self, view):
        view.page().runJavaScript(PAUSE_MEDIA_JS)
        view.page().setLifecycleState(QWebEnginePage.LifecycleState.Frozen)

    def on_tab_changed(self, index):
        view = self.tabs.widget(index)
        if view:
            self.url_bar.setText(view.url().toString())
            self.setWindowTitle("Minimalia")
            self._update_zoom_label()
            view.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
        # Suspend background tabs to save memory
        for i in range(self.tabs.count()):
            other = self.tabs.widget(i)
            if other and other != view:
                if self._is_media_site(other):
                    self._pause_and_freeze(other)
                elif not self._is_tab_active(other):
                    if self._is_static_site(other):
                        other.page().setLifecycleState(QWebEnginePage.LifecycleState.Discarded)
                    else:
                        other.page().setLifecycleState(QWebEnginePage.LifecycleState.Frozen)

    def update_tab_title(self, view, title):
        index = self.tabs.indexOf(view)
        if index >= 0:
            short = title[:25] + "…" if len(title) > 25 else title
            if getattr(view, '_is_private', False):
                short = "\U0001F512 " + short
            self.tabs.setTabText(index, short)
        if view == self.current_view():
            self.setWindowTitle("Minimalia")

    def _update_tab_icon(self, view, icon):
        index = self.tabs.indexOf(view)
        if index < 0:
            return
        if getattr(view, '_is_private', False):
            return
        if not icon.isNull():
            self.tabs.setTabIcon(index, icon)

    def update_url_bar(self, view, qurl):
        if view == self.current_view():
            self.url_bar.setText(qurl.toString())

    # ---- Navigation ----

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return
        if "." not in text and " " not in text:
            if '{}' in self.search_url:
                text = self.search_url.format(text)
            else:
                text = f"https://www.google.com/search?q={text}"
        elif not text.startswith(("http://", "https://")):
            text = "https://" + text
        self.current_view().setUrl(QUrl(text))

    def go_home(self):
        self._load_home(self.current_view())

    def _is_tab_active(self, view):
        """Check if a tab is doing something (loading, audio, or active JS)."""
        page = view.page()
        if page.isLoading():
            return True
        if page.recentlyAudible():
            return True
        return False

    def changeEvent(self, event):
        super().changeEvent(event)
        if not hasattr(self, 'tabs'):
            return
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                for i in range(self.tabs.count()):
                    view = self.tabs.widget(i)
                    if view:
                        if self._is_media_site(view):
                            self._pause_and_freeze(view)
                        elif not self._is_tab_active(view):
                            if self._is_static_site(view):
                                view.page().setLifecycleState(QWebEnginePage.LifecycleState.Discarded)
                            else:
                                view.page().setLifecycleState(QWebEnginePage.LifecycleState.Frozen)
            else:
                for i in range(self.tabs.count()):
                    view = self.tabs.widget(i)
                    if view:
                        view.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)


if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Minimalia.Minimalia.1")

    # Chromium flags
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--disable-background-networking "
        "--disable-default-apps "
        "--disable-extensions "
        "--disable-sync "
        "--disable-translate "
        "--no-first-run "
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Minimalia")
    app.setWindowIcon(QIcon(os.path.join(BUNDLE_DIR, "assets", "ui", "minimalia_appicon.png")))

    profile = QWebEngineProfile("Minimalia", app)
    default_ua = profile.httpUserAgent()
    clean_ua = default_ua.replace("QtWebEngine/6.11.0 ", "")
    profile.setPersistentStoragePath(os.path.join(DATA_DIR, "browser_data"))
    profile.setCachePath(os.path.join(DATA_DIR, "browser_cache"))
    # Cookie policy set after settings are loaded
    profile.setHttpCacheMaximumSize(50 * 1024 * 1024)  # 50 MB cache limit

    from PyQt6.QtWidgets import QProgressBar

    class DownloadDialog(QDialog):
        def __init__(self, download, parent=None):
            super().__init__(parent)
            self.download = download
            self.setWindowTitle("Downloading")
            self.setFixedSize(350, 100)
            layout = QVBoxLayout(self)

            self._label = QLabel("Downloading...")
            layout.addWidget(self._label)

            self._progress = QProgressBar()
            self._progress.setRange(0, 100)
            layout.addWidget(self._progress)

            self._size_label = QLabel("0 B / 0 B")
            self._size_label.setStyleSheet("color: gray; font-size: 11px;")
            layout.addWidget(self._size_label)

            download.receivedBytesChanged.connect(self._update)
            download.isFinishedChanged.connect(self._finished)

        def _fmt(self, b):
            if b < 1024: return f"{b} B"
            if b < 1024**2: return f"{b/1024:.1f} KB"
            if b < 1024**3: return f"{b/1024**2:.1f} MB"
            return f"{b/1024**3:.2f} GB"

        def _update(self):
            recv = self.download.receivedBytes()
            total = self.download.totalBytes()
            if total > 0:
                self._progress.setValue(int(recv * 100 / total))
                self._size_label.setText(f"{self._fmt(recv)} / {self._fmt(total)}")
            else:
                self._progress.setRange(0, 0)
                self._size_label.setText(f"{self._fmt(recv)}")

        def _finished(self):
            if self.download.isFinished():
                self._progress.setValue(100)
                self._label.setText("Finished downloading")
                self._size_label.setText("Find the downloaded file in your Downloads folder.")
                self.setWindowTitle("Download Complete")

    def handle_download(download):
        pending = getattr(app, '_pending_save_path', None)
        if pending:
            download.setDownloadDirectory(os.path.dirname(pending))
            download.setDownloadFileName(os.path.basename(pending))
            app._pending_save_path = None
        download.accept()
        dlg = DownloadDialog(download)
        dlg.show()
        app._download_dialogs = getattr(app, '_download_dialogs', [])
        app._download_dialogs.append(dlg)

    profile.downloadRequested.connect(handle_download)

    settings = load_settings()
    if not (settings and "search_engine" in settings and "experience" in settings):
        dialog = SettingsDialog({}, first_run=True)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        settings = dialog.get_settings()
        save_settings(settings)

    search_engine = settings["search_engine"]
    experience = settings["experience"]
    disable_ai = settings.get("disable_ai", False)
    block_promos = settings.get("block_promos", False)
    custom_url = settings.get("custom_url", None)
    enable_adblock = settings.get("enable_adblock", False)
    enable_history = settings.get("enable_history", False)
    save_cookies = settings.get("save_cookies", False)




    if save_cookies:
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
    else:
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

    profile.setHttpUserAgent(clean_ua)

    if enable_adblock:
        adblock_engine = _load_adblock_engine()
        if adblock_engine:
            interceptor = AdBlockInterceptor(adblock_engine, profile)
            profile.setUrlRequestInterceptor(interceptor)

    window = Browser(search_engine, experience, disable_ai, block_promos, custom_url, profile, enable_history)
    window.showMaximized()
    sys.exit(app.exec())
