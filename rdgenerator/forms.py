
import json
import os
import re
import time
import urllib.request

_VERSION_CACHE = "/tmp/rdgen-rustdesk-versions.json"
_VERSION_TTL = 600
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_FALLBACK_VERSIONS = [
    ("master", "nightly"),
    ("1.5.0", "1.5.0"),
    ("1.4.9", "1.4.9"),
    ("1.4.8", "1.4.8"),
    ("1.4.7", "1.4.7"),
    ("1.4.6", "1.4.6"),
    ("1.4.5", "1.4.5"),
    ("1.4.4", "1.4.4"),
    ("1.4.3", "1.4.3"),
    ("1.4.2", "1.4.2"),
    ("1.4.1", "1.4.1"),
    ("1.4.0", "1.4.0"),
]

def _version_key(tag):
    return tuple(int(part) for part in tag.split("."))

def _read_version_cache():
    try:
        with open(_VERSION_CACHE) as fh:
            data = json.load(fh)
        if isinstance(data.get("choices"), list) and data["choices"]:
            return data
    except Exception:
        return None
    return None

def _write_version_cache(choices, fetched):
    tmp = _VERSION_CACHE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"fetched": fetched, "choices": choices}, fh)
    os.replace(tmp, _VERSION_CACHE)

def rustdesk_version_choices():
    now = time.time()
    cached = _read_version_cache()
    if cached and now - cached["fetched"] < _VERSION_TTL:
        return cached["choices"]
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/rustdesk/rustdesk/releases?per_page=100",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "rdgen",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            releases = json.load(resp)
        tags = []
        for release in releases:
            if release.get("draft") or release.get("prerelease"):
                continue
            tag = release.get("tag_name") or ""
            if _VERSION_RE.match(tag) and _version_key(tag) >= (1, 4, 0):
                tags.append(tag)
        tags = sorted(set(tags), key=_version_key, reverse=True)
        if not tags:
            raise RuntimeError("no stable releases")
        choices = [("master", "nightly")] + [(tag, tag) for tag in tags]
        _write_version_cache(choices, now)
        return choices
    except Exception as exc:
        print(f"rustdesk version list fallback: {exc}")
        if cached:
            return cached["choices"]
        return list(_FALLBACK_VERSIONS)

from django import forms
from PIL import Image

class GenerateForm(forms.Form):
    sh_secret_field = forms.CharField(required=False)
    #Platform
    platform = forms.ChoiceField(choices=[('windows','Windows 64Bit'),('windows-x86','Windows 32Bit'),('linux','Linux'),('android','Android'),('macos','macOS')], initial='windows')
    version = forms.ChoiceField(choices=_FALLBACK_VERSIONS, initial="1.5.0")
    help_text="'master' is the development version (nightly build) with the latest features but may be less stable"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = rustdesk_version_choices()
        self.fields["version"].choices = choices
        if not self.is_bound:
            self.fields["version"].initial = next(
                value for value, _label in choices if value != "master"
            )

    delayFix = forms.BooleanField(initial=True, required=False)

    #General
    exename = forms.CharField(label="Name for EXE file", required=True)
    appname = forms.CharField(label="Custom App Name", required=False)
    direction = forms.ChoiceField(widget=forms.RadioSelect, choices=[
        ('incoming', 'Incoming Only'),
        ('outgoing', 'Outgoing Only'),
        ('both', 'Bidirectional')
    ], initial='both')
    installation = forms.ChoiceField(label="Disable Installation", choices=[
        ('installationY', 'No, enable installation'),
        ('installationN', 'Yes, DISABLE installation')
    ], initial='installationY')
    settings = forms.ChoiceField(label="Disable Settings", choices=[
        ('settingsY', 'No, enable settings'),
        ('settingsN', 'Yes, DISABLE settings')
    ], initial='settingsY')
    androidappid = forms.CharField(label="Custom Android App ID (replaces 'com.carriez.flutter_hbb')", required=False)

    #Custom Server
    serverIP = forms.CharField(label="Host", required=False)
    apiServer = forms.CharField(label="API Server", required=False)
    key = forms.CharField(label="Key", required=False)
    urlLink = forms.CharField(label="Custom URL for links", required=False)
    downloadLink = forms.CharField(label="Custom URL for downloading new versions", required=False)
    compname = forms.CharField(label="Company name",required=False)

    #Visual
    iconfile = forms.FileField(label="Custom App Icon (in .png format)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    logofile = forms.FileField(label="Custom App Logo (in .png format)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    privacyfile = forms.FileField(label="Custom privacy screen (in .png format)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    iconbase64 = forms.CharField(required=False)
    logobase64 = forms.CharField(required=False)
    privacybase64 = forms.CharField(required=False)
    theme = forms.ChoiceField(choices=[
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'Follow System')
    ], initial='system')
    themeDorO = forms.ChoiceField(choices=[('default', 'Default'),('override', 'Override')], initial='default')

    #Security
    passApproveMode = forms.ChoiceField(choices=[('password','Accept sessions via password'),('click','Accept sessions via click'),('password-click','Accepts sessions via both')],initial='password-click')
    permanentPassword = forms.CharField(widget=forms.PasswordInput(), required=False)
    #runasadmin = forms.ChoiceField(choices=[('false','No'),('true','Yes')], initial='false')
    denyLan = forms.BooleanField(initial=False, required=False)
    enableDirectIP = forms.BooleanField(initial=False, required=False)
    #ipWhitelist = forms.BooleanField(initial=False, required=False)
    autoClose = forms.BooleanField(initial=False, required=False)

    #Permissions
    permissionsDorO = forms.ChoiceField(choices=[('default', 'Default'),('override', 'Override')], initial='default')
    permissionsType = forms.ChoiceField(choices=[('custom', 'Custom'),('full', 'Full Access'),('view','Screen share')], initial='custom')
    enableKeyboard =  forms.BooleanField(initial=True, required=False)
    enableClipboard = forms.BooleanField(initial=True, required=False)
    enableFileTransfer = forms.BooleanField(initial=True, required=False)
    enableAudio = forms.BooleanField(initial=True, required=False)
    enableTCP = forms.BooleanField(initial=True, required=False)
    enableRemoteRestart = forms.BooleanField(initial=True, required=False)
    enableRecording = forms.BooleanField(initial=True, required=False)
    enableBlockingInput = forms.BooleanField(initial=True, required=False)
    enableRemoteModi = forms.BooleanField(initial=False, required=False)
    hidecm = forms.BooleanField(initial=False, required=False)
    enablePrinter = forms.BooleanField(initial=True, required=False)
    enableCamera = forms.BooleanField(initial=True, required=False)
    enableTerminal = forms.BooleanField(initial=True, required=False)

    #Other
    removeWallpaper = forms.BooleanField(initial=True, required=False)

    defaultManual = forms.CharField(widget=forms.Textarea, required=False)
    overrideManual = forms.CharField(widget=forms.Textarea, required=False)

    #custom added features
    xOffline = forms.BooleanField(initial=False, required=False)
    removeNewVersionNotif = forms.BooleanField(initial=False, required=False)

    def clean_iconfile(self):
        print("checking icon")
        image = self.cleaned_data['iconfile']
        if image:
            try:
                # Open the image using Pillow
                img = Image.open(image)

                # Check if the image is a PNG (optional, but good practice)
                if img.format != 'PNG':
                    raise forms.ValidationError("Only PNG images are allowed.")

                # Get image dimensions
                width, height = img.size

                # Check for square dimensions
                if width != height:
                    raise forms.ValidationError("Custom App Icon dimensions must be square.")
                
                return image
            except OSError:  # Handle cases where the uploaded file is not a valid image
                raise forms.ValidationError("Invalid icon file.")
            except Exception as e: # Catch any other image processing errors
                raise forms.ValidationError(f"Error processing icon: {e}")
