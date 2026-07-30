#!/usr/bin/env python3
"""
Fix WiX ICE warnings:
- ICE60: Add Language attribute to File elements that are not fonts
- ICE84: Remove condition from InstallValidate action
- ICE61: Fix version comparison issue
"""

import os
import re
import sys
import glob
from pathlib import Path

def fix_ice60(file_path):
    """Fix ICE60: Add Language="*" to File elements that don't have it and are not fonts."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to match File elements without Language attribute
    def replace_file_tag(match):
        full_tag = match.group(0)
        # Skip if already has Language
        if 'Language=' in full_tag:
            return full_tag
        
        # Skip font files by extension or Font attribute
        if any(x in full_tag.lower() for x in ['.ttf', '.otf', 'fontid', 'font']):
            return full_tag
        
        # Add Language="*" before closing tag
        if '/>' in full_tag:
            return full_tag.replace('/>', ' Language="*" />')
        elif full_tag.endswith('>'):
            return full_tag[:-1] + ' Language="*">'
        return full_tag
    
    # Match File tags - more comprehensive pattern
    pattern = r'<File\s+[^>]*(?:Id="[^"]*")[^>]*(?:/>|>)'
    content = re.sub(pattern, replace_file_tag, content)
    
    # Also handle multi-line File tags
    lines = content.split('\n')
    fixed_lines = []
    in_file_tag = False
    file_tag_lines = []
    
    for line in lines:
        if '<File' in line and 'Language=' not in line:
            # Check if it's a complete tag on one line
            if '/>' in line or (line.count('<') == line.count('>')):
                # Single line File tag
                if '.ttf' not in line.lower() and '.otf' not in line.lower() and 'font' not in line.lower():
                    if '/>' in line:
                        line = line.replace('/>', ' Language="*" />')
                    elif '>' in line:
                        line = line.rstrip()[:-1] + ' Language="*">'
                fixed_lines.append(line)
            else:
                # Multi-line File tag - collect lines
                in_file_tag = True
                file_tag_lines = [line]
        elif in_file_tag:
            file_tag_lines.append(line)
            if '>' in line and not line.strip().startswith('<!--'):
                # End of File tag
                file_tag = '\n'.join(file_tag_lines)
                if 'Language=' not in file_tag:
                    if '.ttf' not in file_tag.lower() and '.otf' not in file_tag.lower() and 'font' not in file_tag.lower():
                        # Add Language before closing >
                        file_tag = file_tag.rstrip()[:-1] + ' Language="*">'
                fixed_lines.extend(file_tag.split('\n'))
                in_file_tag = False
                file_tag_lines = []
        else:
            fixed_lines.append(line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    if fixed_content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"Fixed ICE60 warnings in {file_path}")
        return True
    return False

def fix_ice84(file_path):
    """Fix ICE84: Remove condition from InstallValidate action or make it required."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to find InstallValidate with condition in various formats
    # Remove Condition attribute from InstallValidate actions
    
    # Pattern 1: <Action Id="InstallValidate" ... Condition="..." ...>
    pattern1 = r'(<Action\s+Id="InstallValidate"[^>]*?)\s+Condition="[^"]*"([^>]*?>)'
    content = re.sub(pattern1, r'\1\2', content)
    
    # Pattern 2: In InstallExecuteSequence table rows
    # <Custom Action="InstallValidate" ... Condition="..." .../>
    pattern2 = r'(<Custom\s+Action="InstallValidate"[^>]*?)\s+Condition="[^"]*"([^>]*?/?>)'
    content = re.sub(pattern2, r'\1\2', content)
    
    # Pattern 3: Any InstallValidate with condition
    pattern3 = r'(InstallValidate[^>]*?)\s+Condition="[^"]*"'
    content = re.sub(pattern3, r'\1', content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed ICE84 warnings in {file_path}")
        return True
    return False

def fix_ice61(file_path):
    """Fix ICE61: Ensure Maximum version is less than current product version."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Find current product version first
    product_version_match = re.search(r'Version="([^"]*)"', content)
    if not product_version_match:
        # Try Product tag
        product_version_match = re.search(r'<Product[^>]*Version="([^"]*)"', content)
    
    current_version = None
    if product_version_match:
        current_version = product_version_match.group(1)
        print(f"Found product version: {current_version}")
    
    # Find UpgradeVersion with Maximum attribute
    # ICE61: Maximum version should be less than current version
    # If they're equal, we need to make Maximum less
    
    def fix_maximum_version(match):
        max_version = match.group(1)
        if current_version and max_version == current_version:
            # Decrement the last component (build number)
            parts = max_version.split('.')
            if len(parts) >= 4:
                try:
                    build_num = int(parts[-1])
                    if build_num > 0:
                        parts[-1] = str(build_num - 1)
                    else:
                        # If build is 0, decrement revision
                        if len(parts) >= 3:
                            rev_num = int(parts[-2])
                            if rev_num > 0:
                                parts[-2] = str(rev_num - 1)
                                parts[-1] = '9999'  # Set build to high number
                except ValueError:
                    pass
                new_version = '.'.join(parts)
                print(f"Decrementing Maximum version from {max_version} to {new_version} (current: {current_version})")
                return f'Maximum="{new_version}"'
        return match.group(0)
    
    # Look for Maximum attribute in UpgradeVersion or similar
    pattern = r'Maximum="([^"]*)"'
    content = re.sub(pattern, fix_maximum_version, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed ICE61 warnings in {file_path}")
        return True
    return False

def find_wix_files(directory):
    """Find all .wxs and .wxi files in directory."""
    wix_files = []
    for ext in ['*.wxs', '*.wxi']:
        wix_files.extend(glob.glob(os.path.join(directory, '**', ext), recursive=True))
    return wix_files

def main():
    if len(sys.argv) > 1:
        msi_dir = sys.argv[1]
    else:
        msi_dir = '.'
    
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
        print("No WiX warnings to fix (or files already correct)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
