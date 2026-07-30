#!/usr/bin/env python3
"""
WiX hygiene for RustDesk MSI packaging.

RustDesk currently builds with WiX Toolset 4.x.
ICE60's File/@Language fix is WiX 3 only and causes WIX0004 on WiX 4,
so ICE60 is skipped when WiX 4 sources are detected.
"""

import glob
import os
import re
import sys
from pathlib import Path


def is_wix4(content: str) -> bool:
    return (
        "http://wixtoolset.org/schemas/v4/wxs" in content
        or "WixToolset.Sdk" in content
        or re.search(r'Wix\s+xmlns=.*wixtoolset\.org/schemas/v4', content) is not None
    )


def fix_ice60(file_path: str) -> bool:
    """WiX 3 only: add Language=\"*\" to non-font File elements."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if is_wix4(content):
        print(f"Skipping ICE60 on WiX 4 file: {file_path}")
        return False

    original_content = content

    def replace_file_tag(match):
        full_tag = match.group(0)
        if "Language=" in full_tag:
            return full_tag
        if any(x in full_tag.lower() for x in [".ttf", ".otf", "fontid", "font"]):
            return full_tag
        if "/>" in full_tag:
            return full_tag.replace("/>", ' Language="*" />')
        if full_tag.endswith(">"):
            return full_tag[:-1] + ' Language="*">'
        return full_tag

    pattern = r'<File\s+[^>]*(?:Id="[^"]*")[^>]*(?:/>|>)'
    content = re.sub(pattern, replace_file_tag, content)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed ICE60 warnings in {file_path}")
        return True
    return False


def fix_ice84(file_path: str) -> bool:
    """Remove Condition from InstallValidate action when present."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    content = re.sub(
        r'(<Action\s+Id="InstallValidate"[^>]*?)\s+Condition="[^"]*"([^>]*?>)',
        r"\1\2",
        content,
    )
    content = re.sub(
        r'(<Custom\s+Action="InstallValidate"[^>]*?)\s+Condition="[^"]*"([^>]*?/?>)',
        r"\1\2",
        content,
    )
    content = re.sub(r'(InstallValidate[^>]*?)\s+Condition="[^"]*"', r"\1", content)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed ICE84 warnings in {file_path}")
        return True
    return False


def fix_ice61(file_path: str) -> bool:
    """Ensure Upgrade Maximum is below current product version when equal."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    product_version_match = re.search(r'<Package[^>]*Version="([^"]*)"', content)
    if not product_version_match:
        product_version_match = re.search(r'<Product[^>]*Version="([^"]*)"', content)
    if not product_version_match:
        product_version_match = re.search(r'Version="([^"]*)"', content)

    current_version = product_version_match.group(1) if product_version_match else None
    if current_version:
        print(f"Found product version: {current_version}")

    def fix_maximum_version(match):
        max_version = match.group(1)
        if not (current_version and max_version == current_version):
            return match.group(0)
        parts = max_version.split(".")
        if len(parts) >= 4:
            try:
                build_num = int(parts[-1])
                if build_num > 0:
                    parts[-1] = str(build_num - 1)
                elif len(parts) >= 3:
                    rev_num = int(parts[-2])
                    if rev_num > 0:
                        parts[-2] = str(rev_num - 1)
                        parts[-1] = "9999"
            except ValueError:
                return match.group(0)
            new_version = ".".join(parts)
            print(
                f"Decrementing Maximum version from {max_version} to {new_version} "
                f"(current: {current_version})"
            )
            return f'Maximum="{new_version}"'
        return match.group(0)

    content = re.sub(r'Maximum="([^"]*)"', fix_maximum_version, content)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed ICE61 warnings in {file_path}")
        return True
    return False


def find_wix_files(directory: str):
    wix_files = []
    for ext in ["*.wxs", "*.wxi"]:
        wix_files.extend(glob.glob(os.path.join(directory, "**", ext), recursive=True))
    return wix_files


def main():
    msi_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    msi_path = Path(msi_dir)
    if not msi_path.exists():
        print(f"Directory {msi_dir} does not exist")
        return 1

    wix_files = find_wix_files(str(msi_path))
    if not wix_files:
        print(f"No WiX files found in {msi_dir}")
        return 0

    fixed = False
    for wix_file in wix_files:
        try:
            if fix_ice60(wix_file):
                fixed = True
            if fix_ice84(wix_file):
                fixed = True
            if fix_ice61(wix_file):
                fixed = True
        except Exception as e:
            print(f"Error processing {wix_file}: {e}", file=sys.stderr)

    if fixed:
        print("WiX warnings fixed successfully")
    else:
        print("No WiX warnings to fix (or WiX 4; ICE60 skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
